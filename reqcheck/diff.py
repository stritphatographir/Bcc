from collections import defaultdict, deque

from .findings import Finding
from .pipeline import Analysis
from .report import literal


def _identity(finding: Finding):
    return (finding.code, " ".join(finding.criterion.casefold().split()),
            tuple(sorted(" ".join(evidence.quote.split()) for evidence in finding.evidence)))


def _locators(finding: Finding):
    return tuple(sorted((e.locator, " ".join(e.quote.split())) for e in finding.evidence))


def changes(old: list[Finding], new: list[Finding]) -> tuple[list[Finding], list[Finding], int]:
    stable = defaultdict(deque)
    for index, finding in enumerate(old):
        stable[_identity(finding), _locators(finding)].append(index)
    same = set()
    moved_or_new = []
    for finding in new:
        exact = stable[_identity(finding), _locators(finding)]
        if exact:
            same.add(exact.popleft())
        else:
            moved_or_new.append(finding)
    remaining = defaultdict(deque)
    for index, finding in enumerate(old):
        if index not in same:
            remaining[_identity(finding)].append(index)
    added = []
    for finding in moved_or_new:
        candidates = remaining[_identity(finding)]
        if candidates:
            same.add(candidates.popleft())
        else:
            added.append(finding)
    return [finding for index, finding in enumerate(old) if index not in same], added, len(same)


def render_diff(old: Analysis, new: Analysis) -> str:
    missing, added, retained = changes(old.findings, new.findings)
    lines = [
        "# Изменения дефектов", "",
        f"- Исходный документ — {literal(old.passport.document)}",
        f"- Новый документ — {literal(new.passport.document)}",
        f"- Сохранилось — {retained}",
        f"- Не обнаружено повторно — {len(missing)}",
        f"- Новых — {len(added)}", "",
        "Совпадение определяется по критерию и цитатам. Проверьте переформулированные "
        "требования перед закрытием дефекта.", "",
    ]
    if old.passport.failed_agents or new.passport.failed_agents:
        lines.extend(["Часть проверок не выполнена. Результат сравнения предварительный.", ""])
    for title, items in [("Не обнаружены повторно", missing), ("Новые дефекты", added)]:
        lines.extend([f"## {title}", ""])
        for finding in items:
            lines.append("- " + literal(finding.explanation))
            lines.extend(f"  - {literal(e.locator)} · «{literal(e.quote)}»" for e in finding.evidence)
        if not items:
            lines.append("Нет.")
        lines.append("")
    return "\n".join(lines)
