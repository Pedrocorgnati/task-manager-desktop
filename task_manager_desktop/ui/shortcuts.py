from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLineEdit, QPlainTextEdit, QTextEdit, QWidget

_SHORTCUT_MAP: dict[str, str] = {
    "Ctrl+E": "edit_selected",
    "Ctrl+D": "mark_done_selected",
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

_SUPPRESS_IN_TERMINAL: frozenset[str] = frozenset(_SHORTCUT_MAP.values())


@dataclass
class ControllerBundle:
    edit_selected: Callable[[], None] | None = field(default=None)
    mark_done_selected: Callable[[], None] | None = field(default=None)
    select_prev: Callable[[], None] | None = field(default=None)
    select_next: Callable[[], None] | None = field(default=None)
    open_selected: Callable[[], None] | None = field(default=None)
    delete_selected: Callable[[], None] | None = field(default=None)
    esc_handler: Callable[[], None] | None = field(default=None)


class ShortcutsController(QObject):
    def __init__(self, window: QWidget, callbacks: dict[str, Callable[[], None]]) -> None:
        super().__init__(window)
        self._w = window
        self._callbacks = callbacks
        self._shortcuts: list[QShortcut] = []
        self._shortcut_callbacks: dict[QShortcut, str] = {}
        self._filter_installed = False

    def install(self) -> None:
        for key, cb_key in _SHORTCUT_MAP.items():
            sc = QShortcut(QKeySequence(key), self._w)
            sc.setContext(Qt.ShortcutContext.WindowShortcut)
            sc.activated.connect(self._wrap(cb_key))
            self._shortcuts.append(sc)
            self._shortcut_callbacks[sc] = cb_key
        self._install_focus_filter()
        self._sync_shortcuts_enabled()

    def _wrap(self, cb_key: str) -> Callable[[], None]:
        def _fire() -> None:
            if self._focus_is_terminal_input() and cb_key in _SUPPRESS_IN_TERMINAL:
                return
            if self._focus_is_text_input() and cb_key in _SUPPRESS_IN_TEXT:
                return
            cb = self._callbacks.get(cb_key)
            if cb is None:
                return
            cb()

        return _fire

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() in (
            QEvent.Type.FocusIn,
            QEvent.Type.FocusOut,
            QEvent.Type.WindowActivate,
            QEvent.Type.WindowDeactivate,
        ):
            self._sync_shortcuts_enabled()
        return False

    def _install_focus_filter(self) -> None:
        if self._filter_installed:
            return
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
            self._filter_installed = True

    def _sync_shortcuts_enabled(self) -> None:
        text_focus = self._focus_is_text_input()
        terminal_focus = self._focus_is_terminal_input()
        for shortcut in self._shortcuts:
            cb_key = self._shortcut_callbacks.get(shortcut)
            if cb_key is None:
                continue
            disabled = (
                (terminal_focus and cb_key in _SUPPRESS_IN_TERMINAL)
                or (text_focus and cb_key in _SUPPRESS_IN_TEXT)
            )
            shortcut.setEnabled(not disabled)

    def _focus_is_text_input(self) -> bool:
        focus = self._w.focusWidget() or QApplication.focusWidget()
        return isinstance(focus, (QPlainTextEdit, QTextEdit, QLineEdit))

    def _focus_is_terminal_input(self) -> bool:
        focus = self._w.focusWidget() or QApplication.focusWidget()
        if focus is None:
            return False
        try:
            from task_manager_desktop.ui.terminal.terminal_canvas import TerminalCanvas

            if isinstance(focus, TerminalCanvas):
                return True
        except Exception:  # noqa: BLE001
            pass
        return (
            focus.objectName() == "TerminalCanvas"
            or focus.property("testid") == "terminal-workspace-output"
        )


def register_all(main_window: QWidget, bundle: ControllerBundle) -> list[QShortcut]:
    callbacks = {
        k: v
        for k, v in {
            "edit_selected": bundle.edit_selected,
            "mark_done_selected": bundle.mark_done_selected,
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
