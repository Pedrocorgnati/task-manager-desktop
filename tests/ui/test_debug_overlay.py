from __future__ import annotations

from task_manager_desktop.ui.debug_overlay import _is_main_testid, _mask_dynamic_testid


def test_mask_dynamic_testid_replaces_runtime_id_token():
    assert _mask_dynamic_testid("status-btn-p-cew") == "status-btn-{ID}"


def test_mask_dynamic_testid_keeps_static_testid():
    assert _mask_dynamic_testid("header-trash-button") == "header-trash-button"


def test_mask_dynamic_testid_replaces_inside_longer_testid():
    assert _mask_dynamic_testid("task-card-p-cew-title") == "task-card-{ID}-title"


def test_mask_dynamic_testid_replaces_schedule_button_id():
    assert _mask_dynamic_testid("task-card-p-cew-schedule") == "task-card-{ID}-schedule"


def test_main_testids_include_only_structural_panels():
    assert _is_main_testid("header")
    assert _is_main_testid("task-list-pane")
    assert _is_main_testid("task-list-active-section")
    assert _is_main_testid("task-list-waiting-section")
    assert _is_main_testid("subtask-clock-pane")
    assert _is_main_testid("right-pane-vertical")
    assert _is_main_testid("clock-pane")
    assert _is_main_testid("terminal-workspace")
    assert not _is_main_testid("header-new-task-button")
    assert not _is_main_testid("task-card-{ID}")
