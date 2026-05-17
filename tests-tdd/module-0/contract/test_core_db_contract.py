# @tdd-locked: do not edit without /tdd:unlock
# Suite: contract | Module: module-0-foundations | Task: TASK-1
# TIDs: TID-0-1-017
import inspect

import pytest


class TestCoreDbPublicImports:
    """TID-0-1-017 | covers: OVERVIEW Contratos | suite: contract

    Contrato: from task_manager_desktop.core.db import get_connection,
    run_migrations, close_connection.
    """

    def test_db_module_exposes_canonical_symbols(self):
        from task_manager_desktop.core import db

        for symbol in ("get_connection", "run_migrations", "close_connection"):
            assert hasattr(db, symbol), f"Simbolo ausente em core.db: {symbol}"
            assert callable(getattr(db, symbol)), f"{symbol} nao e callable"

        sig_gc = inspect.signature(db.get_connection)
        assert "db_path" in sig_gc.parameters

        sig_rm = inspect.signature(db.run_migrations)
        assert "conn" in sig_rm.parameters

        sig_cc = inspect.signature(db.close_connection)
        assert len(sig_cc.parameters) == 0
