# suite: unit | module: module-1-gestao-de-tasks | task: TASK-2
# @tdd-locked: do not edit without /tdd:unlock
# covers: TASK-2/ST001 — EditTaskDialog pre-preenche campos a partir de Task
# target: task_manager_desktop/ui/dialogs/edit_task_dialog.py
# TIDs: TID-1-2-011
import pytest


# TID-1-2-011 | covers: TASK-2/ST001 prefill
def test_edit_dialog_prefills_all_fields_from_task(qtbot):
    """EditTaskDialog pre-preenche os campos (titulo, type-radio, deps) a partir de Task."""
    from task_manager_desktop.core.models import Status, Task, TaskType
    from task_manager_desktop.ui.dialogs.edit_task_dialog import EditTaskDialog

    task = Task(
        id="x",
        title="Minha task",
        status=Status.PENDING,
        type=TaskType.HUMAN,
        deps=["a1", "b2"],
    )
    dlg = EditTaskDialog(task)
    qtbot.addWidget(dlg)

    assert dlg.form.title_input.text() == "Minha task"
    assert dlg.form.radio_human.isChecked() is True
    assert dlg.form.radio_agent.isChecked() is False
    assert dlg.form.deps_input.text() == "a1, b2"
