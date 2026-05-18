from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QPlainTextEdit, QWidget


class MarkdownEditor(QPlainTextEdit):
    """Editor de texto simples para notas Markdown (JetBrains Mono)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("markdownEditor")
        self.setProperty("class", "md-editor")
        self.setAccessibleName("Editor de notas Markdown")
        self.setAccessibleDescription("Texto puro Markdown, fonte monoespacada")

        font = QFont("JetBrains Mono", 13)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        self.setPlaceholderText("Digite as notas em Markdown...")
