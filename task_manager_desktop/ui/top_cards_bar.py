from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.ui.theme import ACCENT_GOLD, HEADER_BAR_H

_SETTINGS_KEY = "TopCards/values"
_MAX_CARDS = 4


class _TopValueCard(QWidget):
    def __init__(self, index: int, callback) -> None:
        super().__init__()
        self._index = index
        self._callback = callback
        self._value: str = ""

        self.setFixedHeight(46)
        self.setMinimumWidth(132)
        self.setObjectName("topCardsCard")
        self.setProperty("testid", f"top-cards-card-{index + 1}")
        self.setProperty("data-testid", f"top-cards-card-{index + 1}")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 5, 12, 6)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._plus_button = QPushButton("+", self)
        self._plus_button.setObjectName("topCardsPlus")
        self._plus_button.setProperty("testid", f"top-cards-plus-{index + 1}")
        self._plus_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._plus_button.setFixedSize(30, 30)
        self._plus_button.clicked.connect(self._on_edit_requested)
        self._plus_button.setToolTip("Clique para editar o texto do card")

        self._value_label = QLabel("", self)
        self._value_label.setObjectName("topCardsValue")
        self._value_label.setProperty("testid", f"top-cards-value-{index + 1}")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_label.setWordWrap(True)
        self._value_label.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(self._plus_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._value_label, alignment=Qt.AlignmentFlag.AlignCenter)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(212, 175, 55, 95))
        self.setGraphicsEffect(shadow)

        self._apply_rendered_state()

    def set_value(self, value: str) -> None:
        self._value = value
        self._apply_rendered_state()

    def value(self) -> str:
        return self._value

    def _apply_rendered_state(self) -> None:
        has_value = bool(self._value)
        self._value_label.setVisible(has_value)
        self._plus_button.setVisible(not has_value)
        if has_value:
            self._value_label.setText(self._value)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_edit_requested()
            event.accept()
            return
        super().mousePressEvent(event)

    def _on_edit_requested(self) -> None:
        text, ok = QInputDialog.getText(
            self,
            "Editar card",
            "Digite o valor do card:",
            text=self._value,
        )
        if ok:
            self._callback(self._index, text.strip())


class TopCardsBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("topCardsBar")
        self.setProperty("testid", "top-cards-bar")
        self.setFixedHeight(HEADER_BAR_H)

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 6, 12, 6)
        root.setSpacing(12)

        self._cards: list[_TopValueCard] = []
        self._cards = [
            _TopValueCard(index=index, callback=self._on_card_value_edited)
            for index in range(_MAX_CARDS)
        ]
        for card in self._cards:
            root.addWidget(card)

        self._apply_styles()
        self._load_values()

    def _on_card_value_edited(self, index: int, value: str) -> None:
        if 0 <= index < len(self._cards):
            self._cards[index].set_value(value)
            self._persist_values()

    def _load_values(self) -> None:
        settings = QSettings()
        raw_values = settings.value(_SETTINGS_KEY)
        values = self._coerce_values(raw_values)
        while len(values) < _MAX_CARDS:
            values.append("")
        if len(values) > _MAX_CARDS:
            values = values[:_MAX_CARDS]

        for index, card in enumerate(self._cards):
            card.set_value(values[index])

    def _persist_values(self) -> None:
        values = [card.value() for card in self._cards]
        QSettings().setValue(_SETTINGS_KEY, values)

    def _coerce_values(self, raw_values: object) -> list[str]:
        if not isinstance(raw_values, (list, tuple)):
            return []
        coerced: list[str] = []
        for item in raw_values:
            if isinstance(item, str):
                coerced.append(item)
        return coerced

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"""
QWidget#topCardsBar {{
    background: transparent;
}}
QWidget#topCardsCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #FFF8D1,
                                stop:0.18 #FDE68A,
                                stop:0.5 #FBBF24,
                                stop:0.78 {ACCENT_GOLD},
                                stop:1 #9A6A05);
    border: 1px solid #FFE8A3;
    border-radius: 11px;
}}
QWidget#topCardsCard[testid='top-cards-card-1'],
QWidget#topCardsCard[testid='top-cards-card-2'],
QWidget#topCardsCard[testid='top-cards-card-3'],
QWidget#topCardsCard[testid='top-cards-card-4'] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #FFF8D1,
                                stop:0.18 #FDE68A,
                                stop:0.5 #FBBF24,
                                stop:0.78 {ACCENT_GOLD},
                                stop:1 #9A6A05);
    border: 1px solid #FFE8A3;
}}
QWidget#topCardsCard:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #FFFFFF,
                                stop:0.22 #FFF2B8,
                                stop:0.54 #FFD43B,
                                stop:0.82 #E9B633,
                                stop:1 #B98208);
    border: 1px solid #FFF6D6;
}}
QPushButton#topCardsPlus {{
    font-size: 22px;
    font-weight: 900;
    color: #181103;
    border: 1px solid #5C3B02;
    border-radius: 15px;
    background: rgba(255, 255, 255, 0.30);
    min-width: 30px;
    min-height: 30px;
    max-width: 30px;
    max-height: 30px;
    padding: 0;
}}
QPushButton#topCardsPlus:hover {{
    background: rgba(255, 255, 255, 0.56);
    border-color: #111116;
}}
QLabel#topCardsValue {{
    font-weight: 900;
    font-size: 15px;
    color: #171103;
    padding: 0 2px;
}}
"""
        )
