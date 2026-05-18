from __future__ import annotations

from PySide6.QtCore import (
    QAbstractAnimation,
    QEvent,
    QObject,
    QPauseAnimation,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    Qt,
)
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from task_manager_desktop.ui.theme import (
    TOAST_DURATION_MS,
    TOAST_FADE_IN_MS,
    TOAST_FADE_OUT_MS,
    TOAST_OFFSET,
)


class ToastWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setObjectName("toast")
        self.setAccessibleName("toast")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self._label = QLabel("", self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

        self.hide()

        self._anim: QSequentialAnimationGroup | None = None

        if parent is not None:
            parent.installEventFilter(self)

    def show_message(self, text: str, duration_ms: int = TOAST_DURATION_MS) -> None:
        if self._anim is not None:
            self._anim.stop()
        self._label.setText(text)
        self.setAccessibleDescription(text)
        self.adjustSize()
        self._reposition()
        self.setWindowOpacity(0.0)
        self.show()
        self._fade_in(duration_ms)

    def _reposition(self) -> None:
        parent = self.parent()
        if not isinstance(parent, QWidget):
            return
        pw = parent.width()
        ph = parent.height()
        x = pw - self.width() - TOAST_OFFSET
        y = ph - self.height() - TOAST_OFFSET
        self.move(x, y)

    def _fade_in(self, hold_ms: int) -> None:
        fade_in = QPropertyAnimation(self, b"windowOpacity", self)
        fade_in.setDuration(TOAST_FADE_IN_MS)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)

        pause = QPauseAnimation(hold_ms, self)

        fade_out = QPropertyAnimation(self, b"windowOpacity", self)
        fade_out.setDuration(TOAST_FADE_OUT_MS)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)

        self._anim = QSequentialAnimationGroup(self)
        self._anim.addAnimation(fade_in)
        self._anim.addAnimation(pause)
        self._anim.addAnimation(fade_out)
        self._anim.finished.connect(self.hide)
        self._anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def show_info(self, message: str) -> None:
        self.show_message(message)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Resize and obj is self.parent():
            self._reposition()
        return super().eventFilter(obj, event)
