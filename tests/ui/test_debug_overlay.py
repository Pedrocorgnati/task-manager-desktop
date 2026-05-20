from __future__ import annotations

from task_manager_desktop.ui.debug_overlay import _mask_dynamic_testid


def test_mask_dynamic_testid_replaces_runtime_id_token():
    assert _mask_dynamic_testid("status-btn-p-cew") == "status-btn-{ID}"


def test_mask_dynamic_testid_keeps_static_testid():
    assert _mask_dynamic_testid("header-trash-button") == "header-trash-button"


def test_mask_dynamic_testid_replaces_inside_longer_testid():
    assert _mask_dynamic_testid("task-card-p-cew-title") == "task-card-{ID}-title"
