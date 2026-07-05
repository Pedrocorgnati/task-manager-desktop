from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QToolButton,
    QWidget,
)


def select_word_or_next_occurrence(widget) -> None:  # noqa: ANN001
    """Ctrl+D estilo VS Code sobre um widget de texto Qt.

    Sem selecao: seleciona a palavra sob o cursor. Com selecao: salta para a
    proxima ocorrencia identica (case-sensitive), com wrap-around no fim do
    documento. Adaptacao single-selection — o Qt nao tem multi-cursor nativo,
    entao em vez de acumular cursores movemos a selecao para a proxima palavra
    igual (o "selecionar palavra igual" pedido).
    """
    if widget is None:
        return
    cursor = widget.textCursor()
    if not cursor.hasSelection():
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        if cursor.hasSelection():
            widget.setTextCursor(cursor)
        return
    selected = cursor.selectedText()
    if not selected:
        return
    # find() busca a partir do fim da selecao atual -> proxima ocorrencia.
    if widget.find(selected):
        return
    wrap = widget.textCursor()
    wrap.movePosition(QTextCursor.MoveOperation.Start)
    widget.setTextCursor(wrap)
    widget.find(selected)


class FindBar(QWidget):
    """Barra de busca estilo VS Code (Ctrl+F) sobre um widget de texto Qt.

    Opera sobre qualquer QPlainTextEdit/QTextEdit/QTextBrowser via a API comum
    de QTextCursor (find/textCursor/setTextCursor). Navegacao: Enter/F3 proximo,
    Shift+Enter/Shift+F3 anterior, Esc fecha. Permanece oculta (altura zero) ate
    ser aberta, sem ocupar espaco no layout.
    """

    closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("markdownFindBar")
        self.setProperty("testid", "markdown-find-bar")
        self._target = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._input = QLineEdit(self)
        self._input.setObjectName("markdownFindInput")
        self._input.setProperty("testid", "markdown-find-input")
        self._input.setPlaceholderText("Localizar")
        self._input.setClearButtonEnabled(True)
        layout.addWidget(self._input, 1)

        self._count = QLabel("", self)
        self._count.setObjectName("markdownFindCount")
        self._count.setProperty("testid", "markdown-find-count")
        layout.addWidget(self._count)

        self._prev_btn = QToolButton(self)
        self._prev_btn.setObjectName("markdownFindPrev")
        self._prev_btn.setProperty("testid", "markdown-find-prev")
        self._prev_btn.setText("‹")
        self._prev_btn.setToolTip("Anterior (Shift+Enter)")
        self._prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._prev_btn)

        self._next_btn = QToolButton(self)
        self._next_btn.setObjectName("markdownFindNext")
        self._next_btn.setProperty("testid", "markdown-find-next")
        self._next_btn.setText("›")
        self._next_btn.setToolTip("Próximo (Enter)")
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._next_btn)

        self._close_btn = QToolButton(self)
        self._close_btn.setObjectName("markdownFindClose")
        self._close_btn.setProperty("testid", "markdown-find-close")
        self._close_btn.setText("✕")
        self._close_btn.setToolTip("Fechar (Esc)")
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._close_btn)

        self.setStyleSheet(
            "QWidget#markdownFindBar { background: #17181D;"
            " border-bottom: 1px solid rgba(255,255,255,0.10); }"
            "QLineEdit#markdownFindInput { background: #0D0E12; color: #F8FAFC;"
            " border: 1px solid #3B3D46; border-radius: 6px; padding: 4px 8px;"
            " font-size: 12px; selection-background-color: #FBBF24;"
            " selection-color: #111116; }"
            "QLineEdit#markdownFindInput:focus { border-color: #FBBF24; }"
            "QLabel#markdownFindCount { color: #A1A1AA; font-size: 11px; }"
            "QToolButton { background: transparent; color: #E4E4E7; border: none;"
            " border-radius: 6px; font-size: 15px; font-weight: 700;"
            " padding: 2px 6px; }"
            "QToolButton:hover { background: rgba(255,255,255,0.10); }"
        )

        self._input.textChanged.connect(self._on_text_changed)
        self._input.returnPressed.connect(self.find_next)
        self._prev_btn.clicked.connect(self.find_prev)
        self._next_btn.clicked.connect(self.find_next)
        self._close_btn.clicked.connect(self.close_bar)

        # Atalhos ativos enquanto o input tem foco (WidgetShortcut).
        for seq, slot in (
            ("Shift+Return", self.find_prev),
            ("Shift+Enter", self.find_prev),
            ("F3", self.find_next),
            ("Shift+F3", self.find_prev),
            ("Esc", self.close_bar),
        ):
            sc = QShortcut(QKeySequence(seq), self._input)
            sc.setContext(Qt.ShortcutContext.WidgetShortcut)
            sc.activated.connect(slot)

        self.hide()

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    def set_target(self, widget) -> None:  # noqa: ANN001
        self._target = widget

    def open_with_selection(self, widget) -> None:  # noqa: ANN001
        """Mostra a barra e prepopula com a selecao atual (como no VS Code)."""
        self._target = widget
        if widget is not None:
            cursor = widget.textCursor()
            if cursor.hasSelection():
                # selectedText usa U+2029 para quebras; busca so faz sentido
                # numa linha, entao mantemos so o trecho ate o primeiro break.
                self._input.setText(cursor.selectedText().split(" ")[0])
        self.show()
        self._input.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self._input.selectAll()
        self._update_count()

    def close_bar(self) -> None:
        self.hide()
        if self._target is not None:
            self._target.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.closed.emit()

    def find_next(self) -> None:
        self._find(backward=False, incremental=False)

    def find_prev(self) -> None:
        self._find(backward=True, incremental=False)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _on_text_changed(self, _text: str) -> None:
        self._find(backward=False, incremental=True)
        self._update_count()

    def _find(self, backward: bool, incremental: bool) -> bool:
        target = self._target
        text = self._input.text()
        if target is None or not text:
            return False
        if incremental:
            # Recomeca da posicao inicial da selecao corrente para que a
            # primeira ocorrencia seja encontrada conforme o usuario digita.
            cursor = target.textCursor()
            cursor.setPosition(cursor.selectionStart())
            target.setTextCursor(cursor)
        found = self._do_find(target, text, backward)
        if not found:
            # Wrap-around: recomeca do fim (backward) ou do topo (forward).
            cursor = target.textCursor()
            cursor.movePosition(
                QTextCursor.MoveOperation.End
                if backward
                else QTextCursor.MoveOperation.Start
            )
            target.setTextCursor(cursor)
            found = self._do_find(target, text, backward)
        return found

    @staticmethod
    def _do_find(target, text: str, backward: bool) -> bool:  # noqa: ANN001
        if backward:
            return target.find(text, QTextDocument.FindFlag.FindBackward)
        return target.find(text)

    def _update_count(self) -> None:
        target = self._target
        text = self._input.text()
        if target is None or not text:
            self._count.setText("")
            return
        doc = target.document()
        count = 0
        cursor = QTextCursor(doc)
        while True:
            cursor = doc.find(text, cursor)
            if cursor.isNull():
                break
            count += 1
        self._count.setText(f"{count} resultado(s)" if count else "Nenhum")
