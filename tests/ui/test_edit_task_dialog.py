from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialogButtonBox

from task_manager_desktop.core.models import Status, Task, TaskType
from task_manager_desktop.ui.dialogs.edit_task_dialog import EditTaskDialog


@pytest.fixture
def sample_task():
    return Task(
        id="abc",
        title="X",
        status=Status.PENDING,
        type=TaskType.OFFLINE,
        projeto="systemforge",
        deps=["a1b", "c2d"],
    )


def test_dialog_prefills_all_fields(qtbot, sample_task):
    dlg = EditTaskDialog(sample_task)
    qtbot.addWidget(dlg)
    assert dlg.form.title_input.text() == "X"
    assert dlg.form.radio_offline.isChecked() is True
    assert dlg.form.radio_online.isChecked() is False
    assert dlg.form.projeto_input.text() == "systemforge"
    assert dlg.form.deps_input.text() == "a1b, c2d"


def test_save_button_labeled_salvar(qtbot, sample_task):
    dlg = EditTaskDialog(sample_task)
    qtbot.addWidget(dlg)
    ok_btn = dlg.button_box.button(QDialogButtonBox.StandardButton.Ok)
    assert ok_btn.text() == "Salvar"


def test_empty_title_blocks_save(qtbot, sample_task):
    dlg = EditTaskDialog(sample_task)
    qtbot.addWidget(dlg)
    dlg.form.title_input.clear()
    ok_btn = dlg.button_box.button(QDialogButtonBox.StandardButton.Ok)
    qtbot.mouseClick(ok_btn, Qt.MouseButton.LeftButton)
    assert dlg.result() == 0  # nao foi accepted
    assert dlg.form.title_input.property("invalid") is True


def test_toggle_radio_updates_get_data(qtbot, sample_task):
    dlg = EditTaskDialog(sample_task)
    qtbot.addWidget(dlg)
    dlg.form.radio_online.setChecked(True)
    ok_btn = dlg.button_box.button(QDialogButtonBox.StandardButton.Ok)
    qtbot.mouseClick(ok_btn, Qt.MouseButton.LeftButton)
    assert dlg.get_data()["type"] == TaskType.ONLINE


def test_empty_projeto_normalizes_to_outros(qtbot, sample_task):
    dlg = EditTaskDialog(sample_task)
    qtbot.addWidget(dlg)
    dlg.form.projeto_input.clear()
    ok_btn = dlg.button_box.button(QDialogButtonBox.StandardButton.Ok)
    qtbot.mouseClick(ok_btn, Qt.MouseButton.LeftButton)
    assert dlg.get_data()["projeto"] == "outros"


def test_enter_in_title_submits(qtbot, sample_task):
    dlg = EditTaskDialog(sample_task)
    qtbot.addWidget(dlg)
    qtbot.keyPress(dlg.form.title_input, Qt.Key.Key_Return)
    assert dlg.result() == QDialogButtonBox.StandardButton.Ok.value or dlg.result() == 1


def test_esc_closes_dialog(qtbot, sample_task):
    dlg = EditTaskDialog(sample_task)
    qtbot.addWidget(dlg)
    dlg.show()
    qtbot.keyClick(dlg, Qt.Key.Key_Escape)
    assert not dlg.isVisible()


def test_cancel_rejects_dialog(qtbot, sample_task):
    dlg = EditTaskDialog(sample_task)
    qtbot.addWidget(dlg)
    cancel_btn = dlg.button_box.button(QDialogButtonBox.StandardButton.Cancel)
    qtbot.mouseClick(cancel_btn, Qt.MouseButton.LeftButton)
    assert dlg.result() == 0


def test_get_data_returns_all_fields(qtbot, sample_task):
    dlg = EditTaskDialog(sample_task)
    qtbot.addWidget(dlg)
    data = dlg.get_data()
    assert "title" in data
    assert "type" in data
    assert "projeto" in data
    assert "deps" in data


def test_dialog_is_modal(qtbot, sample_task):
    dlg = EditTaskDialog(sample_task)
    qtbot.addWidget(dlg)
    assert dlg.isModal()
