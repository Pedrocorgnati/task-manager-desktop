# suite: contract | module: module-1-gestao-de-tasks | task: TASK-1
# @tdd-locked: do not edit without /tdd:unlock
# covers: OVERVIEW.md/Contratos — HeaderBar.new_task_requested = Signal() consumido por module-4
# TIDs: TID-1-1-023
# target: task_manager_desktop/ui/header_bar.py


# TID-1-1-023 | covers: OVERVIEW.md/Contratos
def test_header_bar_new_task_requested_is_signal_no_args(qtbot):
    """Contrato HeaderBar.new_task_requested = Signal() consumido por module-4.
    Verifica existencia do atributo + tipo Signal + zero argumentos."""
    from task_manager_desktop.ui.header import HeaderBar

    bar = HeaderBar()
    qtbot.addWidget(bar)

    assert hasattr(bar, "new_task_requested")
    # Signal can be connected and emits
    results = []
    bar.new_task_requested.connect(lambda: results.append(1))
    bar.new_task_requested.emit()
    assert results == [1]
