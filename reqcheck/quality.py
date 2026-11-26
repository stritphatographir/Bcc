import re
from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, Field

from .findings import Finding
from .segmenter import Requirement

CRITERIA = {
    "Необходимость": r"необходим|neces",
    "Уместность": r"умест|appropriat",
    "Однозначность": r"однознач|ambigu",
    "Полнота": r"полн|complet",
    "Единичность": r"единич|атомар|singular",
    "Осуществимость": r"осуществ|выполним|feasib",
    "Проверяемость": r"проверя|измерим|verif",
    "Правильность": r"правильност|correct",
    "Соответствие форме": r"соответств.? форм|conform",
    "Согласованность набора": r"согласован|противореч|consisten",
    "Понятность набора": r"понятност|comprehens",
    "Валидируемость набора": r"валидируем|validat",
}
PENALTIES = {"critical": 40, "major": 15, "minor": 5}


class Quality(BaseModel):
    requirements: dict[str, int] = Field(default_factory=dict)
    affected_criteria: dict[str, int] = Field(default_factory=dict)
    readiness: Literal["blocked", "incomplete", "ready"] = "incomplete"
    score: int | None = None
    partial: bool = True


def score_quality(requirements: list[Requirement], findings: list[Finding], failed: list[str]) -> Quality:
    penalties = defaultdict(dict)
    affected: dict[str, set[str]] = {criterion: set() for criterion in CRITERIA}
    for finding in findings:
        criteria = [name for name, pattern in CRITERIA.items() if re.search(pattern, finding.criterion, re.I)]
        for identifier in finding.requirements:
            for criterion in criteria or [finding.criterion]:
                if criterion in affected:
                    affected[criterion].add(identifier)
                penalties[identifier][criterion] = max(
                    penalties[identifier].get(criterion, 0), PENALTIES[finding.severity],
                )
    scores = {r.id: max(0, 100 - sum(penalties[r.id].values())) for r in requirements}
    partial = bool(failed or not requirements)
    if any(f.severity in {"major", "critical"} for f in findings):
        readiness = "blocked"
    else:
        readiness = "incomplete" if partial else "ready"
    return Quality(
        requirements=scores, affected_criteria={key: len(value) for key, value in affected.items()},
        readiness=readiness, score=round(sum(scores.values()) / len(scores)) if scores else None, partial=partial,
    )
