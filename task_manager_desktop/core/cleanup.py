from __future__ import annotations

import sqlite3
import sys
import traceback
from typing import Final

SOFT_DELETE_DAYS: Final[int] = 3
HARD_DELETE_DAYS: Final[int] = 30


def _strip_orphan_deps(conn: sqlite3.Connection) -> None:
    """Remove deps que apontam para tasks inexistentes em todas as tasks restantes."""
    rows = conn.execute("SELECT id, deps FROM tasks WHERE deps IS NOT NULL AND deps != ''").fetchall()
    updates: list[tuple[str, str]] = []
    for row in rows:
        task_id: str = row["id"]
        raw_deps: str = row["deps"] or ""
        deps = [d for d in raw_deps.split(",") if d]
        if not deps:
            continue
        placeholders = ",".join("?" * len(deps))
        existing = {
            r["id"]
            for r in conn.execute(
                f"SELECT id FROM tasks WHERE id IN ({placeholders})", deps
            ).fetchall()
        }
        clean = [d for d in deps if d in existing]
        if clean != deps:
            updates.append((",".join(clean), task_id))
    if updates:
        conn.executemany("UPDATE tasks SET deps = ? WHERE id = ?", updates)


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
        if cur2.rowcount > 0:
            _strip_orphan_deps(conn)
        conn.commit()
        if cur2.rowcount > 0:
            conn.execute("VACUUM")
    except sqlite3.OperationalError:
        traceback.print_exc(file=sys.stderr)
        raise


__all__ = ["HARD_DELETE_DAYS", "SOFT_DELETE_DAYS", "run_cleanup_on_boot"]
