"""Tests for eval.score.score: recall, labeled precision, stale-report guard."""
import hashlib
import json
from pathlib import Path

import pytest

from eval.score import score

GOLDEN = """# Golden defects

- G01. First defect: month rule conflict.
- G02. Second defect: GET used for save.
- G03. Third defect: unit mismatch.
"""

# Findings D-01..D-04 have evidence; D-05 has none and can never be a hit.
FINDINGS = [
    {"message": "month rule conflict", "evidence": ["максимум один такой push"]},
    {"message": "GET saves state", "evidence": ["Сохранение порода"]},
    {"message": "units differ", "evidence": ["тиын vs тенге"]},
    {"message": "unlabeled extra finding", "evidence": ["weak wording"]},
    {"message": "no evidence here", "evidence": []},
]


def write_case(tmp_path: Path, decisions: dict | None) -> tuple[Path, Path, Path]:
    golden = tmp_path / "golden_defects.md"
    golden.write_text(GOLDEN, encoding="utf-8")
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"findings": FINDINGS}, ensure_ascii=False), encoding="utf-8")
    if decisions is None:
        decisions_path = tmp_path / "adjudication.json"
    else:
        decisions_path = tmp_path / "adjudication.json"
        decisions = dict(decisions)
        decisions.setdefault("report_sha256", hashlib.sha256(report.read_bytes()).hexdigest())
        decisions_path.write_text(json.dumps(decisions, ensure_ascii=False), encoding="utf-8")
    return golden, report, decisions_path


def test_recall_and_counts(tmp_path):
    golden, report, decisions = write_case(tmp_path, {
        "hits": {"G01": ["D-01"], "G02": ["D-02"]},
        "false_positives": ["D-03"],
    })
    result = score(golden, report, decisions)
    assert (result.matched_defects, result.total_defects) == (2, 3)
    assert [m.split(".")[0] for m in result.misses] == ["G03"]
    assert result.true_positives == 2
    assert result.false_positives == 1


def test_unlabeled_findings_excluded_from_precision(tmp_path):
    # D-04 and D-05 are in the report but labeled nowhere: precision ignores them.
    golden, report, decisions = write_case(tmp_path, {"hits": {"G01": ["D-01"]}})
    result = score(golden, report, decisions)
    assert result.matched_defects == 1
    assert result.total_defects == 3
    assert result.true_positives == 1
    assert result.false_positives == 0


def test_duplicate_reference_counts_once(tmp_path):
    golden, report, decisions = write_case(tmp_path, {
        "hits": {"G01": ["D-01", "D-01"], "G02": ["D-01"]},
    })
    result = score(golden, report, decisions)
    assert result.matched_defects == 2
    assert result.true_positives == 1


def test_review_outside_golden_affects_precision_only(tmp_path):
    result = score(*write_case(tmp_path, {
        "hits": {"G01": ["D-01"]}, "valid_extra": ["D-04"],
        "false_positives": ["D-03"], "undecided": ["D-02"],
    }))
    assert (result.matched_defects, result.true_positives, result.false_positives) == (1, 2, 1)
    assert result.undecided == 1


@pytest.mark.parametrize("key", ["hits", "false_positives", "undecided"])
def test_extra_cannot_have_two_labels(tmp_path, key):
    other = {"G01": ["D-04"]} if key == "hits" else ["D-04"]
    with pytest.raises(ValueError, match="несовместимые"):
        score(*write_case(tmp_path, {"valid_extra": ["D-04"], key: other}))


def test_stale_report_rejected(tmp_path):
    golden, report, decisions = write_case(tmp_path, {"hits": {"G01": ["D-01"]}})
    data = json.loads(report.read_text(encoding="utf-8"))
    data["findings"].append({"message": "regenerated", "evidence": ["new"]})
    report.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="другому отчёту"):
        score(golden, report, decisions)


def test_unknown_goal_rejected(tmp_path):
    golden, report, decisions = write_case(tmp_path, {"hits": {"G99": ["D-01"]}})
    with pytest.raises(ValueError):
        score(golden, report, decisions)


def test_reference_out_of_range_rejected(tmp_path):
    golden, report, decisions = write_case(tmp_path, {"hits": {"G01": ["D-99"]}})
    with pytest.raises(ValueError, match="Ошибочная ссылка"):
        score(golden, report, decisions)


def test_reference_without_evidence_rejected(tmp_path):
    golden, report, decisions = write_case(tmp_path, {"hits": {"G01": ["D-05"]}})
    with pytest.raises(ValueError, match="Ошибочная ссылка"):
        score(golden, report, decisions)


def test_malformed_reference_rejected(tmp_path):
    golden, report, decisions = write_case(tmp_path, {"hits": {"G01": ["R-01"]}})
    with pytest.raises((ValueError, AttributeError)):
        score(golden, report, decisions)


def test_no_decisions_file(tmp_path):
    golden, report, decisions = write_case(tmp_path, None)
    assert not decisions.exists()
    result = score(golden, report, decisions)
    assert result.matched_defects == 0
    assert result.total_defects == 3
    assert result.true_positives == 0
    assert result.false_positives == 0
    assert len(result.misses) == 3
