from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class HeaderBar(QWidget):
    new_task_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setObjectName("HeaderBar")
        self.setAccessibleName("Barra de cabeçalho")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        self.btn_new = QPushButton("+", self)
        self.btn_new.setProperty("class", "primary")
        self.btn_new.setFixedSize(36, 36)
        self.btn_new.setToolTip("Nova task (Ctrl+N)")
        self.btn_new.setAccessibleName("Criar nova task")
        self.btn_new.setAccessibleDescription("Atalho Ctrl+N")
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.clicked.connect(self.new_task_requested.emit)
        layout.addWidget(self.btn_new)

        layout.addStretch()

    def install_shortcut(self, parent: QWidget) -> None:
        shortcut = QShortcut(QKeySequence("Ctrl+N"), parent)
        shortcut.activated.connect(self.new_task_requested.emit)
