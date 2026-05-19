from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from task_manager_desktop.ui.icons import (
    TRASH_SVG,
    svg_to_icon,
)

_ALL_PROJECTS_LABEL = "Todos"
_SEARCH_DEBOUNCE_MS = 150


class HeaderBar(QWidget):
    new_task_requested = Signal()
    search_text_changed = Signal(str)
    project_filter_changed = Signal(object)  # str | None; None = "Todos"
    clear_completed_clicked = Signal()
    trash_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setObjectName("HeaderBar")
        self.setAccessibleName("Barra de cabeçalho")

        self._search_debounce = QTimer(self)
        self._search_debounce.setSingleShot(True)
        self._search_debounce.setInterval(_SEARCH_DEBOUNCE_MS)
        self._search_debounce.timeout.connect(self._emit_search_changed)

        self._build_ui()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        self.btn_new = QPushButton("+", self)
        self.btn_new.setProperty("class", "primary")
        self.btn_new.setFixedSize(36, 36)
        self.btn_new.setToolTip("Nova task (Ctrl+N)")
        self.btn_new.setAccessibleName("Criar nova task")
        self.btn_new.setAccessibleDescription("Atalho Ctrl+N")
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.clicked.connect(self.new_task_requested.emit)
        layout.addWidget(self.btn_new)

        self._search = QLineEdit(self)
        self._search.setObjectName("headerSearch")
        self._search.setPlaceholderText("Buscar por título ou notas... (Ctrl+F)")
        self._search.setClearButtonEnabled(True)
        self._search.setAccessibleName("Campo de busca por título ou notas")
        self._search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._search.setMinimumWidth(280)
        self._search.setFixedHeight(36)
        self._search.textChanged.connect(self._on_search_text_changed)
        layout.addWidget(self._search, 1)

        self._project_filter = QComboBox(self)
        self._project_filter.setObjectName("headerProjectFilter")
        self._project_filter.setAccessibleName("Filtro por projeto")
        self._project_filter.setMinimumWidth(140)
        self._project_filter.setMaximumWidth(200)
        self._project_filter.setFixedHeight(36)
        self._project_filter.addItem(_ALL_PROJECTS_LABEL)
        self._project_filter.currentIndexChanged.connect(self._on_project_changed)
        layout.addWidget(self._project_filter)

        self._btn_clear_done = QPushButton("Limpar concluídas", self)
        self._btn_clear_done.setProperty("class", "ghost-sm")
        self._btn_clear_done.setAccessibleName(
            "Mover tasks concluídas para a Lixeira (nenhuma disponível)"
        )
        self._btn_clear_done.setToolTip("Nenhuma task concluída visível")  # default: disabled
        self._btn_clear_done.setEnabled(False)  # disabled by default
        self._btn_clear_done.setMinimumHeight(36)
        self._btn_clear_done.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_clear_done.clicked.connect(self.clear_completed_clicked.emit)
        layout.addWidget(self._btn_clear_done)

        self._btn_trash = QToolButton(self)
        self._btn_trash.setObjectName("headerTrash")
        self._btn_trash.setAccessibleName("Abrir Lixeira de tasks")
        self._btn_trash.setToolTip("Lixeira (tasks ocultas até 30 dias)")
        self._btn_trash.setIcon(svg_to_icon(TRASH_SVG, 20))
        self._btn_trash.setIconSize(QSize(20, 20))
        self._btn_trash.setFixedSize(36, 36)
        self._btn_trash.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_trash.clicked.connect(self.trash_clicked.emit)
        layout.addWidget(self._btn_trash)

    # ------------------------------------------------------------------
    # External shortcut hook (Ctrl+N) — unchanged contract
    # ------------------------------------------------------------------
    def install_shortcut(self, parent: QWidget) -> None:
        shortcut = QShortcut(QKeySequence("Ctrl+N"), parent)
        shortcut.activated.connect(self.new_task_requested.emit)

    # ------------------------------------------------------------------
    # Properties for external access
    # ------------------------------------------------------------------
    @property
    def search_field(self) -> QLineEdit:
        return self._search

    @property
    def combo(self) -> QComboBox:
        return self._project_filter

    # ------------------------------------------------------------------
    # Clear Done Button State Control
    # ------------------------------------------------------------------
    def set_clear_done_enabled(self, has_visible_done: bool) -> None:
        """Enable/disable 'Limpar concluídas' button based on visible done tasks."""
        self._btn_clear_done.setEnabled(has_visible_done)
        if not has_visible_done:
            self._btn_clear_done.setToolTip("Nenhuma task concluída visível")
            self._btn_clear_done.setAccessibleName(
                "Mover tasks concluídas para a Lixeira (nenhuma disponível)"
            )
        else:
            self._btn_clear_done.setToolTip("")
            self._btn_clear_done.setAccessibleName("Mover tasks concluídas para a Lixeira")

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def _on_search_text_changed(self, _text: str) -> None:
        self._search_debounce.start()

    def _emit_search_changed(self) -> None:
        self.search_text_changed.emit(self._search.text())

    def clear_search(self) -> None:
        self._search.clear()
        self._search_debounce.stop()
        self.search_text_changed.emit("")

    def focus_search(self) -> None:
        self._search.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self._search.selectAll()

    def search_has_focus(self) -> bool:
        return self._search.hasFocus()

    def clear_search_focus(self) -> None:
        self._search.clearFocus()

    # ------------------------------------------------------------------
    # ProjectFilter
    # ------------------------------------------------------------------
    def _on_project_changed(self, _idx: int) -> None:
        self._update_project_active_state()
        value = self.current_project()
        self.project_filter_changed.emit(value)

    def _update_project_active_state(self) -> None:
        active = self.current_project() is not None
        self._project_filter.setProperty("active", "true" if active else "false")
        self._project_filter.style().unpolish(self._project_filter)
        self._project_filter.style().polish(self._project_filter)
        self._project_filter.update()

    def current_project(self) -> str | None:
        text = self._project_filter.currentText()
        if text == _ALL_PROJECTS_LABEL:
            return None
        return text

    def set_projects(self, projects: list[str]) -> None:
        previous = self._project_filter.currentText()
        unique_sorted = sorted({p for p in projects if p and p != _ALL_PROJECTS_LABEL})

        self._project_filter.blockSignals(True)
        self._project_filter.clear()
        self._project_filter.addItem(_ALL_PROJECTS_LABEL)
        for proj in unique_sorted:
            self._project_filter.addItem(proj)

        target_idx = 0
        if previous in unique_sorted:
            target_idx = self._project_filter.findText(previous)
        self._project_filter.setCurrentIndex(max(0, target_idx))
        self._project_filter.blockSignals(False)

        self._update_project_active_state()

        if previous != self._project_filter.currentText():
            self.project_filter_changed.emit(self.current_project())

    # Alias for backward compat with caller code using Portuguese naming
    def set_projetos(self, projects: list[str]) -> None:
        self.set_projects(projects)
