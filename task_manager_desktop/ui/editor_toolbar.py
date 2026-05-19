from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from task_manager_desktop.ui.theme import TOOLBAR_H


class EditorToolbar(QWidget):
    """Header persistente do painel de notas Markdown."""

    save_requested = Signal()
    cancel_requested = Signal()
    toggle_preview_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(TOOLBAR_H)
        self.setAccessibleName("Barra de ferramentas do editor de notas")
        self.setObjectName("editorToolbar")

        self._title = QLabel("Notas Markdown", self)
        self._title.setObjectName("markdownHeaderTitle")
        self._title.setAccessibleName("Título do painel de notas")

        self._mode = QLabel("Editando", self)
        self._mode.setObjectName("markdownModePill")
        self._mode.setAccessibleName("Modo atual do painel de notas")

        self.btn_toggle = QPushButton("Preview", self)
        self.btn_toggle.setProperty("class", "ghost-sm")
        self.btn_toggle.setAccessibleName("Alternar entre edição e preview das notas")

        self.btn_save = QPushButton("Salvar", self)
        self.btn_save.setProperty("class", "success")
        self.btn_save.setAccessibleName("Salvar notas Markdown")

        self.btn_cancel = QPushButton("Cancelar", self)
        self.btn_cancel.setProperty("class", "ghost")
        self.btn_cancel.setAccessibleName("Descartar alterações e voltar ao visualizador")
        self.btn_cancel.setVisible(False)

        shortcut_hint = QLabel("Ctrl+S", self)
        shortcut_hint.setObjectName("editorShortcutHint")
        shortcut_hint.setAccessibleName("Atalho: Ctrl+S para salvar")
        shortcut_hint.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 0, 22, 0)
        layout.setSpacing(10)
        layout.addWidget(self._title)
        layout.addWidget(self._mode)
        layout.addStretch()
        layout.addWidget(shortcut_hint)
        layout.addWidget(self.btn_toggle)
        layout.addWidget(self.btn_cancel)
        layout.addWidget(self.btn_save)

        self.btn_save.clicked.connect(self.save_requested.emit)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        self.btn_toggle.clicked.connect(self.toggle_preview_requested.emit)

    def set_preview_mode(self, preview: bool) -> None:
        self._mode.setText("Preview" if preview else "Editando")
        self.btn_toggle.setText("Editar" if preview else "Preview")

    def set_task_enabled(self, enabled: bool) -> None:
        self.btn_save.setEnabled(enabled)
        self.btn_toggle.setEnabled(enabled)
