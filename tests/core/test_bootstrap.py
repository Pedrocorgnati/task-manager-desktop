import os
import sqlite3
import stat

import pytest

from task_manager_desktop.core.db import close_connection


@pytest.fixture(autouse=True)
def reset_db_singleton():
    yield
    close_connection()


def test_first_run_creates_directory_with_mode_700(tmp_data_home):
    from task_manager_desktop.core.bootstrap import ensure_data_dir_and_db
    ensure_data_dir_and_db(data_home=tmp_data_home)
    app_dir = tmp_data_home / "task-manager-desktop"
    assert app_dir.exists()
    mode = stat.S_IMODE(os.stat(app_dir).st_mode)
    assert mode == 0o700


def test_first_run_creates_tasks_db(tmp_data_home):
    from task_manager_desktop.core.bootstrap import ensure_data_dir_and_db
    db_path = ensure_data_dir_and_db(data_home=tmp_data_home)
    assert db_path.exists()
    assert db_path.name == "tasks.db"
    assert db_path.is_absolute()


def test_first_run_applies_schema(tmp_data_home):
    from task_manager_desktop.core.bootstrap import ensure_data_dir_and_db
    db_path = ensure_data_dir_and_db(data_home=tmp_data_home)
    conn = sqlite3.connect(str(db_path))
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "tasks" in tables
    assert "_schema_version" in tables


def test_subsequent_run_does_not_change_permissions(tmp_data_home):
    from task_manager_desktop.core.bootstrap import ensure_data_dir_and_db
    app_dir = tmp_data_home / "task-manager-desktop"
    app_dir.mkdir(mode=0o755)
    ensure_data_dir_and_db(data_home=tmp_data_home)
    mode = stat.S_IMODE(os.stat(app_dir).st_mode)
    assert mode == 0o755


def test_permission_error_propagated(tmp_path):
    """Simula data_home sem permissao de escrita."""
    from task_manager_desktop.core.bootstrap import ensure_data_dir_and_db
    data_home = tmp_path / "no_write"
    data_home.mkdir(mode=0o555)
    try:
        with pytest.raises((PermissionError, OSError)):
            ensure_data_dir_and_db(data_home=data_home)
    finally:
        os.chmod(data_home, 0o755)


def test_returns_absolute_path(tmp_data_home):
    from task_manager_desktop.core.bootstrap import ensure_data_dir_and_db
    db_path = ensure_data_dir_and_db(data_home=tmp_data_home)
    assert db_path.is_absolute()


def test_app_dir_name_is_task_manager_desktop(tmp_data_home):
    """AC-T-002 subset: diretorio XDG deve se chamar task-manager-desktop."""
    from task_manager_desktop.core.bootstrap import ensure_data_dir_and_db
    ensure_data_dir_and_db(data_home=tmp_data_home)
    expected_dir = tmp_data_home / "task-manager-desktop"
    assert expected_dir.exists(), f"Esperado diretorio {expected_dir}"


def test_xdg_data_home_env_used_when_set(monkeypatch, tmp_path):
    """_get_xdg_data_home retorna XDG_DATA_HOME quando setado."""
    from task_manager_desktop.core.bootstrap import _get_xdg_data_home
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert _get_xdg_data_home() == tmp_path


def test_xdg_data_home_fallback_when_not_set(monkeypatch):
    """_get_xdg_data_home retorna ~/.local/share quando XDG_DATA_HOME ausente."""
    from pathlib import Path

    from task_manager_desktop.core.bootstrap import _get_xdg_data_home
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    assert _get_xdg_data_home() == Path.home() / ".local" / "share"


def test_subsequent_run_does_not_call_makedirs(tmp_data_home, monkeypatch):
    """Segunda chamada nao tenta criar diretorio ja existente."""
    import os

    from task_manager_desktop.core.bootstrap import ensure_data_dir_and_db
    app_dir = tmp_data_home / "task-manager-desktop"
    app_dir.mkdir(mode=0o700)
    makedirs_calls = []
    original = os.makedirs

    def spy(*args, **kwargs):
        makedirs_calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(os, "makedirs", spy)
    ensure_data_dir_and_db(data_home=tmp_data_home)
    assert len(makedirs_calls) == 0
