from typing import Literal

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    locator: str
    quote: str


class Finding(BaseModel):
    code: str
    criterion: str
    severity: Literal["critical", "major", "minor"]
    evidence: list[Evidence] = Field(min_length=1)
    explanation: str
    fix: str
    question: str
    stakeholder: Literal["Аналитик", "Владелец продукта", "Разработка", "Тестирование", "Безопасность"] = "Аналитик"
    requirements: list[str] = Field(default_factory=list)
    scope: Literal["requirement", "set"] = "set"
    agent: str = "linter"
