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


def test_russian_plural():
    from reqcheck.report import plural

    forms = ("дефект", "дефекта", "дефектов")
    assert [plural(n, *forms) for n in (1, 2, 5, 11, 12, 21, 22, 25, 101, 111)] == [
        "дефект", "дефекта", "дефектов", "дефектов", "дефектов", "дефект", "дефекта", "дефектов", "дефект", "дефектов"]


def test_passport_duration_and_cached_response_origin():
    from datetime import datetime, timedelta, timezone
    from pathlib import Path

    from reqcheck.pipeline import Analysis
    from reqcheck.report import render_markdown

    result = Analysis.model_validate_json(Path("reports/report.json").read_bytes())
    result.passport.started = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result.passport.finished = result.passport.started + timedelta(seconds=1.25)
    result.passport.calls = result.passport.responses = 0
    result.passport.cache_hits = 20
    markdown = render_markdown(result)
    lines = [
        "- Длительность — 1,25 с",
        "- Запросы к модели в этом прогоне — 0 (успешных ответов — 0)",
        "- Ответы модели из кэша — 20 (получены ранее от той же модели; ключ кэша — SHA-256 запроса)",
        "- Происхождение ответов — все ответы модели в этом прогоне получены из кэша",
    ]
    for line in lines:
        assert line in markdown
        assert line[2:] in render_html(markdown)
    assert markdown.index("- Окончание") < markdown.index(lines[0]) < markdown.index("- Модель")
    result.passport.calls = 1
    assert lines[-1] not in render_markdown(result)
    result.passport.calls = result.passport.cache_hits = 0
    assert lines[-1] not in render_markdown(result)
