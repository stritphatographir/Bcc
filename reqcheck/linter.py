import re

from .findings import Evidence, Finding
from .loader import Source
from .segmenter import Requirement

WEAK = re.compile(
    r"\b(быстро|удобно|при необходимости|своевременно|достаточно|и/или|около|максимально|"
    r"как правило|по возможности|разумный срок|и т\.\s*[дп]\.)", re.I,
)


def lint(sources: list[Source], requirements: list[Requirement]) -> list[Finding]:
    result = []

    def add(code, criterion, severity, evidence, explanation, fix, question, requirement=None):
        result.append(Finding(
            code=code, criterion=criterion, severity=severity,
            evidence=[Evidence(locator=s.locator, quote=s.text) for s in evidence],
            explanation=explanation, fix=fix, question=question,
            requirements=[requirement.id] if requirement else [],
            scope="requirement" if requirement else "set",
        ))

    for requirement in requirements:
        match = WEAK.search(requirement.quote)
        if match:
            word = match[0]
            add("weak-word", "Проверяемость", "major", [requirement.source],
                f"Формулировка «{word}» допускает разные критерии проверки.",
                f"Заменить «{word}» измеримым условием с единицей и пределом.",
                f"Какое наблюдаемое условие или предельное значение заменит «{word}»?", requirement)

    for index, source in enumerate(sources):
        body = source.text
        section = source.section[-1] if source.section else ""
        if source.heading and re.search(r"требован|критери|согласующ|архитектур", body, re.I):
            if index == len(sources) - 1 or sources[index + 1].heading and len(sources[index + 1].section) <= len(source.section):
                add("empty-section", "Полнота", "major", [source], f"Раздел «{section}» пуст.",
                    "Добавить согласованные условия или явно указать неприменимость.",
                    f"Какие условия должны быть записаны в разделе «{section}»?")
        if re.search(r"\b(?:TBD|TODO|заполняются|не заполнен|не проставлены)\b|:\s*—\s*(?:\||$)|\|\s*—\s*\|\s*$", body, re.I):
            add("placeholder", "Полнота", "major", [source], f"В разделе «{section}» осталось поле шаблона.",
                "Заполнить поле согласованным значением и указать ответственного.",
                f"Какое значение и кто утверждает для незаполненного поля раздела «{section}»?")
        if body.startswith("|") and re.search(r"да\s*/\s*нет", body, re.I):
            add("checklist", "Модифицируемость", "minor", [source], "Результат проверки не отмечен.",
                "Указать результат проверки и ссылку на подтверждение.",
                f"Какой результат проверки следует зафиксировать для строки «{body.split('|')[1].strip()}»?")
        if re.fullmatch(r"[|\s]+", body) and re.search("согласующ", section, re.I):
            add("approvers", "Трассируемость", "minor", [source], "В строке согласования нет ответственных.",
                "Указать подразделения, ответственных и отметки согласования.",
                "Кто утверждает эту версию документа от каждого подразделения?")
        if re.search(r"\bтенге\b", body, re.I) and re.search(r"\bтиын\w*", body, re.I):
            add("mixed-units", "Согласованность", "major", [source],
                "В одном правиле хранения указаны разные денежные единицы. Правило перевода отсутствует.",
                "Задать единицу сравнения сумм, пересчёт и округление.",
                "В какой единице сравниваются суммы и как округляются дробные значения?")

    for index, source in enumerate(sources):
        if not re.search(r"\|\s*(?:REST type|HTTP(?: method)?|метод)\s*\|\s*GET\s*\|", source.text, re.I):
            continue
        for neighbor in sources[max(0, index - 4):index + 8]:
            if neighbor.section == source.section and re.search(r"сохранени|сохраняет|/(?:save|create|update|delete)", neighbor.text, re.I):
                add("http-get-write", "Согласованность", "critical", [source, neighbor],
                    "GET указан для операции, меняющей состояние.",
                    "Определить отдельный метод чтения и метод изменения с кодами ответа.",
                    "Какие HTTP-методы и коды ответа должны применяться для чтения и изменения?")
                break
    return result
