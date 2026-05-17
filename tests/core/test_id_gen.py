import re
import sqlite3
from unittest.mock import patch

import pytest

from task_manager_desktop.core.id_gen import ALPHABET, ID_LENGTH, MAX_ATTEMPTS, generate_id

ID_REGEX = re.compile(r"^[0-9a-z]{3}$")


@pytest.fixture
def empty_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY)")
    yield conn
    conn.close()


def test_generates_base36_3char_ids(empty_conn):
    ids = set()
    for _ in range(100):
        new_id = generate_id(empty_conn)
        assert ID_REGEX.match(new_id), f"Invalid ID: {new_id}"
        ids.add(new_id)
        empty_conn.execute("INSERT INTO tasks (id) VALUES (?)", (new_id,))
    assert len(ids) == 100


def test_collision_forces_retry(empty_conn):
    empty_conn.execute("INSERT INTO tasks (id) VALUES (?)", ("abc",))
    draws = iter(["a", "b", "c", "x", "y", "z"])
    with patch(
        "task_manager_desktop.core.id_gen.secrets.choice",
        side_effect=lambda _: next(draws),
    ):
        result = generate_id(empty_conn)
    assert result == "xyz"


def test_raises_when_attempts_exhausted(empty_conn):
    rows = [(c1 + c2 + c3,) for c1 in ALPHABET for c2 in ALPHABET for c3 in ALPHABET]
    empty_conn.executemany("INSERT INTO tasks (id) VALUES (?)", rows)
    with pytest.raises(RuntimeError, match="Could not generate unique ID"):
        generate_id(empty_conn)


def test_alphabet_is_base36():
    assert len(ALPHABET) == 36
    assert all(c.isdigit() or c.islower() for c in ALPHABET)


def test_id_length_constant():
    assert ID_LENGTH == 3


def test_max_attempts_constant():
    assert MAX_ATTEMPTS == 100
