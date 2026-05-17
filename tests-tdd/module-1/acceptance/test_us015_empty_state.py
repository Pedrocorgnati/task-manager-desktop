# suite: acceptance | module: module-1-gestao-de-tasks | task: TASK-1/ST004
# @tdd-locked: do not edit without /tdd:unlock
# covers: US-015 — Empty states informativos em todos os estados vazios
# TIDs: TID-1-1-009
from PySide6.QtWidgets import QLabel

from task_manager_desktop.ui.task_list import TaskList


# TID-1-1-009 | covers: US-015 | bdd_type: EDGE
def test_task_list_shows_empty_label_when_no_tasks(qtbot):
    """Empty state da TaskList: 'Sem tasks. Clique em + para criar a primeira.'"""
    widget = TaskList()
    qtbot.addWidget(widget)
    widget.refresh([])

    labels = widget.findChildren(QLabel, "emptyStateText")
    assert len(labels) == 1, "Empty state label deve existir quando lista esta vazia"
    assert labels[0].text() == "Sem tasks. Clique em + para criar a primeira."
