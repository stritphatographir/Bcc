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
