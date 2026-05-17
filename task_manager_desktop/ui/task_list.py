from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.models import Sector, Task
from task_manager_desktop.core.sector import compute_sector, count_open_deps
from task_manager_desktop.ui.task_card import TaskCard

_SECTOR_ORDER = [Sector.ACTIVE, Sector.WAITING, Sector.BLOCKED, Sector.DONE]
_SECTOR_LABELS = {
    Sector.ACTIVE: "Em andamento",
    Sector.WAITING: "A fazer",
    Sector.BLOCKED: "Bloqueadas",
    Sector.DONE: "Concluídas",
}


def _task_sector(task: Task, all_tasks: dict[str, Task]) -> Sector:
    has_open = count_open_deps(task.deps, all_tasks) > 0
    sector, _ = compute_sector(task.status, has_open)
    return sector


class TaskList(QScrollArea):
    task_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setObjectName("TaskList")
        self._callbacks: dict = {}
        self._tasks: list[Task] = []

        self._container = QWidget(self)
        self._container.setObjectName("taskListContainer")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(0)
        self._layout.addStretch()
        self.setWidget(self._container)

    def set_callbacks(self, callbacks: dict) -> None:
        self._callbacks = callbacks

    def refresh(self, tasks: list[Task]) -> None:
        self._tasks = tasks
        self._rebuild(tasks)

    def _rebuild(self, tasks: list[Task]) -> None:
        # Clear existing widgets except the stretch at the end
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_tasks: dict[str, Task] = {t.id: t for t in tasks}

        if not tasks:
            empty = QLabel("Sem tasks. Clique em + para criar a primeira.", self._container)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setObjectName("emptyStateText")
            empty.setWordWrap(True)
            empty.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._layout.insertWidget(0, empty)
            return

        # Group tasks by sector
        groups: dict[Sector, list[Task]] = {s: [] for s in _SECTOR_ORDER}
        for task in tasks:
            sector = _task_sector(task, all_tasks)
            groups[sector].append(task)

        insert_pos = 0
        for sector in _SECTOR_ORDER:
            sector_tasks = groups[sector]

            header = self._make_sector_header(_SECTOR_LABELS[sector])
            self._layout.insertWidget(insert_pos, header)
            insert_pos += 1

            if not sector_tasks:
                empty_lbl = QLabel("vazio", self._container)
                empty_lbl.setObjectName("sectorEmpty")
                self._layout.insertWidget(insert_pos, empty_lbl)
                insert_pos += 1
            else:
                for task in sector_tasks:
                    card = TaskCard(task, self._callbacks, tasks, self._container)
                    card.selected.connect(self.task_selected.emit)
                    self._layout.insertWidget(insert_pos, card)
                    insert_pos += 1

    def _make_sector_header(self, label: str) -> QLabel:
        header = QLabel(label, self._container)
        header.setObjectName("sectorHeader")
        return header
