import json
import re
from collections import defaultdict
from collections.abc import Sequence
from difflib import unified_diff
from typing import Literal

from pydantic import BaseModel, Field

from .clarifier import finding_id
from .findings import Finding
from .loader import Source
from .segmenter import Requirement
from .simulator import Simulation


class TestCase(BaseModel):
    id: str
    kind: Literal["positive", "negative", "boundary"]
    requirements: list[str]
    gherkin: str


class Rewrite(BaseModel):
    requirement: str
    locator: str
    findings: list[str]
    proposal: str
    diff: str


class TraceRow(BaseModel):
    requirement: str
    goal: str | None = None
    acceptance: list[str]
    contracts: list[str]
    tests: list[str]


class QA(BaseModel):
    tests: list[TestCase] = Field(default_factory=list)
    uncovered: list[str] = Field(default_factory=list)
    rewrites: list[Rewrite] = Field(default_factory=list)
    trace: list[TraceRow] = Field(default_factory=list)


def _values(values: dict) -> str:
    return ", ".join(f"{key} = {json.dumps(value, ensure_ascii=False)}" for key, value in values.items())


def build_qa(requirements: list[Requirement], findings: list[Finding],
             simulation: Simulation, sources: list[Source],
             follow_up: Sequence[Finding] = ()) -> QA:
    by_locator = defaultdict(list)
    for requirement in requirements:
        by_locator[requirement.source.locator].append(requirement.id)
    qa = QA()
    acceptance = defaultdict(list)
    tests_by_requirement = defaultdict(list)
    for scenario in simulation.scenarios:
        locators = [simulation.rules[i - 1].evidence.locator for i in scenario.applicable_rules]
        if scenario.evidence:
            locators.append(scenario.evidence.locator)
        linked = list(dict.fromkeys(req for locator in locators for req in by_locator[locator]))
        if scenario.evidence:
            for req in linked:
                acceptance[req].append(scenario.evidence.locator)
        if scenario.status != "covered" or not scenario.outcomes or not linked:
            continue
        kind = "boundary"
        if scenario.evidence:
            kind = "negative" if any(value is False for value in scenario.expected.values()) else "positive"
        identifier = f"T-{len(qa.tests) + 1:03}"
        given = _values(scenario.facts) if scenario.facts else "выполнены условия правила"
        gherkin = "\n".join((
            "# language: ru", f"Функциональность: {scenario.scope}",
            f"  Сценарий: {scenario.label}", f"    Дано {given}",
            f"    Тогда {_values(scenario.outcomes)}",
        ))
        qa.tests.append(TestCase(id=identifier, kind=kind, requirements=linked, gherkin=gherkin))
        for req in linked:
            tests_by_requirement[req].append(identifier)

    fixes = defaultdict(list)
    contracts = defaultdict(list)
    contract_locations = {source.locator for source in sources if any(
        re.search(r"\bapi\b|данн|data|request|response|запрос|ответ", section, re.I)
        for section in source.section
    )}
    for finding_index, finding in enumerate(findings):
        related = list(dict.fromkeys(finding.requirements or [
            req for evidence in finding.evidence for req in by_locator[evidence.locator]
        ]))
        for req in related:
            fixes[req].append((finding_id(finding_index), finding.fix))
            if len(finding.evidence) > 1:
                contracts[req].extend(e.locator for e in finding.evidence if e.locator in contract_locations)
    revised = defaultdict(list)
    for finding in follow_up:
        for req in finding.requirements:
            revised[req].append(finding.fix)

    goals = [source for source in sources if not source.heading and source.section and
             re.match(r"^(?:\d+[. ]+)?(?:цели?|goal|objective)", source.section[-1], re.I)]
    for requirement in requirements:
        ref = requirement.id
        if not tests_by_requirement[ref]:
            qa.uncovered.append(ref)
        goal_matches = [g for g in goals if g.section[:-1] == requirement.source.section[:len(g.section) - 1]]
        linked_contracts = contracts[ref].copy()
        if requirement.source.locator in contract_locations:
            linked_contracts.insert(0, requirement.source.locator)
        qa.trace.append(TraceRow(
            requirement=ref, goal=goal_matches[0].locator if len(goal_matches) == 1 else None,
            acceptance=list(dict.fromkeys(acceptance[ref])), contracts=list(dict.fromkeys(linked_contracts)),
            tests=tests_by_requirement[ref],
        ))
        if fixes[ref]:
            proposals = revised[ref] or [fix for _, fix in fixes[ref]]
            proposal = "\n".join(dict.fromkeys(proposals))
            diff = "\n".join(unified_diff(
                requirement.quote.splitlines(), proposal.splitlines(),
                fromfile=requirement.source.locator, tofile="проект " + ref, lineterm="",
            ))
            qa.rewrites.append(Rewrite(
                requirement=ref, locator=requirement.source.locator, proposal=proposal, diff=diff,
                findings=[identifier for identifier, _ in fixes[ref]],
            ))
    return qa
