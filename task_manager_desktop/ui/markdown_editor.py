from __future__ import annotations

import re

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QPlainTextEdit, QWidget

_HEADING_RE = re.compile(r"^(#{1,6})\s+")


class _MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, parent) -> None:  # noqa: ANN001
        super().__init__(parent)
        self._heading = QTextCharFormat()
        self._heading.setFontWeight(QFont.Weight.Black)
        self._heading.setForeground(QColor("#F8FAFC"))

    def set_light_mode(self, light: bool) -> None:
        self._heading.setForeground(QColor("#111116" if light else "#F8FAFC"))
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        if _HEADING_RE.match(text):
            self.setFormat(0, len(text), self._heading)


class _LineNumberArea(QWidget):
    def __init__(self, editor: MarkdownEditor) -> None:
        super().__init__(editor)
        self._editor = editor
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        self._editor.line_number_area_paint_event(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._editor.line_number_area_mouse_press(event.position().toPoint().y())
            event.accept()
            return
        super().mousePressEvent(event)


class MarkdownEditor(QPlainTextEdit):
    """Editor Markdown com line numbers, headings em bold e fold simples."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("markdownEditor")
        self.setProperty("class", "md-editor")
        self.setProperty("testid", "markdown-editor-input")
        self.setAccessibleName("Editor de notas Markdown")
        self.setAccessibleDescription("Texto Markdown com fonte monoespacada, numeração de linhas e seções recolhíveis")

        font = QFont("JetBrains Mono", 13)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        self._line_number_bg = QColor("#0D0E12")
        self._line_number_fg = QColor("#686C78")
        self._fold_fg = QColor("#FBBF24")
        self._line_number_area = _LineNumberArea(self)
        self._highlighter = _MarkdownHighlighter(self.document())

        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._update_line_number_area)

        self._update_line_number_area_width()
        self.setPlaceholderText("Digite as notas em Markdown...")

    def set_reader_theme(self, light: bool) -> None:
        if light:
            self._line_number_bg = QColor("#EFEDE5")
            self._line_number_fg = QColor("#52525B")
            self._fold_fg = QColor("#D97706")
        else:
            self._line_number_bg = QColor("#0D0E12")
            self._line_number_fg = QColor("#686C78")
            self._fold_fg = QColor("#FBBF24")
        self._highlighter.set_light_mode(light)
        self._line_number_area.update()

    def set_reader_font_size(self, size: int) -> None:
        font = self.font()
        font.setPointSize(size)
        self.setFont(font)
        self._update_line_number_area_width()
        self._line_number_area.update()

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 22 + self.fontMetrics().horizontalAdvance("9") * digits + 14

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def _update_line_number_area_width(self) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect=None, dy: int = 0) -> None:  # noqa: ANN001
        if dy:
            self._line_number_area.scroll(0, dy)
        elif rect is None:
            self._line_number_area.update()
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect is not None and rect.contains(self.viewport().rect()):
            self._update_line_number_area_width()

    def line_number_area_paint_event(self, event) -> None:  # noqa: ANN001
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), self._line_number_bg)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        width = self._line_number_area.width()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(self._line_number_fg)
                painter.drawText(0, top, width - 18, self.fontMetrics().height(), Qt.AlignmentFlag.AlignRight, number)

                level = self._heading_level(block.text())
                if level >= 2:
                    painter.setPen(self._fold_fg)
                    marker = ">" if block.userState() == 1 else "v"
                    painter.drawText(width - 14, top, 12, self.fontMetrics().height(), Qt.AlignmentFlag.AlignCenter, marker)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def line_number_area_mouse_press(self, y: int) -> None:
        block = self.firstVisibleBlock()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid():
            if block.isVisible() and top <= y <= bottom:
                if self._heading_level(block.text()) >= 2:
                    self.toggle_fold(block.blockNumber())
                return
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())

    def toggle_fold(self, block_number: int) -> None:
        heading = self.document().findBlockByNumber(block_number)
        if not heading.isValid():
            return
        level = self._heading_level(heading.text())
        if level < 2:
            return

        collapse = heading.userState() != 1
        heading.setUserState(1 if collapse else 0)

        block = heading.next()
        while block.isValid():
            child_level = self._heading_level(block.text())
            if child_level and child_level <= level:
                break
            block.setVisible(not collapse)
            block.setLineCount(0 if collapse else max(1, block.layout().lineCount()))
            block = block.next()

        self.document().markContentsDirty(heading.position(), self.document().characterCount())
        self.viewport().update()
        self._line_number_area.update()

    @staticmethod
    def _heading_level(text: str) -> int:
        match = _HEADING_RE.match(text)
        return len(match.group(1)) if match else 0
