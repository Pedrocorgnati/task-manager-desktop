from task_manager_desktop.core.cycles import _has_path, resolve_cycles
from task_manager_desktop.core.models import Task


def _t(id_: str, deps: list[str] | None = None) -> Task:
    return Task(id=id_, title=id_.upper(), deps=deps or [])


# --- _has_path (unit, private but tested for coverage) ---

def test_has_path_self_returns_self():
    """Linha 13: start == target retorna [start] imediatamente."""
    assert _has_path("a", "a", {}) == ["a"]


def test_has_path_visited_node_skipped():
    """Linha 19: node ja visitado e ignorado (grafo em diamante, sem target)."""
    # A -> B, A -> C -> B: "B" e empurrado 2x; na 2a vez cai no 'continue'
    a = _t("a", deps=["b", "c"])
    b = _t("b")
    c = _t("c", deps=["b"])
    all_tasks = {"a": a, "b": b, "c": c}
    result = _has_path("a", "z", all_tasks)
    assert result is None  # "z" nao existe; confirma que nao trava em loop


def test_has_path_ghost_dep_skipped():
    """Linha 22: dep que nao existe em all_tasks e ignorado silenciosamente."""
    a = _t("a", deps=["ghost"])
    result = _has_path("a", "z", {"a": a})
    assert result is None  # "ghost" nao esta em all_tasks; nao levanta excecao


# --- resolve_cycles ---

def test_direct_cycle_a_b():
    a = _t("a", deps=["b"])
    deps, desc = resolve_cycles("b", ["a"], {"a": a})
    assert deps == []
    assert desc is not None and "Substituida dep 'a'" in desc


def test_chain_cycle_a_b_c():
    a = _t("a", deps=["b"])
    b = _t("b", deps=["c"])
    deps, desc = resolve_cycles("c", ["a"], {"a": a, "b": b})
    assert deps == []
    assert desc is not None
    assert "->" in desc


def test_self_reference_is_dropped():
    deps, desc = resolve_cycles("a", ["a"], {"a": _t("a")})
    assert deps == []


def test_invalid_ids_silently_dropped():
    deps, desc = resolve_cycles("z", ["abc", "xyz999"], {"abc": _t("abc")})
    assert deps == ["abc"]
    assert desc is None


def test_no_cycle_preserves_all_deps():
    a = _t("a")
    b = _t("b")
    deps, desc = resolve_cycles("c", ["a", "b"], {"a": a, "b": b})
    assert set(deps) == {"a", "b"}
    assert desc is None


def test_description_contains_cycle_path():
    a = _t("a", deps=["b"])
    b = _t("b", deps=["c"])
    _, desc = resolve_cycles("c", ["a"], {"a": a, "b": b})
    assert desc is not None
    assert "a->b->c" in desc


def test_dep_with_ghost_reference_in_existing_task():
    """resolve_cycles com tarefa cujo dep interno e inexistente (linha 22 via resolve)."""
    a = _t("a", deps=["ghost"])
    deps, desc = resolve_cycles("z", ["a"], {"a": a})
    assert deps == ["a"]  # "a" nao forma ciclo com "z"
    assert desc is None
