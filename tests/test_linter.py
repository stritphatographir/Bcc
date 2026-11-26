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
