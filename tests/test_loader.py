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


def test_pdf_reports_pages_without_text(tmp_path):
    from reportlab.pdfgen import canvas

    from reqcheck.loader import load, unread_pages

    path = tmp_path / "mixed.pdf"
    pdf = canvas.Canvas(str(path))
    pdf.drawString(72, 720, "Requirement 1: the system shall log every payment.")
    pdf.showPage()
    pdf.showPage()  # second page: image-only scan, no text layer
    pdf.save()
    assert unread_pages(path) == [2]
    assert load(path)[0].locator == "страница 1, строка 1"
