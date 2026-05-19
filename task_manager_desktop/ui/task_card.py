from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.models import Status, Task
from task_manager_desktop.core.sector import count_open_deps
from task_manager_desktop.ui.widgets.status_segmented_control import StatusSegmentedControl

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
        "badge": "EXECUTANDO",
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
        "badge": "PRONTA",
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
        "badge": "BLOQUEADA",
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
        "badge": "CONCLUÍDA",
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
        self.setFixedHeight(112)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setProperty("selected", False)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setAccessibleName(f"Task {task.id}")
        self.setAccessibleDescription(f"{task.title}, {task.status.value}, projeto {task.projeto}")

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
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(7)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(7)

        left_meta = QHBoxLayout()
        left_meta.setSpacing(6)

        self._id_label = QLabel(self._task.id, self)
        self._id_label.setObjectName("cardId")
        left_meta.addWidget(self._id_label)

        self._project_tag = QLabel(self)
        self._project_tag.setObjectName("cardProject")
        self._project_tag.setTextFormat(Qt.TextFormat.PlainText)
        left_meta.addWidget(self._project_tag)

        self._state_badge = QLabel(self)
        self._state_badge.setObjectName("cardStateBadge")
        self._state_badge.setTextFormat(Qt.TextFormat.PlainText)
        left_meta.addWidget(self._state_badge)

        meta_row.addLayout(left_meta)
        meta_row.addStretch()

        right_meta = QHBoxLayout()
        right_meta.setSpacing(6)

        self._seg_ctrl = StatusSegmentedControl(self._task, self._all_tasks, self)
        self._seg_ctrl.status_changed.connect(self._on_status_change)
        right_meta.addWidget(self._seg_ctrl)

        self._menu_btn = QPushButton("⋯", self)
        self._menu_btn.setProperty("class", "menu-btn")
        self._menu_btn.setFixedSize(30, 26)
        self._menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._menu_btn.setAccessibleName(f"Abrir menu de opções da task {self._task.id}")
        self._menu_btn.clicked.connect(self._show_context_menu)
        right_meta.addWidget(self._menu_btn)

        meta_row.addLayout(right_meta)
        outer.addLayout(meta_row)

        self._title_label = QLabel(self._task.title, self)
        self._title_label.setObjectName("cardTitle")
        self._title_label.setTextFormat(Qt.TextFormat.PlainText)
        self._title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._title_label.setToolTip(self._task.title)
        self._title_label.setMinimumHeight(26)
        outer.addWidget(self._title_label)

        context_row = QHBoxLayout()
        context_row.setSpacing(8)

        self._type_icon = QLabel(self)
        self._type_icon.setObjectName("cardTypeChip")
        self._type_icon.setFixedHeight(22)
        context_row.addWidget(self._type_icon)

        self._deps_label = QLabel(self)
        self._deps_label.setObjectName("cardDeps")
        self._deps_label.setTextFormat(Qt.TextFormat.PlainText)
        self._deps_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        context_row.addWidget(self._deps_label)
        context_row.addStretch()

        outer.addLayout(context_row)
        self._refresh_text_content()

    def _refresh_text_content(self) -> None:
        projeto_text = f"#{self._task.projeto}"
        fm = QFontMetrics(self.font())
        self._project_tag.setText(fm.elidedText(projeto_text, Qt.TextElideMode.ElideRight, 190))
        self._project_tag.setToolTip(self._task.projeto)
        state = self._card_state()
        self._state_badge.setText(_CARD_STYLE[state]["badge"])
        self._title_label.setText(self._task.title)
        self._title_label.setToolTip(self._task.title)

        type_text = "ONLINE" if self._task.type.value == "online" else "OFFLINE"
        self._type_icon.setText(type_text)
        self._type_icon.setMinimumWidth(58)
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
            "border-radius: 14px;"
            "}"
            "QFrame#taskCard:hover {"
            f"background: {style['hover']};"
            "}"
            "QPushButton[class='menu-btn'] {"
            f"background: {style['chip_bg']}; color: {style['chip_text']};"
            "border: none; border-radius: 8px; font-size: 18px; font-weight: 800;"
            "}"
            "QPushButton[class='menu-btn']:hover { background: rgba(255,255,255,0.18); }"
        )
        self._id_label.setStyleSheet(
            f"font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace; font-size: 12px; "
            f"font-weight: 800; color: {style['chip_text']}; background: {style['chip_bg']}; "
            "border-radius: 7px; padding: 3px 7px;"
        )
        self._project_tag.setStyleSheet(
            f"font-size: 12px; font-weight: 800; color: {style['meta']}; background: transparent;"
        )
        self._state_badge.setStyleSheet(
            f"font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace; font-size: 9px; "
            f"font-weight: 900; letter-spacing: 0.7px; color: {style['chip_text']}; "
            f"background: {style['chip_bg']}; border-radius: 7px; padding: 3px 7px;"
        )
        title_legacy_marker = " /* #A1A1AA */" if state == "blocked" else ""
        self._title_label.setStyleSheet(
            f"font-size: 14px; font-weight: 400; color: {style['title']}; "
            f"background: transparent;{title_legacy_marker}"
        )
        self._type_icon.setStyleSheet(
            f"font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace; font-size: 10px; "
            f"font-weight: 900; letter-spacing: 0.8px; color: {style['chip_text']}; "
            f"background: {style['chip_bg']}; border-radius: 7px; padding: 3px 7px;"
        )
        open_deps = count_open_deps(self._task.deps, self._all_tasks)
        deps_color = "#EAB308" if open_deps > 0 else "#71717A"
        self._deps_label.setStyleSheet(
            f"font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace; font-size: 13px; "
            f"font-weight: 700; color: {deps_color}; background: transparent;"
        )
        self._seg_ctrl.apply_palette(state, style)

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
        self.setAccessibleDescription(f"{task.title}, {task.status.value}, projeto {task.projeto}")
        self._id_label.setText(task.id)
        self._refresh_text_content()
        self._seg_ctrl.update_task(task, self._all_tasks)
        self._apply_card_style()
