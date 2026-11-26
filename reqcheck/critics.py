from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from pydantic import BaseModel

from .findings import Evidence, Finding
from .llm import Client, LLMError
from .loader import Source
from .segmenter import Requirement


class Issue(BaseModel):
    criterion: str
    severity: Literal["critical", "major", "minor"]
    evidence: list[Evidence]
    explanation: str
    fix: str
    question: str


class Review(BaseModel):
    findings: list[Issue]


INSTRUCTIONS = (
    "Пиши по-русски. evidence: один или несколько объектов с locator из входа и дословной "
    "непрерывной цитатой quote из строки с этим locator. Для противоречия приведи обе стороны. "
    "Один дефект на запись, без повторов. Объясни, какие два результата возможны или почему "
    "невозможно выполнить проверку. fix — конкретная правка с явными условиями, без выдуманных решений. "
    "question — один вопрос к владельцу решения. critical — блокирует разработку или проверку, "
    "major — меняет поведение или покрытие, minor — мешает чтению или сопровождению. "
    "Если дефектов нет, верни пустой список."
)

LENSES = {
    "Согласованность": "Проверь согласованность и осуществимость набора. Ищи конфликты правил, примеров, "
                      "дат и границ, последовательностей событий, условий и терминов в разных разделах.",
    "Полнота сценариев": "Проверь полноту, понятность и пригодность для валидации. Ищи отсутствующие "
                         "ветви, переходы состояния, граничные случаи, альтернативы и критерии приёмки.",
    "Контракты": "Проверь интерфейсы и данные: операции чтения и записи, методы, типы, единицы, "
                 "коды результата, ошибки, повторную доставку, авторизацию и обработку персональных данных.",
    "Эксплуатация": "Проверь измеримость бизнес-целей, эксплуатационные свойства, безопасность, "
                    "предельную нагрузку, измерение задержки, локализацию, отказ и восстановление.",
    "Трассировка": "Проверь ранжирование, правильность, модифицируемость и трассируемость. "
                   "Ищи дублирование правил, расхождения имён компонентов, пропуски версий, "
                   "согласований, связей с тестами и обязательных документов, навязанный дизайн.",
}


def review(sources: list[Source], requirements: list[Requirement], client: Client,
           answers: list[dict] | None = None) -> tuple[list[Finding], list[str]]:
    source_data = [source.model_dump() for source in sources]
    jobs = [(name, "set", prompt, {"source": source_data, "answers": answers or []})
            for name, prompt in LENSES.items()]
    for start in range(0, len(requirements), 8):
        batch = requirements[start:start + 8]
        jobs.append((
            f"Требования {batch[0].id}–{batch[-1].id}", "requirement",
            "Проверь каждое требование по ISO 29148 §5.2.5: необходимость, уместность, "
            "однозначность, полнота, единичность, осуществимость, проверяемость, "
            "правильность и соответствие форме. Ищи навязанный способ реализации. "
            "Учитывай соседние атомарные фрагменты одной строки.",
            {"requirements": [item.model_dump() for item in batch], "answers": answers or []},
        ))

    def run(job):
        _, scope, prompt, data = job
        try:
            result = client.ask(prompt + "\n" + INSTRUCTIONS, data, Review)
        except LLMError:
            return None
        findings = []
        for issue in result.findings:
            if not issue.evidence:
                continue
            refs = {e.locator for e in issue.evidence}
            ids = [item.id for item in requirements if item.source.locator in refs]
            findings.append(Finding(
                **issue.model_dump(), code="model-review", requirements=ids,
                scope=scope if ids else "set", agent="critic",
            ))
        return findings

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run, jobs))
    return (
        [finding for result in results if result for finding in result],
        [job[0] for job, result in zip(jobs, results) if result is None],
    )
