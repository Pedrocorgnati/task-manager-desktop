# suite: contract | module: module-1-gestao-de-tasks | task: TASK-1
# @tdd-locked: do not edit without /tdd:unlock
# covers: OVERVIEW.md/Contratos — TaskList.refresh(tasks) consumido por module-2/module-4
# TIDs: TID-1-1-022
# target: task_manager_desktop/ui/task_list.py
import inspect


# TID-1-1-022 | covers: OVERVIEW.md/Contratos
def test_task_list_refresh_signature_is_stable(qtbot):
    """Contrato TaskList.refresh(tasks: list[Task]) -> None
    assinatura estavel consumida por module-2/module-4 (introspeccao via inspect.signature)."""
    from task_manager_desktop.ui.task_list import TaskList

    tl = TaskList()
    qtbot.addWidget(tl)

    sig = inspect.signature(TaskList.refresh)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "tasks" in params
    # accepts None, inspect.Parameter.empty, or 'None' string (from __future__ annotations)
    assert sig.return_annotation in (None, inspect.Parameter.empty, "None")
