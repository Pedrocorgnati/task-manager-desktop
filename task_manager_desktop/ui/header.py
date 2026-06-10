from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
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
    DOCUMENT_SVG,
    LAYOUT_STACK_SVG,
    PROMPT_SVG,
    TOOLS_SVG,
    TRASH_SVG,
    svg_to_icon,
)
from task_manager_desktop.ui.theme import HEADER_BAR_H


def _systemforge_root() -> Path:
    header_path = Path(__file__).resolve()
    for parent in header_path.parents:
        if (parent / ".claude" / "projects").is_dir():
            return parent
    return header_path.parents[4]


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
_TEST_MODE_LAUNCHER_STYLE = (
    "QPushButton { background-color: #27272A; color: #FAFAFA;"
    "  border: 1px solid #52525B; border-radius: 6px;"
    "  font-size: 11px; font-weight: 700; padding: 0 8px; }"
    "QPushButton:hover { background-color: #3F3F46; border-color: #71717A; }"
    "QPushButton:checked { background-color: #FBBF24; color: #18181B;"
    "  border-color: #FBBF24; }"
)


class _DraggableFloatingPanel(QWidget):
    """Painel filho flutuante com drag limitado ao widget pai."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._drag_offset: QPoint | None = None
        self.was_dragged = False

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        parent = self.parentWidget()
        if parent is None:
            return
        top_left_global = event.globalPosition().toPoint() - self._drag_offset
        top_left = parent.mapFromGlobal(top_left_global)
        max_x = max(0, parent.width() - self.width())
        max_y = max(0, parent.height() - self.height())
        self.move(
            min(max(0, top_left.x()), max_x),
            min(max(0, top_left.y()), max_y),
        )
        self.was_dragged = True
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)


class HeaderBar(QWidget):
    new_task_requested = Signal()
    type_filter_changed = Signal(object)  # frozenset[str]
    clear_completed_clicked = Signal()
    trash_clicked = Signal()
    # DataTest test-mode: emits "off" | "main" | "body" | "buttons"
    test_mode_changed = Signal(str)
    datatest_terminal_write_toggled = Signal(bool)
    terminal_layout_mode_toggled = Signal(bool)
    terminal_collapse_requested = Signal()
    # Emite o caminho ABSOLUTO de um arquivo do SystemForge para abrir no leitor.
    doc_file_requested = Signal(str)
    _PX_RULER_WIDTHS = (10, 50, 100)

    # Atalhos de documentos do SystemForge: (rótulo, caminho relativo à raiz).
    # Os arquivos vivem FORA da pasta task-manager-desktop; o caminho é resolvido
    # contra _systemforge_root() em runtime.
    _DOC_SHORTCUTS = (
        ("array.py", "ai-forge/lead-finder/array.py"),
        ("imbound-queries.txt", "ai-forge/lead-finder/output/imbound-queries.txt"),
        ("imbound-prepare.txt", "ai-forge/lead-finder/output/imbound-prepare.txt"),
        ("ASSETS-TO-CREATE.md", "forged-goods/assets/ASSETS-TO-CREATE.md"),
        ("pedro-corgnati.md", "forged-goods/assets/pedro-corgnati.md"),
        ("lessie-results.md", "ai-forge/lead-finder/lessie-prompts/results/lessie-results.md"),
        ("WORKFLOW-DETAILED.md", "WORKFLOW-DETAILED.md"),
    )
    _LESSIE_PROMPTS_DIR = "ai-forge/lead-finder/lessie-prompts"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(HEADER_BAR_H)
        self.setObjectName("HeaderBar")
        self.setProperty("testid", "header")
        self.setAccessibleName("Barra de cabeçalho")
        self._type_checkboxes: dict[str, QCheckBox] = {}
        self._px_ruler_toasts: list[QLabel] = []
        self._px_ruler_visible = False
        self._px_ruler_resize_filter: QObject | None = None
        self._test_mode_panel: _DraggableFloatingPanel | None = None

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
        self._btn_clear_done.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
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
        self._btn_trash.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._btn_trash.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_trash.clicked.connect(self.trash_clicked.emit)
        primary_layout.addWidget(self._btn_trash)

        self._btn_tools = QToolButton(self)
        self._btn_tools.setObjectName("headerToolsMenu")
        self._btn_tools.setProperty("testid", "header-tools-button")
        self._btn_tools.setProperty("data-testid", "header-tools-button")
        self._btn_tools.setAccessibleName("Abrir ferramentas")
        self._btn_tools.setToolTip("Ferramentas")
        self._btn_tools.setIcon(svg_to_icon(TOOLS_SVG, 20))
        self._btn_tools.setIconSize(QSize(20, 20))
        self._btn_tools.setFixedSize(40, 40)
        self._btn_tools.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._btn_tools.setCheckable(True)
        self._btn_tools.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_tools.toggled.connect(self._toggle_tools_panel)
        layout.addWidget(self._btn_tools)

        self._btn_docs = QToolButton(self)
        self._btn_docs.setObjectName("headerDocsMenu")
        self._btn_docs.setProperty("testid", "header-docs-button")
        self._btn_docs.setProperty("data-testid", "header-docs-button")
        self._btn_docs.setAccessibleName("Abrir documentos do SystemForge")
        self._btn_docs.setToolTip("Documentos do SystemForge")
        self._btn_docs.setIcon(svg_to_icon(DOCUMENT_SVG, 20))
        self._btn_docs.setIconSize(QSize(20, 20))
        self._btn_docs.setFixedSize(40, 40)
        self._btn_docs.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._btn_docs.setCheckable(True)
        self._btn_docs.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_docs.toggled.connect(self._toggle_docs_panel)
        layout.addWidget(self._btn_docs)

        self._btn_lessie_prompts = QToolButton(self)
        self._btn_lessie_prompts.setObjectName("headerLessiePromptsMenu")
        self._btn_lessie_prompts.setProperty("testid", "header-lessie-prompts-button")
        self._btn_lessie_prompts.setProperty("data-testid", "header-lessie-prompts-button")
        self._btn_lessie_prompts.setAccessibleName("Abrir prompts do Lessie")
        self._btn_lessie_prompts.setToolTip("Prompts do Lessie")
        self._btn_lessie_prompts.setIcon(svg_to_icon(PROMPT_SVG, 20))
        self._btn_lessie_prompts.setIconSize(QSize(20, 20))
        self._btn_lessie_prompts.setFixedSize(40, 40)
        self._btn_lessie_prompts.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly
        )
        self._btn_lessie_prompts.setCheckable(True)
        self._btn_lessie_prompts.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_lessie_prompts.toggled.connect(self._toggle_lessie_prompts_panel)
        layout.addWidget(self._btn_lessie_prompts)

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
        self._btn_terminal_layout.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly
        )
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

        self._btn_datatest_panel = QPushButton("DataTest", self)
        self._btn_datatest_panel.setObjectName("headerDataTestPanelToggle")
        self._btn_datatest_panel.setProperty("testid", "header-datatest-toggle")
        self._btn_datatest_panel.setAccessibleName("Abrir controles DataTest")
        self._btn_datatest_panel.setFixedSize(76, 32)
        self._btn_datatest_panel.setCheckable(True)
        self._btn_datatest_panel.setToolTip("Abrir controles DataTest")
        self._btn_datatest_panel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_datatest_panel.setStyleSheet(_TEST_MODE_LAUNCHER_STYLE)
        self._btn_datatest_panel.toggled.connect(self._toggle_test_mode_panel)
        layout.addWidget(self._btn_datatest_panel)

        # Test-mode Buttons (Main / Body / Btn) + terminal-write checkbox.
        # Comportamento radio-like: no maximo 1 checado. Re-click desliga (-> off).
        self._btn_datatest = QPushButton("Main")
        self._btn_datatest.setFixedSize(64, 32)
        self._btn_datatest.setCheckable(True)
        self._btn_datatest.setToolTip("Exibir data-testid principais (Ctrl+Shift+D)")
        self._btn_datatest.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_datatest.setStyleSheet(_TEST_MODE_BTN_STYLE_ALL)

        self._btn_bodytest = QPushButton("Body")
        self._btn_bodytest.setFixedSize(64, 32)
        self._btn_bodytest.setCheckable(True)
        self._btn_bodytest.setToolTip("Exibir data-testid EXCETO em botoes (Ctrl+Shift+B)")
        self._btn_bodytest.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_bodytest.setStyleSheet(_TEST_MODE_BTN_STYLE_BODY)

        self._btn_btntest = QPushButton("Btn")
        self._btn_btntest.setFixedSize(64, 32)
        self._btn_btntest.setCheckable(True)
        self._btn_btntest.setToolTip("Exibir data-testid APENAS em botoes (Ctrl+Shift+T)")
        self._btn_btntest.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_btntest.setStyleSheet(_TEST_MODE_BTN_STYLE_BTN)

        self._btn_px_ruler = QPushButton("px ruler")
        self._btn_px_ruler.setFixedSize(76, 32)
        self._btn_px_ruler.setCheckable(True)
        self._btn_px_ruler.setToolTip("Mostrar régua de largura em pixels")
        self._btn_px_ruler.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_px_ruler.setStyleSheet(_TEST_MODE_BTN_STYLE_BTN)
        self._btn_px_ruler.toggled.connect(self._toggle_px_ruler)

        self._datatest_terminal_checkbox = QCheckBox(self)
        self._datatest_terminal_checkbox.setObjectName("headerDataTestTerminalToggle")
        self._datatest_terminal_checkbox.setFixedSize(18, 32)
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

        self._test_mode_grid = _DraggableFloatingPanel(self)
        self._test_mode_panel = self._test_mode_grid
        self._test_mode_grid.setObjectName("DataTestFloatingPanel")
        self._test_mode_grid.setProperty("testid", "test-mode-overlay-controls")
        self._test_mode_grid.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._test_mode_grid.setFixedHeight(52)
        self._test_mode_grid.setStyleSheet(
            "QWidget#DataTestFloatingPanel { background-color: #1C1C1F;"
            "  border: 1px solid #52525B; border-radius: 8px; }"
        )
        _tm_row_layout = QHBoxLayout(self._test_mode_grid)
        _tm_row_layout.setContentsMargins(10, 8, 10, 8)
        _tm_row_layout.setSpacing(6)
        _tm_row_layout.addWidget(
            self._datatest_terminal_checkbox,
            alignment=Qt.AlignmentFlag.AlignVCenter,
        )
        _tm_row_layout.addWidget(self._btn_datatest)
        _tm_row_layout.addWidget(self._btn_bodytest)
        _tm_row_layout.addWidget(self._btn_btntest)
        _tm_row_layout.addWidget(self._btn_px_ruler)
        self._test_mode_grid.hide()

        # QButtonGroup com exclusive=False; logica radio manual no handler.
        # exclusive=True bloquearia o re-click de desligar o ativo.
        self._test_mode_group = QButtonGroup(self)
        self._test_mode_group.setExclusive(False)
        self._test_mode_group.addButton(self._btn_datatest)
        self._test_mode_group.addButton(self._btn_bodytest)
        self._test_mode_group.addButton(self._btn_btntest)

        self._test_mode_buttons: dict[str, QPushButton] = {
            "main": self._btn_datatest,
            "body": self._btn_bodytest,
            "buttons": self._btn_btntest,
        }
        # Flag para evitar reentrancia quando desligamos os outros botoes.
        self._test_mode_syncing = False
        for btn in self._test_mode_buttons.values():
            btn.toggled.connect(self._on_test_mode_button_toggled)

        self._tools_panel = QFrame(self)
        self._tools_panel.setObjectName("headerToolsPanel")
        self._tools_panel.setProperty("testid", "header-tools-panel")
        self._tools_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._tools_panel.setStyleSheet(
            "QFrame#headerToolsPanel { background-color: #1C1E25;"
            " border: 1px solid #363942; border-radius: 10px; }"
            "QPushButton#headerToolEntry {"
            " background: #1C1E25; color: #E4E4E7; border: 1px solid #363942;"
            " border-radius: 8px; font-size: 12px; font-weight: 800;"
            " text-align: left; padding: 6px 10px; }"
            "QPushButton#headerToolEntry:hover {"
            " background: #2A2110; border-color: #FBBF24; }"
        )
        tools_layout = QVBoxLayout(self._tools_panel)
        tools_layout.setContentsMargins(8, 8, 8, 8)
        tools_layout.setSpacing(6)
        self._btn_tool_forge_pick = QPushButton("forge-pick", self._tools_panel)
        self._btn_tool_forge_pick.setObjectName("headerToolEntry")
        self._btn_tool_forge_pick.setProperty("testid", "header-tool-forge-pick")
        self._btn_tool_forge_pick.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_tool_forge_pick.clicked.connect(self._open_forge_pick_tool)
        tools_layout.addWidget(self._btn_tool_forge_pick)
        self._btn_tool_forge_outreach = QPushButton(
            "forge-outreach", self._tools_panel
        )
        self._btn_tool_forge_outreach.setObjectName("headerToolEntry")
        self._btn_tool_forge_outreach.setProperty(
            "testid", "header-tool-forge-outreach"
        )
        self._btn_tool_forge_outreach.setAccessibleName(
            "Abrir forge-outreach (gerador de prospecção)"
        )
        self._btn_tool_forge_outreach.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_tool_forge_outreach.clicked.connect(self._open_forge_outreach_tool)
        tools_layout.addWidget(self._btn_tool_forge_outreach)
        self._tools_panel.adjustSize()
        self._tools_panel.hide()

        self._docs_panel = QFrame(self)
        self._docs_panel.setObjectName("headerDocsPanel")
        self._docs_panel.setProperty("testid", "header-docs-panel")
        self._docs_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._docs_panel.setStyleSheet(
            "QFrame#headerDocsPanel { background-color: #1C1E25;"
            " border: 1px solid #363942; border-radius: 10px; }"
            "QPushButton#headerDocEntry {"
            " background: #1C1E25; color: #E4E4E7; border: 1px solid #363942;"
            " border-radius: 8px; font-size: 12px; font-weight: 800;"
            " text-align: left; padding: 6px 10px; }"
            "QPushButton#headerDocEntry:hover {"
            " background: #2A2110; border-color: #FBBF24; }"
        )
        docs_layout = QVBoxLayout(self._docs_panel)
        docs_layout.setContentsMargins(8, 8, 8, 8)
        docs_layout.setSpacing(6)
        for label, relpath in self._DOC_SHORTCUTS:
            slug = label.lower().replace(".", "-").replace("/", "-")
            btn = QPushButton(label, self._docs_panel)
            btn.setObjectName("headerDocEntry")
            btn.setProperty("testid", f"header-doc-{slug}")
            btn.setToolTip(relpath)
            btn.setAccessibleName(f"Abrir {relpath} no leitor")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, rp=relpath: self._open_doc(rp))
            docs_layout.addWidget(btn)
        self._docs_panel.adjustSize()
        self._docs_panel.hide()

        self._lessie_prompts_panel = QFrame(self)
        self._lessie_prompts_panel.setObjectName("headerLessiePromptsPanel")
        self._lessie_prompts_panel.setProperty("testid", "header-lessie-prompts-panel")
        self._lessie_prompts_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._lessie_prompts_panel.setStyleSheet(
            "QFrame#headerLessiePromptsPanel { background-color: #1C1E25;"
            " border: 1px solid #363942; border-radius: 10px; }"
            "QPushButton#headerDocEntry {"
            " background: #1C1E25; color: #E4E4E7; border: 1px solid #363942;"
            " border-radius: 8px; font-size: 12px; font-weight: 800;"
            " text-align: left; padding: 6px 10px; }"
            "QPushButton#headerDocEntry:hover {"
            " background: #2A2110; border-color: #FBBF24; }"
        )
        lessie_layout = QVBoxLayout(self._lessie_prompts_panel)
        lessie_layout.setContentsMargins(8, 8, 8, 8)
        lessie_layout.setSpacing(6)

        lessie_prompt_files = self._collect_lessie_prompt_shortcuts()
        if not lessie_prompt_files:
            empty_btn = QPushButton(
                "Nenhum arquivo .md encontrado", self._lessie_prompts_panel
            )
            empty_btn.setObjectName("headerDocEntry")
            empty_btn.setEnabled(False)
            lessie_layout.addWidget(empty_btn)
        else:
            for label, relpath in lessie_prompt_files:
                slug = f"lessie-{label.lower().replace('.', '-')}"
                btn = QPushButton(label, self._lessie_prompts_panel)
                btn.setObjectName("headerDocEntry")
                btn.setProperty("testid", f"header-lessie-doc-{slug}")
                btn.setToolTip(relpath)
                btn.setAccessibleName(f"Abrir {relpath} no leitor")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(
                    lambda _checked=False, rp=relpath: self._open_doc(rp)
                )
                lessie_layout.addWidget(btn)
        self._lessie_prompts_panel.adjustSize()
        self._lessie_prompts_panel.hide()

    def _toggle_test_mode_panel(self, checked: bool) -> None:
        panel = self._test_mode_panel
        if panel is None:
            return
        if checked:
            host = self.window()
            if not isinstance(host, QWidget):
                host = self
            if panel.parentWidget() is not host:
                panel.setParent(host)
            self._position_test_mode_panel()
            panel.show()
            panel.raise_()
        else:
            panel.hide()

    def _position_test_mode_panel(self) -> None:
        panel = self._test_mode_panel
        if panel is None:
            return
        host = panel.parentWidget()
        if host is None:
            return
        panel.adjustSize()
        margin = 12
        if not panel.was_dragged:
            panel.move(
                max(margin, host.width() - panel.width() - margin),
                max(margin, host.height() - panel.height() - margin),
            )
            return
        panel.move(
            min(max(0, panel.x()), max(0, host.width() - panel.width())),
            min(max(0, panel.y()), max(0, host.height() - panel.height())),
        )

    def _toggle_tools_panel(self, checked: bool) -> None:
        if checked:
            if self._btn_docs.isChecked():
                self._btn_docs.setChecked(False)
            if self._btn_lessie_prompts.isChecked():
                self._btn_lessie_prompts.setChecked(False)
            self._position_tools_panel()
            self._tools_panel.show()
            self._tools_panel.raise_()
            return
        self._tools_panel.hide()

    def _position_tools_panel(self) -> None:
        self._position_dropdown_panel(self._tools_panel, self._btn_tools)

    def _toggle_docs_panel(self, checked: bool) -> None:
        if checked:
            # Mutuamente exclusivo com o painel de ferramentas (ancoram no mesmo
            # canto e se sobreporiam). Desmarcar dispara o hide do outro painel.
            if self._btn_tools.isChecked():
                self._btn_tools.setChecked(False)
            if self._btn_lessie_prompts.isChecked():
                self._btn_lessie_prompts.setChecked(False)
            self._position_docs_panel()
            self._docs_panel.show()
            self._docs_panel.raise_()
            return
        self._docs_panel.hide()

    def _toggle_lessie_prompts_panel(self, checked: bool) -> None:
        if checked:
            if self._btn_tools.isChecked():
                self._btn_tools.setChecked(False)
            if self._btn_docs.isChecked():
                self._btn_docs.setChecked(False)
            self._position_lessie_prompts_panel()
            self._lessie_prompts_panel.show()
            self._lessie_prompts_panel.raise_()
            return
        self._lessie_prompts_panel.hide()

    def _position_docs_panel(self) -> None:
        self._position_dropdown_panel(self._docs_panel, self._btn_docs)

    def _position_lessie_prompts_panel(self) -> None:
        self._position_dropdown_panel(self._lessie_prompts_panel, self._btn_lessie_prompts)

    def _position_dropdown_panel(self, panel: QFrame, anchor: QWidget) -> None:
        # Reparenta o painel para a janela top-level antes de posicionar. Como
        # filho do header (uma barra horizontal fina), o painel ficaria recortado
        # ao retangulo do header e a parte que desce abaixo dele seria invisivel.
        host = self.window()
        if not isinstance(host, QWidget):
            host = self
        if panel.parentWidget() is not host:
            panel.setParent(host)
        panel.adjustSize()
        # Ancora logo abaixo do botao, alinhado a esquerda do anchor.
        top_left = anchor.mapTo(host, QPoint(0, anchor.height() + 4))
        x = top_left.x()
        y = top_left.y()
        max_x = max(0, host.width() - panel.width())
        max_y = max(0, host.height() - panel.height())
        panel.move(min(max(0, x), max_x), min(max(0, y), max_y))

    def _open_doc(self, relpath: str) -> None:
        forge_root = _systemforge_root()
        abs_path = forge_root / relpath
        self.doc_file_requested.emit(str(abs_path))

    def _open_forge_pick_tool(self) -> None:
        forge_root = _systemforge_root()
        tool_app = forge_root / "ai-forge" / "forge-pick" / "app.py"
        try:
            subprocess.Popen(
                ["python3", str(tool_app)],
                cwd=str(forge_root),
                start_new_session=True,
            )
        except FileNotFoundError:
            return
        self._btn_tools.setChecked(False)

    def _open_forge_outreach_tool(self) -> None:
        forge_root = _systemforge_root()
        tool_root = forge_root / "ai-forge" / "forge-outreach"
        run_py = tool_root / "run.py"
        if not run_py.is_file():
            self._show_tool_launch_warning(
                f"forge-outreach indisponível: {run_py} não encontrado."
            )
            return
        # sys.executable garante o mesmo interpretador (com PySide6) do
        # task-manager; python3 do PATH pode nao ter as dependencias.
        python = sys.executable or "python3"
        try:
            proc = subprocess.Popen(
                [python, str(run_py)],
                cwd=str(tool_root),
                start_new_session=True,
            )
        except (FileNotFoundError, OSError) as exc:
            self._show_tool_launch_warning(f"Falha ao abrir forge-outreach: {exc}")
            return
        # Zero Silencio: morte precoce do filho (ImportError, crash de boot)
        # vira aviso visivel em vez de clique mudo.
        QTimer.singleShot(
            1500, self, lambda p=proc: self._check_tool_launch(p, "forge-outreach")
        )
        self._btn_tools.setChecked(False)

    def _check_tool_launch(self, proc: subprocess.Popen, name: str) -> None:
        code = proc.poll()
        if code is not None and code != 0:
            self._show_tool_launch_warning(
                f"{name} terminou com erro ao iniciar (exit {code})."
            )

    def _show_tool_launch_warning(self, message: str) -> None:
        try:
            from task_manager_desktop.ui.toast import ToastWidget

            top = self.window()
            if isinstance(top, QWidget):
                toast = ToastWidget(top)
                toast.show_message(message)
        except Exception:  # noqa: BLE001
            pass

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._btn_tools.isChecked():
            self._position_tools_panel()
        if self._btn_docs.isChecked():
            self._position_docs_panel()
        if self._btn_lessie_prompts.isChecked():
            self._position_lessie_prompts_panel()

    def _collect_lessie_prompt_shortcuts(self) -> list[tuple[str, str]]:
        forge_root = _systemforge_root()
        prompts_dir = forge_root / self._LESSIE_PROMPTS_DIR
        if not prompts_dir.exists():
            return []
        results: list[tuple[str, str]] = []
        for path in sorted(prompts_dir.glob("*.md")):
            if path.is_file():
                relative = path.relative_to(forge_root)
                results.append((path.name, str(relative)))
        return results

    def take_primary_controls(self) -> QWidget:
        self._primary_controls.setParent(None)
        return self._primary_controls

    def take_test_mode_grid(self) -> QWidget:
        """Compat legado: entrega o painel DataTest flutuante, oculto por padrão."""
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
        if mode not in ("main", "body", "buttons"):
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
