from reqcheck.clarifier import questions
from reqcheck.findings import Evidence, Finding


def test_questions_are_prioritized_and_linked():
    finding = Finding(code="example", criterion="Полнота", severity="minor",
                      evidence=[Evidence(locator="2", quote="текст")],
                      explanation="Нет значения.", fix="Задать значение.", question="Какое значение?")
    result = questions([finding, finding.model_copy(update={"severity": "critical"})])
    assert len(result) == 1
    assert result[0].priority == "critical"
    assert result[0].finding_ids == ["D-002", "D-001"]
