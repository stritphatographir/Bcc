import json
import re
from itertools import combinations
from operator import eq, ge, gt, le, lt, ne
from typing import Literal

from pydantic import BaseModel, Field

from .findings import Evidence, Finding
from .llm import Client
from .loader import Source
from .segmenter import Requirement
from .verifier import match_evidence

Scalar = bool | int | float | str
COMPARISONS = {"eq": eq, "ne": ne, "lt": lt, "le": le, "gt": gt, "ge": ge}
BEHAVIOR_SECTION = re.compile(
    r"бизнес.правил|\bфункциональн|критери.*при[её]м|при[её]мочн|особые правила|"
    r"требования к интеграции|сценари|business rules|acceptance|behavior|use cases",
    re.I,
)


def _number(value: Scalar) -> bool:
    return type(value) in (int, float)


def _same(left: Scalar, right: Scalar) -> bool:
    return _comparable(left, right) and left == right


def _comparable(left: Scalar, right: Scalar) -> bool:
    return type(left) is type(right) or _number(left) and _number(right)


class Condition(BaseModel):
    field: str = Field(min_length=1)
    operator: Literal["eq", "ne", "lt", "le", "gt", "ge"]
    value: Scalar

    def accepts(self, value: Scalar) -> bool:
        if not _comparable(value, self.value):
            return False
        if self.operator == "eq":
            return _same(value, self.value)
        if self.operator == "ne":
            return not _same(value, self.value)
        return _number(value) and _number(self.value) and COMPARISONS[self.operator](value, self.value)

    def candidates(self) -> list[Scalar]:
        value = self.value
        if _number(value):
            step = 1 if type(value) is int else 0.01
            return [value, value - step, value + step]
        if isinstance(value, bool):
            return [value, not value]
        return [value]


class FactReference(BaseModel):
    field: str = Field(min_length=1)


class Rule(BaseModel):
    scope: str = Field(min_length=1)
    label: str = Field(min_length=1)
    conditions: list[Condition]
    outcome: dict[str, Scalar | FactReference] = Field(min_length=1)
    evidence: Evidence


class Case(BaseModel):
    scope: str = Field(min_length=1)
    label: str = Field(min_length=1)
    facts: dict[str, Scalar]
    expected: dict[str, Scalar] = Field(min_length=1)
    evidence: Evidence


class DecisionTable(BaseModel):
    rules: list[Rule]
    cases: list[Case]


class Scenario(BaseModel):
    scope: str
    label: str
    facts: dict[str, Scalar]
    expected: dict[str, Scalar] = Field(default_factory=dict)
    evidence: Evidence | None = None
    status: Literal["covered", "conflict", "uncovered"]
    applicable_rules: list[int]


class Simulation(BaseModel):
    rules: list[Rule] = Field(default_factory=list)
    scenarios: list[Scenario] = Field(default_factory=list)
    dropped: int = 0


def _seed(conditions: list[Condition], known: dict[str, list[Scalar]]) -> dict[str, Scalar] | None:
    grouped: dict[str, list[Condition]] = {}
    for condition in conditions:
        grouped.setdefault(condition.field, []).append(condition)
    facts = {}
    for field, constraints in grouped.items():
        values = [value for constraint in constraints for value in constraint.candidates()]
        values.extend(known.get(field, []))
        bounds = sorted({c.value for c in constraints if _number(c.value)})
        if any(type(value) is float for value in bounds):
            values.extend(left + (right - left) / 2 for left, right in zip(bounds, bounds[1:]))
        for value in values:
            if all(constraint.accepts(value) for constraint in constraints):
                facts[field] = value
                break
        else:
            return None
    return facts


def _resolved(value: Scalar | FactReference, facts: dict[str, Scalar]) -> Scalar | None:
    if isinstance(value, FactReference):
        return facts.get(value.field)
    if isinstance(value, str):
        reference = re.fullmatch(r"\{(?:field:\s*)?([\w.-]+)\}", value)
        if reference:
            return facts.get(reference[1])
        if re.search(r"\w_\w|\s[+*/-]\s", value):
            return None
    return value


def evaluate(table: DecisionTable, sources: list[Source], requirements: list[Requirement]):
    by_locator = {source.locator: source.text for source in sources}
    rules = [rule.model_copy(update={"evidence": evidence}) for rule in table.rules
             if (evidence := match_evidence(rule.evidence, by_locator)) is not None]
    cases = [case.model_copy(update={"evidence": evidence}) for case in table.cases
             if (evidence := match_evidence(case.evidence, by_locator)) is not None]
    result = Simulation(rules=rules, dropped=len(table.rules) + len(table.cases) - len(rules) - len(cases))
    findings: list[Finding] = []
    seen_cases: set[tuple[str, str]] = set()
    seen_conflicts: set[tuple[str, tuple[tuple[str, str], ...]]] = set()

    def check(scope, label, facts, expected, evidence=None, other_cases=()):
        applied = [(i, rule) for i, rule in enumerate(rules, 1) if rule.scope == scope and all(
            cond.field in facts and cond.accepts(facts[cond.field]) for cond in rule.conditions
        )]
        outputs: dict[str, list[tuple[Scalar, Evidence]]] = {}
        if evidence is not None:
            for field, value in expected.items():
                outputs[field] = [(value, evidence)]
        for alternative in other_cases:
            for field, value in alternative.expected.items():
                if field in expected:
                    outputs[field].append((value, alternative.evidence))
        for _, rule in applied:
            for field, value in rule.outcome.items():
                resolved = _resolved(value, facts)
                if resolved is not None:
                    outputs.setdefault(field, []).append((resolved, rule.evidence))
        comparable_outputs = {
            field for field, values in outputs.items()
            if any(source != evidence and (field not in expected or _comparable(value, expected[field]))
                   for value, source in values)
        }
        status = "covered" if comparable_outputs and expected.keys() <= comparable_outputs else "uncovered"
        for field, values in outputs.items():
            for (first, first_source), (second, second_source) in combinations(values, 2):
                if not _comparable(first, second) or _same(first, second):
                    continue
                if first_source.locator == second_source.locator and (
                    first_source.quote in second_source.quote or second_source.quote in first_source.quote
                ):
                    continue
                status = "conflict"
                citations = (first_source, second_source)
                signature = (field, tuple(sorted((e.locator, e.quote) for e in citations)))
                if signature in seen_conflicts:
                    continue
                seen_conflicts.add(signature)
                locators = {item.locator for item in citations}
                facts_text = json.dumps(facts, ensure_ascii=False, sort_keys=True)
                findings.append(Finding(
                    code="simulation-conflict", criterion="Согласованность", severity="critical",
                    evidence=list(citations), scope="set", agent="simulator",
                    requirements=[r.id for r in requirements if r.source.locator in locators],
                    explanation=f"Сценарий «{label}» ({facts_text}): для «{field}» получены "
                                f"несовместимые результаты «{first}» и «{second}».",
                    fix=f"Указать один результат для «{field}» при условиях {facts_text} "
                        "и привести правила и критерий приёмки в соответствие.",
                    question=f"Какой результат для «{field}» верен в сценарии «{label}» "
                             f"({facts_text}): «{first}» или «{second}»?",
                ))
        result.scenarios.append(Scenario(
            scope=scope, label=label, facts=facts, expected=expected, evidence=evidence,
            status=status, applicable_rules=[i for i, _ in applied],
        ))
        seen_cases.add((scope, json.dumps(facts, sort_keys=True)))

    cohorts: dict[tuple[str, str], list[Case]] = {}
    for case in cases:
        key = (case.scope, json.dumps(case.facts, sort_keys=True))
        cohorts.setdefault(key, []).append(case)
    for cohort in cohorts.values():
        for case in cohort:
            check(case.scope, case.label, case.facts, case.expected, case.evidence,
                  (alternate for alternate in cohort if alternate is not case))

    def synthetic(scope, label, facts):
        if (scope, json.dumps(facts, sort_keys=True)) not in seen_cases:
            check(scope, label, facts, {})

    known: dict[str, dict[str, list[Scalar]]] = {}
    for case in cases:
        scope_data = known.setdefault(case.scope, {})
        for field, value in case.facts.items():
            scope_data.setdefault(field, []).append(value)
    for rule in rules:
        scope_data = known.setdefault(rule.scope, {})
        for condition in rule.conditions:
            scope_data.setdefault(condition.field, []).append(condition.value)

    for rule in rules:
        facts = _seed(rule.conditions, known[rule.scope])
        if facts is None:
            continue
        for condition in rule.conditions:
            for value in condition.candidates():
                synthetic(rule.scope, f"Граница правила «{rule.label}»", facts | {condition.field: value})
        synthetic(rule.scope, rule.label, facts)

    for first, second in combinations(rules, 2):
        if first.scope != second.scope or not any(
            first.outcome[field] != second.outcome[field]
            for field in first.outcome.keys() & second.outcome.keys()
        ):
            continue
        facts = _seed(first.conditions + second.conditions, known[first.scope])
        if facts is not None:
            synthetic(first.scope, f"Совместное действие правил «{first.label}» и «{second.label}»", facts)
    return result, findings


def behavior_sources(sources: list[Source]) -> list[Source]:
    return [source for source in sources if any(BEHAVIOR_SECTION.search(s) for s in source.section)]


def simulate(sources: list[Source], requirements: list[Requirement], client: Client):
    candidates = behavior_sources(sources)
    if not candidates:
        candidates = [requirement.source for requirement in requirements] or sources
    candidates = list({source.locator: source for source in candidates}.values())
    table = client.ask(
        "Извлеки таблицу решений из бизнес-правил и примеров приёмки. "
        "rule: scope (одна операция), label, conditions, outcome, evidence. case: тот же scope, label, "
        "facts (дано), expected (ожидаемый результат), evidence. Используй одинаковые имена полей, "
        "значения и единицы для связанных правил и примеров. Начни с критериев приёмки. Для каждого "
        "expected найди правило про этот же результат. Дай этому правилу ровно тот же scope и тот же "
        "ключ в outcome. Все проверяемые conditions должны иметь ключи в facts примера, если значения "
        "следуют из его текста. Например, правило запрещает доставку в выходной, а пример ожидает "
        "доставку в субботу. Вырази оба результата полем доставка, с condition выходной=true и "
        "facts выходной=true. Результаты false и true. Не кодируй срок как результат, если по сроку "
        "можно определить ожидаемое действие при известных фактах. Сравнение lt/le/gt/ge только для чисел. "
        "В outcome пиши наблюдаемое значение или ссылку на факт {field: имя_поля}, когда значение "
        "совпадает с известным фактом. Не пиши формулы или имена полей как строковые результаты. "
        "Время суток переводи в минуты с начала дня, если нужно сравнить границы. "
        "Для текстовых состояний используй eq/ne. Не опускай условия применимости. "
        "Сосредоточься на датах и переходах месяца, порогах, смене настройки, повторной обработке, "
        "возвратах и смене состояния. Не выдумывай правила, входные значения или ожидания. "
        "Включи все указанные критерии приёмки, которые можно представить этими полями. "
        "Для каждой записи evidence содержит исходный locator и дословный непрерывный quote из этой строки.",
        [source.model_dump() for source in candidates], DecisionTable,
    )
    return evaluate(table, sources, requirements)
