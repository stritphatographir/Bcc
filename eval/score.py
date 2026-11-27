"""Score a generated JSON report against evidence-backed adjudications."""
import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Score:
    matched_defects: int
    total_defects: int
    true_positives: int
    false_positives: int
    misses: list[str]
    total_findings: int
    undecided: int = 0


def score(golden: Path, report: Path, decisions: Path) -> Score:
    source = golden.read_text(encoding="utf-8")
    defects = dict(re.findall(r"^- (G\d+)\. (.+)$", source, re.M))
    raw = report.read_bytes()
    findings = json.loads(raw)["findings"]
    try:
        review = json.loads(decisions.read_text(encoding="utf-8"))
    except FileNotFoundError:
        review = None
    if review is not None and review["report_sha256"] != hashlib.sha256(raw).hexdigest():
        raise ValueError("Оценка относится к другому отчёту. Сверьте цитаты и обновите файл оценки.")
    review = review or {}

    def finding_index(reference: str, *, require_evidence: bool) -> int:
        match = re.fullmatch(r"D-([0-9]+)", reference)
        index = int(match[1]) - 1 if match else -1
        if not 0 <= index < len(findings) or (require_evidence and not findings[index]["evidence"]):
            raise ValueError(f"Ошибочная ссылка на вывод: {reference}")
        return index

    hits = set()
    positives = set()
    for goal, references in review.get("hits", {}).items():
        if goal not in defects or not references:
            raise ValueError(f"Неизвестный дефект или нет ссылок: {goal}")
        positives.update(finding_index(reference, require_evidence=True) for reference in references)
        hits.add(goal)
    negatives = {finding_index(ref, require_evidence=False) for ref in review.get("false_positives", [])}
    extra = {finding_index(ref, require_evidence=True) for ref in review.get("valid_extra", [])}
    undecided = {finding_index(ref, require_evidence=False) for ref in review.get("undecided", [])}
    groups = (positives, extra, negatives, undecided)
    if sum(map(len, groups)) != len(set().union(*groups)):
        raise ValueError("Один вывод получил две несовместимые оценки.")
    misses = [f"{key}. {value}" for key, value in defects.items() if key not in hits]
    return Score(len(hits), len(defects), len(positives) + len(extra), len(negatives),
                 misses, len(findings), len(undecided))


def render_ablation(report: Path, ablation: Path) -> str:
    data = json.loads(ablation.read_text(encoding="utf-8"))
    if data["report_sha256"] != hashlib.sha256(report.read_bytes()).hexdigest():
        raise ValueError("Таблица ablation относится к другому отчёту.")
    lines = ["| Профиль | Recall | Precision | Оценённые выводы |", "| --- | --- | --- | --- |"]
    for row in data["profiles"]:
        labeled = row["true_positives"] + row["false_positives"]
        recall = f"{row['matched_defects']}/{data['total_defects']}"
        precision = f"{row['true_positives']}/{labeled}"
        lines.append(f"| {row['name']} | {recall} | {precision} | {labeled}/{row['total_findings']} |")
    return "\n".join(lines)


def main():
    import sys

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Recall по совпадению места и смысла дефекта")
    parser.add_argument("--report", type=Path, default=Path("reports/report.json"))
    parser.add_argument("--golden", type=Path, default=Path("eval/golden_defects.md"))
    parser.add_argument("--decisions", type=Path, default=Path("eval/adjudication.json"))
    parser.add_argument("--ablation", type=Path, help="Таблица измерений для выбранного отчёта")
    args = parser.parse_args()
    try:
        result = score(args.golden, args.report, args.decisions)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    if not args.decisions.exists():
        parser.error("Файл сверки отсутствует. Сначала разметьте отчёт.")
    hits, total = result.matched_defects, result.total_defects
    print(f"Recall: {hits}/{total} ({hits / total:.1%})" if total else "Recall: нет эталонных дефектов")
    true = result.true_positives
    labeled = true + result.false_positives
    print(f"Precision: {true}/{labeled} ({true / labeled:.1%})" if labeled else "Precision: нет оценённых выводов")
    print(f"Оценено выводов: {labeled}/{result.total_findings}")
    if result.undecided:
        print(f"Недостаточно данных для оценки: {result.undecided}")
    for miss in result.misses:
        print(f"- {miss}")
    ablation = args.ablation
    default_ablation = Path("eval/ablation.json")
    if ablation is None and args.report == Path("reports/report.json") and default_ablation.is_file():
        ablation = default_ablation
    if ablation:
        try:
            print("\n" + render_ablation(args.report, ablation))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            parser.error(str(exc))


if __name__ == "__main__":
    main()
