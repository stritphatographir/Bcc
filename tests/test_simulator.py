from reqcheck.loader import Source
from reqcheck.simulator import Condition, DecisionTable, evaluate


def test_simulation_keeps_a_documented_counterexample():
    sources = [
        Source(locator="1", text="До 10 минут заявка остаётся открытой."),
        Source(locator="2", text="Через 9 минут заявка закрыта."),
    ]
    table = DecisionTable.model_validate({
        "rules": [{
            "scope": "заявка", "label": "срок заявки",
            "conditions": [{"field": "минуты", "operator": "lt", "value": 10}],
            "outcome": {"статус": "открыта"},
            "evidence": {"locator": "1", "quote": sources[0].text},
        }],
        "cases": [{
            "scope": "заявка", "label": "проверка срока",
            "facts": {"минуты": 9}, "expected": {"статус": "закрыта"},
            "evidence": {"locator": "2", "quote": sources[1].text},
        }],
    })
    result, findings = evaluate(table, sources, [])
    assert {case.status for case in result.scenarios} == {"conflict", "uncovered"}
    assert len(findings) == 1
    assert findings[0].severity == "critical"
    assert [e.locator for e in findings[0].evidence] == ["2", "1"]
    assert "9" in findings[0].explanation


def test_simulation_rejects_a_case_with_fabricated_evidence():
    table = DecisionTable.model_validate({
        "rules": [],
        "cases": [{
            "scope": "заявка", "label": "подложный сценарий",
            "facts": {"срок": 3}, "expected": {"статус": "закрыта"},
            "evidence": {"locator": "1", "quote": "этой строки нет"},
        }],
    })
    result, findings = evaluate(table, [Source(locator="1", text="Срок наступил.")], [])
    assert result.scenarios == [] and findings == []
    assert result.dropped == 1


def test_simulation_synthesizes_an_overlap_between_rules():
    sources = [
        Source(locator="1", text="Сумма от 100 включает комиссию."),
        Source(locator="2", text="Сумма до 100 включительно без комиссии."),
    ]
    table = DecisionTable.model_validate({
        "rules": [
            {
                "scope": "платёж", "label": f"правило {i}",
                "conditions": [{"field": "сумма", "operator": operator, "value": 100}],
                "outcome": {"комиссия": fee},
                "evidence": {"locator": source.locator, "quote": source.text},
            }
            for i, (source, operator, fee) in enumerate(zip(sources, ("ge", "le"), (True, False)), 1)
        ],
        "cases": [],
    })
    result, findings = evaluate(table, sources, [])
    assert [row.facts["сумма"] for row in result.scenarios if row.status == "conflict"] == [100]
    assert len(findings) == 1


def test_not_equal_requires_comparable_types():
    condition = Condition(field="retry_count", operator="ne", value=2)
    assert condition.accepts(3)
    assert not condition.accepts("2")
    assert not condition.accepts(False)


def test_conflicting_acceptance_cases_can_share_one_source_line():
    source = Source(locator="1", text="После повтора A. После повтора B.")
    table = DecisionTable.model_validate({
        "rules": [],
        "cases": [{
            "scope": "операция", "label": f"повтор {outcome}",
            "facts": {"повтор": True}, "expected": {"результат": outcome},
            "evidence": {"locator": "1", "quote": f"После повтора {outcome}."},
        } for outcome in ("A", "B")],
    })
    result, findings = evaluate(table, [source], [])
    assert len(findings) == 1
    assert [scenario.status for scenario in result.scenarios] == ["conflict", "conflict"]
