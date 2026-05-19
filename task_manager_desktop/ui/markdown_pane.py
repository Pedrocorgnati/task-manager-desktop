from __future__ import annotations

import dataclasses
import sqlite3
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QHideEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.exceptions import TaskNotFoundError
from task_manager_desktop.ui.editor_toolbar import EditorToolbar
from task_manager_desktop.ui.markdown_editor import MarkdownEditor
from task_manager_desktop.ui.markdown_viewer import MarkdownViewer

if TYPE_CHECKING:
    from task_manager_desktop.core.models import Task
    from task_manager_desktop.repositories.task_repository import TaskRepository


class MarkdownPane(QWidget):
    """Painel direito de notas Markdown.

    O fluxo principal e editor-first: ao selecionar uma task, as notas ficam
    editaveis imediatamente. O viewer existe como preview alternavel.
    """

    notes_saved = Signal(str, str)   # (task_id, new_notes)
    editing_changed = Signal(bool)   # True = modo editor

    _IDX_VIEWER = 0
    _IDX_EDITOR = 1

    def __init__(
        self,
        repo: TaskRepository | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._repo = repo
        self._current_task: Task | None = None

        self.setObjectName("markdownPane")
        self.setAccessibleName("Painel de notas")

        # Botao mantido apenas como alias de retrocompatibilidade para testes/codigo antigo.
        # Ele nao entra no layout visual: a edicao agora e sempre direta.
        self._edit_btn = QPushButton("Editar", self)
        self._edit_btn.setObjectName("editButton")
        self._edit_btn.setProperty("class", "edit-btn")
        self._edit_btn.setToolTip("Editar notas desta task")
        self._edit_btn.setAccessibleName("Entrar no modo editor de notas")
        self._edit_btn.setVisible(False)

        # --- Header + pages ---
        self._toolbar = EditorToolbar(self)
        self._viewer = MarkdownViewer(self)
        self._editor = MarkdownEditor(self)

        # --- Stack ---
        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._viewer)   # index 0
        self._stack.addWidget(self._editor)   # index 1

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._toolbar)
        outer.addWidget(self._stack, 1)

        # Wire-up
        self._edit_btn.clicked.connect(self._enter_editor)
        self._toolbar.save_requested.connect(self._save)
        self._toolbar.cancel_requested.connect(self._cancel)
        self._toolbar.toggle_preview_requested.connect(self._toggle_preview)

        self._save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self._editor)
        self._save_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._save_shortcut.activated.connect(self._save)

        self.set_task(None)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_task(self, task: Task | None) -> None:
        """Define a task ativa. Faz save implicito se havia edicao pendente."""
        if (
            self._current_task is not None
            and self._editor.toPlainText() != (self._current_task.notes or "")
        ):
            self._implicit_save()

        self._current_task = task
        self._viewer.set_task(task)
        self._editor.setPlainText(task.notes if task else "")
        self._edit_btn.setVisible(False)
        self._editor.setEnabled(task is not None)
        self._toolbar.set_task_enabled(task is not None)
        if task is None:
            self._stack.setCurrentIndex(self._IDX_VIEWER)
            self._toolbar.set_preview_mode(True)
            self.editing_changed.emit(False)
        else:
            self._stack.setCurrentIndex(self._IDX_EDITOR)
            self._toolbar.set_preview_mode(False)
            self.editing_changed.emit(True)

    def is_editing(self) -> bool:
        return (
            self._current_task is not None
            and self._editor.toPlainText() != (self._current_task.notes or "")
        )

    def current_task_id(self) -> str | None:
        return self._current_task.id if self._current_task is not None else None

    def clear(self) -> None:
        self.set_task(None)

    def hideEvent(self, event: QHideEvent) -> None:
        self._editor.clearFocus()
        super().hideEvent(event)

    # ------------------------------------------------------------------
    # Public accessors (used by tests and external observers)
    # ------------------------------------------------------------------
    @property
    def stack(self) -> QStackedWidget:
        return self._stack

    @property
    def viewer(self) -> MarkdownViewer:
        return self._viewer

    @property
    def editor(self) -> MarkdownEditor:
        return self._editor

    @property
    def toolbar(self) -> EditorToolbar:
        return self._toolbar

    @property
    def btn_edit(self) -> QPushButton:
        return self._edit_btn

    # ------------------------------------------------------------------
    # Internal transitions
    # ------------------------------------------------------------------
    def _enter_editor(self) -> None:
        if self._current_task is None:
            return
        self._stack.setCurrentIndex(self._IDX_EDITOR)
        self._toolbar.set_preview_mode(False)
        self._editor.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.editing_changed.emit(True)

    def _toggle_preview(self) -> None:
        if self._current_task is None:
            return
        if self._stack.currentIndex() == self._IDX_EDITOR:
            preview_task = dataclasses.replace(
                self._current_task,
                notes=self._editor.toPlainText(),
            )
            self._viewer.set_task(preview_task)
            self._editor.clearFocus()
            self._stack.setCurrentIndex(self._IDX_VIEWER)
            self._toolbar.set_preview_mode(True)
            self.editing_changed.emit(False)
        else:
            self._enter_editor()

    def _save(self) -> None:
        if self._current_task is None:
            return
        current_index = self._stack.currentIndex()
        new_notes = self._editor.toPlainText()
        self._toolbar.btn_save.setEnabled(False)
        self._toolbar.btn_save.setText("Salvando...")
        self._toolbar.btn_toggle.setEnabled(False)
        self._editor.setReadOnly(True)
        try:
            if self._repo is not None:
                self._repo.update_notes(self._current_task.id, new_notes)
        except (TaskNotFoundError, sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as exc:
            # CL-085: erros de save de nota mostram Toast nao-bloqueante; editor permanece aberto
            self._show_save_error_toast(exc)
            return  # mantem stack em IDX_EDITOR
        finally:
            self._toolbar.btn_save.setEnabled(True)
            self._toolbar.btn_toggle.setEnabled(True)
            self._toolbar.btn_save.setText("Salvar")
            self._editor.setReadOnly(False)
        try:
            self._current_task = dataclasses.replace(self._current_task, notes=new_notes)
        except Exception:  # noqa: BLE001
            pass
        self._viewer.set_task(self._current_task)
        self._stack.setCurrentIndex(current_index)
        self._toolbar.set_preview_mode(current_index == self._IDX_VIEWER)
        self.editing_changed.emit(current_index == self._IDX_EDITOR)
        self.notes_saved.emit(self._current_task.id, new_notes)

    def _cancel(self) -> None:
        self._editor.setPlainText(self._current_task.notes if self._current_task else "")
        self._editor.clearFocus()
        self._stack.setCurrentIndex(self._IDX_VIEWER)
        self._toolbar.set_preview_mode(True)
        self.editing_changed.emit(False)

    def _implicit_save(self) -> None:
        if self._current_task is None or self._repo is None:
            return
        task_id = self._current_task.id
        new_notes = self._editor.toPlainText()
        try:
            self._repo.update_notes(task_id, new_notes)
        except Exception:  # noqa: BLE001
            self._show_toast_warning("Falha ao salvar notas da task anterior.")
            return
        try:
            self._current_task = dataclasses.replace(
                self._current_task, notes=new_notes
            )
        except Exception:  # noqa: BLE001
            pass
        self.notes_saved.emit(task_id, new_notes)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _show_save_error_toast(self, exc: BaseException) -> None:
        """Toast nao-bloqueante para falhas de save de notas (CL-085)."""
        self._show_toast_warning(f"Erro ao salvar: {exc}")

    def _show_io_error(self, exc: BaseException) -> None:
        """ErrorDialog modal para erros criticos irrecuperaveis de I/O do banco."""
        try:
            from task_manager_desktop.ui.dialogs import ErrorDialog
        except Exception:  # noqa: BLE001
            return
        db_path = getattr(self._repo, "db_path", "") if self._repo else ""
        ErrorDialog.show_io_error(self, exc, str(db_path))

    def _show_toast_warning(self, message: str) -> None:
        try:
            from task_manager_desktop.ui.toast import ToastWidget
            top = self.window()
            if isinstance(top, QWidget):
                toast = ToastWidget(top)
                toast.show_message(message)
        except Exception:  # noqa: BLE001
            pass
