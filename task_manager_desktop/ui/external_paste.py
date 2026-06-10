"""Mecanismo compartilhado de "colar na janela externa focada".

Extraído de ``markdown_pane.py`` para reuso por outros apps do AI Forge
(ex.: forge-outreach), sem mudança de comportamento: clipboard + xdotool,
com detecção de terminal (Ctrl+Shift+V) e fallback Ctrl+V.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable

from PySide6.QtCore import QObject, QSize, Qt, QTimer
from PySide6.QtGui import QClipboard, QColor
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QPushButton

from task_manager_desktop.ui.icons import SEND_ARROW_SVG, svg_to_icon

EXTERNAL_PASTE_DELAY_MS = 2000

# Marcadores de WM_CLASS (substring, case-insensitive) de terminais conhecidos.
# Terminais colam por Ctrl+Shift+V; o restante das janelas usa Ctrl+V.
TERMINAL_WM_CLASS_MARKERS = (
    "term",        # gnome-terminal, xfce4-terminal, qterminal, xterm, wezterm, terminator...
    "konsole",
    "alacritty",
    "kitty",
    "tilix",
    "urxvt",
    "rxvt",
    "foot",
    "st-256color",
)


def detect_paste_shortcut(markers: tuple[str, ...] | None = None) -> str:
    """Escolhe a combinacao de paste conforme a janela focada.

    Terminais usam Ctrl+Shift+V; o restante usa Ctrl+V. O Shift+Insert
    anterior falhava em boa parte dos terminais (GNOME Terminal, Konsole,
    Tilix, xfce4-terminal...) porque cola da selecao PRIMARY, nao do
    clipboard — e em varios esta desligado por default. Ctrl+Shift+V e o
    atalho canonico de paste do clipboard nesses terminais. Estas leituras
    sao rapidas e acontecem ANTES do paste, entao nao concorrem com o
    serving do clipboard. Qualquer falha de deteccao cai no Ctrl+V historico
    — sem travar o paste.

    ``markers`` permite ao caller injetar a lista de WM_CLASS (preserva o
    seam de monkeypatch do markdown_pane); default = lista deste modulo.
    """
    active_markers = TERMINAL_WM_CLASS_MARKERS if markers is None else markers
    try:
        win = subprocess.run(
            ["xdotool", "getactivewindow"],
            capture_output=True, text=True, timeout=1,
        ).stdout.strip()
        if not win:
            return "ctrl+v"
        wm_class = subprocess.run(
            ["xprop", "-id", win, "WM_CLASS"],
            capture_output=True, text=True, timeout=1,
        ).stdout.lower()
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return "ctrl+v"
    if any(marker in wm_class for marker in active_markers):
        return "ctrl+shift+v"
    return "ctrl+v"


def paste_text_to_focused_window(
    text: str,
    shortcut: str,
    *,
    owner: QObject,
    on_warning: Callable[[str], None],
    on_check: Callable[[subprocess.Popen], None] | None = None,
) -> None:
    """Serve ``text`` no clipboard e dispara o atalho de paste na janela focada.

    ``owner`` ancora o QTimer da verificacao diferida de falha (Zero Silencio).
    ``on_check`` substitui a verificacao diferida default (preserva o hook de
    instancia ``MarkdownPane._check_paste_result``).
    """
    clipboard = QApplication.clipboard()
    clipboard.setText(text, QClipboard.Mode.Clipboard)
    if clipboard.supportsSelection():
        clipboard.setText(text, QClipboard.Mode.Selection)
    # Deixa o event loop assumir a posse do clipboard antes de disparar o paste.
    QApplication.processEvents()
    try:
        # Popen (NAO-bloqueante) e critico: subprocess.run congelaria o event
        # loop do Qt e, sem um clipboard manager rodando, o app nao conseguiria
        # servir o SelectionRequest X11 da janela alvo -> paste vazio. Mantendo
        # o loop vivo, o Qt responde ao pedido de clipboard durante o paste.
        proc = subprocess.Popen(
            ["xdotool", "key", "--clearmodifiers", shortcut],
        )
    except FileNotFoundError:
        on_warning("xdotool nao encontrado; markdown copiado para o clipboard.")
        return
    # Verificacao diferida de falha (Zero Silencio) sem bloquear o loop.
    checker = (
        on_check
        if on_check is not None
        else (lambda p: _check_paste_result(p, on_warning))
    )
    QTimer.singleShot(400, owner, lambda p=proc: checker(p))


def _check_paste_result(
    proc: subprocess.Popen, on_warning: Callable[[str], None]
) -> None:
    code = proc.poll()
    if code is not None and code != 0:
        on_warning("Falha ao colar; markdown copiado para o clipboard.")


def style_external_paste_button(
    button: QPushButton,
    *,
    testid: str = "markdown-external-paste-button",
    size: int = 56,
    icon_px: int = 30,
) -> None:
    """Aplica a identidade visual canonica do botao flutuante de paste externo."""
    button.setObjectName("markdownExternalPasteButton")
    button.setProperty("testid", testid)
    button.setProperty("data-testid", testid)
    button.setAccessibleName("Colar markdown na janela focada")
    button.setToolTip("Colar markdown na janela focada em 2 segundos")
    button.setFixedSize(size, size)
    button.setIcon(svg_to_icon(SEND_ARROW_SVG, icon_px))
    button.setIconSize(QSize(icon_px, icon_px))
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setStyleSheet(
        "QPushButton#markdownExternalPasteButton {"
        " background-color: #2563EB; border: 1px solid #60A5FA;"
        f" border-radius: {size // 2}px; padding: 0;"
        "}"
        "QPushButton#markdownExternalPasteButton:hover {"
        " background-color: #1D4ED8; border-color: #93C5FD;"
        "}"
        "QPushButton#markdownExternalPasteButton:pressed {"
        " background-color: #1E40AF; padding-top: 2px;"
        "}"
        "QPushButton#markdownExternalPasteButton:disabled {"
        " background-color: #334155; border-color: #475569;"
        "}"
    )
    shadow = QGraphicsDropShadowEffect(button)
    shadow.setBlurRadius(26)
    shadow.setOffset(0, 8)
    shadow.setColor(QColor(0, 0, 0, 150))
    button.setGraphicsEffect(shadow)
