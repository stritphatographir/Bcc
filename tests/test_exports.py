import csv
import json

from docx import Document

from reqcheck.exports import export
from reqcheck.findings import Evidence, Finding
from reqcheck.pipeline import Analysis, Passport
from datetime import datetime, timezone


def test_exports_preserve_finding_ids_and_citations(tmp_path):
    now = datetime.now(timezone.utc)
    result = Analysis(
        passport=Passport(document="spec.md", sha256="hash", model="mock", provider="example", version="sha",
                          started=now, finished=now, calls=0, cache_hits=0, dropped=0, failed_agents=[], mode="test"),
        requirements=[], questions=[],
        findings=[Finding(code="gap", criterion="Полнота", severity="major", explanation="Нет порога.",
                          fix="Указать порог.", question="Какой порог?",
                          evidence=[Evidence(locator="строка 4", quote="=порог")])],
    )
    csv_path, json_path, docx_path = export(result, tmp_path / "result")
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["External issue ID"] == "D-001"
    assert "строка 4" in rows[0]["Description"]
    assert json.loads(json_path.read_bytes())["issues"][0]["fields"]["summary"].startswith("D-001")
    doc = Document(docx_path)
    assert any("строка 4" in p.text for p in doc.paragraphs)
    assert doc.tables
