import hashlib
import json

import httpx

import reqcheck.config as config
import reqcheck.pipeline as pipeline
from reqcheck.__main__ import main
from reqcheck.config import Settings

DOC = (
    "# Спецификация отчётов\n\n"
    "## Требования\n\n"
    "- Ф-1. Система должна отправлять отчёт быстро.\n"
    "- Ф-2. Система должна хранить сумму в тенге.\n\n"
    "## Критерии приёмки\n\n"
    "- К-1. Отчёт формируется за 5 минут.\n"
)
SECTIONS = [
    "## Паспорт прогона", "## Выделенные требования", "## Проверка каждого требования",
    "## Проверка набора требований", "## Уточняющие вопросы",
    "## Сводка", "## Вердикт",
]


def run_cli(tmp_path, monkeypatch, transport):
    document = tmp_path / "спецификация.md"
    document.write_text(DOC, encoding="utf-8")
    output = tmp_path / "отчёт" / "отчёт.md"
    settings = Settings("http://test/v1", "dummy", "тест-модель", tmp_path / "cache")
    monkeypatch.setattr(config.Settings, "from_env", classmethod(lambda cls: settings))
    real = pipeline.Client
    monkeypatch.setattr(pipeline, "Client",
                        lambda value: real(value, transport=transport))
    monkeypatch.setattr("sys.argv", ["reqcheck", str(document), "-o", str(output)])
    main()
    return document, output


def mocked(request):
    system = json.loads(request.content)["messages"][0]["content"]
    if "Выдели" in system:
        content = '{"requirements": []}'
    elif "таблицу решений" in system:
        content = '{"rules": [], "cases": []}'
    elif "согласованность и осуществимость" in system:
        issue = {
            "criterion": "Проверяемость",
            "severity": "critical",
            "evidence": [{"locator": "строка 5", "quote": "отправлять отчёт быстро"}],
            "explanation": "Срок отправки не определён.",
            "fix": "Указать предельный срок отправки.",
            "question": "Какой срок следует проверять?",
        }
        invalid = dict(issue, evidence=[{"locator": "строка 999", "quote": "нет такой строки"}])
        content = json.dumps({"findings": [issue, invalid]})
    else:
        content = '{"findings": []}'
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def offline(request):
    raise httpx.ConnectError("network blocked")


def test_full_run_writes_three_files(tmp_path, monkeypatch, capsys):
    document, output = run_cli(tmp_path, monkeypatch, httpx.MockTransport(mocked))
    for path in (output, output.with_suffix(".html"), output.with_suffix(".json")):
        assert path.is_file()
    printed = capsys.readouterr().out
    assert all(str(output.with_suffix(s)) in printed for s in ("", ".html", ".json"))

    markdown = output.read_text(encoding="utf-8")
    for section in SECTIONS:
        assert section in markdown
    assert "быстро" in markdown
    assert "| ID в отчёте | ID в документе | Краткая формулировка |" in markdown
    summary, questions = markdown.split("## Сводка", 1)[1].split("## Уточняющие вопросы", 1)
    assert "Непроверяемые" in summary and "строка 5" in summary
    assert "отправлять отчёт быстро" in questions
    assert r"- Модель — тест\-модель" in markdown

    html = output.with_suffix(".html").read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert 'charset="utf-8"' in html
    assert "<table>" in html and "Спецификация отчётов" in html

    result = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
    passport = result["passport"]
    assert passport["document"] == "спецификация.md"
    assert passport["sha256"] == hashlib.sha256(document.read_bytes()).hexdigest()
    assert passport["model"] == "тест-модель" and passport["provider"] == "test"
    assert passport["mode"] == "Полная проверка" and passport["failed_agents"] == []
    assert passport["calls"] > 0 and passport["dropped"] == 1
    assert passport["started"] < passport["finished"]

    body = " ".join(document.read_text(encoding="utf-8").split())
    findings = result["findings"] + result["follow_up"]
    assert findings and all(
        " ".join(evidence["quote"].split()) in body
        for finding in findings for evidence in finding["evidence"]
    )
    assert result["questions"] and all(
        set(question["finding_ids"]) <= {f"D-{i + 1:03}" for i in range(len(findings))}
        for question in result["questions"]
    )
    trace_path = output.with_suffix(".trace.jsonl")
    trace = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert trace[0]["agent"] == "Чтение документа"
    assert any(row["type"] == "llm" and row["status"] == "ok" for row in trace)
    assert trace[-1]["agent"] == "Подготовка отчёта"


def test_offline_falls_back_to_linter_only(tmp_path, monkeypatch):
    document, output = run_cli(tmp_path, monkeypatch, httpx.MockTransport(offline))
    for path in (output, output.with_suffix(".html"), output.with_suffix(".json")):
        assert path.is_file()
    markdown = output.read_text(encoding="utf-8")
    for section in SECTIONS:
        assert section in markdown
    assert "Только правила" in markdown
    assert "быстро" in markdown

    result = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
    passport = result["passport"]
    assert passport["mode"] == "Только правила"
    assert passport["failed_agents"]
    assert any(f["agent"] == "linter" for f in result["findings"])
    assert all(f["agent"] != "critic" for f in result["findings"])
    assert passport["sha256"] == hashlib.sha256(document.read_bytes()).hexdigest()
