from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from task_manager_desktop.ui.icons import MOON_SVG, PENCIL_SVG, SUN_SVG, svg_to_icon
from task_manager_desktop.ui.theme import TOOLBAR_H


class EditorToolbar(QWidget):
    """Header persistente do painel de notas Markdown."""

    save_requested = Signal()
    cancel_requested = Signal()
    toggle_preview_requested = Signal()
    toggle_reader_theme_requested = Signal()
    toggle_terminal_collapse_requested = Signal()
    send_to_terminal_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(TOOLBAR_H)
        self.setProperty("testid", "editor-toolbar")
        self.setAccessibleName("Barra de ferramentas do editor de notas")
        self.setObjectName("editorToolbar")

        self._title = QLabel("Notas Markdown", self)
        self._title.setObjectName("markdownHeaderTitle")
        self._title.setProperty("testid", "editor-toolbar-title")
        self._title.setAccessibleName("Título do painel de notas")
        self._title.setFixedHeight(32)
        self._title.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        self._mode = QLabel("Editando", self)
        self._mode.setObjectName("markdownModePill")
        self._mode.setProperty("testid", "editor-toolbar-mode")
        self._mode.setAccessibleName("Modo atual do painel de notas")
        self._mode.setVisible(False)

        self.btn_toggle = QPushButton("Preview", self)
        self.btn_toggle.setProperty("testid", "editor-btn-toggle-preview")
        self.btn_toggle.setVisible(False)

        self.btn_terminal_collapse = QPushButton("▲", self)
        self.btn_terminal_collapse.setProperty("class", "ghost-sm")
        self.btn_terminal_collapse.setProperty("testid", "terminal-workspace-collapse")
        self.btn_terminal_collapse.setAccessibleName("Alternar terminal embarcado")
        self.btn_terminal_collapse.setToolTip("Expandir terminal (Ctrl+J)")
        self.btn_terminal_collapse.setFixedSize(34, 34)

        self.btn_reader_theme = QPushButton(self)
        self.btn_reader_theme.setObjectName("markdownThemeToggle")
        self.btn_reader_theme.setProperty("testid", "editor-btn-toggle-reader-theme")
        self.btn_reader_theme.setAccessibleName("Alternar tema do leitor Markdown")
        self.btn_reader_theme.setToolTip("Alternar tema claro/escuro do Markdown")
        self.btn_reader_theme.setFixedSize(38, 34)
        self.btn_reader_theme.setIconSize(QSize(21, 21))

        self.btn_send_to_terminal = QPushButton(self)
        self.btn_send_to_terminal.setObjectName("markdownSendToTerminal")
        self.btn_send_to_terminal.setProperty("class", "ghost-sm")
        self.btn_send_to_terminal.setProperty("testid", "editor-btn-send-to-terminal")
        self.btn_send_to_terminal.setAccessibleName("Enviar notas para o terminal")
        self.btn_send_to_terminal.setToolTip("Colar o texto das notas no terminal")
        self.btn_send_to_terminal.setFixedSize(34, 34)
        self.btn_send_to_terminal.setIcon(svg_to_icon(PENCIL_SVG, 20))
        self.btn_send_to_terminal.setIconSize(QSize(20, 20))
        self.btn_send_to_terminal.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_save = QPushButton("Salvar", self)
        self.btn_save.setProperty("testid", "editor-btn-save")
        self.btn_save.setAccessibleName("Salvar notas")
        self.btn_save.setVisible(False)

        self.btn_cancel = QPushButton("Cancelar", self)
        self.btn_cancel.setProperty("testid", "editor-btn-cancel")
        self.btn_cancel.setAccessibleName("Cancelar edição de notas")
        self.btn_cancel.setVisible(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 0, 22, 0)
        layout.setSpacing(10)
        layout.addWidget(self._title, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch()
        layout.addWidget(self.btn_send_to_terminal, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.btn_terminal_collapse, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.btn_reader_theme, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_save.clicked.connect(self.save_requested.emit)
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        self.btn_toggle.clicked.connect(self.toggle_preview_requested.emit)
        self.btn_reader_theme.clicked.connect(self.toggle_reader_theme_requested.emit)
        self.btn_terminal_collapse.clicked.connect(self.toggle_terminal_collapse_requested.emit)
        self.btn_send_to_terminal.clicked.connect(self.send_to_terminal_requested.emit)
        self.set_reader_light_mode(False)

    def set_preview_mode(self, preview: bool) -> None:
        pass  # badge e botão de preview removidos; modo é sempre editor

    def set_task_enabled(self, enabled: bool) -> None:
        pass  # botão salvar removido; auto-save via Ctrl+S ou troca de task

    def set_terminal_collapsed(self, collapsed: bool) -> None:
        """Update chevron text/tooltip: ▲ quando colapsado (clica pra expandir), ▼ quando expandido."""
        self.btn_terminal_collapse.setText("▲" if collapsed else "▼")
        self.btn_terminal_collapse.setToolTip(
            "Expandir terminal (Ctrl+J)" if collapsed else "Colapsar terminal (Ctrl+J)"
        )

    def set_reader_light_mode(self, light: bool) -> None:
        self.btn_reader_theme.setIcon(svg_to_icon(MOON_SVG if light else SUN_SVG, 21))
        self.btn_reader_theme.setToolTip(
            "Trocar Markdown para tema escuro" if light else "Trocar Markdown para tema claro"
        )
