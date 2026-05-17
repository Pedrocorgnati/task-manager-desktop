# suite: unit | module: module-1-gestao-de-tasks | task: TASK-2
# @tdd-locked: do not edit without /tdd:unlock
# covers: TASK-2/ST001 — TaskFormWidget.validate() retorna False e marca/limpa erro
# target: task_manager_desktop/ui/widgets/task_form_widget.py
# TIDs: TID-1-2-010
import pytest


# TID-1-2-010 | covers: TASK-2/ST001 form
def test_validate_returns_false_and_marks_error_on_empty_title(qtbot):
    """TaskFormWidget.validate() retorna False com titulo vazio e marca/limpa erro via mark_title_invalid/clear_title_error."""
    from task_manager_desktop.ui.dialogs.task_form_widget import TaskFormWidget

    w = TaskFormWidget()
    qtbot.addWidget(w)

    # With empty title, validate returns False and marks invalid
    assert w.validate() is False
    assert w.title_input.property("invalid") is True
    assert not w._title_error.isHidden()

    # clear_title_error removes the mark
    w.clear_title_error()
    assert w.title_input.property("invalid") is None
    assert w._title_error.isHidden()
