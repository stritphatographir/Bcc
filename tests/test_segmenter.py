from reqcheck.loader import Source
from reqcheck.segmenter import segment


def test_explicit_atoms_and_acceptance():
    result, failed = segment([
        Source(locator="1", text="* **Ф-1.** Система открывает счёт. По умолчанию счёт пуст."),
        Source(locator="2", text="| Ввод | Действие | Результат |"),
        Source(locator="3", text="| --- | --- | --- |"),
        Source(locator="4", text="| 0 | Снять 1 | Отказ |"),
    ])
    assert [r.document_id for r in result] == ["Ф-1", "Ф-1", None]
    assert result[-1].source.locator == "4"
    assert result[1].quote == "По умолчанию счёт пуст."
    assert not failed
