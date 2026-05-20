from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QVBoxLayout, QWidget

from task_manager_desktop.ui.markdown_pane import MarkdownPane

if TYPE_CHECKING:
    from task_manager_desktop.core.models import Task
    from task_manager_desktop.repositories.task_repository import TaskRepository


class MarkdownReader(QWidget):
    """Wrapper de retrocompatibilidade sobre MarkdownPane.

    app.py usa esta classe diretamente; toda lógica vive em MarkdownPane.

    Proxy attributes para compatibilidade com testes existentes:
      _stack, _viewer, _editor, _on_edit_clicked, _on_cancel_clicked,
      _on_save_clicked, _show_io_error, _save_shortcut, _IDX_* constants.
    """

    # Index constants — viewer/placeholder share index 0 (empty state via MarkdownViewer)
    _IDX_PLACEHOLDER = 0
    _IDX_VIEWER = 0
    _IDX_EDITOR = 1

    switch_blocked = Signal(str)
    toggle_terminal_collapse_requested = Signal()
    send_to_terminal_requested = Signal(str)

    def __init__(
        self,
        repo: TaskRepository | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("testid", "markdown-reader")
        self._pane = MarkdownPane(repo=repo, parent=self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._pane)

        # Backward-compat shortcut (tests emit _save_shortcut.activated).
        # WidgetShortcut (default): fires only when this widget itself has focus — which
        # never happens during editing (the inner editor has focus). Avoids double-save.
        self._save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self._save_shortcut.activated.connect(self._pane._save)

        # Bubble: pane → reader (consumido pelo app.py para o vertical splitter terminal).
        self._pane.toggle_terminal_collapse_requested.connect(
            self.toggle_terminal_collapse_requested.emit
        )
        self._pane.send_to_terminal_requested.connect(
            self.send_to_terminal_requested.emit
        )

    def set_terminal_collapsed(self, collapsed: bool) -> None:
        """Atualiza o chevron do toolbar (▲ colapsado / ▼ expandido)."""
        self._pane._toolbar.set_terminal_collapsed(collapsed)

    # ------------------------------------------------------------------
    # Backward-compat proxy properties
    # ------------------------------------------------------------------
    @property
    def _stack(self):  # noqa: ANN201
        return self._pane._stack

    @property
    def _viewer(self):  # noqa: ANN201
        """Returns the inner QTextBrowser for backward compat."""
        return self._pane._viewer._browser

    @property
    def _editor(self):  # noqa: ANN201
        return self._pane._editor

    # ------------------------------------------------------------------
    # Backward-compat methods
    # ------------------------------------------------------------------
    def _on_edit_clicked(self) -> None:
        self._pane._enter_editor()

    def _on_cancel_clicked(self) -> None:
        self._pane._cancel()

    def _on_save_clicked(self) -> None:
        self._pane._save()

    def _show_io_error(self, exc: BaseException) -> None:
        self._pane._show_io_error(exc)

    # ------------------------------------------------------------------
    # Public API (espelho de MarkdownPane)
    # ------------------------------------------------------------------
    def show_task(self, task: Task) -> None:
        self._pane.set_task(task)

    def clear(self) -> None:
        self._pane.clear()

    def current_task_id(self) -> str | None:
        return self._pane.current_task_id()

    def is_editing(self) -> bool:
        return self._pane.is_editing()
