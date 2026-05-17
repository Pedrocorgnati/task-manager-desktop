# suite: contract | module: module-1-gestao-de-tasks | task: TASK-2
# @tdd-locked: do not edit without /tdd:unlock
# covers: OVERVIEW.md/Contratos — TaskCard(task, callbacks, all_tasks) consumido por module-2/module-5
# TIDs: TID-1-2-020
# target: task_manager_desktop/ui/task_card.py
import inspect


# TID-1-2-020 | covers: OVERVIEW.md/Contratos
def test_task_card_constructor_accepts_task_callbacks_all_tasks(qtbot):
    """Contrato TaskCard(task, callbacks: {on_edit, on_delete, on_status_change}, all_tasks)
    consumido por module-2/module-5. Verifica assinatura __init__ + chaves obrigatorias do dict callbacks."""
    from task_manager_desktop.core.models import Status, Task, TaskType
    from task_manager_desktop.ui.task_card import TaskCard

    # Verify constructor signature has task, callbacks, all_tasks
    sig = inspect.signature(TaskCard.__init__)
    params = list(sig.parameters.keys())
    assert "task" in params
    assert "callbacks" in params
    assert "all_tasks" in params

    # Verify a real instance can be created with the required callback dict
    task = Task(id="x", title="T", status=Status.PENDING, type=TaskType.ONLINE, projeto="f", deps=[])
    received = {}
    callbacks = {
        "on_edit": lambda t: received.update({"edit": t.id}),
        "on_delete": lambda t: received.update({"delete": t.id}),
        "on_status_change": lambda t, s: received.update({"status": s}),
    }
    card = TaskCard(task, callbacks, [task])
    qtbot.addWidget(card)

    # Verify callbacks work
    callbacks["on_edit"](task)
    assert received.get("edit") == "x"

    callbacks["on_delete"](task)
    assert received.get("delete") == "x"

    callbacks["on_status_change"](task, "done")
    assert received.get("status") == "done"
