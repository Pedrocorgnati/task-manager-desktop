from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

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


@dataclass
class ControllerBundle:
    edit_selected: Callable[[], None] | None = field(default=None)
    mark_done_selected: Callable[[], None] | None = field(default=None)
    focus_search: Callable[[], None] | None = field(default=None)
    clear_search: Callable[[], None] | None = field(default=None)
    select_prev: Callable[[], None] | None = field(default=None)
    select_next: Callable[[], None] | None = field(default=None)
    open_selected: Callable[[], None] | None = field(default=None)
    delete_selected: Callable[[], None] | None = field(default=None)
    esc_handler: Callable[[], None] | None = field(default=None)


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
        focus = self._w.focusWidget() or QApplication.focusWidget()
        return isinstance(focus, (QPlainTextEdit, QTextEdit, QLineEdit))


def register_all(main_window: QWidget, bundle: ControllerBundle) -> list[QShortcut]:
    callbacks = {
        k: v
        for k, v in {
            "edit_selected": bundle.edit_selected,
            "mark_done_selected": bundle.mark_done_selected,
            "focus_search": bundle.focus_search,
            "clear_search": bundle.clear_search,
            "select_prev": bundle.select_prev,
            "select_next": bundle.select_next,
            "open_selected": bundle.open_selected,
            "delete_selected": bundle.delete_selected,
            "esc_handler": bundle.esc_handler,
        }.items()
        if v is not None
    }
    sc = ShortcutsController(main_window, callbacks)
    sc.install()
    return sc._shortcuts


__all__ = [
    "ShortcutsController",
    "ControllerBundle",
    "register_all",
    "_SHORTCUT_MAP",
    "_SUPPRESS_IN_TEXT",
]
