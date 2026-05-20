from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QPushButton, QVBoxLayout, QWidget

from task_manager_desktop.core.models import Status, Task
from task_manager_desktop.ui.theme import PALETTE

# Cada botao e quadrado (width == height) e ocupa 33% da altura do controle.
_BTN_SIZE = 24
# Raio dos cantos que encaixam nas quinas do card (igual ao border-radius do card).
_CORNER_RADIUS = 12
# Dimensoes do controle: 1 botao de largura, 3 de altura — colado na borda do card.
CONTROL_WIDTH = _BTN_SIZE
CONTROL_HEIGHT = _BTN_SIZE * 3


class StatusSegmentedControl(QWidget):
    status_changed = Signal(str)

    _STATUS_VALUES = [
        ("IP", Status.IN_PROGRESS),
        ("P", Status.PENDING),
        ("D", Status.DONE),
    ]

    def __init__(
        self,
        task: Task,
        all_tasks: dict[str, Task],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("statusControl")
        self.setProperty("testid", f"status-control-{task.id}")
        self.setFixedSize(CONTROL_WIDTH, CONTROL_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QWidget#statusControl { background: transparent; }")
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
        layout = QVBoxLayout(self)
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
            btn.setProperty("testid", f"status-btn-{label.lower()}-{self._task.id}")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(_BTN_SIZE, _BTN_SIZE)
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
        if status == Status.PENDING:
            bg = "#EAB308"
        elif status == Status.IN_PROGRESS:
            bg = "#16A34A"
        else:
            bg = "#71717A"

        # Topo (IP) acompanha o canto superior direito do card; base (D) o
        # canto inferior direito; meio (P) reto — lado direito desce em bloco.
        if status == Status.IN_PROGRESS:
            radius = f"border-top-right-radius: {_CORNER_RADIUS}px;"
        elif status == Status.DONE:
            radius = f"border-bottom-right-radius: {_CORNER_RADIUS}px;"
        else:
            radius = ""

        # Selecionado: borda branca em volta. Caso contrario: apenas uma borda
        # preta na esquerda, separando os 3 botoes do resto do card.
        if checked:
            border = "border: 2px solid #FFFFFF;"
        else:
            border = "border: none; border-left: 2px solid #000000;"

        return (
            "QPushButton {"
            f"background: {bg}; color: #FFFFFF;"
            f"{border}{radius}"
            "padding: 0;"
            "font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace;"
            "font-size: 9px; font-weight: 900;"
            "}"
            "QPushButton:hover { border: 2px solid #FFFFFF; }"
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
        self.setProperty("testid", f"status-control-{task.id}")
        for label, status in self._STATUS_VALUES:
            self._buttons[status].setProperty("testid", f"status-btn-{label.lower()}-{task.id}")
        for status, btn in self._buttons.items():
            btn.setChecked(task.status == status)
        self._apply_checked_style()
