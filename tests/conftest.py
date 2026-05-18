import sqlite3

import pytest


def pytest_addoption(parser):
    """TASK-4/ST011: --run-perf opt-in flag to enforce p95 budget."""
    parser.addoption(
        "--run-perf",
        action="store_true",
        default=False,
        help="Enforce @pytest.mark.perf assertions (p95/p99 budgets).",
    )


@pytest.fixture
def in_memory_db():
    """Banco SQLite em memoria para testes isolados."""
    from task_manager_desktop.core.db import close_connection
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()
    close_connection()


@pytest.fixture
def tmp_data_home(tmp_path):
    """Diretorio temporario simulando XDG_DATA_HOME."""
    return tmp_path
