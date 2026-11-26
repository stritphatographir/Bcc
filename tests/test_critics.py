from reqcheck.critics import review
from reqcheck.llm import LLMError
from reqcheck.loader import Source


def test_partial_failure_does_not_erase_successes():
    class Client:
        def ask(self, task, data, schema):
            if "согласованность" in task:
                raise LLMError("offline")
            return schema(findings=[])

    findings, failed = review([Source(locator="1", text="Описание")], [], Client())
    assert findings == []
    assert "Согласованность" in failed
    assert "Полнота сценариев" not in failed
