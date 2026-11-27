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
