from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QUrl, Signal
from PySide6.QtWidgets import (
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.ui._external_link import _open_external_link
from task_manager_desktop.ui.empty_state import EmptyStateLabel

if TYPE_CHECKING:
    from task_manager_desktop.core.models import Task


class MarkdownViewer(QWidget):
    """Painel direito — visualizador de notas Markdown (somente-leitura).

    Emite link_clicked para links HTTP/HTTPS detectados no conteúdo.
    """

    link_clicked = Signal(QUrl)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAccessibleName("Painel de notas da task")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._browser = QTextBrowser(self)
        self._browser.setObjectName("markdownBrowser")
        self._browser.setAccessibleName("Conteúdo das notas em Markdown")
        self._browser.setOpenLinks(False)
        self._browser.anchorClicked.connect(self._on_anchor_clicked)

        try:
            from task_manager_desktop.core.bootstrap import notes_assets_path
            self._browser.setSearchPaths([str(notes_assets_path())])
        except Exception:  # noqa: BLE001
            pass

        self._empty = EmptyStateLabel("", parent=self)
        self._empty.setAccessibleName("Sem task selecionada")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._browser)
        layout.addWidget(self._empty)

        self.set_task(None)

    def set_task(self, task: Task | None) -> None:
        if task is None:
            self._empty.set_text("Selecione uma task para ver as notas.")
            self._empty.setAccessibleName("Sem task selecionada")
            self._browser.setVisible(False)
            self._empty.setVisible(True)
        elif not task.notes:
            self._empty.set_text("Sem notas ainda. Volte para Editar e escreva a primeira nota.")
            self._empty.setAccessibleName("Task sem notas")
            self._browser.setVisible(False)
            self._empty.setVisible(True)
        else:
            self._browser.setMarkdown(task.notes)
            self._browser.verticalScrollBar().setValue(0)
            self._browser.setVisible(True)
            self._empty.setVisible(False)

    def has_notes(self) -> bool:
        return self._browser.isVisible()

    def _on_anchor_clicked(self, url: QUrl) -> None:
        _open_external_link(url)
        self.link_clicked.emit(url)
