import json
import re
from collections import defaultdict

from .findings import Evidence, Finding
from .loader import Source
from .segmenter import Requirement

ROLES = {
    "request": re.compile(r"^(?:параметры запроса|запрос|request(?: parameters| body)?)\b", re.I),
    "response": re.compile(r"^(?:параметры ответа|ответ|response)\b", re.I),
    "statuses": re.compile(r"^(?:статусы|коды ответов|ошибки api|http status|status codes)\b", re.I),
}
FIELD_TYPES = {
    "int": "integer", "integer": "integer", "целое": "integer",
    "string": "string", "строка": "string", "text": "string",
    "bool": "boolean", "boolean": "boolean", "логический": "boolean",
    "decimal": "number", "number": "number", "число": "number",
    "object": "object", "array": "array",
}
STATUS = r"[1-5]\d{2}"
STATUS_START = re.compile(rf"^[#*\s]*({STATUS})\b(?:[*.\s]|$)")
VALIDATION = re.compile(r"\b(?:проверьте|неверн\w*|некоррект\w*|недопуст\w*|валидац\w*|invalid|validation)\b", re.I)
INPUT = re.compile(r"\b(?:параметр\w*|ввод\w*|запрос\w*|input|parameter\w*|payload)\b", re.I)
FORMAT = re.compile(r"\b(?:синтаксис\w*|формат\w*|syntax|format|malformed)\b", re.I)


def _validation_error_example(line: Source) -> bool:
    try:
        body = json.loads(line.text.strip().strip('`'))
    except ValueError:
        return False
    if not isinstance(body, dict):
        return False
    is_error = body.get('success') is False or any(
        str(body.get(key, '')).casefold() in {'error', 'failed', 'failure'} for key in ('status', 'result')
    )
    return is_error and any(
        isinstance(body.get(key), str) and VALIDATION.search(body[key]) for key in ('message', 'error', 'detail')
    )


def _fields(lines: list[Source]) -> dict[str, tuple[str, Source]]:
    fields = {}
    columns = None
    for line in lines:
        if not line.text.startswith("|"):
            columns = None
            continue
        cells = [cell.strip(" *`_") for cell in line.text.strip("|").split("|")]
        names = [i for i, cell in enumerate(cells) if cell.casefold() in {"параметр", "parameter", "поле", "field", "name"}]
        types = [i for i, cell in enumerate(cells) if cell.casefold() in {"формат", "format", "тип", "type"}]
        if names and types:
            columns = (names[0], types[0])
            continue
        if columns is None:
            continue
        name_index, type_index = columns
        if max(columns) >= len(cells):
            continue
        name, kind = cells[name_index], FIELD_TYPES.get(cells[type_index].casefold())
        if kind and re.fullmatch(r"[\w.-]+", name):
            fields[name] = (kind, line)
    return fields


def review_api(sources: list[Source], requirements: list[Requirement]) -> list[Finding]:
    contracts = defaultdict(lambda: defaultdict(list))
    for source in sources:
        for index, section in enumerate(source.section):
            role = next((key for key, pattern in ROLES.items() if pattern.search(section)), None)
            if role:
                contracts[source.section[:index]][role].append(source)
                break
    findings = []

    def add(code, lines, explanation, fix, question):
        locators = {line.locator for line in lines}
        findings.append(Finding(
            code=code, criterion="Контракт API", severity="major", scope="set", agent="api-contract",
            evidence=[Evidence(locator=line.locator, quote=line.text) for line in lines],
            explanation=explanation, fix=fix, question=question, stakeholder="Разработка",
            requirements=[r.id for r in requirements if r.source.locator in locators],
        ))

    for roles in contracts.values():
        request, response = _fields(roles["request"]), _fields(roles["response"])
        for field in sorted(request.keys() & response.keys()):
            given, request_line = request[field]
            returned, response_line = response[field]
            if given == returned:
                continue
            add("api-type-mismatch", [request_line, response_line],
                f"Поле «{field}» имеет тип {given} в запросе и {returned} в ответе.",
                "Установить единый тип или явно задать преобразование между запросом и ответом.",
                f"Какой тип должен использовать клиент для поля «{field}» в каждом направлении?")

        statuses = roles["statuses"]
        if not statuses:
            continue
        invalid_request = next((line for line in statuses if (match := STATUS_START.match(line.text))
                                and match[1] in {'400', '422'} and VALIDATION.search(line.text)
                                and INPUT.search(line.text)), None)
        if invalid_request:
            error_code = STATUS_START.match(invalid_request.text)[1]
            success_headings = {line.section: line for line in statuses if line.heading
                                and (match := STATUS_START.match(line.text)) and match[1].startswith('2')}
            for line in statuses:
                heading = success_headings.get(line.section)
                if heading is None or not _validation_error_example(line):
                    continue
                if FORMAT.search(invalid_request.text) and not FORMAT.search(line.text):
                    continue
                success_code = STATUS_START.match(heading.text)[1]
                add('api-validation-status-conflict', [heading, line, invalid_request],
                    f'Для ошибки проверки входных данных показан ответ HTTP {success_code}, '
                    f'но для неверных параметров указан HTTP {error_code}. Условие выбора кода не описано.',
                    'Задать единый код для ошибки проверки или явно разделить условия возврата двух ответов.',
                    f'Какой код получит клиент при недопустимом значении поля: {success_code} или {error_code}?')
        declared = set()
        for line in statuses:
            match = re.match(rf"^[#*\s]*({STATUS})\b(?:[*.\s]|$)", line.text)
            if match:
                declared.add(match[1])
        reported = set()
        for line in roles["response"] + statuses:
            if not re.search(r"статус|результат|возвращ|верн[еёу]|ответ|успех|\bHTTP\b", line.text, re.I):
                continue
            for code in re.findall(rf"\b({STATUS})\b", line.text):
                if code in declared or code in reported:
                    continue
                reported.add(code)
                add("api-undocumented-status", [line, statuses[0]] if line != statuses[0] else [line],
                    f"Упомянут HTTP-статус {code}, для которого нет отдельного описания в списке статусов.",
                    f"Описать условие возврата и схему ответа {code} или исправить ссылку на код.",
                    f"В каком случае возвращается HTTP {code} и какое тело получит клиент?")
    return findings
