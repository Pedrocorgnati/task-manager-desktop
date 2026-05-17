from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget

from task_manager_desktop.core.models import Status, Task
from task_manager_desktop.core.sector import count_open_deps
from task_manager_desktop.ui.theme import PALETTE


class StatusSegmentedControl(QWidget):
    status_changed = Signal(str)

    _STATUS_VALUES = [
        ("P", Status.PENDING),
        ("IP", Status.IN_PROGRESS),
        ("D", Status.DONE),
    ]

    def __init__(
        self,
        task: Task,
        all_tasks: dict[str, Task],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._task = task
        self._all_tasks = all_tasks
        self._build_ui()
        self._apply_checked_style()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        _accessible_names = {
            Status.PENDING: "Status Pendente",
            Status.IN_PROGRESS: "Em progresso",
            Status.DONE: "Concluída",
        }
        self._buttons: dict[Status, QPushButton] = {}
        for label, status in self._STATUS_VALUES:
            btn = QPushButton(label, self)
            btn.setProperty("class", "seg-status")
            btn.setProperty("value", label)
            btn.setCheckable(True)
            btn.setFixedSize(28, 22)
            btn.setChecked(self._task.status == status)
            btn.setAccessibleName(_accessible_names[status])
            self._btn_group.addButton(btn)
            self._buttons[status] = btn
            layout.addWidget(btn)

        # Atalhos publicos para tests e acesso externo
        self.btn_p = self._buttons[Status.PENDING]
        self.btn_ip = self._buttons[Status.IN_PROGRESS]
        self.btn_d = self._buttons[Status.DONE]

        self._btn_group.buttonClicked.connect(self._on_button_clicked)

    def _on_button_clicked(self, btn: QPushButton) -> None:
        value = btn.property("value")
        status_map = {"P": "pending", "IP": "in_progress", "D": "done"}
        new_status = status_map.get(value, "pending")
        self._apply_checked_style()
        self.status_changed.emit(new_status)

    def _apply_checked_style(self) -> None:
        ip_btn = self._buttons[Status.IN_PROGRESS]
        has_open = (
            count_open_deps(self._task.deps, self._all_tasks) > 0
            if self._task.status == Status.IN_PROGRESS
            else False
        )
        if ip_btn.isChecked():
            if has_open:
                ip_btn.setStyleSheet(
                    f"QPushButton {{ background: {PALETTE['COLOR_WARNING']}; color: {PALETTE['BG_BASE']}; }}"
                )
            else:
                ip_btn.setStyleSheet(
                    f"QPushButton {{ background: {PALETTE['COLOR_SUCCESS']}; color: #064E3B; }}"
                )
        else:
            ip_btn.setStyleSheet("")

    def update_task(self, task: Task, all_tasks: dict[str, Task]) -> None:
        self._task = task
        self._all_tasks = all_tasks
        for status, btn in self._buttons.items():
            btn.setChecked(task.status == status)
        self._apply_checked_style()
