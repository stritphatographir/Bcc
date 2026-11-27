from reqcheck.api_contract import review_api
from reqcheck.loader import Source
from reqcheck.verifier import verify


def test_contract_type_mismatch_and_undocumented_status():
    def source(locator, text, section):
        return Source(locator=locator, text=text, section=("Spec", "REST API", section))

    sources = [
        source("1", "| Parameter | Format | Logic |", "Параметры запроса"),
        source("2", "| `balance` | integer | При записи |", "Параметры запроса"),
        source("3", "Успех, если возвращается 200 или 201.", "Ответ"),
        source("4", "| Parameter | Format | Logic |", "Ответ"),
        source("5", "| `balance` | string | При успехе |", "Ответ"),
        source("6", "**200.** Успешное обновление.", "Статусы"),
    ]
    findings = review_api(sources, [])
    assert [f.code for f in findings] == ["api-type-mismatch", "api-undocumented-status"]
    assert "201" in findings[1].explanation and "200" not in findings[1].explanation
    assert verify(findings, sources)[1] == 0


def test_validation_error_has_two_http_statuses_only_within_one_operation():
    def src(i, text, op, heading):
        return Source(locator=str(i), text=text, section=(op, "Статусы", heading))

    sources = [
        Source(locator="6", text="201 Created", section=("Создание", "Статусы", "201 Created"), heading=True),
        src(1, '{"status":"error","message":"Проверьте дату окончания"}', "Создание", "201 Created"),
        src(2, "**400.** Неверные параметры запроса.", "Создание", "400 Bad Request"),
        Source(locator="9", text="200 OK", section=("Отмена", "Статусы", "200 OK"), heading=True),
        src(3, '{"status":"error","message":"Сервис временно недоступен"}', "Отмена", "200 OK"),
        src(4, "**400.** Неверные параметры запроса.", "Отмена", "400 Bad Request"),
        src(5, '{"status":"error","message":"Проверьте формат даты"}', "Чтение", "200 OK"),
        Source(locator="10", text="200 OK", section=("Оплата", "Статусы", "200 OK"), heading=True),
        src(7, '{"status":"error","message":"Проверьте доступный остаток"}', "Оплата", "200 OK"),
        src(8, "**400.** Некорректный формат запроса.", "Оплата", "400 Bad Request"),
    ]
    findings = [f for f in review_api(sources, []) if f.code == "api-validation-status-conflict"]
    assert [[e.locator for e in f.evidence] for f in findings] == [["6", "1", "2"]]
    assert verify(findings, sources)[1] == 0
