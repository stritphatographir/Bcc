"""Deterministic checks of the document structure (no LLM).

* happy-path diagrams: a process / sequence diagram written as an arrow chain with no alternative branch;
* duplicated rules: the same rule stated twice in different prose sections (IEEE 830 §4.3.7 modifiable).
* missing numeric default: a configurable range is described alongside a separate toggle default.

Checks rely on headings, markup and word patterns, never on document facts.
"""
import re

from .findings import Evidence, Finding
from .loader import Source
from .segmenter import Requirement

DIAGRAM_SECTION = re.compile(r"bpmn|sequence|диаграмм|схем|процесс|flow|поток", re.I)
ARROW = re.compile(r"→|->|=>|-->")
BRANCH = re.compile(
    r"\b(?:иначе|если\s+нет|ошибк\w*|отказ\w*|неуспе\w*|отклон\w*|отмен\w*|таймаут\w*|тайм-аут\w*|"
    r"повтор\w*|alt|else|opt|break|error|fail\w*|timeout|reject\w*)\b|\bне\s+\w+",
    re.I,
)
STOP = {"если", "когда", "также", "этого", "этот", "который", "которая", "которые", "должен", "должна",
        "должно", "должны", "может", "могут", "после", "перед", "через", "между", "только"}
SENTENCE = re.compile(r"[^.!?\n]+[.!?]?")
ADJUSTABLE_RANGE = re.compile(
    r"\b(?:зада[её]т|задают|устанавлива\w+|настраива\w+|выбира\w+|изменя\w+)\s+"
    r"(?:[а-яё-]+\s+){0,3}(?P<name>[а-яё-]+)\s+от\s+\d[\d\s,]*\s+до\s+\d",
    re.I,
)
DEFAULT = re.compile(r"\bпо\s+умолчанию\b", re.I)
TOGGLE_STATE = re.compile(r"\b(?:отключ|выключ|включ|активир|деактивир)\w*", re.I)
INITIAL = re.compile(r"\b(?:начальн|исходн)\w*", re.I)
DEFAULT_VALUE = re.compile(r"\d|\b(?:не\s+(?:задан|установлен)\w*|без\s+значения|пуст\w*)\b", re.I)


def _stems(text: str) -> set[str]:
    return {word[:5] for word in re.findall(r"[а-яёa-z]+", text.casefold()) if len(word) >= 4 and word not in STOP}


def _sentences(source: Source):
    text = re.sub(r"^\s*(?:[*\-]|\d+[.)])\s*", "", source.text)
    for match in SENTENCE.finditer(text):
        sentence = match[0].strip(" *")
        if len(_stems(sentence)) >= 4:
            yield sentence


def happy_path_diagrams(sources: list[Source]) -> list[Finding]:
    diagrams = []
    for source in sources:
        if source.heading or source.text.lstrip().startswith("|"):
            continue
        heading = " ".join(source.section)
        if DIAGRAM_SECTION.search(heading) and len(ARROW.findall(source.text)) >= 2 and not BRANCH.search(source.text):
            diagrams.append(source)
    if not diagrams:
        return []
    names = ", ".join(f"«{s.section[-1]}»" for s in diagrams if s.section)
    return [Finding(
        code="happy-path-diagram", criterion="Полнота", severity="major",
        evidence=[Evidence(locator=s.locator, quote=s.text) for s in diagrams],
        explanation=f"Схемы {names} описывают только успешный путь: нет ветвей отказа, ошибки, повтора "
                    "или невыполненного условия, поэтому альтернативные сценарии не проверяются.",
        fix="Добавить на каждую схему альтернативные ветви с условием и результатом "
            "(условие не выполнено, ошибка внешнего сервиса, повторное событие).",
        question=f"Какие альтернативные ветви и их результат должны быть на схемах {names}: "
                 "что происходит, если условие не выполнено или внешний сервис вернул ошибку?",
        scope="set", agent="structure",
    )]


def duplicated_rules(sources: list[Source], requirements: list[Requirement], threshold: float = 0.6) -> list[Finding]:
    prose = [s for s in sources if not s.heading and not s.text.lstrip().startswith(("|", "```"))]
    seen: list[tuple[Source, str, set[str]]] = []
    result = []
    for source in prose:
        for sentence in _sentences(source):
            stems = _stems(sentence)
            for other, other_sentence, other_stems in seen:
                if other.section == source.section:
                    continue
                if len(stems & other_stems) / len(stems | other_stems) < threshold:
                    continue
                refs = [r.id for r in requirements if r.source.locator in {source.locator, other.locator}]
                result.append(Finding(
                    code="duplicated-rule", criterion="Модифицируемость", severity="minor",
                    evidence=[Evidence(locator=other.locator, quote=other_sentence),
                              Evidence(locator=source.locator, quote=sentence)],
                    explanation="Одно правило записано в двух разделах. При изменении одной формулировки "
                                "вторая останется прежней, и документ станет противоречивым.",
                    fix="Оставить правило в одном разделе, во втором дать ссылку на его идентификатор.",
                    question="Какая из двух формулировок правила основная, и можно ли во втором разделе "
                             "заменить её ссылкой?",
                    requirements=refs, scope="set", agent="structure",
                ))
                break
            seen.append((source, sentence, stems))
    return result


def missing_numeric_defaults(sources: list[Source], requirements: list[Requirement]) -> list[Finding]:
    prose = [source for source in sources if not source.heading]
    clauses = [(source, clause) for source in prose for clause in SENTENCE.findall(source.text)
               if DEFAULT.search(clause) or INITIAL.search(clause)]
    findings = []
    for source in prose:
        match = ADJUSTABLE_RANGE.search(source.text)
        if not match or not any(block == source and DEFAULT.search(clause) and TOGGLE_STATE.search(clause)
                                for block, clause in clauses):
            continue
        name = match['name'].casefold()
        stem = name[:5]
        if any(block.section == source.section and DEFAULT_VALUE.search(clause)
               and re.search(rf"\b{re.escape(stem)}\w*", clause, re.I) for block, clause in clauses):
            continue
        refs = [item.id for item in requirements if item.source.locator == source.locator]
        findings.append(Finding(
            code="missing-numeric-default", criterion="Полнота", severity="major",
            evidence=[Evidence(locator=source.locator, quote=source.text)],
            explanation=f"Описаны допустимый диапазон параметра «{name}» и исходное состояние функции. "
                        "Не определено числовое значение до первой настройки или что его нет.",
            fix=f"Указать начальное значение параметра «{name}» или явно описать состояние без значения.",
            question=f"Какое значение параметра «{name}» нужно показывать до первого сохранения?",
            requirements=refs, scope="requirement" if refs else "set", agent="structure",
        ))
    return findings


def review_structure(sources: list[Source], requirements: list[Requirement]) -> list[Finding]:
    return (happy_path_diagrams(sources) + duplicated_rules(sources, requirements)
            + missing_numeric_defaults(sources, requirements))
