from reqcheck.loader import Source
from reqcheck.structure import duplicated_rules, happy_path_diagrams, review_structure
from reqcheck.verifier import verify


def src(locator, text, *section, heading=False):
    return Source(locator=locator, text=text, section=section, heading=heading)


def test_happy_path_diagram_is_flagged_and_branching_one_is_not():
    sources = [
        src("1", "BPMN", "BPMN", heading=True),
        src("2", "Заявка → проверка → одобрение → выдача.", "BPMN"),
        src("3", "Sequence", "Sequence", heading=True),
        src("4", "Клиент → шлюз → банк. Если банк вернул ошибку → шлюз → клиент: отказ.", "Sequence"),
        src("5", "Архитектура", "Архитектура", heading=True),
        src("6", "Приложение → сервис → база.", "Архитектура"),
    ]
    findings = happy_path_diagrams(sources)
    assert len(findings) == 1 and [e.locator for e in findings[0].evidence] == ["2"]
    assert verify(findings, sources)[1] == 0


def test_rule_repeated_in_another_section_is_flagged_but_tables_are_not():
    sources = [
        src("1", "* **Р-1.** При смене тарифа накопленный остаток бонусов сохраняется.", "Требования"),
        src("2", "1. Смена тарифа сохраняет накопленный остаток бонусов.", "API", "Правила"),
        src("3", "| Смена тарифа | Накопленный остаток бонусов сохраняется |", "Критерии"),
        src("4", "Оплата проходит через шлюз эквайринга банка-партнёра.", "Интеграция"),
    ]
    findings = duplicated_rules(sources, [])
    assert len(findings) == 1
    assert [e.locator for e in findings[0].evidence] == ["1", "2"]
    assert verify(findings, sources)[1] == 0


def test_default_toggle_does_not_define_initial_numeric_value():
    sources = [
        src("2", "Оператор устанавливает интервал от 15 до 90 минут. По умолчанию автообновление отключено.", "Журнал"),
        src("3", "Оператор выбирает глубину от 2 до 10 уровней. По умолчанию глубина равна 4.", "Выгрузка"),
        src("4", "Оператор задаёт размер от 12 до 24 знаков. По умолчанию подсказки отключены.", "Печать"),
        src("5", "Начальный размер составляет 18 знаков.", "Печать"),
        src("6", "Оператор задаёт ёмкость от 20 до 80 единиц. По умолчанию ёмкость не задана.", "Планирование"),
        src("7", "По умолчанию интервал равен 10 минутам.", "Распределение"),
    ]
    findings = [item for item in review_structure(sources, []) if item.code == "missing-numeric-default"]
    assert len(findings) == 1
    assert findings[0].evidence[0].locator == "2"
    assert verify(findings, sources)[1] == 0
