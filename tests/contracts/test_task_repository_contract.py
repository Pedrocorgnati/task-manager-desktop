# suite: contract | module: module-1-gestao-de-tasks | task: TASK-3
# @tdd-locked: do not edit without /tdd:unlock
# covers: OVERVIEW.md/Contratos facade — TaskRepository expoe exatamente 8 metodos publicos
# TIDs: TID-1-3-017
# target: task_manager_desktop/repositories/task_repository.py
import inspect


# TID-1-3-017 | covers: OVERVIEW.md/Contratos facade
def test_task_repository_facade_exposes_nine_public_methods():
    """Facade TaskRepository expoe exatamente 8 metodos publicos:
    create, update, delete, list_active, list_trash, get_by_id,
    mark_hidden, restore (introspeccao + assinaturas).
    """
    from task_manager_desktop.repositories.task_repository import TaskRepository

    expected = {
        "create", "update", "delete",
        "list_active", "list_trash", "get_by_id",
        "mark_hidden", "restore",
        "exists",
        "update_status",       # added in module-2 TASK-1 (ST001)
        "update_order_indexes",  # added in module-2 TASK-1 (ST001)
        "update_notes",        # added in intake-review TASK-1 (B1 MarkdownReader)
        "hide_all_done",       # added in intake-review TASK-4 (B5 TrashDialog + clear-done)
        "list_subtasks",
        "create_subtask",
        "update_subtask_done",
        "update_subtask_state",
        "update_subtask_order_indexes",
        "delete_done_subtasks",
        "update_subtask_notes",
    }

    public_methods = {
        name for name, _ in inspect.getmembers(TaskRepository, predicate=inspect.isfunction)
        if not name.startswith("_")
    }

    assert expected == public_methods
