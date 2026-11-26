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
