from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from task_manager_desktop.controllers.delete_task_controller import DeleteTaskController
from task_manager_desktop.core.models import Status, Task, TaskType


@pytest.fixture
def task():
    return Task(id="abc", title="Tarefa ABC", status=Status.PENDING, type=TaskType.ONLINE)


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.db_path = "/fake/tasks.db"
    repo.list_active.return_value = []
    return repo


@pytest.fixture
def mock_task_list():
    return MagicMock()


@pytest.fixture
def mock_main_window():
    mw = MagicMock()
    mw._current_task_id = None
    return mw


@pytest.fixture
def ctrl(mock_repo, mock_task_list, mock_main_window):
    return DeleteTaskController(mock_repo, mock_task_list, mock_main_window)


def test_handle_calls_repo_delete(ctrl, mock_repo, task):
    ctrl.handle(task)
    mock_repo.delete.assert_called_once_with("abc")


def test_handle_refreshes_task_list_after_delete(ctrl, mock_repo, mock_task_list, task):
    remaining = [Task(id="x", title="X")]
    mock_repo.list_active.return_value = remaining
    ctrl.handle(task)
    mock_task_list.refresh.assert_called_once_with(remaining)


def test_handle_does_not_show_any_qmessagebox(ctrl, task):
    from PySide6.QtWidgets import QMessageBox

    with patch.object(QMessageBox, "exec", side_effect=AssertionError("QMessageBox shown!")):
        with patch.object(QMessageBox, "question", side_effect=AssertionError("QMessageBox.question shown!")):
            ctrl.handle(task)  # must not raise


def test_handle_io_error_shows_error_dialog(ctrl, mock_repo, mock_task_list, task):
    mock_repo.delete.side_effect = sqlite3.OperationalError("disk I/O")

    with patch("task_manager_desktop.controllers.delete_task_controller.ErrorDialog") as mock_ed:
        ctrl.handle(task)
        mock_ed.show_io_error.assert_called_once()

    # task_list.refresh must NOT be called on error
    mock_task_list.refresh.assert_not_called()


def test_handle_io_error_passes_db_path_to_error_dialog(ctrl, mock_repo, task):
    mock_repo.delete.side_effect = sqlite3.OperationalError("disk I/O")
    mock_repo.db_path = "/data/tasks.db"

    with patch("task_manager_desktop.controllers.delete_task_controller.ErrorDialog") as mock_ed:
        ctrl.handle(task)
        call_args = mock_ed.show_io_error.call_args
        # Third positional arg is db_path
        assert call_args[0][2] == "/data/tasks.db"


def test_handle_resets_viewer_when_deleted_task_was_selected(
    mock_repo, mock_task_list, task
):
    main_window = MagicMock()
    main_window._current_task_id = "abc"
    ctrl = DeleteTaskController(mock_repo, mock_task_list, main_window)
    ctrl.handle(task)
    main_window.reset_viewer_to_empty.assert_called_once()


def test_handle_does_not_reset_viewer_when_different_task_selected(
    mock_repo, mock_task_list, task
):
    main_window = MagicMock()
    main_window._current_task_id = "other_task"
    ctrl = DeleteTaskController(mock_repo, mock_task_list, main_window)
    ctrl.handle(task)
    main_window.reset_viewer_to_empty.assert_not_called()


def test_handle_does_not_reset_viewer_when_no_task_selected(ctrl, mock_main_window, task):
    mock_main_window._current_task_id = None
    ctrl.handle(task)
    mock_main_window.reset_viewer_to_empty.assert_not_called()
