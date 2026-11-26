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


class Answer(BaseModel):
    question: Question
    text: str


def questions(findings: list[Finding]) -> list[Question]:
    by_text: dict[tuple[str, str], Question] = {}
    for index, finding in sorted(enumerate(findings), key=lambda row: PRIORITY[row[1].severity]):
        text = " ".join(finding.question.split())
        if not text:
            continue
        key = (finding.stakeholder, text.casefold().rstrip("?"))
        if key not in by_text:
            by_text[key] = Question(
                id=f"Q-{len(by_text) + 1:02}", text=text, priority=finding.severity,
                stakeholder=finding.stakeholder, finding_ids=[],
            )
        by_text[key].finding_ids.append(finding_id(index))
    return list(by_text.values())


def terminal_answers(items: list[Question]) -> list[Answer]:
    if not items:
        return []
    print("Введите ответ, Enter для пропуска или :готово для окончания.")
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
