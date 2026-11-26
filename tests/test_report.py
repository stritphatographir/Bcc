from reqcheck.report import render_html


def test_html_has_tables_and_ignores_source_html():
    html = render_html("# Отчёт\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n<script>alert(1)</script>")
    assert "<table>" in html
    assert "<script>" not in html


def test_verdict_answers_development_and_testing_explicitly():
    from pathlib import Path

    from reqcheck.pipeline import Analysis
    from reqcheck.report import render_markdown

    result = Analysis.model_validate_json(Path("reports/report.json").read_bytes())
    verdict = render_markdown(result).split("## Вердикт", 1)[1].split("\n## ", 1)[0]
    assert "**Начинать разработку:** нельзя" in verdict
    assert "**Начинать тестирование:** нельзя" in verdict
    assert "Требования с критическими дефектами — R" in verdict


def test_first_fixes_do_not_repeat_the_same_quote():
    from pathlib import Path

    from reqcheck.pipeline import Analysis
    from reqcheck.report import render_markdown

    result = Analysis.model_validate_json(Path("reports/report.json").read_bytes())
    fixes = render_markdown(result).split("Первоочередные правки", 1)[1].split("\n## ", 1)[0]
    ids = [line.split("**")[1] for line in fixes.splitlines() if line.startswith("- **")]
    quotes = [result.findings[int(i.split("-")[1]) - 1].evidence[0].quote for i in ids]
    assert 1 < len(ids) <= 5 and len(set(quotes)) == len(quotes)
