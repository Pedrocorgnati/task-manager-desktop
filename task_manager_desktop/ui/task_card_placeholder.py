from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from task_manager_desktop.core.models import Task


class TaskCardPlaceholder(QFrame):
    """Representacao textual simples de uma task (skeleton pre-TASK-2)."""

    def __init__(self, task: Task, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TaskCardPlaceholder")
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        text = f"{task.id} - {task.title} [{task.status.value}] [type:{task.type.value}]"
        label = QLabel(text, self)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setAccessibleName(f"Task {task.id}: {task.title}")
        layout.addWidget(label)
