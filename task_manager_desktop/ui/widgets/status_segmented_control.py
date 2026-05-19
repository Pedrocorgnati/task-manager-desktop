from __future__ import annotations

from PySide6.QtCore import Qt, Signal
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
        self._surface = {
            "chip_bg": "#27272A",
            "chip_text": PALETTE["TEXT_PRIMARY"],
            "title": PALETTE["TEXT_PRIMARY"],
        }
        self._state_name = "default"
        self._build_ui()
        self._apply_checked_style()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

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
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(42 if status == Status.IN_PROGRESS else 34, 26)
            btn.setChecked(self._task.status == status)
            btn.setAccessibleName(_accessible_names[status])
            self._btn_group.addButton(btn)
            self._buttons[status] = btn
            layout.addWidget(btn)

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

    def apply_palette(self, state_name: str, surface: dict[str, str]) -> None:
        self._state_name = state_name
        self._surface = surface
        self._apply_checked_style()

    def _button_style(self, status: Status, checked: bool) -> str:
        base_bg = self._surface.get("chip_bg", "rgba(24,24,27,0.45)")
        base_text = self._surface.get("chip_text", "#F8FAFC")

        if checked:
            if status == Status.PENDING:
                bg = "#18181B" if self._state_name == "waiting" else "#FBBF24"
                fg = "#F8FAFC" if self._state_name == "waiting" else "#18181B"
            elif status == Status.IN_PROGRESS:
                has_open = count_open_deps(self._task.deps, self._all_tasks) > 0
                bg = "#EAB308" if has_open else "#22C55E"
                fg = "#18181B" if has_open else "#052E16"
            else:
                bg = "#E4E4E7"
                fg = "#18181B"
            border = bg
            weight = 900
        else:
            bg = base_bg
            fg = base_text
            border = "rgba(255,255,255,0.20)"
            weight = 800

        return (
            "QPushButton {"
            f"background: {bg}; color: {fg}; border: 1px solid {border};"
            "border-radius: 8px; padding: 0;"
            "font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace;"
            f"font-size: 11px; font-weight: {weight};"
            "}"
            "QPushButton:hover { background: rgba(255,255,255,0.22); }"
            "QPushButton:focus { border: 2px solid #FFFFFF; outline: none; }"
        )

    def _apply_checked_style(self) -> None:
        for status, btn in self._buttons.items():
            btn.setStyleSheet(self._button_style(status, btn.isChecked()))

    def setValue(self, status_value: str) -> None:
        """Revert segmented to a known status without emitting status_changed.
        Used by ChangeStatusController on I/O error (AC-T-007 QSignalBlocker)."""
        from PySide6.QtCore import QSignalBlocker

        try:
            status = Status(status_value)
        except ValueError:
            return
        with QSignalBlocker(self._btn_group):
            for s, btn in self._buttons.items():
                btn.setChecked(s == status)
        self._apply_checked_style()

    def update_task(self, task: Task, all_tasks: dict[str, Task]) -> None:
        self._task = task
        self._all_tasks = all_tasks
        for status, btn in self._buttons.items():
            btn.setChecked(task.status == status)
        self._apply_checked_style()
