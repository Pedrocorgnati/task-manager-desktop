"""DataTest overlay para exibir testids visualmente em runtime.

Implementacao identica ao workflow-app:
- 4 modos: off, main, body (tudo exceto QAbstractButton), buttons (so QAbstractButton)
- Overlays parented ao centralWidget, posicionados com mapTo(central, ...)
- Click no overlay copia `data-testid="..."` para clipboard
- Feedback visual: vermelho normal -> verde 600ms apos copiar
"""

from __future__ import annotations

import re
from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QLabel,
    QMainWindow,
    QToolBar,
    QWidget,
)

_VALID_MODES = ("off", "main", "body", "buttons")
_MAIN_TESTIDS = frozenset(
    {
        "header",
        "task-list-pane",
        "task-list-active-section",
        "task-list-waiting-section",
        "subtask-clock-pane",
        "right-pane-vertical",
        "clock-pane",
        "terminal-workspace",
    }
)
# status-btn-{label}-{id} e status-control-{id}: todo o sufixo apos o prefixo
# e dinamico por instancia, entao colapsa o conjunto inteiro para {ID}.
_STATUS_ID_TOKEN = re.compile(r"(status-(?:btn|control)-)[a-z0-9-]+")
# task-card-{id}[-sufixo]: o id e dinamico (pode ter mais de um segmento),
# enquanto os sufixos abaixo sao estaveis (ver TaskCard). Ancora no sufixo
# conhecido e mascara apenas o trecho do id.
_TASK_CARD_SUFFIX = "content|id|deps|actions|edit|schedule|delete|title|status-column|menu"
_TASK_CARD_TESTID = re.compile(rf"^(task-card-).+?(-(?:{_TASK_CARD_SUFFIX}))?$")
# subtask ids tem o formato 'st-' + 10 chars hex (ver SubtaskPane._add_subtask).
_SUBTASK_ID_TOKEN = re.compile(r"\bst-[0-9a-f]{10}\b")


def _mask_dynamic_testid(raw: str) -> str:
    """Mascara tokens dinamicos de id como '{ID}' para exibicao estavel.

    Exemplos:
        'status-btn-ip-cew'         -> 'status-btn-{ID}'
        'status-control-vc9'        -> 'status-control-{ID}'
        'task-card-cew-title'       -> 'task-card-{ID}-title'
        'subtask-row-st-ab12cd34ef' -> 'subtask-row-{ID}'
    """
    raw = _STATUS_ID_TOKEN.sub(r"\1{ID}", raw)
    match = _TASK_CARD_TESTID.match(raw)
    if match:
        raw = f"{match.group(1)}{{ID}}{match.group(2) or ''}"
    return _SUBTASK_ID_TOKEN.sub("{ID}", raw)


def _is_main_testid(raw: str) -> bool:
    return raw in _MAIN_TESTIDS


class DataTestOverlay:
    """Gerencia overlays vermelhos sobre widgets com property('testid')."""

    _STYLE_NORMAL_BODY = (
        "background-color: rgba(220, 38, 38, 0.9); color: white;"
        " font-size: 11px; font-weight: 700; padding: 3px 6px;"
        " border-radius: 3px; border: none;"
    )
    _STYLE_NORMAL_BUTTON = (
        "background-color: rgba(37, 99, 235, 0.9); color: white;"
        " font-size: 11px; font-weight: 700; padding: 3px 6px;"
        " border-radius: 3px; border: none;"
    )
    _STYLE_COPIED = (
        "background-color: rgba(34, 197, 94, 0.9); color: white;"
        " font-size: 11px; font-weight: 700; padding: 3px 6px;"
        " border-radius: 3px; border: none;"
    )

    def __init__(self, main_window: QMainWindow) -> None:
        self._main_window = main_window
        self._overlays: list[QLabel] = []
        self._mode: str = "off"
        self._terminal_write_enabled = False
        self._terminal_writer: Callable[[str], None] | None = None

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_active(self) -> bool:
        return self._mode != "off"

    def set_mode(self, mode: str) -> None:
        """Define o modo. Modos validos: off, main, body, buttons.

        - off: esconde todos os overlays
        - main: mostra apenas os testids estruturais principais
        - body: mostra para todos EXCETO QAbstractButton
        - buttons: mostra APENAS QAbstractButton
        """
        if mode not in _VALID_MODES:
            mode = "off"
        self._mode = mode
        if mode == "off":
            self._hide_all()
        else:
            self._show_for_mode(mode)

    def toggle(self) -> None:
        """Alterna entre 'off' e 'main'."""
        self.set_mode("off" if self._mode != "off" else "main")

    def set_terminal_write_enabled(self, enabled: bool) -> None:
        self._terminal_write_enabled = bool(enabled)

    def set_terminal_writer(self, writer: Callable[[str], None] | None) -> None:
        self._terminal_writer = writer

    def refresh(self) -> None:
        """Re-renderiza overlays no modo atual (util apos resize/scroll)."""
        if self._mode != "off":
            self._show_for_mode(self._mode)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _show_for_mode(self, mode: str) -> None:
        self._hide_all()

        central = self._main_window.centralWidget()
        if central is None:
            return

        # Parent overlays to the QMainWindow itself, NOT to centralWidget.
        # centralWidget here is a QSplitter, which auto-arranges any QWidget
        # child into a resizable pane — that would stretch every overlay to
        # full height. QMainWindow does not absorb plain QLabel children
        # into its dock/central layout, so they stay free-floating.
        overlay_parent: QWidget = self._main_window  # type: ignore[assignment]

        # Scan centralWidget + all QToolBars (header lives in a QToolBar via
        # addToolBar, so it is NOT a descendant of centralWidget).
        scan_widgets: list[QWidget] = [central]
        scan_widgets.extend(central.findChildren(QWidget))
        for toolbar in self._main_window.findChildren(QToolBar):
            scan_widgets.append(toolbar)
            scan_widgets.extend(toolbar.findChildren(QWidget))

        used_positions: list[tuple[int, int, int, int]] = []

        for widget in scan_widgets:
            testid = widget.property("testid")
            if not testid:
                continue
            if widget.property("_is_testid_overlay"):
                continue

            is_button = isinstance(widget, QAbstractButton)
            if mode == "body" and is_button:
                continue
            if mode == "buttons" and not is_button:
                continue

            if not widget.isVisible() or not widget.isVisibleTo(overlay_parent):
                continue

            try:
                pos = widget.mapTo(overlay_parent, QPoint(0, 0))
            except RuntimeError:
                continue

            testid_str = str(testid)
            if mode == "main" and not _is_main_testid(testid_str):
                continue

            display_testid = _mask_dynamic_testid(testid_str)
            overlay = QLabel(display_testid, overlay_parent)
            normal_style = self._STYLE_NORMAL_BUTTON if is_button else self._STYLE_NORMAL_BODY
            overlay.setStyleSheet(normal_style)
            overlay.setProperty("_is_testid_overlay", True)
            overlay.setCursor(Qt.CursorShape.PointingHandCursor)
            overlay.setToolTip(f"Clique para copiar: {display_testid}")
            overlay.setWordWrap(False)
            overlay.mousePressEvent = self._make_click_handler(overlay, display_testid, normal_style)

            overlay.adjustSize()
            # Padroniza: ancora no canto inferior esquerdo do widget alvo.
            x = pos.x() + 2
            y = pos.y() + max(0, widget.height() - overlay.height() - 2)

            for ux, uy, uw, uh in used_positions:
                if abs(x - ux) < max(uw, 30) and abs(y - uy) < max(uh, 18):
                    y = max(0, uy - overlay.height() - 2)

            overlay.move(x, y)
            overlay.show()
            overlay.raise_()

            used_positions.append((x, y, overlay.width(), overlay.height()))
            self._overlays.append(overlay)

    def _make_click_handler(self, overlay: QLabel, testid_str: str, normal_style: str):
        def handler(_event):
            selector = f'data-testid="{testid_str}"'
            QApplication.clipboard().setText(selector)
            if self._terminal_write_enabled and self._terminal_writer is not None:
                self._terminal_writer(selector + " ")
            overlay.setStyleSheet(self._STYLE_COPIED)
            QTimer.singleShot(600, lambda: overlay.setStyleSheet(normal_style))
        return handler

    def _hide_all(self) -> None:
        for overlay in self._overlays:
            overlay.hide()
            overlay.deleteLater()
        self._overlays.clear()
