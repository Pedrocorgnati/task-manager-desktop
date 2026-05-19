import sqlite3

import pytest

from task_manager_desktop.core.cleanup import (
    HARD_DELETE_DAYS,
    SOFT_DELETE_DAYS,
    run_cleanup_on_boot,
)


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            title TEXT,
            status TEXT,
            completed_at TEXT,
            hidden_at TEXT,
            deps TEXT
        )
        """
    )
    yield conn
    conn.close()


class _TrackingConn:
    """Wrapper leve para rastrear chamadas a execute()."""

    def __init__(self, real: sqlite3.Connection) -> None:
        self._real = real
        self.executed: list[str] = []

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        self.executed.append(sql)
        return self._real.execute(sql, params)

    def commit(self) -> None:
        self._real.commit()


class _FailConn:
    """Conexao que levanta OperationalError em qualquer execute()."""

    def execute(self, *args, **kwargs):  # type: ignore[override]
        raise sqlite3.OperationalError("locked")

    def commit(self) -> None:
        pass


def test_soft_delete_after_3_days(db):
    db.execute(
        "INSERT INTO tasks VALUES ('a','A','done', datetime('now','-4 days'), NULL, NULL)"
    )
    db.commit()
    run_cleanup_on_boot(db)
    row = db.execute("SELECT hidden_at FROM tasks WHERE id='a'").fetchone()
    assert row[0] is not None


def test_hard_delete_after_30_days(db):
    db.execute(
        "INSERT INTO tasks VALUES ('a','A','done', datetime('now','-31 days'), NULL, NULL)"
    )
    db.commit()
    run_cleanup_on_boot(db)
    assert db.execute("SELECT COUNT(*) FROM tasks WHERE id='a'").fetchone()[0] == 0


def test_recent_done_untouched(db):
    db.execute(
        "INSERT INTO tasks VALUES ('a','A','done', datetime('now','-1 days'), NULL, NULL)"
    )
    db.commit()
    run_cleanup_on_boot(db)
    row = db.execute("SELECT hidden_at FROM tasks WHERE id='a'").fetchone()
    assert row[0] is None


def test_idempotent(db):
    db.execute(
        "INSERT INTO tasks VALUES ('a','A','done', datetime('now','-4 days'), NULL, NULL)"
    )
    db.commit()
    run_cleanup_on_boot(db)
    first = db.execute("SELECT hidden_at FROM tasks WHERE id='a'").fetchone()[0]
    run_cleanup_on_boot(db)
    second = db.execute("SELECT hidden_at FROM tasks WHERE id='a'").fetchone()[0]
    assert first == second


def test_operational_error_is_logged_and_reraised(capsys):
    with pytest.raises(sqlite3.OperationalError, match="locked"):
        run_cleanup_on_boot(_FailConn())  # type: ignore[arg-type]
    captured = capsys.readouterr()
    assert "OperationalError" in captured.err


def test_vacuum_only_when_rows_deleted(db):
    db.execute(
        "INSERT INTO tasks VALUES ('a','A','done', datetime('now','-1 days'), NULL, NULL)"
    )
    db.commit()
    spy = _TrackingConn(db)
    run_cleanup_on_boot(spy)  # type: ignore[arg-type]
    vacuum_calls = [s for s in spy.executed if "VACUUM" in s]
    assert vacuum_calls == []


def test_vacuum_called_when_hard_delete_removes_rows(db):
    db.execute(
        "INSERT INTO tasks VALUES ('a','A','done', datetime('now','-31 days'), NULL, NULL)"
    )
    db.commit()
    spy = _TrackingConn(db)
    run_cleanup_on_boot(spy)  # type: ignore[arg-type]
    vacuum_calls = [s for s in spy.executed if "VACUUM" in s]
    assert len(vacuum_calls) == 1


def test_constants():
    assert SOFT_DELETE_DAYS == 3
    assert HARD_DELETE_DAYS == 30
