"""TerminalPanel — Embedded terminal: PersistentShell + pyte + TerminalCanvas.

Adaptado do `workflow_app.output_panel.OutputPanel` para o task-manager-desktop.
Mantem as 3 engines (PersistentShell / EnhancedScreen / TerminalCanvas) intactas
e remove tudo que era integracao com workflow-app (signal_bus, pipeline runner,
kimi blue arrow, idle timer, paste signals). O resultado eh um QWidget standalone
que so faz: spawnar o shell do user via PTY e renderizar saida em 20fps.
"""

from __future__ import annotations

from typing import Any

import pyte
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QScrollBar,
    QSizePolicy,
    QWidget,
)

from .enhanced_screen import EnhancedScreen
from .persistent_shell import PersistentShell
from .terminal_canvas import Cell, TerminalCanvas

_TERMINAL_COLS = 80
_TERMINAL_ROWS = 24
_BRACKETED_PASTE_MODE = 2004 << 5


class TerminalPanel(QWidget):
    """Painel terminal embarcado: shell persistente + pyte + canvas."""

    def __init__(self, parent: QWidget | None = None, cwd: str | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TerminalPanel")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: #18181B;")

        self._cols = _TERMINAL_COLS
        self._rows = _TERMINAL_ROWS

        self._screen = EnhancedScreen(self._cols, self._rows, history=5000)
        self._stream = pyte.ByteStream(self._screen)
        self._history_cursor = 0
        self._has_pending_render = False

        self._render_timer = QTimer(self)
        self._render_timer.setInterval(50)  # 20 fps
        self._render_timer.timeout.connect(self._flush_pyte)

        # parent=self garante que o QObject do shell entra na ownership tree do panel
        # (cleanup adicional via shutdown() em aboutToQuit — ver app.py).
        self._shell = PersistentShell(cols=self._cols, rows=self._rows, cwd=cwd, parent=self)
        self._shell.output_received.connect(self._on_chunk)
        self._shell_started = False

        self._setup_ui()

    # ── UI ───────────────────────────────────────────────────────────── #

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._terminal = TerminalCanvas()
        self._terminal.setProperty("testid", "terminal-workspace-output")
        self._terminal.raw_key_pressed.connect(self._on_raw_key)
        layout.addWidget(self._terminal, stretch=1)

        self._scrollbar = QScrollBar(Qt.Orientation.Vertical)
        self._scrollbar.setStyleSheet(
            "QScrollBar:vertical { background: #0D1117; width: 10px; }"
            "QScrollBar::handle:vertical { background: #3F3F46; min-height: 20px; border-radius: 4px; }"
            "QScrollBar::handle:vertical:hover { background: #52525B; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: #0D1117; }"
        )
        self._terminal.set_scrollbar(self._scrollbar)
        layout.addWidget(self._scrollbar)

        QTimer.singleShot(0, self._schedule_resize)

    # ── Lifecycle / resize ───────────────────────────────────────────── #

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if self._shell_started:
            return
        layout = self.layout()
        if layout is not None:
            layout.activate()
        cols, rows = self._terminal.recompute_grid()
        if cols > 0 and rows > 0:
            self._cols = cols
            self._rows = rows
            try:
                self._screen.resize(lines=rows, columns=cols)
            except Exception:  # noqa: BLE001
                self._screen = EnhancedScreen(cols, rows, history=5000)
                self._stream = pyte.ByteStream(self._screen)
                self._history_cursor = 0
                self._has_pending_render = False
            self._shell.resize(cols, rows)
        self._shell.start()
        self._shell_started = True

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._schedule_resize()

    def _schedule_resize(self) -> None:
        cols, rows = self._terminal.recompute_grid()
        if cols != self._cols or rows != self._rows:
            self._cols = cols
            self._rows = rows
            self._shell.resize(cols, rows)
            try:
                self._screen.resize(lines=rows, columns=cols)
            except Exception:  # noqa: BLE001
                self._screen = EnhancedScreen(cols, rows, history=5000)
                self._stream = pyte.ByteStream(self._screen)
                self._history_cursor = 0
                self._has_pending_render = False
            self._terminal.recompute_grid()
            self._terminal.update()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.shutdown()
        super().closeEvent(event)

    def shutdown(self) -> None:
        """Cleanup garantido do PTY shell + process group.

        Chamado em dois caminhos: (a) closeEvent do panel (quando recebido),
        (b) QApplication.aboutToQuit conectado em app.py — este e o caminho
        confiavel para teardown no fechamento da janela principal, ja que
        widgets-filho nao recebem closeEvent garantido em todos os SOs.

        Mata o process group inteiro (start_new_session=True faz o shell ser
        lider de sessao). Sem isso, processos filhos do shell (claude, vim, etc)
        vazariam orfaos.
        """
        import os
        import signal as _sig

        self._render_timer.stop()
        if self._shell is None:
            return
        proc = getattr(self._shell, "_proc", None)
        # SIGTERM no process group (cobre filhos do shell).
        if proc is not None and proc.poll() is None:
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, _sig.SIGTERM)
            except (ProcessLookupError, PermissionError, OSError):
                pass
        # Cleanup interno (fecha FD, desliga notifier, terminate o subprocess).
        try:
            self._shell.terminate()
        except Exception:  # noqa: BLE001
            pass
        # Fallback: se ainda vivo apos terminate, SIGKILL no grupo + reap final.
        if proc is not None:
            try:
                proc.wait(timeout=0.5)
            except Exception:  # noqa: BLE001
                try:
                    pgid = os.getpgid(proc.pid)
                    os.killpg(pgid, _sig.SIGKILL)
                except (ProcessLookupError, PermissionError, OSError):
                    pass
                # Reap pos-SIGKILL para evitar zombie do shell.
                try:
                    proc.wait(timeout=1.0)
                except Exception:  # noqa: BLE001
                    pass
        self._shell = None  # type: ignore[assignment]

    # ── Input routing ────────────────────────────────────────────────── #

    def focus_terminal(self) -> None:
        """Move keyboard focus to the canvas that owns raw terminal input."""
        self._terminal.setFocus(Qt.FocusReason.OtherFocusReason)

    def _on_raw_key(self, data: bytes) -> None:
        if self._shell is None:
            return
        self._shell.send_raw(data)

    def paste_text(self, text: str) -> None:
        """Paste text into the shell, honoring bracketed paste mode."""
        if not text or self._shell is None:
            return
        data = text.encode("utf-8", errors="replace")
        if _BRACKETED_PASTE_MODE in self._screen.mode:
            data = b"\x1b[200~" + data + b"\x1b[201~"
        self._shell.send_raw(data)

    def send_enter(self) -> None:
        """Send a bare Enter keypress to the shell."""
        if self._shell is not None:
            self._shell.send_raw(b"\r")

    def run_command(self, command: str, *, enter_delay_ms: int = 80) -> None:
        """Paste a command and submit Enter as a separate PTY write.

        This mirrors workflow-app's terminal behavior: Ink/textual CLIs can
        swallow a trailing carriage return when paste payload and Enter arrive
        in the same chunk, especially with bracketed paste enabled.
        """
        self.paste_text(command)
        QTimer.singleShot(enter_delay_ms, self, self.send_enter)

    # ── Output / render ──────────────────────────────────────────────── #

    def _on_chunk(self, chunk: str) -> None:
        try:
            self._stream.feed(chunk.encode("utf-8", errors="replace"))
        except Exception:  # noqa: BLE001
            return
        self._has_pending_render = True
        if not self._render_timer.isActive():
            self._render_timer.start()

    def _pyte_row_to_cells(self, row_dict: dict[int, Any]) -> list[Cell]:
        if not row_dict:
            return [Cell.empty() for _ in range(self._cols)]
        max_col = max(row_dict.keys()) if row_dict else 0
        cells: list[Cell] = []
        col = 0
        while col <= max(max_col, self._cols - 1):
            ch = row_dict.get(col)
            if ch is not None:
                cell = Cell.from_pyte(ch)
                cells.append(cell)
                if cell.wide:
                    cells.append(None)  # type: ignore[arg-type]
                    col += 2
                else:
                    col += 1
            else:
                cells.append(Cell.empty())
                col += 1
        while len(cells) < self._cols:
            cells.append(Cell.empty())
        return cells[:self._cols]

    def _flush_pyte(self) -> None:
        if not self._has_pending_render:
            return
        self._has_pending_render = False

        history_top = list(self._screen.history.top)
        new_count = len(history_top) - self._history_cursor
        if new_count > 0:
            new_lines: list[list[Cell]] = []
            for line_dict in history_top[self._history_cursor:]:
                new_lines.append(self._pyte_row_to_cells(dict(line_dict)))
            self._terminal.append_scrollback(new_lines)
            self._history_cursor = len(history_top)

        term_cursor_row = self._screen.cursor.y
        term_cursor_col = self._screen.cursor.x

        visible_lines: list[list[Cell]] = []
        for row_idx in range(self._screen.lines):
            row = self._screen.buffer.get(row_idx) or {}
            visible_lines.append(self._pyte_row_to_cells(dict(row)))

        self._terminal.set_visible_lines(
            visible_lines,
            cursor_row=term_cursor_row,
            cursor_col=term_cursor_col,
        )
        self._terminal.scroll_to_bottom()
