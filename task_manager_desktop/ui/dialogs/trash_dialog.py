from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
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
        normalized = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso_str[:16]


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
        self.setFixedSize(520, 360)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setAccessibleName("Lixeira de tasks")

        if parent is not None:
            parent_rect = parent.geometry()
            x = parent_rect.x() + (parent_rect.width() - 520) // 2
            y = parent_rect.y() + (parent_rect.height() - 360) // 2
            self.move(x, y)

        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(4)

        title = QLabel("Lixeira", self)
        title.setObjectName("trashDialogTitle")
        outer.addWidget(title)

        subtitle = QLabel("Tasks ocultadas nos últimos 30 dias", self)
        subtitle.setObjectName("trashSubtitle")
        outer.addWidget(subtitle)

        self._stack = QStackedWidget(self)

        # Index 0 — empty placeholder
        self._placeholder = QLabel("A Lixeira está vazia.", self)
        self._placeholder.setObjectName("trashEmptyPlaceholder")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setAccessibleName("Lixeira vazia")
        self._stack.addWidget(self._placeholder)

        # Index 1 — scroll area with rows
        scroll = QScrollArea(self)
        scroll.setObjectName("trashScroll")
        scroll.setProperty("class", "trash-scroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setAccessibleName("Lista de tasks na Lixeira")
        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)
        self._rows_layout.addStretch(1)
        scroll.setWidget(self._rows_container)
        self._stack.addWidget(scroll)

        outer.addWidget(self._stack, 1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Alias for reload() — used by controller after restore."""
        self.reload()

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
        from PySide6.QtGui import QFontMetrics

        row = QFrame(self._rows_container)
        row.setObjectName("trashRow")
        row.setProperty("task_id", task.id)
        row.setMinimumHeight(56)

        h = QHBoxLayout(row)
        h.setContentsMargins(16, 10, 16, 10)
        h.setSpacing(8)

        left = QVBoxLayout()
        left.setSpacing(2)

        lbl_id = QLabel(task.id, row)
        lbl_id.setObjectName("trashRowId")
        left.addWidget(lbl_id)

        title_text = task.title or "(sem título)"
        lbl_title = QLabel(row)
        lbl_title.setObjectName("trashRowTitle")
        fm = QFontMetrics(lbl_title.font())
        elided = fm.elidedText(title_text, Qt.TextElideMode.ElideRight, 300)
        lbl_title.setText(elided)
        if fm.horizontalAdvance(title_text) > 300:
            lbl_title.setToolTip(title_text)
        lbl_title.setMaximumWidth(300)
        left.addWidget(lbl_title)

        lbl_date = QLabel(_format_completed(task.completed_at), row)
        lbl_date.setObjectName("trashRowDate")
        left.addWidget(lbl_date)

        btn_restore = QPushButton("Restaurar", row)
        btn_restore.setObjectName("trashRowRestore")
        btn_restore.setProperty("class", "restore-btn")
        btn_restore.setAccessibleName(f"Restaurar task: {task.title}")
        btn_restore.setMinimumHeight(30)
        btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restore.clicked.connect(lambda _checked=False, tid=task.id: self._on_restore(tid))

        h.addLayout(left, 1)
        h.addWidget(btn_restore, 0, Qt.AlignmentFlag.AlignVCenter)

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
