# @tdd-locked: do not edit without /tdd:unlock
# Suite: integration | Module: module-0-foundations | Task: TASK-1
# TIDs: TID-0-1-008, TID-0-1-009, TID-0-1-010, TID-0-1-011
import os
import stat
from pathlib import Path

import pytest

from task_manager_desktop.core.db import close_connection


@pytest.fixture(autouse=True)
def reset_db():
    yield
    close_connection()


class TestFirstRunXdgPermissions:
    """TID-0-1-008 | covers: TASK-1/ST003 BDD#1 + US-014 | suite: integration"""

    def test_first_run_cria_diretorio_xdg_mode_0o700(self, tmp_path):
        from task_manager_desktop.core.bootstrap import ensure_data_dir_and_db
        data_home = tmp_path / "xdg"
        data_home.mkdir()
        ensure_data_dir_and_db(data_home=data_home)
        app_dir = data_home / "task-manager-desktop"
        assert app_dir.exists()
        mode = stat.S_IMODE(os.stat(app_dir).st_mode)
        assert mode == 0o700


class TestSubsequentRunPreservesPermissions:
    """TID-0-1-009 | covers: TASK-1/ST003 BDD#2 + US-014 cen.2 | suite: integration"""

    def test_runs_subsequentes_preservam_permissoes_existentes(self, tmp_path):
        from task_manager_desktop.core.bootstrap import ensure_data_dir_and_db
        app_dir = tmp_path / "task-manager-desktop"
        app_dir.mkdir(mode=0o755)
        ensure_data_dir_and_db(data_home=tmp_path)
        mode = stat.S_IMODE(os.stat(app_dir).st_mode)
        assert mode == 0o755


class TestReadOnlyDataHome:
    """TID-0-1-010 | covers: TASK-1/ST003 BDD#3 + US-013 cen.3 | suite: integration"""

    def test_data_home_readonly_dispara_permissionerror_com_path(self, tmp_path):
        from task_manager_desktop.core.bootstrap import ensure_data_dir_and_db
        data_home = tmp_path / "noaccess"
        data_home.mkdir(mode=0o555)
        try:
            with pytest.raises((PermissionError, OSError)):
                ensure_data_dir_and_db(data_home=data_home)
        finally:
            os.chmod(data_home, 0o755)


class TestReturnIsAbsoluteTasksDb:
    """TID-0-1-011 | covers: TASK-1/ST003 BDD#4 | suite: integration"""

    def test_retorno_e_path_absoluto_com_nome_tasks_db(self, tmp_path):
        from task_manager_desktop.core.bootstrap import ensure_data_dir_and_db
        db_path = ensure_data_dir_and_db(data_home=tmp_path)
        assert db_path.is_absolute()
        assert db_path.name == "tasks.db"
