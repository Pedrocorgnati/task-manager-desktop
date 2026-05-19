from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from task_manager_desktop.core.exceptions import TaskNotFoundError
from task_manager_desktop.core.models import (
    Status,
    Task,
    TaskType,
    normalize_projeto,
    parse_deps,
)


def _row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"],
        title=row["title"],
        status=Status(row["status"]),
        type=TaskType(row["type"]),
        projeto=row["projeto"],
        deps=parse_deps(row["deps"] or ""),
        notes=row["notes"] or "",
        order_index=row["order_index"] or 0,
        created_at=row["created_at"] or "",
        completed_at=row["completed_at"],
        hidden_at=row["hidden_at"],
    )


class TaskRepository:
    def __init__(self, conn: sqlite3.Connection, db_path: Path | str = "") -> None:
        self._conn = conn
        self.db_path: Path = Path(db_path) if db_path else Path()

    def create(self, task: Task) -> None:
        self._conn.execute(
            """
            INSERT INTO tasks (id, title, status, type, projeto, deps, notes, order_index, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.id,
                task.title,
                task.status.value,
                task.type.value,
                task.projeto,
                ",".join(task.deps),
                task.notes,
                task.order_index,
                task.created_at or datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()

    def update(self, task_id: str, **fields) -> None:
        allowed = {
            "title",
            "status",
            "type",
            "projeto",
            "deps",
            "notes",
            "order_index",
            "completed_at",
        }
        col_map: dict[str, object] = {}
        for key, val in fields.items():
            if key not in allowed:
                continue
            if key == "deps" and isinstance(val, list):
                col_map["deps"] = ",".join(val)
            elif key == "status" and isinstance(val, Status):
                col_map["status"] = val.value
            elif key == "type" and isinstance(val, TaskType):
                col_map["type"] = val.value
            elif key == "projeto":
                col_map["projeto"] = normalize_projeto(str(val))
            else:
                col_map[key] = val

        if not col_map:
            return

        set_clause = ", ".join(f"{k} = ?" for k in col_map)
        values = list(col_map.values()) + [task_id]
        self._conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
        self._conn.commit()

    def delete(self, task_id: str) -> None:
        self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self._conn.commit()

    def update_notes(self, task_id: str, notes: str) -> None:
        cursor = self._conn.execute(
            "UPDATE tasks SET notes = ? WHERE id = ?",
            (notes, task_id),
        )
        self._conn.commit()
        if cursor.rowcount == 0:
            raise TaskNotFoundError(f"Task {task_id!r} não encontrada")

    def list_active(self) -> list[Task]:
        rows = self._conn.execute(
            "SELECT * FROM tasks WHERE hidden_at IS NULL ORDER BY order_index ASC, created_at ASC"
        ).fetchall()
        return [_row_to_task(r) for r in rows]

    def list_trash(self) -> list[Task]:
        # Sqlite3 nao suporta NULLS LAST nativo; usar IS NULL como primeiro criterio de ordem
        rows = self._conn.execute(
            "SELECT * FROM tasks WHERE hidden_at IS NOT NULL"
            " ORDER BY completed_at IS NULL, completed_at DESC"
        ).fetchall()
        return [_row_to_task(r) for r in rows]

    def get_by_id(self, task_id: str) -> Task | None:
        row = self._conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return _row_to_task(row) if row else None

    def mark_hidden(self, task_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute("UPDATE tasks SET hidden_at = ? WHERE id = ?", (now, task_id))
        self._conn.commit()

    def _filter_existing_deps(self, deps: list[str]) -> list[str]:
        """Retorna apenas os dep IDs que ainda existem na tabela tasks."""
        if not deps:
            return []
        placeholders = ",".join("?" * len(deps))
        rows = self._conn.execute(
            f"SELECT id FROM tasks WHERE id IN ({placeholders})", deps
        ).fetchall()
        existing = {r["id"] for r in rows}
        return [d for d in deps if d in existing]

    def restore(self, task_id: str) -> None:
        row = self._conn.execute(
            "SELECT deps FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        current_deps = []
        if row:
            current_deps = [d for d in (row["deps"] or "").split(",") if d]
        clean_deps = self._filter_existing_deps(current_deps)
        self._conn.execute(
            "UPDATE tasks SET hidden_at = NULL, deps = ? WHERE id = ?",
            (",".join(clean_deps), task_id),
        )
        self._conn.commit()

    def list_projetos(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT projeto FROM tasks WHERE hidden_at IS NULL ORDER BY LOWER(projeto) ASC"
        ).fetchall()
        return [r["projeto"] for r in rows]

    def exists(self, task_id: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return row is not None

    def update_status(
        self,
        task_id: str,
        status: Status,
        completed_at: datetime | None,
    ) -> None:
        completed_str = completed_at.isoformat() if completed_at is not None else None
        self._conn.execute(
            "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?",
            (status.value, completed_str, task_id),
        )
        self._conn.commit()

    def update_order_indexes(self, pairs: list[tuple[str, int]]) -> None:
        if not pairs:
            return
        with self._conn:
            self._conn.executemany(
                "UPDATE tasks SET order_index = ? WHERE id = ?",
                [(order_index, task_id) for task_id, order_index in pairs],
            )

    def hide_all_done(self) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            cursor = self._conn.execute(
                "UPDATE tasks SET hidden_at = ? "
                "WHERE status = ? AND hidden_at IS NULL",
                (now, Status.DONE.value),
            )
            return cursor.rowcount
