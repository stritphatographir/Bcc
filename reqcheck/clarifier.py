import re

from pydantic import BaseModel

from .findings import Finding

PRIORITY = {"critical": 0, "major": 1, "minor": 2}
LABEL = {"critical": "критический", "major": "существенный", "minor": "незначительный"}


def finding_id(index: int) -> str:
    return f"D-{index + 1:03}"


class Question(BaseModel):
    id: str
    priority: str
    stakeholder: str
    text: str
    finding_ids: list[str]
    related: list[str] = []


class Answer(BaseModel):
    question: Question
    text: str


ROUTES = (
    ("Безопасность", r"безопас|конфиденц|персональн|\bpii\b|\bpci\b|\bpan\b|токен|шифр|маскир|утечк|privacy|security"),
    ("Разработка", r"\bhttp\b|\brest\b|\bapi\b|endpoint|curl|json|content-type|query|метод|статус|код ответа"
                   r"|тип пол|integer|string|контракт|интерфейс|идемпотент|повторн[аяо]+ доставк"),
    ("Тестирование", r"тестир|тест-кейс|критери[йия] приёмк|приёмк|проверяем|verif|testab"),
    ("Владелец продукта", r"бизнес.цел|ценност|метрик[аи] успех|business goal|kpi"),
)


def _stakeholder(finding: Finding) -> str:
    """Route a question to the person who can answer it, using what the finding cites, not only its label."""
    if finding.stakeholder != "Аналитик":
        return finding.stakeholder
    if finding.code == "http-get-write":
        return "Разработка"
    # Order matters: the criterion is the strongest signal, the question and quotes are weaker ones.
    for text in (finding.criterion, finding.question, " ".join(e.quote for e in finding.evidence)):
        lowered = text.casefold()
        for stakeholder, pattern in ROUTES:
            if re.search(pattern, lowered):
                return stakeholder
    return "Аналитик"


def _places(finding: Finding) -> set[str]:
    return {" ".join(e.quote.split()).casefold() for e in finding.evidence}


def _rank(text: str) -> tuple[int, int]:
    """Lower is better: a question with explicit alternatives («A или B?») that is not rhetorical («Почему…»)."""
    rhetorical = text.casefold().startswith(("почему", "зачем"))
    return (int(rhetorical) * 2 - int(" или " in text), len(text))


def questions(findings: list[Finding], *, overlap: float = 0.5) -> list[Question]:
    """Turn findings into a short, prioritized list of questions.

    Critics often ask the same thing in different words about the same lines. Findings are grouped by
    complete linkage: every pair in a group asks the same question or cites overlapping quotes
    (Jaccard >= `overlap`). Complete linkage keeps a context line quoted by unrelated findings from
    chaining different topics together. The best-phrased question leads the group; the other distinct
    questions stay attached as `related`, so nothing an analyst should answer is lost.
    """
    ranked = [(index, finding) for index, finding in sorted(enumerate(findings), key=lambda row: PRIORITY[row[1].severity])
              if " ".join(finding.question.split())]
    keys = [" ".join(f.question.split()).casefold().rstrip("?") for _, f in ranked]
    places = [_places(f) for _, f in ranked]

    def similar(a, b):
        union = places[a] | places[b]
        return keys[a] == keys[b] or bool(union) and len(places[a] & places[b]) / len(union) >= overlap

    # One pass is exact for complete linkage: a merged group only adds constraints, so a group that was
    # rejected once can never be accepted later.
    groups = [[node] for node in range(len(ranked))]
    i = 0
    while i < len(groups):
        j = i + 1
        while j < len(groups):
            if all(similar(a, b) for a in groups[i] for b in groups[j]):
                groups[i] = sorted(groups[i] + groups.pop(j))
            else:
                j += 1
        i += 1

    result = []
    for number, members in enumerate(sorted(groups, key=lambda group: group[0]), 1):
        primary = ranked[members[0]][1]  # highest severity, earliest finding: decides the priority
        texts = list(dict.fromkeys(" ".join(ranked[m][1].question.split()) for m in members))
        candidates = [m for m in members if ranked[m][1].severity == primary.severity]
        owner = members[0]
        if _rank(" ".join(primary.question.split()))[0] > 0:  # rhetorical «Почему…»: let a direct question lead
            owner = min(candidates, key=lambda m: _rank(" ".join(ranked[m][1].question.split())))
        lead = " ".join(ranked[owner][1].question.split())
        result.append(Question(id=f"Q-{number:02}", text=lead, priority=primary.severity,
                               stakeholder=_stakeholder(ranked[owner][1]),
                               finding_ids=[finding_id(ranked[m][0]) for m in members],
                               related=[t for t in texts if t.casefold().rstrip("?") != lead.casefold().rstrip("?")]))
    return result


def terminal_answers(items: list[Question], limit: int | None = None) -> list[Answer]:
    """Ask only the top `limit` questions (they are already sorted by priority; default 8)."""
    if not items:
        return []
    if limit is None:
        import os
        limit = int(os.getenv("REQCHECK_INTERACTIVE_LIMIT", "8"))
    items = items[:limit]
    print(f"Главные вопросы: {len(items)}. Введите ответ, Enter для пропуска или :готово для окончания.")
    answers = []
    for item in items:
        print(f"\n{item.id} · {item.stakeholder} · {LABEL[item.priority]} · {', '.join(item.finding_ids)}")
        try:
            text = input(f"{item.text}\n> ").strip()
        except EOFError:
            break
        if text == ":готово":
            break
        if text:
            answers.append(Answer(question=item, text=text))
    return answers
