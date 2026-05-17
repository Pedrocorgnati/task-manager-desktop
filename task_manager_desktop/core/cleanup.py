from __future__ import annotations

import sqlite3
import sys
import traceback
from typing import Final

SOFT_DELETE_DAYS: Final[int] = 3
HARD_DELETE_DAYS: Final[int] = 30


def run_cleanup_on_boot(conn: sqlite3.Connection) -> None:
    try:
        conn.execute(
            "UPDATE tasks SET hidden_at = CURRENT_TIMESTAMP"
            " WHERE status = 'done'"
            " AND completed_at < datetime('now', ?)"
            " AND hidden_at IS NULL",
            (f"-{SOFT_DELETE_DAYS} days",),
        )
        cur2 = conn.execute(
            "DELETE FROM tasks WHERE completed_at < datetime('now', ?)",
            (f"-{HARD_DELETE_DAYS} days",),
        )
        conn.commit()
        if cur2.rowcount > 0:
            conn.execute("VACUUM")
    except sqlite3.OperationalError:
        traceback.print_exc(file=sys.stderr)
        raise


__all__ = ["HARD_DELETE_DAYS", "SOFT_DELETE_DAYS", "run_cleanup_on_boot"]
