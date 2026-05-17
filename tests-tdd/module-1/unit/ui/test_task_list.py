# suite: unit | module: module-1-gestao-de-tasks | task: TASK-1
# @tdd-locked: do not edit without /tdd:unlock
# covers: TASK-1/ST004 — TaskList.refresh limpa e renderiza EmptyStateLabel
# target: task_manager_desktop/ui/task_list.py
# TIDs: TID-1-1-020

from task_manager_desktop.core.models import Task, TaskType
from task_manager_desktop.ui.task_list import TaskList


# TID-1-1-020 | covers: TASK-1/ST004 refresh
def test_refresh_clears_previous_cards_and_shows_empty_state_when_no_tasks(qtbot):
    """TaskList.refresh limpa cards anteriores e renderiza EmptyStateLabel quando lista vazia."""
    from PySide6.QtWidgets import QLabel

    tl = TaskList()
    qtbot.addWidget(tl)

    # First populate with a task
    task = Task(id="a", title="T1", type=TaskType.ONLINE, projeto="outros")
    tl.refresh([task])

    # Now clear
    tl.refresh([])

    # Should show empty state text
    labels = tl.findChildren(QLabel)
    texts = [lbl.text() for lbl in labels]
    assert any("Sem tasks" in t or "Clique" in t for t in texts)

    # No task cards should remain
    from PySide6.QtWidgets import QFrame
    cards = [c for c in tl.findChildren(QFrame) if c.objectName() == "TaskCard"]
    assert len(cards) == 0
