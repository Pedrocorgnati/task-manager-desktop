# suite: contract | module: module-1-gestao-de-tasks | task: TASK-3
# @tdd-locked: do not edit without /tdd:unlock
# covers: OVERVIEW.md/Contratos facade — TaskRepository expoe exatamente 9 metodos publicos
# TIDs: TID-1-3-017
# target: task_manager_desktop/repositories/task_repository.py
import inspect


# TID-1-3-017 | covers: OVERVIEW.md/Contratos facade
def test_task_repository_facade_exposes_nine_public_methods():
    """Facade TaskRepository expoe exatamente 9 metodos publicos:
    create, update, delete, list_active, list_trash, get_by_id,
    mark_hidden, restore, list_projetos (introspeccao + assinaturas).
    """
    from task_manager_desktop.repositories.task_repository import TaskRepository

    expected = {
        "create", "update", "delete",
        "list_active", "list_trash", "get_by_id",
        "mark_hidden", "restore", "list_projetos",
        "exists",
        "update_status",       # added in module-2 TASK-1 (ST001)
        "update_order_indexes",  # added in module-2 TASK-1 (ST001)
    }

    public_methods = {
        name for name, _ in inspect.getmembers(TaskRepository, predicate=inspect.isfunction)
        if not name.startswith("_")
    }

    assert expected == public_methods
