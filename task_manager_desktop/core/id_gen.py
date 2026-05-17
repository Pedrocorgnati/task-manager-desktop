from __future__ import annotations

import secrets
import sqlite3
from string import ascii_lowercase, digits
from typing import Final

ALPHABET: Final[str] = digits + ascii_lowercase
ID_LENGTH: Final[int] = 3
MAX_ATTEMPTS: Final[int] = 100


def generate_id(conn: sqlite3.Connection) -> str:
    for _ in range(MAX_ATTEMPTS):
        candidate = "".join(secrets.choice(ALPHABET) for _ in range(ID_LENGTH))
        row = conn.execute(
            "SELECT 1 FROM tasks WHERE id = ?", (candidate,)
        ).fetchone()
        if row is None:
            return candidate
    raise RuntimeError(
        f"Could not generate unique ID after {MAX_ATTEMPTS} attempts"
    )


__all__ = ["ALPHABET", "ID_LENGTH", "MAX_ATTEMPTS", "generate_id"]
