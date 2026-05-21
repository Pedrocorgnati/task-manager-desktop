from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QSize, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.models import TaskType

from task_manager_desktop.ui.icons import (
    BROOM_SVG,
    LAYOUT_STACK_SVG,
    TRASH_SVG,
    svg_to_icon,
)


_TEST_MODE_BTN_STYLE_ALL = (
    "QPushButton { background-color: transparent; color: #60A5FA;"
    "  border: 1px solid #2563EB; border-radius: 6px;"
    "  font-size: 10px; font-weight: 600; padding: 0 1px; }"
    "QPushButton:hover { color: #FAFAFA; background-color: #1E3A8A;"
    "  border-color: #3B82F6; }"
    "QPushButton:checked { background-color: #2563EB; color: #FAFAFA;"
    "  border-color: #2563EB; font-weight: 700; }"
)
_TEST_MODE_BTN_STYLE_BODY = (
    "QPushButton { background-color: transparent; color: #F87171;"
    "  border: 1px solid #DC2626; border-radius: 6px;"
    "  font-size: 10px; font-weight: 600; padding: 0 1px; }"
    "QPushButton:hover { color: #FAFAFA; background-color: #7F1D1D;"
    "  border-color: #EF4444; }"
    "QPushButton:checked { background-color: #DC2626; color: #FAFAFA;"
    "  border-color: #DC2626; font-weight: 700; }"
)
_TEST_MODE_BTN_STYLE_BTN = (
    "QPushButton { background-color: transparent; color: #60A5FA;"
    "  border: 1px solid #2563EB; border-radius: 6px;"
    "  font-size: 10px; font-weight: 600; padding: 0 1px; }"
    "QPushButton:hover { color: #FAFAFA; background-color: #1E3A8A;"
    "  border-color: #3B82F6; }"
    "QPushButton:checked { background-color: #2563EB; color: #FAFAFA;"
    "  border-color: #2563EB; font-weight: 700; }"
)


class HeaderBar(QWidget):
    new_task_requested = Signal()
    type_filter_changed = Signal(object)  # frozenset[str]
    clear_completed_clicked = Signal()
    trash_clicked = Signal()
    # DataTest test-mode: emits "off" | "all" | "body" | "buttons"
    test_mode_changed = Signal(str)
    datatest_terminal_write_toggled = Signal(bool)
    terminal_layout_mode_toggled = Signal(bool)
    terminal_collapse_requested = Signal()
    _PX_RULER_WIDTHS = (10, 50, 100)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(58)
        self.setObjectName("HeaderBar")
        self.setProperty("testid", "header")
        self.setAccessibleName("Barra de cabeçalho")
        self._type_checkboxes: dict[str, QCheckBox] = {}
        self._px_ruler_toasts: list[QLabel] = []
        self._px_ruler_visible = False
        self._px_ruler_resize_filter: QObject | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        self._primary_controls = QWidget(self)
        self._primary_controls.setObjectName("headerPrimaryControls")
        self._primary_controls.setProperty("testid", "header-primary-controls")
        primary_layout = QHBoxLayout(self._primary_controls)
        primary_layout.setContentsMargins(0, 0, 0, 0)
        primary_layout.setSpacing(8)

        self.btn_new = QPushButton("+", self._primary_controls)
        self.btn_new.setProperty("class", "primary")
        self.btn_new.setProperty("testid", "header-new-task-button")
        self.btn_new.setFixedSize(40, 40)
        self.btn_new.setToolTip("Nova task (Ctrl+N)")
        self.btn_new.setAccessibleName("Criar nova task")
        self.btn_new.setAccessibleDescription("Atalho Ctrl+N")
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.clicked.connect(self.new_task_requested.emit)
        primary_layout.addWidget(self.btn_new)

        self._type_filter = QWidget(self._primary_controls)
        self._type_filter.setObjectName("headerTypeFilter")
        self._type_filter.setProperty("testid", "header-type-filter")
        self._type_filter.setAccessibleName("Filtro por tipo de task")
        self._type_filter.setFixedHeight(54)
        self._type_filter.setFixedWidth(132)
        type_layout = QVBoxLayout(self._type_filter)
        type_layout.setContentsMargins(10, 1, 10, 1)
        type_layout.setSpacing(0)
        for task_type in (TaskType.HUMAN, TaskType.DEV, TaskType.AGENT):
            checkbox = QCheckBox(task_type.value, self._type_filter)
            checkbox.setObjectName(f"headerTypeFilter{task_type.value.title()}")
            checkbox.setProperty("testid", f"header-type-filter-{task_type.value}")
            checkbox.setAccessibleName(f"Filtrar tasks {task_type.value}")
            checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
            checkbox.setChecked(True)
            checkbox.setFixedHeight(17)
            checkbox.toggled.connect(self._on_type_filter_changed)
            self._type_checkboxes[task_type.value] = checkbox
            type_layout.addWidget(checkbox)
        primary_layout.addWidget(self._type_filter)

        self._btn_clear_done = QToolButton(self._primary_controls)
        self._btn_clear_done.setObjectName("headerClearDone")
        self._btn_clear_done.setProperty("testid", "header-clear-done-button")
        self._btn_clear_done.setProperty("data-testid", "header-clear-done-button")
        self._btn_clear_done.setAccessibleName(
            "Mover tasks concluídas para a Lixeira (nenhuma disponível)"
        )
        self._btn_clear_done.setToolTip(
            "Sem tasks concluídas não-permanentes para ocultar"
        )  # default: disabled
        self._btn_clear_done.setEnabled(False)  # disabled by default
        self._btn_clear_done.setIcon(svg_to_icon(BROOM_SVG, 20))
        self._btn_clear_done.setIconSize(QSize(20, 20))
        self._btn_clear_done.setFixedSize(40, 40)
        self._btn_clear_done.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_clear_done.clicked.connect(self.clear_completed_clicked.emit)
        primary_layout.addWidget(self._btn_clear_done)

        self._btn_trash = QToolButton(self._primary_controls)
        self._btn_trash.setObjectName("headerTrash")
        self._btn_trash.setProperty("testid", "header-trash-button")
        self._btn_trash.setProperty("data-testid", "header-trash-button")
        self._btn_trash.setAccessibleName("Abrir Lixeira de tasks")
        self._btn_trash.setToolTip("Lixeira (tasks ocultas até 30 dias)")
        self._btn_trash.setIcon(svg_to_icon(TRASH_SVG, 20))
        self._btn_trash.setIconSize(QSize(20, 20))
        self._btn_trash.setFixedSize(40, 40)
        self._btn_trash.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_trash.clicked.connect(self.trash_clicked.emit)
        primary_layout.addWidget(self._btn_trash)

        layout.addWidget(self._primary_controls)
        layout.addStretch(1)

        self._btn_terminal_layout = QToolButton(self)
        self._btn_terminal_layout.setObjectName("headerTerminalLayout")
        self._btn_terminal_layout.setProperty("testid", "header-terminal-layout-button")
        self._btn_terminal_layout.setAccessibleName("Alternar layout do terminal")
        self._btn_terminal_layout.setToolTip("Layout row: terminal no reader")
        self._btn_terminal_layout.setIcon(svg_to_icon(LAYOUT_STACK_SVG, 20))
        self._btn_terminal_layout.setIconSize(QSize(20, 20))
        self._btn_terminal_layout.setFixedSize(40, 40)
        self._btn_terminal_layout.setCheckable(True)
        self._btn_terminal_layout.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_terminal_layout.toggled.connect(self._on_terminal_layout_toggled)
        layout.addWidget(self._btn_terminal_layout)

        self._btn_terminal_collapse = QToolButton(self)
        self._btn_terminal_collapse.setObjectName("headerTerminalCollapse")
        self._btn_terminal_collapse.setProperty("testid", "terminal-workspace-collapse")
        self._btn_terminal_collapse.setAccessibleName("Alternar terminal")
        self._btn_terminal_collapse.setText("▲")
        self._btn_terminal_collapse.setToolTip("Expandir terminal (Ctrl+J)")
        self._btn_terminal_collapse.setFixedSize(40, 40)
        self._btn_terminal_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_terminal_collapse.clicked.connect(self.terminal_collapse_requested.emit)
        layout.addWidget(self._btn_terminal_collapse)

        # Test-mode Buttons (Data / Body / Btn) + terminal-write checkbox.
        # Comportamento radio-like: no maximo 1 checado. Re-click desliga (-> off).
        self._btn_datatest = QPushButton("Data")
        self._btn_datatest.setFixedSize(68, 16)
        self._btn_datatest.setCheckable(True)
        self._btn_datatest.setToolTip("Exibir todos os data-testid (Ctrl+Shift+D)")
        self._btn_datatest.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_datatest.setStyleSheet(_TEST_MODE_BTN_STYLE_ALL)

        self._btn_bodytest = QPushButton("Body")
        self._btn_bodytest.setFixedSize(68, 16)
        self._btn_bodytest.setCheckable(True)
        self._btn_bodytest.setToolTip("Exibir data-testid EXCETO em botoes (Ctrl+Shift+B)")
        self._btn_bodytest.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_bodytest.setStyleSheet(_TEST_MODE_BTN_STYLE_BODY)

        self._btn_btntest = QPushButton("Btn")
        self._btn_btntest.setFixedSize(68, 16)
        self._btn_btntest.setCheckable(True)
        self._btn_btntest.setToolTip("Exibir data-testid APENAS em botoes (Ctrl+Shift+T)")
        self._btn_btntest.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_btntest.setStyleSheet(_TEST_MODE_BTN_STYLE_BTN)

        self._btn_px_ruler = QPushButton("px ruler")
        self._btn_px_ruler.setFixedSize(68, 16)
        self._btn_px_ruler.setCheckable(True)
        self._btn_px_ruler.setToolTip("Mostrar régua de largura em pixels")
        self._btn_px_ruler.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_px_ruler.setStyleSheet(_TEST_MODE_BTN_STYLE_BTN)
        self._btn_px_ruler.toggled.connect(self._toggle_px_ruler)

        self._datatest_terminal_checkbox = QCheckBox(self)
        self._datatest_terminal_checkbox.setObjectName("headerDataTestTerminalToggle")
        self._datatest_terminal_checkbox.setFixedSize(16, 16)
        self._datatest_terminal_checkbox.setToolTip(
            "Ao clicar no overlay, envia seletor para o terminal e foca no terminal"
        )
        self._datatest_terminal_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self._datatest_terminal_checkbox.setStyleSheet(
            "QCheckBox::indicator {"
            " width: 12px; height: 12px; border-radius: 3px;"
            " border: 1px solid #9CA3AF; background-color: #E5E7EB; }"
            "QCheckBox::indicator:checked {"
            " border: 1px solid #6B7280; background-color: #4B5563; }"
        )
        self._datatest_terminal_checkbox.toggled.connect(self.datatest_terminal_write_toggled.emit)

        self._test_mode_grid = QWidget(self)
        self._test_mode_grid.setProperty("testid", "test-mode-overlay-controls")
        _tm_row_layout = QHBoxLayout(self._test_mode_grid)
        _tm_row_layout.setContentsMargins(0, 0, 0, 0)
        _tm_row_layout.setSpacing(4)
        _tm_row_layout.addWidget(
            self._datatest_terminal_checkbox,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        _tm_row_layout.addWidget(self._btn_datatest)
        _tm_row_layout.addWidget(self._btn_bodytest)
        _tm_row_layout.addWidget(self._btn_btntest)
        _tm_row_layout.addWidget(self._btn_px_ruler)
        # Nao entra no layout do header: a grid e reparentada como overlay
        # no canto inferior direito da coluna 1 via take_test_mode_grid().

        # QButtonGroup com exclusive=False; logica radio manual no handler.
        # exclusive=True bloquearia o re-click de desligar o ativo.
        self._test_mode_group = QButtonGroup(self)
        self._test_mode_group.setExclusive(False)
        self._test_mode_group.addButton(self._btn_datatest)
        self._test_mode_group.addButton(self._btn_bodytest)
        self._test_mode_group.addButton(self._btn_btntest)

        self._test_mode_buttons: dict[str, QPushButton] = {
            "all": self._btn_datatest,
            "body": self._btn_bodytest,
            "buttons": self._btn_btntest,
        }
        # Flag para evitar reentrancia quando desligamos os outros botoes.
        self._test_mode_syncing = False
        for btn in self._test_mode_buttons.values():
            btn.toggled.connect(self._on_test_mode_button_toggled)

    def take_primary_controls(self) -> QWidget:
        self._primary_controls.setParent(None)
        return self._primary_controls

    def take_test_mode_grid(self) -> QWidget:
        """Entrega a grid de test-mode para ser ancorada fora do header
        (overlay no canto inferior direito da coluna 1 — task-list-pane)."""
        self._test_mode_grid.setParent(None)
        return self._test_mode_grid

    # ------------------------------------------------------------------
    # External shortcut hook (Ctrl+N) — unchanged contract
    # ------------------------------------------------------------------
    def install_shortcut(self, parent: QWidget) -> None:
        shortcut = QShortcut(QKeySequence("Ctrl+N"), parent)
        shortcut.activated.connect(self.new_task_requested.emit)

    # ------------------------------------------------------------------
    # Clear Done Button State Control
    # ------------------------------------------------------------------
    def set_clear_done_enabled(self, has_visible_done: bool) -> None:
        """Enable/disable 'Limpar concluídas' button based on visible done tasks."""
        self._btn_clear_done.setEnabled(has_visible_done)
        if not has_visible_done:
            self._btn_clear_done.setToolTip(
                "Sem tasks concluídas não-permanentes para ocultar"
            )
            self._btn_clear_done.setAccessibleName(
                "Mover tasks concluídas para a Lixeira (nenhuma disponível)"
            )
        else:
            self._btn_clear_done.setToolTip("Mover tasks concluídas para a Lixeira")
            self._btn_clear_done.setAccessibleName("Mover tasks concluídas para a Lixeira")

    # ------------------------------------------------------------------
    # Type filter
    # ------------------------------------------------------------------
    def _on_type_filter_changed(self, _checked: bool) -> None:
        self.type_filter_changed.emit(self.current_task_types())

    def current_task_types(self) -> frozenset[str]:
        return frozenset(
            value
            for value, checkbox in self._type_checkboxes.items()
            if checkbox.isChecked()
        )

    # ------------------------------------------------------------------
    # Test-mode (DataTest / BodyTest / BtnTest)
    # ------------------------------------------------------------------
    def _on_test_mode_button_toggled(self, checked: bool) -> None:
        """Mantem exclusividade manual (no max 1 checado) e emite test_mode_changed.

        Comportamento radio-like:
        - Ativar um botao desliga os outros dois.
        - Re-click no botao ativo desliga (modo "off").
        """
        if self._test_mode_syncing:
            return
        sender = self.sender()
        self._test_mode_syncing = True
        try:
            if checked:
                for btn in self._test_mode_buttons.values():
                    if btn is not sender and btn.isChecked():
                        btn.setChecked(False)
        finally:
            self._test_mode_syncing = False

        mode = "off"
        for key, btn in self._test_mode_buttons.items():
            if btn.isChecked():
                mode = key
                break
        self.test_mode_changed.emit(mode)

    def toggle_test_mode(self, mode: str) -> None:
        """Ativa o modo informado, ou desliga se ja estiver ativo.

        Usado pelos atalhos de teclado para manter UI sincronizada.
        """
        if mode not in ("all", "body", "buttons"):
            self._set_all_test_mode_buttons(False)
            return
        target_btn = self._test_mode_buttons[mode]
        target_btn.setChecked(not target_btn.isChecked())

    def _set_all_test_mode_buttons(self, checked: bool) -> None:
        self._test_mode_syncing = True
        try:
            for btn in self._test_mode_buttons.values():
                btn.setChecked(checked)
        finally:
            self._test_mode_syncing = False
        if not checked:
            self.test_mode_changed.emit("off")

    def current_test_mode(self) -> str:
        for key, btn in self._test_mode_buttons.items():
            if btn.isChecked():
                return key
        return "off"

    def is_terminal_write_enabled(self) -> bool:
        return self._datatest_terminal_checkbox.isChecked()

    def _on_terminal_layout_toggled(self, checked: bool) -> None:
        self._btn_terminal_layout.setToolTip(
            "Layout column: terminal abaixo de todo o app"
            if checked
            else "Layout row: terminal no reader"
        )
        self.terminal_layout_mode_toggled.emit(checked)

    def _toggle_px_ruler(self, checked: bool) -> None:
        self._px_ruler_visible = checked
        if checked:
            self._show_px_ruler_toasts()
        else:
            self._hide_px_ruler_toasts()

    def _show_px_ruler_toasts(self) -> None:
        host = self._test_mode_grid.parentWidget() or self
        self._hide_px_ruler_toasts()
        for width_px in self._PX_RULER_WIDTHS:
            toast = QLabel(f"{width_px}px", host)
            toast.setObjectName(f"pxRulerToast{width_px}")
            toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
            toast.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            toast.setFixedWidth(width_px)
            toast.setFixedHeight(20)
            toast.setStyleSheet(
                "background-color: rgba(34, 197, 94, 0.95);"
                "color: #FFFFFF;"
                "font-size: 10px;"
                "font-weight: 700;"
                "border-radius: 3px;"
            )
            toast.show()
            toast.raise_()
            self._px_ruler_toasts.append(toast)
        self._ensure_px_ruler_resize_filter(host)
        self._reposition_px_ruler_toasts()

    def _hide_px_ruler_toasts(self) -> None:
        for toast in self._px_ruler_toasts:
            toast.hide()
            toast.deleteLater()
        self._px_ruler_toasts.clear()
        self._remove_px_ruler_resize_filter()

    def _reposition_px_ruler_toasts(self) -> None:
        if not self._px_ruler_toasts:
            return
        host = self._px_ruler_toasts[0].parentWidget()
        if host is None:
            return
        margin = 8
        gap = 6
        y = host.height() - margin
        for toast in reversed(self._px_ruler_toasts):
            y -= toast.height()
            toast.move(margin, max(0, y))
            toast.raise_()
            y -= gap

    def _ensure_px_ruler_resize_filter(self, host: QWidget) -> None:
        class _ResizeFilter(QObject):
            def __init__(self, owner: HeaderBar, parent: QObject | None = None) -> None:
                super().__init__(parent)
                self._owner = owner

            def eventFilter(self, watched: QObject, event: QEvent) -> bool:
                if event.type() == QEvent.Type.Resize:
                    self._owner._reposition_px_ruler_toasts()
                return False

        self._remove_px_ruler_resize_filter()
        self._px_ruler_resize_filter = _ResizeFilter(self, host)
        host.installEventFilter(self._px_ruler_resize_filter)

    def _remove_px_ruler_resize_filter(self) -> None:
        filter_obj = self._px_ruler_resize_filter
        if filter_obj is None:
            return
        host = filter_obj.parent()
        if isinstance(host, QWidget):
            host.removeEventFilter(filter_obj)
        self._px_ruler_resize_filter = None

    def set_terminal_collapsed(self, collapsed: bool) -> None:
        self._btn_terminal_collapse.setText("▲" if collapsed else "▼")
        self._btn_terminal_collapse.setToolTip(
            "Expandir terminal (Ctrl+J)" if collapsed else "Colapsar terminal (Ctrl+J)"
        )
