import re

from .findings import Evidence, Finding
from .loader import Source
from .segmenter import Requirement

WEAK = re.compile(
    r"\b(быстро|удобно|при необходимости|своевременно|достаточно|и/или|около|максимально|"
    r"как правило|по возможности|разумный срок|и т\.\s*[дп]\.)", re.I,
)
REQUEST_BODY = re.compile(r"\b(?:request body|тело запроса)\b", re.I)
MEDIA_TYPE_HEADER = re.compile(r"\bcontent-type\s*[:|]\s*[\w.+-]+/[\w.+-]+", re.I)
CONDITIONAL = re.compile(r"\b(?:если|когда|при\s+условии|if|when|unless)\b", re.I)
NO_REQUEST_BODY = re.compile(
    r"\b(?:тело(?:\s+запроса)?\s+не\s+(?:используется|переда[её]тся|предусмотрено)|"
    r"без\s+тела|no\s+request\s+body|request\s+body\s+is\s+not\s+(?:used|sent))\b", re.I,
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

    body_media_type = {}
    no_body = {}
    for index, source in enumerate(sources):
        body = source.text
        section = source.section[-1] if source.section else ""
        if not source.heading and REQUEST_BODY.search(section) and not CONDITIONAL.search(f"{section} {body}"):
            if MEDIA_TYPE_HEADER.search(re.sub(r"[*`_]", "", body)):
                body_media_type.setdefault(source.section, source)
            if NO_REQUEST_BODY.search(body):
                no_body.setdefault(source.section, source)
        if source.heading and re.search(r"требован|критери|согласующ|архитектур", body, re.I):
            if index == len(sources) - 1 or sources[index + 1].heading and len(sources[index + 1].section) <= len(source.section):
                add("empty-section", "Полнота", "major", [source], f"Раздел «{section}» пуст.",
                    "Добавить согласованные условия или явно указать неприменимость.",
                    f"Какие условия должны быть записаны в разделе «{section}»?")
        if re.search(
            r"\b(?:TBD|TODO|заполняются|не заполнен|не проставлены)\b|:\s*—\s*(?:\||$)|"
            r"^\|[^|]+\|\s*—\s*\|\s*$", body, re.I,
        ):
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

    for section, media_type in body_media_type.items():
        omitted = no_body.get(section)
        if omitted:
            add("content-type-without-body", "Согласованность", "major",
                [media_type] if media_type == omitted else [media_type, omitted],
                "Для тела запроса указан Content-Type, но тот же раздел говорит, что тело не передаётся. "
                "Неясно, следует ли клиенту отправлять этот заголовок при отсутствии тела.",
                "Убрать требование к заголовку для запроса без тела или описать тело и его формат.",
                "Должен ли клиент отправлять Content-Type при отсутствии тела запроса?")

    for index, source in enumerate(sources):
        table = re.sub(r"[*`]", "", source.text)
        if not re.search(r"\|\s*(?:REST type|HTTP(?: method)?|метод)\s*\|\s*GET\s*\|", table, re.I):
            continue
        for neighbor in sources[max(0, index - 4):index + 8]:
            if neighbor.section == source.section and re.search(r"сохранени|сохраняет|/(?:save|create|update|delete)", neighbor.text, re.I):
                add("http-get-write", "Согласованность", "critical", [source, neighbor],
                    "GET указан для операции, меняющей состояние.",
                    "Определить отдельный метод чтения и метод изменения с кодами ответа.",
                    "Какие HTTP-методы и коды ответа должны применяться для чтения и изменения?")
                break
    return result
