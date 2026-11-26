from reqcheck.findings import Evidence, Finding
from reqcheck.loader import Source
from reqcheck.qa import build_qa
from reqcheck.segmenter import Requirement
from reqcheck.simulator import Case, Condition, DecisionTable, Rule, evaluate


def test_qa_connects_source_test_and_rewrite():
    one = Source(locator="1", text="Запрос на 10 единиц получает скидку.", section=("Правила",))
    two = Source(locator="2", text="Запрос 10 единиц: скидка есть.", section=("Критерии приёмки",))
    req = Requirement(id="R-01", document_id=None, quote=one.text, source=one)
    sim, _ = evaluate(DecisionTable(
        rules=[Rule(scope="скидка", label="порог", conditions=[Condition(field="единицы", operator="ge", value=10)],
                    outcome={"скидка": True}, evidence=Evidence(locator="1", quote=one.text))],
        cases=[Case(scope="скидка", label="порог", facts={"единицы": 10}, expected={"скидка": True},
                    evidence=Evidence(locator="2", quote=two.text))],
    ), [one, two], [req])
    defect = Finding(code="gap", criterion="Полнота", severity="major", evidence=[Evidence(locator="1", quote=one.text)],
                     requirements=[req.id], explanation="Нет единицы.", fix="Скидка от 10 штук.", question="Какие единицы?")
    qa = build_qa([req], [defect], sim, [one, two])
    assert not qa.uncovered
    assert qa.tests[0].requirements == ["R-01"]
    assert "Тогда" in qa.tests[0].gherkin
    assert qa.trace[0].acceptance == ["2"]
    assert qa.trace[0].tests == [case.id for case in qa.tests]
    assert "+Скидка от 10 штук." in qa.rewrites[0].diff
