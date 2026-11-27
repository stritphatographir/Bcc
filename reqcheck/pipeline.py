import hashlib
import subprocess
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit

from pydantic import BaseModel, Field

from .api_contract import review_api
from .clarifier import Answer, Question, finding_id, questions
from .config import Settings
from .critics import review
from .findings import Finding
from .fintech import review_fintech
from .linter import lint
from .llm import Client, LLMError
from .loader import load, unread_pages
from .qa import QA, build_qa
from .quality import Quality, score_quality
from .segmenter import Requirement, segment
from .simulator import Simulation, simulate
from .structure import review_structure
from .trace import TraceEvent, TraceLog
from .verifier import verify


class ModelRun(BaseModel):
    provider: str
    model: str
    calls: int
    responses: int  # Successful live responses; excludes cache hits.
    cache_hits: int


class Passport(BaseModel):
    document: str
    sha256: str
    model: str
    provider: str
    version: str
    started: datetime
    finished: datetime
    calls: int
    cache_hits: int
    responses: int = 0
    llm_error: str = ""
    switch_reason: str = ""
    model_runs: list[ModelRun] = Field(default_factory=list)
    dropped: int
    failed_agents: list[str]
    unread_pages: list[int] = Field(default_factory=list)
    mode: str


class Analysis(BaseModel):
    passport: Passport
    requirements: list[Requirement]
    findings: list[Finding]
    questions: list[Question]
    answers: list[Answer] = Field(default_factory=list)
    follow_up: list[Finding] = Field(default_factory=list)
    simulation: Simulation = Field(default_factory=Simulation)
    qa: QA = Field(default_factory=QA)
    quality: Quality = Field(default_factory=Quality)
    trace: list[TraceEvent] = Field(default_factory=list)


def _version() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parent,
            text=True, stderr=subprocess.DEVNULL, timeout=3,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "версия из Git недоступна"


def analyze(path: Path, settings: Settings, *,
            progress: Callable[[str], None] = lambda _: None,
            collect: Callable[[list[Question]], list[Answer]] = lambda _: []) -> Analysis:
    started = datetime.now(timezone.utc)
    version = _version()
    trace = TraceLog()
    active_stage = None
    stage_start = None

    def step(name, **counts):
        nonlocal active_stage, stage_start
        if active_stage:
            trace.add("stage", active_stage, "ok", started=stage_start, outputs=counts)
        active_stage, stage_start = name, perf_counter()
        trace.add("stage", name, "start")
        progress(name)

    step("Чтение документа")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    sources = load(path)
    step("Выделение требований", blocks=len(sources))
    failed = []
    with Client(settings) as client:
        client.trace = trace
        client.on_switch = progress
        requirements, incomplete = segment(sources, client)
        if incomplete:
            failed.append("Сегментация")
        step("Проверка правил", requirements=len(requirements))
        rules = (lint(sources, requirements) + review_fintech(sources, requirements)
                 + review_api(sources, requirements) + review_structure(sources, requirements))
        step("Проверка требований и связей", findings=len(rules))
        issues, failed_reviews = review(sources, requirements, client, votes=settings.critic_votes)
        failed.extend(failed_reviews)
        simulation = Simulation()
        step("Моделирование сценариев", findings=len(issues), failed=len(failed_reviews))
        try:
            simulation, scenario_issues = simulate(sources, requirements, client, issues)
        except LLMError:
            failed.append("Моделирование сценариев")
        else:
            issues.extend(scenario_issues)
        step("Сверка цитат", rules=len(simulation.rules), scenarios=len(simulation.scenarios))
        findings, dropped = verify(rules + issues, sources)
        step("Уточняющие вопросы", findings=len(findings), dropped=dropped)
        items = questions(findings)
        answers = collect(items)
        follow_up = []
        if answers:
            step("Повторная проверка после уточнений", questions=len(items), answers=len(answers))
            refs = {ref for answer in answers for ref in answer.question.finding_ids}
            affected = [f for i, f in enumerate(findings) if finding_id(i) in refs]
            ids = {ref for f in affected for ref in f.requirements}
            locators = {e.locator for f in affected for e in f.evidence}
            sections = {s.section for s in sources if s.locator in locators}
            follow_up, failed_again = review(
                [s for s in sources if s.section in sections],
                [r for r in requirements if r.id in ids], client,
                [a.model_dump() for a in answers],
                votes=settings.critic_votes,
            )
            failed.extend(f"После уточнений: {name}" for name in failed_again)
            follow_up, count = verify(follow_up, sources)
            dropped += count

    if client.responses == 0:
        mode = "Только правила"
    else:
        mode = "Частичная проверка" if failed else "Полная проверка"
    passport = Passport(
        document=path.name, sha256=digest, model=settings.model,
        provider=urlsplit(settings.base_url).hostname or "", version=version,
        started=started, finished=datetime.now(timezone.utc), calls=client.calls,
        cache_hits=client.hits, responses=client.responses - client.hits,
        llm_error=client.offline or "", dropped=dropped, failed_agents=failed, mode=mode,
        switch_reason=getattr(client, "switch_reason", ""), unread_pages=unread_pages(path),
        model_runs=getattr(client, "model_runs", []),
    )
    qa = build_qa(requirements, findings, simulation, sources, follow_up)
    quality = score_quality(requirements, findings, failed)
    step("Подготовка отчёта", findings=len(findings), questions=len(items), answers=len(answers))
    return Analysis(passport=passport, requirements=requirements, findings=findings,
                    questions=items, answers=answers, follow_up=follow_up, simulation=simulation, qa=qa,
                    quality=quality, trace=trace.events)
