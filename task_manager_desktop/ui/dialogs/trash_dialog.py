from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.models import Task

if TYPE_CHECKING:
    from task_manager_desktop.repositories.task_repository import TaskRepository


def _format_completed(iso_str: str | None) -> str:
    if not iso_str:
        return "—"
    try:
        # Strip trailing Z, fromisoformat handles "+00:00" suffixes
        normalized = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso_str[:16]


def _elide(text: str, max_chars: int = 60) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


class TrashDialog(QDialog):
    restore_requested = Signal(str)
    restore_failed = Signal(str)

    def __init__(
        self,
        repo: TaskRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._rows: dict[str, QFrame] = {}

        self.setWindowTitle("Lixeira")
        self.setMinimumSize(480, 360)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setAccessibleName("Lixeira de tasks")

        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        title = QLabel("Lixeira", self)
        title.setObjectName("trashDialogTitle")
        outer.addWidget(title)

        self._stack = QStackedWidget(self)

        # Index 0 — empty placeholder
        self._placeholder = QLabel("Nenhuma task na lixeira.", self)
        self._placeholder.setObjectName("trashEmptyPlaceholder")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stack.addWidget(self._placeholder)

        # Index 1 — scroll area with rows
        scroll = QScrollArea(self)
        scroll.setObjectName("trashScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(6)
        self._rows_layout.addStretch(1)
        scroll.setWidget(self._rows_container)
        self._stack.addWidget(scroll)

        outer.addWidget(self._stack, 1)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        btns.rejected.connect(self.reject)
        btns.accepted.connect(self.accept)
        outer.addWidget(btns)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def reload(self) -> None:
        for row in list(self._rows.values()):
            row.setParent(None)
            row.deleteLater()
        self._rows.clear()

        tasks = self._repo.list_trash()
        for task in tasks:
            self._add_row(task)

        self._stack.setCurrentIndex(1 if tasks else 0)

    def remove_row(self, task_id: str) -> None:
        row = self._rows.pop(task_id, None)
        if row is not None:
            row.setParent(None)
            row.deleteLater()
        if not self._rows:
            self._stack.setCurrentIndex(0)

    def row_ids(self) -> list[str]:
        return list(self._rows.keys())

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _add_row(self, task: Task) -> None:
        row = QFrame(self._rows_container)
        row.setObjectName("trashRow")
        row.setProperty("task_id", task.id)
        row.setFrameShape(QFrame.Shape.StyledPanel)

        h = QHBoxLayout(row)
        h.setContentsMargins(8, 6, 8, 6)
        h.setSpacing(12)

        lbl_id = QLabel(task.id, row)
        lbl_id.setObjectName("trashRowId")
        lbl_id.setFixedWidth(80)

        lbl_title = QLabel(_elide(task.title or "(sem título)"), row)
        lbl_title.setObjectName("trashRowTitle")
        lbl_title.setMinimumWidth(240)

        lbl_date = QLabel(_format_completed(task.completed_at), row)
        lbl_date.setObjectName("trashRowDate")
        lbl_date.setFixedWidth(140)

        btn_restore = QPushButton("Restaurar", row)
        btn_restore.setObjectName("trashRowRestore")
        btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restore.clicked.connect(lambda _checked=False, tid=task.id: self._on_restore(tid))

        h.addWidget(lbl_id)
        h.addWidget(lbl_title, 1)
        h.addWidget(lbl_date)
        h.addWidget(btn_restore)

        # Insert before the trailing stretch
        self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)
        self._rows[task.id] = row

    def _on_restore(self, task_id: str) -> None:
        try:
            self._repo.restore(task_id)
        except (sqlite3.OperationalError, sqlite3.IntegrityError) as exc:
            self.restore_failed.emit(str(exc))
            from task_manager_desktop.ui.dialogs import ErrorDialog

            ErrorDialog.show_io_error(self, exc, self._repo.db_path)
            return

        self.remove_row(task_id)
        self.restore_requested.emit(task_id)
