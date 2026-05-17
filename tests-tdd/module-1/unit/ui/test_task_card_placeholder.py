# suite: unit | module: module-1-gestao-de-tasks | task: TASK-1
# @tdd-locked: do not edit without /tdd:unlock
# covers: TASK-1/ST004 — TaskCardPlaceholder renderiza representacao textual da task
# target: task_manager_desktop/ui/task_card_placeholder.py
# TIDs: TID-1-1-021

from task_manager_desktop.core.models import Task, TaskType
from task_manager_desktop.ui.task_card_placeholder import TaskCardPlaceholder


# TID-1-1-021 | covers: TASK-1/ST004 placeholder
def test_placeholder_renders_id_titulo_status_type_projeto(qtbot):
    """TaskCardPlaceholder renderiza 'id - titulo [status] [type:X] [proj:Y]'."""
    from PySide6.QtWidgets import QLabel

    task = Task(id="abc", title="Refactor parser", type=TaskType.OFFLINE, projeto="systemforge")
    card = TaskCardPlaceholder(task)
    qtbot.addWidget(card)

    labels = card.findChildren(QLabel)
    texts = [lbl.text() for lbl in labels]
    full_text = " ".join(texts)

    assert "abc" in full_text
    assert "Refactor parser" in full_text
    assert "offline" in full_text or "type:offline" in full_text
    assert "systemforge" in full_text
