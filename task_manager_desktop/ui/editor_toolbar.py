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
    """Barra de ferramentas do editor de notas Markdown."""

    save_requested = Signal()
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(TOOLBAR_H)
        self.setAccessibleName("Barra de ferramentas do editor de notas")
        self.setObjectName("editorToolbar")

        self.btn_save = QPushButton("Salvar", self)
        self.btn_save.setProperty("class", "success")
        self.btn_save.setAccessibleName("Salvar notas e voltar ao visualizador")

        self.btn_cancel = QPushButton("Cancelar", self)
        self.btn_cancel.setProperty("class", "ghost")
        self.btn_cancel.setAccessibleName("Descartar alterações e voltar ao visualizador")

        shortcut_hint = QLabel("Ctrl+S / Esc", self)
        shortcut_hint.setObjectName("editorShortcutHint")
        shortcut_hint.setAccessibleName("Atalhos: Ctrl+S para salvar, Esc para cancelar")
        shortcut_hint.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)
        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_cancel)
        layout.addStretch()
        layout.addWidget(shortcut_hint)

        self.btn_save.clicked.connect(self.save_requested.emit)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
