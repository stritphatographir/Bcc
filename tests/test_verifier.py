from reqcheck.findings import Evidence, Finding
from reqcheck.loader import Source
from reqcheck.verifier import verify


def test_quote_must_match_at_stated_location():
    good = Finding(code="example", criterion="Полнота", severity="major",
                   evidence=[Evidence(locator="2", quote="точная цитата")],
                   explanation="Не задано условие.", fix="Задать условие.", question="Какое условие?")
    wrong = good.model_copy(update={"evidence": [Evidence(locator="1", quote="точная цитата")]})
    sources = [Source(locator="1", text="Другая строка"), Source(locator="2", text="точная   цитата")]
    findings, dropped = verify([good, wrong], sources)
    assert dropped == 1
    assert findings[0].evidence[0].quote == "точная   цитата"
