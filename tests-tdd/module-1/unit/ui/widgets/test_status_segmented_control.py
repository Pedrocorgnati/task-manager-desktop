# suite: unit | module: module-1-gestao-de-tasks | task: TASK-2
# @tdd-locked: do not edit without /tdd:unlock
# covers: TASK-2/ST002 — StatusSegmentedControl selecao e sinal canonico
# target: task_manager_desktop/ui/widgets/status_segmented_control.py
# TIDs: TID-1-2-017, TID-1-2-018
from __future__ import annotations

from task_manager_desktop.core.models import Status, Task
from task_manager_desktop.ui.widgets.status_segmented_control import StatusSegmentedControl


def _task(status: Status = Status.PENDING) -> Task:
    return Task(id="t", title="T", status=status, deps=[])


# TID-1-2-017 | covers: TASK-2/ST002 segmented
def test_segmented_control_selects_correct_button_by_status_and_open_deps(qtbot):
    """StatusSegmentedControl seleciona botao certo segundo current_status e has_open_deps."""
    w_p = StatusSegmentedControl(_task(Status.PENDING), {}, None)
    qtbot.addWidget(w_p)
    assert w_p.btn_p.isChecked() is True
    assert w_p.btn_ip.isChecked() is False
    assert w_p.btn_d.isChecked() is False

    w_ip = StatusSegmentedControl(_task(Status.IN_PROGRESS), {}, None)
    qtbot.addWidget(w_ip)
    assert w_ip.btn_ip.isChecked() is True
    assert w_ip.btn_p.isChecked() is False
    assert w_ip.btn_d.isChecked() is False

    w_d = StatusSegmentedControl(_task(Status.DONE), {}, None)
    qtbot.addWidget(w_d)
    assert w_d.btn_d.isChecked() is True
    assert w_d.btn_p.isChecked() is False
    assert w_d.btn_ip.isChecked() is False


# TID-1-2-018 | covers: TASK-2/ST002 signal
def test_status_changed_emits_canonical_str_values(qtbot):
    """StatusSegmentedControl.status_changed emite str canonica {'pending','in_progress','done'}."""
    w = StatusSegmentedControl(_task(), {}, None)
    qtbot.addWidget(w)

    received = []
    w.status_changed.connect(received.append)

    w._on_button_clicked(w.btn_p)
    w._on_button_clicked(w.btn_ip)
    w._on_button_clicked(w.btn_d)

    assert "pending" in received
    assert "in_progress" in received
    assert "done" in received
    assert all(v in {"pending", "in_progress", "done"} for v in received)
