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
