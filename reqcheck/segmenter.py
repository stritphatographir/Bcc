import re

from pydantic import BaseModel

from .llm import Client, LLMError
from .loader import Source

EXPLICIT = re.compile(
    r"^(?:[-*+]\s+)?\**((?:[A-Za-zА-Яа-яЁё]{1,10}[-–]\d+(?:\.\d+)*|\d+(?:\.\d+)*))[.)]?\**\s+"
)
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[А-ЯЁA-Z])")


class Requirement(BaseModel):
    id: str
    document_id: str | None
    source: Source
    quote: str


class Selection(BaseModel):
    line: int
    quote: str


class Selections(BaseModel):
    requirements: list[Selection]


def _table(lines: list[Source], index: int) -> bool:
    text = lines[index].text
    return (
        text.startswith("|")
        and not re.fullmatch(r"[| :\-]+", text)
        and not (index + 1 < len(lines) and re.fullmatch(r"[| :\-]+", lines[index + 1].text))
    )


def segment(lines: list[Source], client: Client | None = None) -> tuple[list[Requirement], bool]:
    candidates = []
    prose = []
    for index, source in enumerate(lines):
        body = source.text
        if source.heading or re.fullmatch(r"[-*_]{3,}", body):
            continue
        match = EXPLICIT.match(body)
        if match:
            for quote in SENTENCE.split(body[match.end():]):
                candidates.append((index, match[1], quote))
        elif _table(lines, index):
            section = source.section[-1] if source.section else ""
            if not re.search(r"ревью|согласующ|общие сведения|чек-лист", section, re.I):
                candidates.append((index, None, body))
        elif not body.startswith(("|", "```")):
            prose.append(index)

    failed = False
    for start in range(0, len(prose), 35):
        batch = prose[start:start + 35]
        found = set()
        if client:
            try:
                answer = client.ask(
                    "Выдели атомарные требования: бизнес-правила, ограничения, поведение, данные и интерфейсы. "
                    "Не включай только вводные сведения. Для каждого фрагмента верни line и дословную "
                    "непрерывную цитату из text указанной строки. Разделяй независимые условия.",
                    [{"line": i, "section": lines[i].section, "text": lines[i].text} for i in batch],
                    Selections,
                )
                for entry in answer.requirements:
                    quote = entry.quote.strip()
                    if entry.line in batch and quote and quote in lines[entry.line].text:
                        candidates.append((entry.line, None, quote))
                        found.add(entry.line)
            except LLMError:
                failed = True
        for index in batch:
            if index in found:
                continue
            source = lines[index]
            if re.search(r"требован|критери|правил|ограничен", " ".join(source.section[1:]), re.I) or re.search(
                r"долж(?:ен|на|но|ны)|обязан|запрещен|не допускается|^[-*+] ", source.text, re.I,
            ):
                candidates.extend((index, None, quote) for quote in SENTENCE.split(source.text))

    ordered = sorted(dict.fromkeys(candidates), key=lambda row: (row[0], lines[row[0]].text.find(row[2])))
    return [
        Requirement(id=f"R-{number:02}", document_id=label, source=lines[index], quote=quote)
        for number, (index, label, quote) in enumerate(ordered, 1)
    ], failed
