import re
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from pydantic import BaseModel

from .findings import Evidence, Finding
from .llm import Client, LLMError
from .loader import Source
from .segmenter import Requirement
from .simulator import behavior_sources


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


def vote(ballots: list[list[Finding] | None]) -> list[Finding]:
    buckets = {}
    for ballot in ballots:
        seen = set()
        for finding in ballot or []:
            key = (
                " ".join(finding.criterion.casefold().split()),
                tuple(sorted((e.locator, " ".join(e.quote.split())) for e in finding.evidence)),
            )
            if key in seen:
                continue
            seen.add(key)
            buckets.setdefault(key, []).append(finding)
    results = []
    severity = {"minor": 0, "major": 1, "critical": 2}
    for group in buckets.values():
        if len(group) * 2 <= len(ballots):
            continue
        ranked = sorted(group, key=lambda f: severity[f.severity])
        exemplar = ranked[(len(ranked) - 1) // 2]
        results.append(exemplar.model_copy(update={"confidence": len(group) / len(ballots)}))
    return results


def review(sources: list[Source], requirements: list[Requirement], client: Client,
           answers: list[dict] | None = None, *, votes: int = 1) -> tuple[list[Finding], list[str]]:
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
    behavior = behavior_sources(sources)
    if behavior and len(behavior) < len(sources):
        jobs.append((
            "Согласованность поведения и приёмки", "set",
            "Сопоставь каждое бизнес-правило с другими правилами и с ожидаемым результатом "
            "каждого приёмочного примера. Пошагово вычисли результат там, где вход задан. "
            "Сравни границу периода и выбор даты события, повтор после смены настройки, "
            "условия запуска и исключения. Ищи только конфликты или дублирование правил. "
            "В примере конфликта выполни все условия обеих цитат. Если после изменения настройки "
            "действие наступает при следующем событии, включи это событие в сценарий. "
            "Для каждого вывода нужны две точные цитаты, по одной для каждой стороны.",
            {"source": [item.model_dump() for item in behavior], "answers": answers or []},
        ))
        policy = [source for source in sources if any(re.search(
            r"цел[ьи]|архитектур|sequence|нефункциональн|требования к данным|nfr|objective", section, re.I,
        ) for section in source.section)]
        contracts = [source for source in sources if any(re.search(
            r"логик[аи] (?:работы|операции)|параметры запроса|request parameters|query parameters|"
            r"данные|данным|ошибк|исключени|\berrors?\b|exceptions?",
            section, re.I,
        ) for section in source.section)]
        focused = {source.locator for source in behavior + policy + contracts}
        jobs.append((
            "Полнота состояний и данных", "set",
            "Проверь только три класса пробелов; верни максимум по одному выводу на класс. "
            "(1) Найди правило, которое ограничивает допустимость операции состоянием объекта, "
            "видом объекта или валютой. Если исключённые случаи не описаны, назови конкретный вход "
            "и спроси, следует ли отклонить его или обработать отдельно. Цитируй правило допустимости. "
            "(2) Если запрос одновременно меняет состояние функции и передаёт обязательный параметр "
            "её настройки, проверь явное поведение при выключении: сохранять ли параметр и проверять "
            "ли его границы, даже когда функция выключена. Цитируй обе строки параметров или правило обработки. "
            "(3) Сопоставь явный перечень сохраняемых атрибутов с полями, которые контракт требует "
            "сохранять в том же хранилище. Назови конкретный отсутствующий атрибут или единицу, "
            "приведи цитаты из обеих частей. Не считай список исчерпывающим, если он дан как пример.",
            {"source": [item.model_dump() for item in sources if item.locator in focused],
             "answers": answers or []},
        ))
        if policy:
            jobs.append((
                "Связность целей, сроков и терминов", "set",
                "Сопоставь обещанный результат в целях и допустимую задержку в эксплуатационных "
                "требованиях. Сравни названия одного компонента в архитектуре и последовательности. "
                "Опиши только конкретные расхождения, которые меняют критерий приёмки или границу "
                "ответственности. Цитируй обе стороны каждого расхождения.",
                {"source": [item.model_dump() for item in policy], "answers": answers or []},
            ))

    def ballot(job, attempt):
        _, scope, prompt, data = job
        if attempt:
            variants = (
                "Сначала сопоставь исходные цитаты, затем оцени по заданным критериям.",
                "Сначала проверь условия и наблюдаемый результат, затем запиши выводы по заданным критериям.",
            )
            prompt += f"\nНезависимая проверка {attempt + 1}. " + variants[(attempt - 1) % len(variants)]
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

    def run(job):
        ballots = [ballot(job, index) for index in range(votes)]
        if sum(result is not None for result in ballots) * 2 <= votes:
            return None
        if votes == 1:
            return ballots[0]
        return vote(ballots)

    with ThreadPoolExecutor(max_workers=getattr(getattr(client, "settings", None), "concurrency", 3)) as pool:
        results = list(pool.map(run, jobs))
    return (
        [finding for result in results if result for finding in result],
        [job[0] for job, result in zip(jobs, results) if result is None],
    )
