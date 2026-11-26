from reqcheck.critics import review, vote
from reqcheck.findings import Evidence, Finding
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


def test_majority_counts_each_ballot_once_and_keeps_confidence():
    issue = Finding(
        code="model-review", criterion="Полнота", severity="major",
        evidence=[Evidence(locator="1", quote="выполнить операцию")],
        explanation="Отсутствует результат операции.", fix="Указать результат.",
        question="Какой результат ожидается?",
    )
    duplicate = issue.model_copy()
    shared = issue.model_copy(update={"evidence": [Evidence(locator="1", quote="выполнить  операцию")]})
    unrelated = issue.model_copy(update={"criterion": "Однозначность"})
    result = vote([[issue, duplicate, unrelated], [shared], []])
    assert len(result) == 1
    assert result[0].confidence == 2 / 3


def test_failed_ballot_does_not_count_as_agreement():
    issue = Finding(
        code="model-review", criterion="Полнота", severity="major",
        evidence=[Evidence(locator="1", quote="операция")],
        explanation="Нет результата.", fix="Указать результат.", question="Какой результат?",
    )
    assert vote([[issue], None, None]) == []
