from reqcheck.loader import load


def test_locators(tmp_path):
    path = tmp_path / "example.md"
    path.write_text("# Root\n\n## Details\n| action | result |\n| --- | --- |\n| join | welcome |", encoding="utf-8")
    lines = load(path)
    assert lines[-1].locator == "строка 6"
    assert lines[-1].section == ("Root", "Details")
    assert lines[-1].text == "| join | welcome |"


def test_pdf_sample():
    from pathlib import Path

    lines = load(Path("examples/requirements.pdf"))
    assert any("Уведомление о расходах по карте" in line.text for line in lines)
