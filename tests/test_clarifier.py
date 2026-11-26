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


def make(question, *quotes, severity="major", criterion="Однозначность", stakeholder="Аналитик"):
    return Finding(code="model-review", criterion=criterion, severity=severity,
                   evidence=[Evidence(locator=f"строка {i}", quote=q) for i, q in enumerate(quotes, 1)],
                   explanation="—", fix="—", question=question, stakeholder=stakeholder)


def test_paraphrases_about_the_same_lines_become_one_question_without_losing_any():
    result = questions([
        make("Почему для сохранения выбран GET?", "REST type GET", "curl -G", severity="critical"),
        make("Какой метод нужен для сохранения: GET или POST?", "REST type GET", "curl -G", severity="critical"),
        make("Какой код вернуть при ошибке суммы?", "200 ERROR"),
    ])
    assert len(result) == 2
    first = result[0]
    assert first.text == "Какой метод нужен для сохранения: GET или POST?"  # direct question leads
    assert first.related == ["Почему для сохранения выбран GET?"]
    assert first.finding_ids == ["D-001", "D-002"] and first.priority == "critical"


def test_shared_context_line_does_not_chain_unrelated_topics():
    goal = "Узнать о бюджете в момент покупки."
    result = questions([
        make("В какой единице сравнивать суммы?", "сумма в тиынах", goal),
        make("Как округлять тиыны?", "сумма в тиынах"),
        make("Какая задержка допустима?", goal, "в течение минуты"),
        make("Какая пиковая нагрузка?", "в течение минуты"),
    ])
    groups = [set(q.finding_ids) for q in result]
    assert {"D-001", "D-002"} in groups and {"D-003", "D-004"} in groups


def test_questions_are_routed_by_what_they_cite():
    result = questions([
        make("Какой тип у поля amount?", "| amount | integer |", criterion="Согласованность"),
        make("Что показывать на экране блокировки?", "последние четыре цифры карты",
             criterion="Конфиденциальность данных"),
    ])
    assert [q.stakeholder for q in result] == ["Разработка", "Безопасность"]


def test_interactive_mode_asks_only_the_top_questions(monkeypatch):
    from reqcheck.clarifier import terminal_answers

    items = questions([make(f"Вопрос {i}?", f"цитата {i}") for i in range(12)])
    asked = []
    monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "ответ")
    answers = terminal_answers(items, limit=3)
    assert len(asked) == 3 and len(answers) == 3
