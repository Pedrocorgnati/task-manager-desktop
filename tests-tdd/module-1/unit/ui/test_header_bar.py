# suite: unit | module: module-1-gestao-de-tasks | task: TASK-1
# @tdd-locked: do not edit without /tdd:unlock
# covers: TASK-1/ST002 — HeaderBar sinal e acessibilidade do botao '+'
# target: task_manager_desktop/ui/header_bar.py
# TIDs: TID-1-1-015, TID-1-1-016
from PySide6.QtCore import Qt


# TID-1-1-015 | covers: TASK-1/ST002 signal
def test_plus_button_click_emits_new_task_requested_exactly_once(qtbot):
    """Clique no botao '+' emite HeaderBar.new_task_requested exatamente uma vez."""
    from task_manager_desktop.ui.header import HeaderBar

    bar = HeaderBar()
    qtbot.addWidget(bar)

    emitted = []
    bar.new_task_requested.connect(lambda: emitted.append(1))
    qtbot.mouseClick(bar.btn_new, Qt.LeftButton)

    assert len(emitted) == 1


# TID-1-1-016 | covers: TASK-1/ST002 a11y
def test_plus_button_exposes_tooltip_and_accessible_name(qtbot):
    """Botao '+' expoe tooltip 'Nova task (Ctrl+N)' e accessibleName 'Criar nova task'."""
    from task_manager_desktop.ui.header import HeaderBar

    bar = HeaderBar()
    qtbot.addWidget(bar)

    assert "Ctrl+N" in bar.btn_new.toolTip()
    assert bar.btn_new.accessibleName() == "Criar nova task"
    assert "Ctrl+N" in bar.btn_new.accessibleDescription()
