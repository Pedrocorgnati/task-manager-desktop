from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit, QTextEdit, QWidget

_SHORTCUT_MAP: dict[str, str] = {
    "Ctrl+E": "edit_selected",
    "Ctrl+D": "mark_done_selected",
    "Ctrl+F": "focus_search",
    "Ctrl+Backspace": "clear_search",
    "Up": "select_prev",
    "Down": "select_next",
    "Return": "open_selected",
    "Enter": "open_selected",
    "Delete": "delete_selected",
    "Escape": "esc_handler",
}

_SUPPRESS_IN_TEXT: frozenset[str] = frozenset(
    {
        "delete_selected",
        "select_prev",
        "select_next",
        "open_selected",
        "edit_selected",
        "mark_done_selected",
    }
)


class ShortcutsController:
    def __init__(self, window: QWidget, callbacks: dict[str, Callable[[], None]]) -> None:
        self._w = window
        self._callbacks = callbacks
        self._shortcuts: list[QShortcut] = []

    def install(self) -> None:
        for key, cb_key in _SHORTCUT_MAP.items():
            sc = QShortcut(QKeySequence(key), self._w)
            sc.setContext(Qt.ShortcutContext.WindowShortcut)
            sc.activated.connect(self._wrap(cb_key))
            self._shortcuts.append(sc)

    def _wrap(self, cb_key: str) -> Callable[[], None]:
        def _fire() -> None:
            if cb_key in _SUPPRESS_IN_TEXT and self._focus_is_text_input():
                return
            cb = self._callbacks.get(cb_key)
            if cb is None:
                return
            cb()

        return _fire

    def _focus_is_text_input(self) -> bool:
        # window.focusWidget() works even when the window is not the OS active
        # window (pytest-qt offscreen, popup overlays); QApplication.focusWidget()
        # is the broader fallback for focus that escaped the controlled window.
        focus = self._w.focusWidget() or QApplication.focusWidget()
        return isinstance(focus, (QPlainTextEdit, QTextEdit, QLineEdit))


__all__ = ["ShortcutsController"]
