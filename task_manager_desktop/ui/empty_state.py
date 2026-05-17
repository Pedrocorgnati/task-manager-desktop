from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget


class EmptyStateLabel(QWidget):
    def __init__(
        self,
        text: str,
        hint: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAccessibleName(text)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)

        self._label = QLabel(text, self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setObjectName("emptyStateText")
        layout.addWidget(self._label)

        self._hint_label: QLabel | None = None
        if hint:
            self.setAccessibleDescription(hint)
            self._hint_label = QLabel(hint, self)
            self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._hint_label.setWordWrap(True)
            self._hint_label.setObjectName("emptyStateHint")
            self._hint_label.setProperty("muted", True)
            layout.addWidget(self._hint_label)

    def set_text(self, text: str) -> None:
        self._label.setText(text)

    def set_hint(self, hint: str) -> None:
        if self._hint_label is not None:
            self._hint_label.setText(hint)
