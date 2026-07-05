# suite: unit | module: module-1-gestao-de-tasks | task: TASK-1
# @tdd-locked: do not edit without /tdd:unlock
# covers: TASK-1/ST001 — NewTaskDialog.get_data(), validate(), keyboard shortcuts
# target: task_manager_desktop/ui/dialogs/new_task_dialog.py
# TIDs: TID-1-1-012, TID-1-1-013, TID-1-1-014
from PySide6.QtCore import Qt


# TID-1-1-012 | covers: TASK-1/ST001 get_data()
def test_get_data_parses_deps(qtbot):
    """NewTaskDialog.get_data() aplica parse_deps e retorna dict."""
    from task_manager_desktop.ui.dialogs.new_task_dialog import NewTaskDialog

    dlg = NewTaskDialog()
    qtbot.addWidget(dlg)
    qtbot.keyClicks(dlg.title_edit, "Test task")
    qtbot.keyClicks(dlg.deps_edit, "a1b, c2d")

    data = dlg.get_data()

    assert data["title"] == "Test task"
    assert data["deps"] == ["a1b", "c2d"]


# TID-1-1-013 | covers: TASK-1/ST001 validate()
def test_validate_empty_title_marks_field_error_tooltip_and_focus(qtbot):
    """Validacao de titulo vazio aplica classe field-error, tooltip e setFocus."""
    from task_manager_desktop.ui.dialogs.new_task_dialog import NewTaskDialog

    dlg = NewTaskDialog()
    qtbot.addWidget(dlg)
    dlg.show()

    # Simulate OK click without entering a title
    qtbot.mouseClick(dlg._ok_btn, Qt.LeftButton)

    assert dlg.title_edit.property("class") == "field-error"
    assert dlg._title_error.isVisible()
    assert "obrigatório" in dlg._title_error.text()
    assert dlg.result() != dlg.DialogCode.Accepted


# TID-1-1-014 | covers: TASK-1/ST001 keyboard
def test_enter_on_title_triggers_ok_esc_triggers_cancel(qtbot):
    """Atalhos: Enter no titulo dispara OK; Esc aciona Cancelar."""
    from task_manager_desktop.ui.dialogs.new_task_dialog import NewTaskDialog

    # Enter with valid title → accept. workspace_root e obrigatorio (v11),
    # entao precisa estar preenchido para o form validar e aceitar.
    dlg = NewTaskDialog()
    qtbot.addWidget(dlg)
    qtbot.keyClicks(dlg.title_edit, "Valid title")
    dlg.form.workspace_root_input.setText("output/workspace/valid-title")
    qtbot.keyPress(dlg.title_edit, Qt.Key_Return)
    assert dlg.result() == dlg.DialogCode.Accepted

    # Esc → reject
    dlg2 = NewTaskDialog()
    qtbot.addWidget(dlg2)
    dlg2.show()
    qtbot.keyPress(dlg2, Qt.Key_Escape)
    assert dlg2.result() == dlg2.DialogCode.Rejected
