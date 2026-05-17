# @tdd-locked: do not edit without /tdd:unlock
# Suite: contract | Module: module-0-foundations | Task: TASK-1
# TIDs: TID-0-1-018
import inspect
from pathlib import Path
from typing import get_type_hints

import pytest


class TestEnsureDataDirAndDbSignature:
    """TID-0-1-018 | covers: OVERVIEW Contratos | suite: contract

    Contrato: ensure_data_dir_and_db(data_home: Path | None = None) -> Path
    validado via inspect.signature + typing.get_type_hints.
    """

    def test_ensure_data_dir_and_db_signature_canonical(self):
        from task_manager_desktop.core.bootstrap import ensure_data_dir_and_db

        sig = inspect.signature(ensure_data_dir_and_db)
        params = list(sig.parameters.keys())
        assert params == ["data_home"], f"Parametros inesperados: {params}"

        default = sig.parameters["data_home"].default
        assert default is None, f"Default de data_home deve ser None, got {default!r}"

        hints = get_type_hints(ensure_data_dir_and_db)
        assert hints.get("return") is Path, f"Return deve ser Path, got {hints.get('return')}"
