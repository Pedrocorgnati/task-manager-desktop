# suite: contract | module: module-1-gestao-de-tasks | task: TASK-2
# @tdd-locked: do not edit without /tdd:unlock
# covers: OVERVIEW.md/Contratos — EditTaskController.projects_changed = Signal() consumido por module-4
# TIDs: TID-1-2-022
# target: task_manager_desktop/controllers/edit_task_controller.py


# TID-1-2-022 | covers: OVERVIEW.md/Contratos
def test_edit_task_controller_projects_changed_is_signal_no_args(qtbot):
    """Contrato EditTaskController.projects_changed = Signal() consumido por module-4 ProjectFilter.
    Verifica existencia do atributo + tipo Signal + zero argumentos."""
    from unittest.mock import MagicMock

    from task_manager_desktop.controllers.edit_task_controller import EditTaskController
    from task_manager_desktop.ui.task_list import TaskList

    repo = MagicMock()
    tl = TaskList()
    qtbot.addWidget(tl)
    ctrl = EditTaskController(repo, tl, tl, parent=None)

    # Verify projects_changed exists
    assert hasattr(ctrl, "projects_changed")

    # Verify it's connectable (Signal interface)
    received = []
    ctrl.projects_changed.connect(lambda: received.append(True))
    ctrl.projects_changed.emit()
    assert received == [True]
