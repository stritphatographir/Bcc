import hashlib
import subprocess
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
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
from .loader import load
from .qa import QA, build_qa
from .segmenter import Requirement, segment
from .simulator import Simulation, simulate
from .verifier import verify


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
    dropped: int
    failed_agents: list[str]
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
    progress("Чтение документа")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    sources = load(path)
    progress("Выделение требований")
    failed = []
    with Client(settings) as client:
        requirements, incomplete = segment(sources, client)
        if incomplete:
            failed.append("Сегментация")
        progress("Проверка правил")
        rules = lint(sources, requirements) + review_fintech(sources, requirements) + review_api(sources, requirements)
        progress("Проверка требований и связей")
        issues, failed_reviews = review(sources, requirements, client, votes=settings.critic_votes)
        failed.extend(failed_reviews)
        simulation = Simulation()
        progress("Моделирование сценариев")
        try:
            simulation, scenario_issues = simulate(sources, requirements, client)
        except LLMError:
            failed.append("Моделирование сценариев")
        else:
            issues.extend(scenario_issues)
        progress("Сверка цитат")
        findings, dropped = verify(rules + issues, sources)
        progress("Уточняющие вопросы")
        items = questions(findings)
        answers = collect(items)
        follow_up = []
        if answers:
            progress("Повторная проверка после уточнений")
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
        provider=urlsplit(settings.base_url).hostname or "", version=_version(),
        started=started, finished=datetime.now(timezone.utc), calls=client.calls,
        cache_hits=client.hits, dropped=dropped, failed_agents=failed, mode=mode,
    )
    qa = build_qa(requirements, findings, simulation, sources, follow_up)
    return Analysis(passport=passport, requirements=requirements, findings=findings,
                    questions=items, answers=answers, follow_up=follow_up, simulation=simulation, qa=qa)
