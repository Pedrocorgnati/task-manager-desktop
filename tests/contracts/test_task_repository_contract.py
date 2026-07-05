# suite: contract | module: module-1-gestao-de-tasks | task: TASK-3
# @tdd-unlocked: 2026-05-21 (hardening round repo layer; ver source.md 05-20)
#   Justificativa: o hardening round adicionou o metodo publico mandatorio
#   update_subtask_text(subtask_id, text) -> None ao TaskRepository (fix #6:
#   substitui a escrita RAW que a subtask pane fazia sem boundary). O contrato
#   de "conjunto exato de metodos publicos" precisa incluir o novo metodo.
# covers: OVERVIEW.md/Contratos facade — conjunto exato de metodos publicos do TaskRepository
# TIDs: TID-1-3-017
# target: task_manager_desktop/repositories/task_repository.py
import inspect


# TID-1-3-017 | covers: OVERVIEW.md/Contratos facade
def test_task_repository_facade_exposes_nine_public_methods():
    """Facade TaskRepository expoe exatamente o conjunto de metodos publicos
    declarado em `expected` (introspeccao). O conjunto cresce de forma
    controlada conforme novas tasks/hardening adicionam metodos; qualquer
    metodo publico fora desta lista (ou removido dela) quebra o contrato.
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
        "subtask_types_by_task",  # added with subtask-based header-type-filter
        "create_subtask",
        "update_subtask_done",
        "update_subtask_state",
        "update_subtask_order_indexes",
        "delete_done_subtasks",
        "update_subtask_notes",
        "update_subtask_text",  # added in hardening round 05-21 (fix #6)
        "update_subtask_type",  # added with subtask type radio + icon (v9)
        "update_favorito",     # added in loop 05-20 TASK-008 (favorito/permanente)
        "update_permanente",   # added in loop 05-20 TASK-008 (favorito/permanente)
        "update_em_preparacao",  # added with setor manual "Em preparação" (v8)
        "update_coin_favorite",  # added with persisted coin marker (v12)
        "update_dot_favorite",   # added with persisted dot marker (v12)
        "list_clock_timers",
        "create_clock_timer",
        "update_clock_timer",
        "delete_clock_timer",
        "schedule_permanent_task",
        "get_permanent_schedule",
        "trigger_due_permanent_schedules",
    }

    public_methods = {
        name for name, _ in inspect.getmembers(TaskRepository, predicate=inspect.isfunction)
        if not name.startswith("_")
    }

    assert expected == public_methods
