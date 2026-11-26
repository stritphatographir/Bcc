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
