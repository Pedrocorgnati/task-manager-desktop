from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum


class Status(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskType(str, Enum):
    AGENT = "agent"
    DEV = "dev"
    HUMAN = "human"


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
            4: "Concluída",
        }
        return _LABELS[self.value]


class Color(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    GRAY = "gray"
    NEUTRAL = "neutral"


def parse_deps(s: str) -> list[str]:
    return [p.strip() for p in s.split(",") if p.strip()]


@dataclass
class Task:
    id: str
    title: str
    status: Status = Status.PENDING
    type: TaskType = TaskType.AGENT
    deps: list[str] = field(default_factory=list)
    notes: str = ""
    order_index: int = 0
    created_at: str = ""
    completed_at: str | None = None
    hidden_at: str | None = None


@dataclass
class Subtask:
    id: str
    task_id: str
    text: str
    done: bool = False
    color: str = "#FBBF24"
    order_index: int = 0
    state: int = 0
    notes: str = ""


__all__ = [
    "Color",
    "Sector",
    "Status",
    "Subtask",
    "Task",
    "TaskType",
    "parse_deps",
]
