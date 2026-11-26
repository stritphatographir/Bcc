from datetime import datetime, timezone
from threading import Lock
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, Field


class TraceEvent(BaseModel):
    type: Literal["stage", "llm"]
    agent: str
    status: str
    time: datetime
    duration_ms: int | None = None
    inputs: dict[str, int | str] = Field(default_factory=dict)
    outputs: dict[str, int | str] = Field(default_factory=dict)


class TraceLog:
    def __init__(self):
        self.events: list[TraceEvent] = []
        self._lock = Lock()

    def add(self, kind, agent, status, *, started=None, inputs=None, outputs=None):
        with self._lock:
            self.events.append(TraceEvent(
                type=kind, agent=agent, status=status, time=datetime.now(timezone.utc),
                duration_ms=round((perf_counter() - started) * 1000) if started is not None else None,
                inputs=inputs or {}, outputs=outputs or {},
            ))


def jsonl(events: list[TraceEvent]) -> str:
    return "".join(event.model_dump_json() + "\n" for event in events)
