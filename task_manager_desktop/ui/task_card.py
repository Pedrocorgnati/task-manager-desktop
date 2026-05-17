from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt, Signal
from PySide6.QtGui import QFontMetrics, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
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
from task_manager_desktop.ui.icons import WIFI_OFF_SVG, WIFI_SVG
from task_manager_desktop.ui.theme import PALETTE
from task_manager_desktop.ui.widgets.status_segmented_control import StatusSegmentedControl

_CARD_BG: dict[str, str] = {
    "ip_active": "#1C2E24",
    "ip_blocked": "#2A2110",
    "pending": PALETTE["BG_CARD"],
    "done": PALETTE["BG_CARD"],
}

_CARD_BORDER: dict[str, str] = {
    "ip_active": PALETTE["COLOR_SUCCESS"],
    "ip_blocked": PALETTE["COLOR_WARNING"],
    "pending": PALETTE["BORDER_STRONG"],
    "done": PALETTE["BORDER_STRONG"],
}

_TITLE_COLOR: dict[str, str] = {
    "ip_active": PALETTE["TEXT_PRIMARY"],
    "ip_blocked": PALETTE["TEXT_PRIMARY"],
    "pending_nodeps": PALETTE["TEXT_PRIMARY"],
    "pending_deps": PALETTE["TEXT_SECONDARY"],
    "done": PALETTE["TEXT_MUTED"],
}


def _make_icon_pixmap(svg_str: str) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


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

        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setProperty("selected", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAccessibleName(f"Task {task.id}")
        self.setAccessibleDescription(
            f"{task.title}, {task.status.value}, projeto {task.projeto}"
        )

        self._build_ui()
        self._apply_card_style()

    def _card_state(self) -> str:
        open_deps = count_open_deps(self._task.deps, self._all_tasks)
        if self._task.status == Status.IN_PROGRESS:
            return "ip_active" if open_deps == 0 else "ip_blocked"
        if self._task.status == Status.DONE:
            return "done"
        return "pending"

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(2)

        # Linha 1: meta-row
        meta_row = QHBoxLayout()
        meta_row.setSpacing(4)

        left_meta = QHBoxLayout()
        left_meta.setSpacing(4)

        self._id_label = QLabel(self._task.id, self)
        self._id_label.setObjectName("cardId")
        self._id_label.setStyleSheet(
            f"font-family: 'JetBrains Mono', monospace; font-size: 11px; color: {PALETTE['TEXT_MUTED']};"
        )
        left_meta.addWidget(self._id_label)

        projeto_text = f"#{self._task.projeto}"
        fm = QFontMetrics(self.font())
        elided = fm.elidedText(projeto_text, Qt.TextElideMode.ElideRight, 160)
        self._project_tag = QLabel(elided, self)
        self._project_tag.setObjectName("cardProject")
        self._project_tag.setTextFormat(Qt.TextFormat.PlainText)
        self._project_tag.setToolTip(self._task.projeto)
        self._project_tag.setStyleSheet(f"font-size: 12px; color: {PALETTE['TEXT_SECONDARY']};")
        left_meta.addWidget(self._project_tag)

        meta_row.addLayout(left_meta)
        meta_row.addStretch()

        right_meta = QHBoxLayout()
        right_meta.setSpacing(0)

        self._seg_ctrl = StatusSegmentedControl(
            self._task, self._all_tasks, self
        )
        self._seg_ctrl.status_changed.connect(self._on_status_change)
        right_meta.addWidget(self._seg_ctrl)

        self._menu_btn = QPushButton("⋯", self)
        self._menu_btn.setProperty("class", "menu-btn")
        self._menu_btn.setFixedSize(24, 22)
        self._menu_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #A1A1AA; "
            "border: none; border-radius: 4px; font-size: 16px; }"
            "QPushButton:hover { background: #3F3F46; color: #FAFAFA; }"
        )
        self._menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._menu_btn.setAccessibleName(f"Abrir menu de opções da task {self._task.id}")
        self._menu_btn.clicked.connect(self._show_context_menu)
        right_meta.addWidget(self._menu_btn)

        meta_row.addLayout(right_meta)
        outer.addLayout(meta_row)

        # Linha 2: title-row
        title_row = QHBoxLayout()
        self._title_label = QLabel(self._task.title, self)
        self._title_label.setObjectName("cardTitle")
        self._title_label.setTextFormat(Qt.TextFormat.PlainText)
        self._title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        title_row.addWidget(self._title_label)
        outer.addLayout(title_row)

        # Linha 3: status-row
        status_row = QHBoxLayout()
        status_row.setSpacing(4)

        self._type_icon = QLabel(self)
        svg = WIFI_SVG if self._task.type.value == "online" else WIFI_OFF_SVG
        self._type_icon.setPixmap(_make_icon_pixmap(svg))
        self._type_icon.setFixedSize(16, 16)
        self._type_icon.setToolTip(self._task.type.value)
        status_row.addWidget(self._type_icon)

        self._deps_label = QLabel(self)
        self._deps_label.setObjectName("cardDeps")
        self._deps_label.setStyleSheet(
            "font-family: 'JetBrains Mono', monospace; font-size: 11px;"
        )
        if self._task.deps:
            self._deps_label.show()
            self._refresh_deps_label()
        else:
            self._deps_label.hide()
        status_row.addWidget(self._deps_label)
        status_row.addStretch()

        outer.addLayout(status_row)

    def _refresh_deps_label(self) -> None:
        open_count = count_open_deps(self._task.deps, self._all_tasks)
        color = "#eab308" if open_count > 0 else "#71717A"
        text = "→ " + ", ".join(self._task.deps)
        self._deps_label.setText(text)
        self._deps_label.setStyleSheet(
            f"font-family: 'JetBrains Mono', monospace; font-size: 11px; color: {color};"
        )

    def _apply_card_style(self) -> None:
        state = self._card_state()
        bg = _CARD_BG.get(state, "#27272A")
        border = _CARD_BORDER.get(state, "#3F3F46")

        open_deps = count_open_deps(self._task.deps, self._all_tasks)
        if self._task.status == Status.DONE:
            title_color = _TITLE_COLOR["done"]
        elif self._task.status == Status.PENDING and open_deps > 0:
            title_color = _TITLE_COLOR["pending_deps"]
        else:
            title_color = _TITLE_COLOR.get(state, _TITLE_COLOR["pending_nodeps"])

        self._title_label.setStyleSheet(
            f"font-size: 13px; font-weight: 500; color: {title_color};"
        )

        if self._selected:
            self.setStyleSheet(
                f"TaskCard {{ background: #323236; border-radius: 6px; "
                f"border-left: 3px solid {border}; border-right: 2px solid #FBBF24; }}"
            )
        else:
            self.setStyleSheet(
                f"TaskCard {{ background: {bg}; border-radius: 6px; "
                f"border-left: 3px solid {border}; }}"
            )

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.setProperty("selected", selected)
        self._apply_card_style()

    def _on_status_change(self, new_status: str) -> None:
        cb = self._callbacks.get("on_status_change")
        if cb:
            cb(self._task, new_status)

    def _show_context_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #27272A; border: 1px solid #3f3f46; "
            "border-radius: 8px; padding: 4px; }"
            "QMenu::item { padding: 8px 16px; border-radius: 4px; color: #FAFAFA; }"
            "QMenu::item:selected { background: #3F3F46; }"
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
        super().mousePressEvent(event)
        self.selected.emit(self._task)

    def update_task(self, task: Task, all_tasks: list[Task]) -> None:
        self._task = task
        self._all_tasks_list = all_tasks
        self._all_tasks = {t.id: t for t in all_tasks}
        self._id_label.setText(task.id)
        self._title_label.setText(task.title)
        svg = WIFI_SVG if task.type.value == "online" else WIFI_OFF_SVG
        self._type_icon.setPixmap(_make_icon_pixmap(svg))
        self._type_icon.setToolTip(task.type.value)
        if task.deps:
            self._deps_label.show()
            self._refresh_deps_label()
        else:
            self._deps_label.hide()
        self._seg_ctrl.update_task(task, self._all_tasks)
        self._apply_card_style()
