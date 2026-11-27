import pytest

from reqcheck.fintech import review_fintech
from reqcheck.loader import Source
from reqcheck.verifier import verify


def test_fintech_flags_rounding_and_retry_key_for_financial_operations():
    sources = [
        Source(locator="1", text="Выплата конвертируется в тенге по курсу на дату расчёта."),
        Source(locator="2", text="При повторной доставке платёжного поручения сохранить исходный результат."),
    ]
    findings = review_fintech(sources, [])
    assert {"money-rounding", "idempotency-key"} <= {item.code for item in findings}
    assert verify(findings, sources)[1] == 0


def test_fintech_skips_topics_when_document_is_not_financial():
    sources = [Source(locator="1", text="Повторная доставка сообщения; карта маршрута вывода отчёта.")]
    assert review_fintech(sources, []) == []


def test_timing_gap_cites_goal_and_delay():
    sources = [
        Source(locator="1", text="Клиент узнаёт о выплате в момент подтверждения.", section=("Цели",)),
        Source(locator="2", text="Сервис отправляет уведомление в течение двух минут.", section=("NFR",)),
    ]
    findings = review_fintech(sources, [])
    timing = next(f for f in findings if f.code == "goal-delay")
    assert [e.locator for e in timing.evidence] == ["1", "2"]


def test_retained_financial_identifiers_need_a_retention_policy():
    sources = [Source(locator="1", text="Система должна сохранять идентификаторы получателей платежей.")]
    policy = Source(locator="2", text="Идентификаторы удаляются через 90 дней после закрытия реестра.")
    read_only = [Source(locator="3", text="При поиске платежа использовать идентификатор получателя.")]
    prohibited = [Source(locator="4", text="Система не должна хранить идентификаторы получателей платежей.")]
    inline = [Source(locator="5", text="Хранить идентификаторы получателей платежей 90 дней.")]
    unrelated = Source(locator="6", text="Срок хранения журналов — 7 дней. Срок хранения идентификаторов: TBD.")

    findings = [item for item in review_fintech(sources, []) if item.code == "identifier-retention"]
    assert len(findings) == 1 and findings[0].evidence[0].locator == "1"
    assert verify(findings, sources)[1] == 0
    assert all(item.code != "identifier-retention" for item in review_fintech(sources + [policy], []))
    assert all(item.code != "identifier-retention" for item in review_fintech(read_only, []))
    assert all(item.code != "identifier-retention" for item in review_fintech(prohibited, []))
    assert all(item.code != "identifier-retention" for item in review_fintech(inline, []))
    assert any(item.code == "identifier-retention" for item in review_fintech(sources + [unrelated], []))


def test_dispatch_marker_requires_an_event_for_setting_it():
    records = [Source(locator="1", text="Хранить сумму выплаты и флаг отправки документа.")]
    confirmed = Source(locator="2", text="Флаг отправки документа устанавливается после подтверждения доставки.")
    confirmed_first = Source(locator="3", text="После подтверждения доставки система устанавливает флаг отправки документа.")
    external = Source(locator="4", text="Показывать статус доставки выплаты, полученный от банка без изменений.")
    rule = 'dispatch-marker-event'

    findings = [f for f in review_fintech(records, []) if f.code == rule]
    assert len(findings) == 1 and findings[0].evidence[0].locator == "1"
    assert verify(findings, records)[1] == 0
    assert all(f.code != rule for f in review_fintech(records + [confirmed], []))
    assert all(f.code != rule for f in review_fintech(records + [confirmed_first], []))
    assert all(f.code != rule for f in review_fintech([external], []))


@pytest.mark.parametrize(
    ("code", "trigger", "answer"),
    [
        ("cutoff-boundary", "Платежи принимаются до 16:30.", "Платежи принимаются до 16:30 включительно."),
        ("cutoff-late", "Платежи принимаются до 16:30.", "Платежи после 16:30 относятся к следующему расчётному дню."),
        ("conversion-target", "Выплаты конвертируются по курсу на дату покупки.",
         "Выплаты конвертируются в евро по курсу на дату покупки."),
        ("conversion-rate-missing", "Выплаты конвертируются по курсу на дату покупки.",
         "При отсутствии курса выплата откладывается до публикации курса."),
        ("conversion-aggregation", "Итоговая сумма нескольких платежей конвертируется по курсу на дату покупки.",
         "Каждая операция конвертируется отдельно по курсу своей валюты и даты, затем суммы складываются."),
        ("money-unit", "| Сумма перевода | 2 знака после запятой |",
         "Все денежные суммы хранятся в центах."),
        ("refund-negative-balance", "Сумма выплаты уменьшается на сумму возвратов.",
         "При отрицательном остатке долг переносится на следующий период."),
        ("refund-carry-balance", "Возвраты после формирования выплаты переносятся на следующий период.",
         "Если в следующем периоде нет положительного остатка, возврат переносится ещё на один период."),
        ("refund-formation-order", "Возвраты после формирования выплаты переносятся на следующий период.",
         "При совпадении времени возврата и формирования выплаты возврат входит в следующую выплату."),
        ("external-rejection", "Платёжное поручение передаётся банку.",
         "Если банк отклоняет поручение, система передаёт его оператору на исправление."),
        ("external-timeout", "Платёжное поручение передаётся банку.",
         "При тайм-ауте система запрашивает статус поручения у банка."),
        ("external-retry-key", "Платёжное поручение передаётся банку.",
         "При повторной отправке поручения используется исходный ключ идемпотентности."),
    ],
)
def test_fintech_reports_gap_until_document_answers_it(code, trigger, answer):
    context = Source(locator="1", text="Регламент выплат", heading=True)
    rule = Source(locator="2", text=trigger)
    sources = [context, rule]
    findings = review_fintech(sources, [])
    finding = next(item for item in findings if item.code == code)
    assert [(e.locator, e.quote) for e in finding.evidence] == [("2", trigger)]
    assert finding.question and finding.fix and finding.severity and finding.criterion
    assert verify(findings, sources)[1] == 0

    # The first and third answers replace the ambiguous wording itself.
    answered = [context] if code in {"cutoff-boundary", "conversion-target"} else sources.copy()
    answered.append(Source(locator="3", text=answer))
    assert all(item.code != code for item in review_fintech(answered, []))


def test_cutoff_inclusion_for_another_time_does_not_answer_the_payment_rule():
    sources = [
        Source(locator="1", text="Платежи принимаются до 16:30."),
        Source(locator="2", text="Оператор работает до 19:00 включительно."),
    ]
    assert any(f.code == "cutoff-boundary" for f in review_fintech(sources, []))


def test_dispatch_deadline_does_not_hide_the_ambiguous_payment_cutoff():
    sources = [
        Source(locator="1", text="Платёжное поручение отправляется в банк не позднее 17:00."),
        Source(locator="2", text="В выплату включаются платежи, принятые до 16:30."),
    ]
    findings = [f for f in review_fintech(sources, []) if f.code == "cutoff-boundary"]
    assert [f.evidence[0].locator for f in findings] == ["2"]


def test_single_operation_conversion_does_not_imply_aggregation():
    sources = [
        Source(locator="1", text="Каждый платёж конвертируется в евро по отдельному курсу."),
        Source(locator="2", text="Система отображает оборот архива."),
    ]
    assert all(f.code != "conversion-aggregation" for f in review_fintech(sources, []))


@pytest.mark.parametrize(("code", "rule"), [
    ("external-timeout", "При тайм-ауте загрузки фото система запрашивает статус."),
    ("external-timeout", "При потере ответа банка на расчётный реестр система запрашивает его статус."),
    ("external-timeout", "При потере ответа внешнего шлюза на поручение система запрашивает его статус."),
    ("external-rejection", "При отказе банка принять расчётный реестр система уведомляет оператора."),
    ("external-rejection", "При отклонении поручения внешним шлюзом система уведомляет оператора."),
])
def test_unrelated_external_error_rule_does_not_suppress_finding(code, rule):
    sources = [
        Source(locator="1", text="Платёжное поручение передаётся банку."),
        Source(locator="2", text=rule),
    ]
    assert any(f.code == code for f in review_fintech(sources, []))


def test_matching_lost_bank_response_rule_suppresses_finding():
    sources = [
        Source(locator="1", text="Платёжное поручение передаётся банку."),
        Source(locator="2", text="При потере ответа банка на поручение система запрашивает его статус."),
    ]
    assert all(f.code != "external-timeout" for f in review_fintech(sources, []))


@pytest.mark.parametrize("key", ["новый ключ идемпотентности", "ключ идемпотентности"])
def test_retry_key_requires_explicit_reuse(key):
    sources = [
        Source(locator="1", text="Платёжное поручение передаётся банку."),
        Source(locator="2", text=f"При повторной отправке поручения используется {key}."),
    ]
    assert any(f.code == "external-retry-key" for f in review_fintech(sources, []))


def test_no_later_than_is_inclusive_but_still_needs_a_late_arrival_rule():
    source = Source(locator="1", text="Платежи принимаются не позднее 16:30.")
    codes = {f.code for f in review_fintech([source], [])}
    assert "cutoff-boundary" not in codes
    assert "cutoff-late" in codes


@pytest.mark.parametrize("currency", ["NOK", "гривны"])
def test_named_target_currency_suppresses_finding(currency):
    source = Source(locator="1", text=f"Выплаты конвертируются в {currency} по курсу на дату покупки.")
    assert all(f.code != "conversion-target" for f in review_fintech([source], []))


def test_zero_balance_rule_does_not_answer_negative_balance():
    sources = [
        Source(locator="1", text="Сумма выплаты уменьшается на сумму возвратов."),
        Source(locator="2", text="При нулевом остатке выплата блокируется."),
    ]
    assert any(f.code == "refund-negative-balance" for f in review_fintech(sources, []))


def test_money_units_in_other_fields_and_examples_do_not_fill_a_schema_gap():
    sources = [
        Source(locator="1", text="| Сумма перевода | EUR | 2 знака |"),
        Source(locator="2", text="| Комиссия | 2 знака |"),
        Source(locator="3", text="Пример выплаты: 100 евро."),
    ]
    findings = [f for f in review_fintech(sources, []) if f.code == "money-unit"]
    assert [f.evidence[0].locator for f in findings] == ["2"]
