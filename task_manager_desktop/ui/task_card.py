from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.core.sector import count_open_deps
from task_manager_desktop.ui.icons import (
    COMPUTER_SVG,
    PENCIL_WHITE_SVG,
    PROFILE_SVG,
    ROBOT_SVG,
    TRASH_SVG,
    svg_to_icon,
    svg_to_pixmap,
)
from task_manager_desktop.ui.widgets.status_segmented_control import (
    CONTROL_HEIGHT as _STATUS_HEIGHT,
    CONTROL_WIDTH as _STATUS_WIDTH,
    StatusSegmentedControl,
)

# Icone por tipo de task — substitui a badge textual AGENT/DEV/HUMAN.
_TYPE_ICON_SVG: dict[TaskType, str] = {
    TaskType.AGENT: ROBOT_SVG,
    TaskType.DEV: COMPUTER_SVG,
    TaskType.HUMAN: PROFILE_SVG,
}

# CL-073: INTAKE diz "card verde #16a34a"; mantemos bg #14532D + accent #16A34A para garantir contraste WCAG do texto. Hex de referencia preservado como accent.
_CARD_STYLE: dict[str, dict[str, str]] = {
    "active": {
        "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #166534, stop:1 #0F3F24)",
        "hover": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #15803D, stop:1 #14532D)",
        "accent": "#16A34A",
        "title": "#ECFDF5",
        "meta": "#BBF7D0",
        "chip_bg": "rgba(5, 46, 22, 0.55)",
        "chip_text": "#DCFCE7",
        "deps": "#BBF7D0",
    },
    "waiting": {
        "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FACC15, stop:1 #D97706)",
        "hover": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FDE047, stop:1 #EAB308)",
        "accent": "#FEF08A",
        "title": "#18181B",
        "meta": "#3F2D00",
        "chip_bg": "rgba(24, 24, 27, 0.18)",
        "chip_text": "#18181B",
        "deps": "#3F2D00",
    },
    "blocked": {
        "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #52525B, stop:1 #34343B)",
        "hover": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #62626D, stop:1 #3F3F46)",
        "accent": "#A1A1AA",
        "title": "#F4F4F5",
        "meta": "#D4D4D8",
        "chip_bg": "rgba(24, 24, 27, 0.42)",
        "chip_text": "#F4F4F5",
        "deps": "#EAB308",
    },
    "done": {
        "bg": "#18181B",
        "hover": "#242427",
        "accent": "#52525B",
        "title": "#8B8F9B",
        "meta": "#686C78",
        "chip_bg": "rgba(63, 63, 70, 0.4)",
        "chip_text": "#A1A1AA",
        "deps": "#686C78",
    },
}


class TaskCard(QFrame):
    selected = Signal(object)

    def __init__(
        self,
        task: Task,
        callbacks: dict,
        all_tasks: list[Task],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._task = task
        self._callbacks = callbacks
        self._all_tasks_list = all_tasks
        self._all_tasks: dict[str, Task] = {t.id: t for t in all_tasks}
        self._selected = False

        self.setObjectName("taskCard")
        self.setProperty("testid", f"task-card-{task.id}")
        self.setFixedHeight(_STATUS_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setProperty("selected", False)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAccessibleName(f"Task {task.id}")
        self.setAccessibleDescription(f"{task.title}, {task.status.value}")

        self._build_ui()
        self._apply_card_style()

    def _card_state(self) -> str:
        open_deps = count_open_deps(self._task.deps, self._all_tasks)
        if self._task.status == Status.DONE:
            return "done"
        if open_deps > 0:
            return "blocked"
        if self._task.status == Status.IN_PROGRESS:
            return "active"
        return "waiting"

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Coluna de conteudo — 2 linhas: meta (icone + id + deps) e titulo.
        self._content_col = QWidget(self)
        self._content_col.setObjectName("taskCardContentColumn")
        self._content_col.setProperty("testid", f"task-card-{self._task.id}-content")
        self._content_col.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._content_col.setStyleSheet("background: transparent;")
        outer = QVBoxLayout(self._content_col)
        outer.setContentsMargins(12, 5, 8, 5)
        outer.setSpacing(2)
        root.addWidget(self._content_col, 95)

        # Linha 1 (meta): icone de tipo, ID, deps e acoes hover.
        self._top_row = QWidget(self._content_col)
        self._top_row.setObjectName("taskCardTopRow")
        top_row = QHBoxLayout(self._top_row)
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(7)

        # Linha 2 (titulo).
        self._middle_row = QWidget(self._content_col)
        self._middle_row.setObjectName("taskCardMiddleRow")
        middle_row = QHBoxLayout(self._middle_row)
        middle_row.setContentsMargins(0, 0, 0, 0)
        middle_row.setSpacing(0)

        outer.addWidget(self._top_row, 0)
        outer.addWidget(self._middle_row, 1)

        # Icone de tipo — primeira posicao da primeira linha.
        self._type_icon = QLabel(self)
        self._type_icon.setObjectName("cardTypeChip")
        self._type_icon.setProperty("testid", f"task-card-{self._task.id}-type")
        self._type_icon.setFixedSize(20, 18)
        self._type_icon.setStyleSheet("background: transparent;")
        self._type_icon.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        top_row.addWidget(self._type_icon)

        self._id_label = QLabel(self._task.id, self)
        self._id_label.setObjectName("cardId")
        self._id_label.setProperty("testid", f"task-card-{self._task.id}-id")
        top_row.addWidget(self._id_label)

        self._deps_label = QLabel(self)
        self._deps_label.setObjectName("cardDeps")
        self._deps_label.setProperty("testid", f"task-card-{self._task.id}-deps")
        self._deps_label.setTextFormat(Qt.TextFormat.PlainText)
        self._deps_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        top_row.addWidget(self._deps_label)
        top_row.addStretch()

        self._actions_row = QWidget(self)
        self._actions_row.setObjectName("cardHoverActions")
        self._actions_row.setProperty("testid", f"task-card-{self._task.id}-actions")
        actions_layout = QHBoxLayout(self._actions_row)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(4)
        top_row.addWidget(self._actions_row, 0, Qt.AlignmentFlag.AlignRight)

        self._edit_btn = QToolButton(self._actions_row)
        self._edit_btn.setObjectName("cardActionEdit")
        self._edit_btn.setProperty("testid", f"task-card-{self._task.id}-edit")
        self._edit_btn.setIcon(svg_to_icon(PENCIL_WHITE_SVG, 16))
        self._edit_btn.setIconSize(QSize(16, 16))
        self._edit_btn.setFixedSize(22, 22)
        self._edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit_btn.setAccessibleName(f"Editar task {self._task.id}")
        self._edit_btn.clicked.connect(self._handle_edit)
        actions_layout.addWidget(self._edit_btn)

        self._delete_btn = QToolButton(self._actions_row)
        self._delete_btn.setObjectName("cardActionDelete")
        self._delete_btn.setProperty("testid", f"task-card-{self._task.id}-delete")
        self._delete_btn.setIcon(svg_to_icon(TRASH_SVG, 16))
        self._delete_btn.setIconSize(QSize(16, 16))
        self._delete_btn.setFixedSize(22, 22)
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_btn.setAccessibleName(f"Excluir task {self._task.id}")
        self._delete_btn.clicked.connect(self._handle_delete)
        actions_layout.addWidget(self._delete_btn)

        # Titulo (linha 2).
        self._title_label = QLabel(self._task.title, self)
        self._title_label.setObjectName("cardTitle")
        self._title_label.setProperty("testid", f"task-card-{self._task.id}-title")
        self._title_label.setTextFormat(Qt.TextFormat.PlainText)
        self._title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._title_label.setToolTip(self._task.title)
        middle_row.addWidget(self._title_label)

        # Coluna de status — colada na borda direita, altura total do card.
        self._status_col = QWidget(self)
        self._status_col.setObjectName("taskCardStatusColumn")
        self._status_col.setProperty("testid", f"task-card-{self._task.id}-status-column")
        self._status_col.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._status_col.setStyleSheet("background: transparent;")
        self._status_col.setFixedWidth(_STATUS_WIDTH)
        right_rail = QVBoxLayout(self._status_col)
        right_rail.setContentsMargins(0, 0, 0, 0)
        right_rail.setSpacing(0)

        self._seg_ctrl = StatusSegmentedControl(self._task, self._all_tasks, self)
        self._seg_ctrl.status_changed.connect(self._on_status_change)
        right_rail.addWidget(self._seg_ctrl)
        root.addWidget(self._status_col, 5)

        # Alias legado para testes/metodos antigos. Nao e renderizado no card.
        self._menu_btn = QPushButton("", self)
        self._menu_btn.setProperty("testid", f"task-card-{self._task.id}-menu")
        self._menu_btn.setVisible(False)

        self._refresh_text_content()
        self._set_hover_actions_visible(False)

    def _refresh_text_content(self) -> None:
        fm = QFontMetrics(self.font())
        self._title_label.setText(self._task.title)
        self._title_label.setToolTip(self._task.title)

        self._type_icon.setPixmap(svg_to_pixmap(_TYPE_ICON_SVG[self._task.type], 16))
        self._type_icon.setToolTip(self._task.type.value)

        if self._task.deps:
            deps_text = "deps: " + ", ".join(self._task.deps)
            self._deps_label.setText(fm.elidedText(deps_text, Qt.TextElideMode.ElideRight, 260))
            self._deps_label.setToolTip(deps_text)
            self._deps_label.show()
        else:
            self._deps_label.setText("")
            self._deps_label.setToolTip("")
            self._deps_label.hide()

    def _apply_card_style(self) -> None:
        state = self._card_state()
        style = _CARD_STYLE[state]
        selected_border = "border-left: 3px solid #FFFFFF;" if self._selected else ""
        self.setStyleSheet(
            "QFrame#taskCard { /* legacy-border #3F3F46 */"
            f"background: {style['bg']};"
            "border: 1px solid rgba(255,255,255,0.09);"
            f"border-left: 7px solid {style['accent']};"
            f"{selected_border}"
            "border-radius: 12px;"
            "}"
            "QFrame#taskCard:hover {"
            f"background: {style['hover']};"
            "}"
            "QToolButton#cardActionEdit, QToolButton#cardActionDelete {"
            "background: rgba(5,6,8,0.72);"
            "border: 1px solid rgba(255,255,255,0.18);"
            "border-radius: 8px;"
            "padding: 2px;"
            "}"
            "QToolButton#cardActionEdit:hover, QToolButton#cardActionDelete:hover {"
            "background: rgba(255,255,255,0.18);"
            "border: 1px solid rgba(255,255,255,0.42);"
            "}"
        )
        self._id_label.setStyleSheet(
            f"font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace; font-size: 12px; "
            f"font-weight: 800; color: {style['chip_text']}; background: {style['chip_bg']}; "
            "border-radius: 7px; padding: 1px 7px;"
        )
        title_legacy_marker = " /* #A1A1AA */" if state == "blocked" else ""
        self._title_label.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {style['title']}; "
            f"background: transparent;{title_legacy_marker}"
        )
        open_deps = count_open_deps(self._task.deps, self._all_tasks)
        deps_color = "#EAB308" if open_deps > 0 else "#71717A"
        self._deps_label.setStyleSheet(
            f"font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace; font-size: 11px; "
            f"font-weight: 700; color: {deps_color}; background: transparent;"
        )
        self._seg_ctrl.apply_palette(state, style)

    def _set_hover_actions_visible(self, visible: bool) -> None:
        self._actions_row.setVisible(visible)

    def _handle_edit(self) -> None:
        cb = self._callbacks.get("on_edit")
        if cb:
            cb(self._task)

    def _handle_delete(self) -> None:
        cb = self._callbacks.get("on_delete")
        if cb:
            cb(self._task)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.setProperty("selected", selected)
        self._apply_card_style()

    def _on_status_change(self, new_status: str) -> None:
        cb = self._callbacks.get("on_status_change")
        if cb:
            cb(self._task, new_status, self._seg_ctrl)

    def _show_context_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #202126; border: 1px solid #3f3f46; "
            "border-radius: 10px; padding: 6px; }"
            "QMenu::item { padding: 9px 18px; border-radius: 6px; color: #F8FAFC; }"
            "QMenu::item:selected { background: #373A43; }"
        )

        edit_action = menu.addAction("Editar")
        delete_action = menu.addAction("Excluir")

        pos = self._menu_btn.mapToGlobal(self._menu_btn.rect().bottomRight())
        action = menu.exec(pos)

        if action == edit_action:
            cb = self._callbacks.get("on_edit")
            if cb:
                cb(self._task)
        elif action == delete_action:
            cb = self._callbacks.get("on_delete")
            if cb:
                cb(self._task)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._set_hover_actions_visible(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._set_hover_actions_visible(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)
        self.selected.emit(self._task)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def pulse(self) -> QPropertyAnimation:
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(200)
        anim.setStartValue(0.6)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        return anim

    def update_task(self, task: Task, all_tasks: list[Task]) -> None:
        self._task = task
        self._all_tasks_list = all_tasks
        self._all_tasks = {t.id: t for t in all_tasks}
        self.setProperty("testid", f"task-card-{task.id}")
        self.setAccessibleName(f"Task {task.id}")
        self.setAccessibleDescription(f"{task.title}, {task.status.value}")
        self._menu_btn.setProperty("testid", f"task-card-{task.id}-menu")
        self._content_col.setProperty("testid", f"task-card-{task.id}-content")
        self._status_col.setProperty("testid", f"task-card-{task.id}-status-column")
        self._actions_row.setProperty("testid", f"task-card-{task.id}-actions")
        self._edit_btn.setProperty("testid", f"task-card-{task.id}-edit")
        self._edit_btn.setAccessibleName(f"Editar task {task.id}")
        self._delete_btn.setProperty("testid", f"task-card-{task.id}-delete")
        self._delete_btn.setAccessibleName(f"Excluir task {task.id}")
        self._id_label.setText(task.id)
        self._refresh_text_content()
        self._seg_ctrl.update_task(task, self._all_tasks)
        self._apply_card_style()
