from reqcheck.linter import lint
from reqcheck.loader import Source
from reqcheck.segmenter import segment


def test_rules_preserve_source():
    sources = [
        Source(locator="1", text="Ф-8. Система должна быстро ответить."),
        Source(locator="2", text="| REST type | GET |", section=("API",)),
        Source(locator="3", text="| URL | /cart/save |", section=("API",)),
    ]
    findings = lint(sources, segment(sources)[0])
    assert {"weak-word", "http-get-write"} <= {f.code for f in findings}
    assert all(e.quote in next(s.text for s in sources if s.locator == e.locator)
               for f in findings for e in f.evidence)


def test_markdown_contract_labels_and_optional_data_mapping():
    section = ("API",)
    sources = [
        Source(locator="1", text="| **HTTP method** | `GET` |", section=section),
        Source(locator="2", text="| **URL** | `/items/save` |", section=section),
        Source(locator="3", text="| **Schema** | — |", section=section),
        Source(locator="4", text="| `result` | string | — |", section=section),
    ]
    findings = lint(sources, [])
    assert [(f.code, f.evidence[0].locator) for f in findings] == [
        ("placeholder", "3"),
        ("http-get-write", "1"),
    ]


def test_request_media_type_is_paired_only_with_the_same_body_section():
    sources = [
        Source(locator="1", text="* **Content-Type:** `text/plain`", section=("Lookup", "Тело запроса")),
        Source(locator="2", text="Клиент отправляет запрос без тела.", section=("Lookup", "Тело запроса")),
        Source(locator="3", text="Content-Type: application/xml", section=("Lookup", "Response body")),
        Source(locator="4", text="Content-Type: text/csv", section=("Import", "Request body")),
        Source(locator="5", text="Тело не передаётся.", section=("List", "Request body")),
        Source(locator="6", text="Если задан фильтр, отправить Content-Type: application/xml.", section=("Search", "Request body")),
        Source(locator="7", text="Без фильтра клиент отправляет запрос без тела.", section=("Search", "Request body")),
        Source(locator="8", text="Отправить Content-Type: text/plain, даже если тело не передаётся.", section=("Legacy", "Request body")),
    ]
    findings = [f for f in lint(sources, []) if f.code == "content-type-without-body"]
    assert [[e.locator for e in f.evidence] for f in findings] == [["1", "2"]]
