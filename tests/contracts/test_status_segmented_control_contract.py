# suite: contract | module: module-1-gestao-de-tasks | task: TASK-2
# @tdd-locked: do not edit without /tdd:unlock
# covers: OVERVIEW.md/Contratos — StatusSegmentedControl.status_changed = Signal(str)
# TIDs: TID-1-2-021
# target: task_manager_desktop/ui/widgets/status_segmented_control.py


# TID-1-2-021 | covers: OVERVIEW.md/Contratos
def test_status_segmented_control_status_changed_signal_str_canonical_values(qtbot):
    """Contrato StatusSegmentedControl.status_changed = Signal(str) com valores canonicos
    em {'pending', 'in_progress', 'done'}. Verifica tipo Signal + arg str + enumeracao."""
    from task_manager_desktop.core.models import Status, Task
    from task_manager_desktop.ui.widgets.status_segmented_control import StatusSegmentedControl

    task = Task(id="t", title="T", status=Status.PENDING, deps=[])
    w = StatusSegmentedControl(task, {}, None)
    qtbot.addWidget(w)

    # Verify status_changed attribute exists
    assert hasattr(w, "status_changed")

    # Verify it emits str values
    received = []
    w.status_changed.connect(received.append)

    w._on_button_clicked(w.btn_p)
    w._on_button_clicked(w.btn_ip)
    w._on_button_clicked(w.btn_d)

    assert len(received) == 3
    assert all(isinstance(v, str) for v in received)
    assert set(received) == {"pending", "in_progress", "done"}
