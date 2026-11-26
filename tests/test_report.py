from reqcheck.report import render_html


def test_html_has_tables_and_ignores_source_html():
    html = render_html("# Отчёт\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n<script>alert(1)</script>")
    assert "<table>" in html
    assert "<script>" not in html
