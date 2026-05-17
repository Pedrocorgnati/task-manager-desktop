# @tdd-locked: do not edit without /tdd:unlock
# Suite: contract | Module: module-0-foundations | Task: TASK-2
# TIDs: TID-0-2-026
import inspect

import pytest


class TestResolveCyclesSignature:
    """TID-0-2-026 | covers: OVERVIEW Contratos | suite: contract

    Contrato: resolve_cycles(start_id: str, dep_ids: list[str], all_tasks: dict[str, Task])
                -> tuple[list[str], str | None].
    """

    def test_resolve_cycles_signature_canonical(self):
        from task_manager_desktop.core.cycles import resolve_cycles

        sig = inspect.signature(resolve_cycles)
        params = list(sig.parameters.keys())
        assert len(params) == 3, f"Esperado 3 parametros, got: {params}"
        assert params[0] == "task_id"
        assert params[1] == "proposed_deps"
        assert params[2] == "all_tasks"
