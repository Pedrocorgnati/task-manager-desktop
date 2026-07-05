from __future__ import annotations

import re
import unicodedata
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
    PERMANENT = 5
    # Setor manual: a task fica retida em "Em preparação" enquanto sua
    # estrategia e escrita, ate que um botao de status a devolva ao fluxo.
    EM_PREPARACAO = 6

    def label_pt(self) -> str:
        _LABELS: dict[int, str] = {
            1: "Em andamento",
            2: "A fazer",
            3: "Bloqueada",
            4: "Concluída",
            5: "Permanentes",
            6: "Em preparação",
        }
        return _LABELS[self.value]


class Color(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    GRAY = "gray"
    NEUTRAL = "neutral"


def parse_deps(s: str) -> list[str]:
    return [p.strip() for p in s.split(",") if p.strip()]


def slugify(text: str) -> str:
    """Converte um titulo em slug com hifens.

    'Lead Hunting Engine' -> 'lead-hunting-engine'. Remove acentos, baixa a
    caixa e troca qualquer sequencia de caracteres nao alfanumericos por um
    unico hifen, sem hifens nas pontas. Retorna 'task' quando o titulo nao
    produz nenhum caractere util (ex.: so simbolos).
    """
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug or "task"


def default_workspace_root(title: str) -> str:
    """Caminho-semente do workspace SystemForge a partir do titulo da task.

    Padrao 'output/workspace/{titulo-com-hifen}' usado no seed das tasks
    existentes (migracao v11) e como sugestao no formulario de criacao.
    """
    return f"output/workspace/{slugify(title)}"


@dataclass
class Task:
    id: str
    title: str
    status: Status = Status.PENDING
    # O tipo (agent/dev/human) NAO vive mais na task: cada parte do trabalho e
    # uma subtask com seu proprio tipo (ver Subtask.type, migration v10 dropou
    # a coluna tasks.type). O TaskType continua existindo para as subtasks.
    deps: list[str] = field(default_factory=list)
    notes: str = ""
    order_index: int = 0
    created_at: str = ""
    completed_at: str | None = None
    hidden_at: str | None = None
    favorito: bool = False
    permanente: bool = False
    # Marcadores de ranqueamento extras (migration v12), irmãos de `favorito`:
    # cada um soma +1 no score de ordenacao do setor (ver sort_sector_tasks).
    # `coin_favorite` e a moeda; `dot_favorite` e a bolinha. Persistidos como
    # colunas booleanas em `tasks`, exatamente como `favorito`.
    coin_favorite: bool = False
    dot_favorite: bool = False
    # Flag manual do setor "Em preparação" (migration v8). Quando True a task e
    # retida nesse setor independentemente de pending/in_progress; qualquer
    # mudanca de status pelos botoes do card zera a flag.
    em_preparacao: bool = False
    # Caminho do workspace do repositorio SystemForge associado a esta task
    # (migration v11). Campo obrigatorio no formulario; o botao de play do card
    # cola este valor na janela focada.
    workspace_root: str = ""


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
    # Tipo da subtask (agent/dev/human). Default AGENT. Persistido na coluna
    # `type` da tabela `subtasks` (migration v9). E o unico portador de tipo no
    # dominio — a task em si nao tem mais tipo (migration v10).
    type: TaskType = TaskType.AGENT


@dataclass
class ClockTimer:
    id: str
    title: str
    duration_seconds: int = 0
    remaining_seconds: int = 0
    ends_at: str = ""
    color: str = "#71717A"
    state: str = "running"
    paused: bool = False
    paused_at: str | None = None
    # Discrimina a div dona do timer: "normal" (div Timers) | "daily" (div
    # Daily Timers). Conjuntos independentes — cada div lista/cria só o seu kind.
    kind: str = "normal"
    created_at: str = ""
    updated_at: str = ""


__all__ = [
    "Color",
    "ClockTimer",
    "Sector",
    "Status",
    "Subtask",
    "Task",
    "TaskType",
    "default_workspace_root",
    "parse_deps",
    "slugify",
]
