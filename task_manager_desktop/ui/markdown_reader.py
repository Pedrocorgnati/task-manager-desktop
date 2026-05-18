from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from task_manager_desktop.core.models import Task
    from task_manager_desktop.repositories.task_repository import TaskRepository


class MarkdownReader(QWidget):
    """Painel direito: visualizar e editar notas em Markdown.

    Modos via QStackedWidget:
      idx 0 = placeholder ("Selecione uma task")
      idx 1 = viewer (QTextBrowser.setMarkdown)
      idx 2 = editor (QPlainTextEdit + toolbar Salvar/Cancelar)
    """

    _IDX_PLACEHOLDER = 0
    _IDX_VIEWER = 1
    _IDX_EDITOR = 2

    switch_blocked = Signal(str)

    def __init__(
        self,
        repo: "TaskRepository | None" = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._current_task: "Task | None" = None

        self.setObjectName("markdownReader")
        self.setAccessibleName("Visualizador e editor de notas")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._stack = QStackedWidget(self)
        outer.addWidget(self._stack)

        self._placeholder = QLabel("Selecione uma task para ver as notas.", self)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setObjectName("emptyStateText")
        self._stack.addWidget(self._placeholder)

        self._viewer_widget = self._build_viewer()
        self._stack.addWidget(self._viewer_widget)

        self._editor_widget = self._build_editor()
        self._stack.addWidget(self._editor_widget)

        self._stack.setCurrentIndex(self._IDX_PLACEHOLDER)

    # ------------------------------------------------------------------
    # Constructors of inner views
    # ------------------------------------------------------------------
    def _build_viewer(self) -> QWidget:
        w = QWidget(self)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(8)

        topbar = QHBoxLayout()
        topbar.setSpacing(8)
        self._btn_edit = QPushButton("Editar", w)
        self._btn_edit.setObjectName("readerEditButton")
        self._btn_edit.setAccessibleName("Editar notas")
        self._btn_edit.clicked.connect(self._on_edit_clicked)
        topbar.addStretch(1)
        topbar.addWidget(self._btn_edit)
        layout.addLayout(topbar)

        self._viewer = QTextBrowser(w)
        self._viewer.setObjectName("notesViewer")
        self._viewer.setOpenExternalLinks(True)
        self._viewer.setOpenLinks(True)
        layout.addWidget(self._viewer, 1)
        return w

    def _build_editor(self) -> QWidget:
        w = QWidget(self)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(8)

        self._editor = QPlainTextEdit(w)
        self._editor.setObjectName("notesEditor")
        self._editor.setAccessibleName("Editor de notas em Markdown")
        layout.addWidget(self._editor, 1)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        toolbar.addStretch(1)
        self._btn_cancel = QPushButton("Cancelar", w)
        self._btn_cancel.setObjectName("readerCancelButton")
        self._btn_cancel.clicked.connect(self._on_cancel_clicked)
        toolbar.addWidget(self._btn_cancel)

        self._btn_save = QPushButton("Salvar", w)
        self._btn_save.setObjectName("readerSaveButton")
        self._btn_save.setDefault(True)
        self._btn_save.clicked.connect(self._on_save_clicked)
        toolbar.addWidget(self._btn_save)
        layout.addLayout(toolbar)

        shortcut = QShortcut(QKeySequence("Ctrl+S"), self._editor)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(self._on_save_clicked)
        self._save_shortcut = shortcut
        return w

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def show_task(self, task: "Task") -> None:
        """Exibe a task no viewer. Idempotente sobre o mesmo task_id (no flicker)."""
        if self._stack.currentIndex() == self._IDX_EDITOR:
            self.switch_blocked.emit(
                "Salve ou cancele as alteracoes antes de trocar de task."
            )
            return

        if (
            self._current_task is not None
            and self._current_task.id == task.id
            and self._stack.currentIndex() == self._IDX_VIEWER
            and (self._current_task.notes or "") == (task.notes or "")
        ):
            self._current_task = task
            return

        scroll_pos = (
            self._viewer.verticalScrollBar().value()
            if self._stack.currentIndex() == self._IDX_VIEWER
            else 0
        )
        same_task = (
            self._current_task is not None and self._current_task.id == task.id
        )
        self._current_task = task
        notes = task.notes or ""
        if not notes:
            self._viewer.setMarkdown("")
            self._viewer.setPlaceholderText(
                "Sem notas. Clique em Editar para comecar."
            )
        else:
            self._viewer.setMarkdown(notes)
        if same_task:
            self._viewer.verticalScrollBar().setValue(scroll_pos)
        self._stack.setCurrentIndex(self._IDX_VIEWER)

    def clear(self) -> None:
        """Volta ao placeholder sem task selecionada."""
        self._current_task = None
        self._editor.setPlainText("")
        self._stack.setCurrentIndex(self._IDX_PLACEHOLDER)

    def current_task_id(self) -> str | None:
        return self._current_task.id if self._current_task is not None else None

    def is_editing(self) -> bool:
        return self._stack.currentIndex() == self._IDX_EDITOR

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------
    def _on_edit_clicked(self) -> None:
        if self._current_task is None:
            return
        self._editor.setPlainText(self._current_task.notes or "")
        self._stack.setCurrentIndex(self._IDX_EDITOR)
        self._editor.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _on_cancel_clicked(self) -> None:
        if self._current_task is None:
            self._stack.setCurrentIndex(self._IDX_PLACEHOLDER)
            return
        notes = self._current_task.notes or ""
        self._viewer.setMarkdown(notes)
        self._stack.setCurrentIndex(self._IDX_VIEWER)

    def _on_save_clicked(self) -> None:
        if self._current_task is None or self._repo is None:
            return
        new_text = self._editor.toPlainText()
        try:
            self._repo.update_notes(self._current_task.id, new_text)
        except (sqlite3.OperationalError, sqlite3.IntegrityError) as exc:
            self._show_io_error(exc)
            return
        try:
            self._current_task.notes = new_text  # type: ignore[misc]
        except Exception:  # noqa: BLE001
            pass
        self._viewer.setMarkdown(new_text)
        self._stack.setCurrentIndex(self._IDX_VIEWER)

    # ------------------------------------------------------------------
    # Error helper
    # ------------------------------------------------------------------
    def _show_io_error(self, exc: BaseException) -> None:
        try:
            from task_manager_desktop.ui.dialogs import ErrorDialog
        except Exception:  # noqa: BLE001
            return
        db_path = ""
        if self._repo is not None:
            db_path = getattr(self._repo, "db_path", "") or ""
        ErrorDialog.show_io_error(self, exc, db_path)
