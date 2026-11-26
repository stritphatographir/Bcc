from reqcheck.diff import changes
from reqcheck.findings import Evidence, Finding


def make(quote, locator):
    return Finding(code="vague", criterion="Проверяемость", severity="major",
                   explanation="Нет критерия.", fix="Указать критерий.", question="Как измерить?",
                   evidence=[Evidence(locator=locator, quote=quote)])


def test_diff_matches_a_moved_quote_and_keeps_duplicate_occurrences():
    old = [make("быстро", "1"), make("быстро", "2"), make("удобно", "7")]
    new = [make("быстро", "8"), make("своевременно", "9")]
    missing, added, present = changes(old, new)
    assert [item.evidence[0].quote for item in missing] == ["быстро", "удобно"]
    assert [item.evidence[0].quote for item in added] == ["своевременно"]
    assert present == 1
