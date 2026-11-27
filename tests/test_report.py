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


def test_model_switch_is_visible_and_serialized():
    from pathlib import Path

    from reqcheck.pipeline import Analysis
    from reqcheck.report import render_markdown

    data = Analysis.model_validate_json(Path("reports/report.json").read_bytes()).model_dump()
    data["passport"].update(
        switch_reason="Основная модель недоступна: HTTP 429",
        model_runs=[
            dict(provider="primary.example", model="primary", calls=2, responses=1, cache_hits=3),
            dict(provider="local.example", model="local", calls=4, responses=4, cache_hits=2),
        ],
    )
    result = Analysis.model_validate(data)
    markdown = render_markdown(result)
    for text in (
        "Переключение модели — Основная модель недоступна: HTTP 429",
        "распределение по моделям приведено ниже",
        r"primary\.example | primary | 2 | 1 | 3",
        r"local\.example | local | 4 | 4 | 2",
        "Успешные ответы без кэша",
    ):
        if " | " in text:
            assert text in markdown
        else:
            assert text in markdown
            assert text in render_html(markdown)
    html = render_html(markdown)
    assert "<td>local.example</td>" in html
    serialized = Analysis.model_validate_json(result.model_dump_json()).passport
    assert serialized.switch_reason == data["passport"]["switch_reason"]
    assert serialized.model_runs[0].responses == 1
    assert serialized.model == data["passport"]["model"]
    assert serialized.provider == data["passport"]["provider"]


def test_no_switch_keeps_historical_rendering():
    from pathlib import Path

    from reqcheck.pipeline import Analysis
    from reqcheck.report import render_markdown

    result = Analysis.model_validate_json(Path("reports/report.json").read_bytes())
    markdown = render_markdown(result)
    assert result.passport.switch_reason == ""
    assert result.passport.model_runs == []
    assert "Переключение модели" not in markdown
    data = result.model_dump()
    data["passport"].update(switch_reason="", model_runs=[])
    assert render_markdown(Analysis.model_validate(data)) == markdown


def test_pipeline_copies_model_switch_metadata(monkeypatch, tmp_path):
    from reqcheck import pipeline
    from reqcheck.config import Settings
    from reqcheck.simulator import Simulation

    class SwitchedClient:
        calls = 2
        hits = 1
        responses = 2
        offline = None
        switch_reason = "Основная модель недоступна"
        model_runs = [dict(provider="backup.example", model="backup", calls=1, responses=1, cache_hits=1)]

        def __init__(self, settings):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(pipeline, "Client", SwitchedClient)
    def segment(sources, client):
        client.on_switch("Переключение на резервную модель")
        return [], False

    monkeypatch.setattr(pipeline, "segment", segment)
    monkeypatch.setattr(pipeline, "review", lambda *args, **kwargs: ([], []))
    monkeypatch.setattr(pipeline, "simulate", lambda *args: (Simulation(), []))
    path = tmp_path / "spec.txt"
    path.write_text("Example requirement", encoding="utf-8")
    progress = []
    result = pipeline.analyze(
        path, Settings(model="primary", base_url="https://primary.example/v1", api_key="test"),
        progress=progress.append,
    )
    assert "Переключение на резервную модель" in progress
    assert result.passport.switch_reason == SwitchedClient.switch_reason
    assert result.passport.model_runs[0].model_dump() == SwitchedClient.model_runs[0]
    assert result.passport.model == "primary"
    assert result.passport.provider == "primary.example"
