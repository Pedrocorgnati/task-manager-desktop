from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Final


class Status(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskType(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class Sector(IntEnum):
    ACTIVE = 1
    WAITING = 2
    BLOCKED = 3
    DONE = 4

    def label_pt(self) -> str:
        _LABELS: dict[int, str] = {
            1: "Em andamento",
            2: "A fazer",
            3: "Bloqueada",
            4: "Concluida",
        }
        return _LABELS[self.value]


class Color(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    GRAY = "gray"
    NEUTRAL = "neutral"


PROJETO_DEFAULT: Final[str] = "outros"


def parse_deps(s: str) -> list[str]:
    return [p.strip() for p in s.split(",") if p.strip()]


def normalize_projeto(value: str | None) -> str:
    if value is None or not value.strip():
        return PROJETO_DEFAULT
    return value


@dataclass
class Task:
    id: str
    title: str
    status: Status = Status.PENDING
    type: TaskType = TaskType.ONLINE
    projeto: str = PROJETO_DEFAULT
    deps: list[str] = field(default_factory=list)
    notes: str = ""
    order_index: int = 0
    created_at: str = ""
    completed_at: str | None = None
    hidden_at: str | None = None


__all__ = [
    "Color",
    "PROJETO_DEFAULT",
    "Sector",
    "Status",
    "Task",
    "TaskType",
    "normalize_projeto",
    "parse_deps",
]
