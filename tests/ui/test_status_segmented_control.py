from __future__ import annotations

from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.ui.widgets.status_segmented_control import StatusSegmentedControl


def _make_task(status: Status = Status.PENDING, deps=None) -> Task:
    return Task(
        id="t1",
        title="Test",
        status=status,
        type=TaskType.ONLINE,
        projeto="forge",
        deps=deps or [],
    )


def test_pending_button_checked_by_default(qtbot):
    task = _make_task(Status.PENDING)
    w = StatusSegmentedControl(task, {}, None)
    qtbot.addWidget(w)
    assert w.btn_p.isChecked() is True
    assert w.btn_ip.isChecked() is False
    assert w.btn_d.isChecked() is False


def test_in_progress_button_checked(qtbot):
    task = _make_task(Status.IN_PROGRESS)
    w = StatusSegmentedControl(task, {}, None)
    qtbot.addWidget(w)
    assert w.btn_ip.isChecked() is True
    assert w.btn_p.isChecked() is False
    assert w.btn_d.isChecked() is False


def test_done_button_checked(qtbot):
    task = _make_task(Status.DONE)
    w = StatusSegmentedControl(task, {}, None)
    qtbot.addWidget(w)
    assert w.btn_d.isChecked() is True
    assert w.btn_p.isChecked() is False
    assert w.btn_ip.isChecked() is False


def test_status_changed_signal_emitted(qtbot):
    task = _make_task(Status.PENDING)
    w = StatusSegmentedControl(task, {}, None)
    qtbot.addWidget(w)
    with qtbot.waitSignal(w.status_changed, timeout=500) as blocker:
        w.btn_d.setChecked(True)
        w._on_button_clicked(w.btn_d)
    assert blocker.args == ["done"]


def test_mutually_exclusive(qtbot):
    task = _make_task(Status.PENDING)
    w = StatusSegmentedControl(task, {}, None)
    qtbot.addWidget(w)
    w.btn_ip.setChecked(True)
    assert w.btn_p.isChecked() is False
    assert w.btn_d.isChecked() is False


def test_update_task_changes_checked_button(qtbot):
    task = _make_task(Status.PENDING)
    w = StatusSegmentedControl(task, {}, None)
    qtbot.addWidget(w)
    updated = _make_task(Status.DONE)
    w.update_task(updated, {})
    assert w.btn_d.isChecked() is True
    assert w.btn_p.isChecked() is False


def test_signal_emits_canonical_status_strings(qtbot):
    task = _make_task(Status.PENDING)
    w = StatusSegmentedControl(task, {}, None)
    qtbot.addWidget(w)
    received = []
    w.status_changed.connect(lambda s: received.append(s))
    w._on_button_clicked(w.btn_ip)
    w._on_button_clicked(w.btn_d)
    w._on_button_clicked(w.btn_p)
    assert "in_progress" in received
    assert "done" in received
    assert "pending" in received
