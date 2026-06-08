# @tdd-unlocked: feature favorito/permanente alterou o contrato canonico
#   (source.md §3.2) — compute_sector ganhou o parametro `permanente`.
# Suite: contract | Module: module-0-foundations | Task: TASK-2
# TIDs: TID-0-2-025
import inspect
from typing import get_type_hints

import pytest

from task_manager_desktop.core.models import Status


class TestComputeSectorSignature:
    """TID-0-2-025 | covers: OVERVIEW Contratos | suite: contract

    Contrato: compute_sector(status: Status, has_open_deps: bool,
    permanente: bool = False) -> tuple[Sector, str].
    """

    def test_compute_sector_signature_canonical(self):
        from task_manager_desktop.core.sector import compute_sector

        sig = inspect.signature(compute_sector)
        params = list(sig.parameters.keys())
        assert params == [
            "status",
            "has_open_deps",
            "permanente",
            "em_preparacao",
        ], (f"Params inesperados: {params}")

        hints = get_type_hints(compute_sector)
        assert hints.get("status") is Status
        assert hints.get("has_open_deps") is bool
        assert hints.get("permanente") is bool
        assert hints.get("em_preparacao") is bool
