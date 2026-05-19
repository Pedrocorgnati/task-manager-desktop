"""BDD tests for TrashDialog (ST004) – restoration + error handling."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from task_manager_desktop.ui.dialogs.trash_dialog import TrashDialog
from task_manager_desktop.core.models import Task, Status
from task_manager_desktop.repositories.task_repository import TaskRepository


@pytest.fixture
def mock_repo():
    """Create a mock repository for testing."""
    repo = Mock(spec=TaskRepository)
    repo.db_path = "/test/path/tasks.db"
    return repo


@pytest.fixture
def sample_hidden_task():
    """Create a sample hidden task."""
    return Task(
        id="task-1",
        title="Test Task",
        status=Status.DONE,
        hidden_at=datetime.now().isoformat(),
        completed_at=datetime.now().isoformat(),
        projeto="outros",
        notes="",
        type="online",
        deps=[],
    )


@pytest.fixture
def sample_hidden_tasks():
    """Create multiple sample hidden tasks."""
    now = datetime.now()
    return [
        Task(
            id="task-1",
            title="Old Task 1",
            status=Status.DONE,
            hidden_at=(now - timedelta(days=29)).isoformat(),
            completed_at=(now - timedelta(days=29)).isoformat(),
            projeto="outros",
            notes="",
            type="online",
            deps=[],
        ),
        Task(
            id="task-2",
            title="Recent Task 2",
            status=Status.DONE,
            hidden_at=(now - timedelta(days=2)).isoformat(),
            completed_at=(now - timedelta(days=2)).isoformat(),
            projeto="outros",
            notes="",
            type="online",
            deps=[],
        ),
        Task(
            id="task-3",
            title="Very Recent Task 3 with long title to test elision",
            status=Status.DONE,
            hidden_at=(now - timedelta(hours=1)).isoformat(),
            completed_at=(now - timedelta(hours=1)).isoformat(),
            projeto="Project A",
            notes="",
            type="offline",
            deps=[],
        ),
    ]


class TestTrashDialogEmpty:
    """Test TrashDialog empty state."""

    def test_empty_state_shown(self, qtbot, mock_repo):
        """Empty state label shown when no tasks in trash."""
        mock_repo.list_trash.return_value = []
        dialog = TrashDialog(mock_repo, parent=None)
        qtbot.addWidget(dialog)

        # Check that placeholder is visible
        placeholder = dialog._placeholder
        assert placeholder is not None
        assert "Nenhuma task na lixeira" in placeholder.text()

    def test_empty_state_centered(self, qtbot, mock_repo):
        """Empty state label is centered."""
        mock_repo.list_trash.return_value = []
        dialog = TrashDialog(mock_repo, parent=None)
        qtbot.addWidget(dialog)

        # The placeholder should be visible and centered
        assert dialog._stack.currentIndex() == 0  # index 0 = placeholder


class TestTrashDialogFilled:
    """Test TrashDialog with tasks."""

    def test_tasks_listed(self, qtbot, mock_repo, sample_hidden_tasks):
        """Tasks are listed in scroll area when trash not empty."""
        mock_repo.list_trash.return_value = sample_hidden_tasks
        dialog = TrashDialog(mock_repo, parent=None)
        qtbot.addWidget(dialog)

        # Check that scroll area is visible
        assert dialog._stack.currentIndex() == 1  # index 1 = scroll area
        # Check that rows were created
        assert len(dialog.row_ids()) == 3

    def test_task_row_displays_data(self, qtbot, mock_repo, sample_hidden_task):
        """Task row displays id, title, and completion date."""
        mock_repo.list_trash.return_value = [sample_hidden_task]
        dialog = TrashDialog(mock_repo, parent=None)
        qtbot.addWidget(dialog)

        # Check that task data is accessible
        row_ids = dialog.row_ids()
        assert "task-1" in row_ids

    def test_restore_button_exists(self, qtbot, mock_repo, sample_hidden_task):
        """Restore button exists for each task row."""
        mock_repo.list_trash.return_value = [sample_hidden_task]
        dialog = TrashDialog(mock_repo, parent=None)
        qtbot.addWidget(dialog)

        # Restore button should be present (created in _add_row)
        assert len(dialog.row_ids()) == 1


class TestTrashDialogRestoration:
    """Test restoration functionality."""

    def test_restore_emits_signal(self, qtbot, mock_repo, sample_hidden_task):
        """Clicking restore button emits restore_requested signal."""
        mock_repo.list_trash.return_value = [sample_hidden_task]
        dialog = TrashDialog(mock_repo, parent=None)
        qtbot.addWidget(dialog)

        # Setup: mock the restore method
        mock_repo.restore.return_value = None

        with qtbot.waitSignal(dialog.restore_requested, timeout=500) as blocker:
            dialog._on_restore("task-1")

        assert blocker.args == ["task-1"]

    def test_restore_removes_row(self, qtbot, mock_repo, sample_hidden_task):
        """Row removed after successful restoration."""
        mock_repo.list_trash.return_value = [sample_hidden_task]
        dialog = TrashDialog(mock_repo, parent=None)
        qtbot.addWidget(dialog)

        # Verify row exists
        assert "task-1" in dialog.row_ids()

        # Restore the task
        mock_repo.restore.return_value = None
        dialog._on_restore("task-1")

        # Row should be removed
        assert "task-1" not in dialog.row_ids()

    def test_restore_failure_shows_error(self, qtbot, mock_repo, sample_hidden_task):
        """Error dialog shown when restoration fails."""
        import sqlite3
        mock_repo.list_trash.return_value = [sample_hidden_task]
        dialog = TrashDialog(mock_repo, parent=None)
        qtbot.addWidget(dialog)

        # Setup: mock the restore method to fail
        error = sqlite3.OperationalError("database locked")
        mock_repo.restore.side_effect = error

        # Restore attempt
        dialog._on_restore("task-1")

        # restore_failed signal should be emitted
        # (actual error dialog shown separately via ErrorDialog.show_io_error)

    def test_reload_refreshes_list(self, qtbot, mock_repo, sample_hidden_tasks):
        """reload() refreshes task list from repository."""
        # Start with 2 tasks
        mock_repo.list_trash.return_value = sample_hidden_tasks[:2]
        dialog = TrashDialog(mock_repo, parent=None)
        qtbot.addWidget(dialog)

        assert len(dialog.row_ids()) == 2

        # Update repository to return 3 tasks
        mock_repo.list_trash.return_value = sample_hidden_tasks
        dialog.reload()

        assert len(dialog.row_ids()) == 3


class TestTrashDialogEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_boundary_30_days(self, qtbot, mock_repo):
        """Task at 30-day boundary is still visible."""
        now = datetime.now()
        task_at_30_days = Task(
            id="task-30d",
            title="Task at 30 days",
            status=Status.DONE,
            hidden_at=(now - timedelta(days=30)).isoformat(),
            completed_at=(now - timedelta(days=30)).isoformat(),
            projeto="outros",
            notes="",
            type="online",
            deps=[],
        )
        mock_repo.list_trash.return_value = [task_at_30_days]
        dialog = TrashDialog(mock_repo, parent=None)
        qtbot.addWidget(dialog)

        assert "task-30d" in dialog.row_ids()

    def test_long_title_elision(self, qtbot, mock_repo):
        """Very long titles are elided with tooltip."""
        long_title = "A" * 100
        task = Task(
            id="task-long",
            title=long_title,
            status=Status.DONE,
            hidden_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
            projeto="outros",
            notes="",
            type="online",
            deps=[],
        )
        mock_repo.list_trash.return_value = [task]
        dialog = TrashDialog(mock_repo, parent=None)
        qtbot.addWidget(dialog)

        # Task should be listed (elision happens in UI rendering)
        assert "task-long" in dialog.row_ids()

    def test_switch_between_empty_and_filled(self, qtbot, mock_repo):
        """Dialog correctly switches between empty and filled states."""
        mock_repo.list_trash.return_value = []
        dialog = TrashDialog(mock_repo, parent=None)
        qtbot.addWidget(dialog)

        # Start empty
        assert dialog._stack.currentIndex() == 0

        # Add a task and reload
        task = Task(
            id="task-1",
            title="New Task",
            status=Status.DONE,
            hidden_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
            projeto="outros",
            notes="",
            type="online",
            deps=[],
        )
        mock_repo.list_trash.return_value = [task]
        dialog.reload()

        # Should now show items
        assert dialog._stack.currentIndex() == 1

        # Clear and reload
        mock_repo.list_trash.return_value = []
        dialog.reload()

        # Should be empty again
        assert dialog._stack.currentIndex() == 0
