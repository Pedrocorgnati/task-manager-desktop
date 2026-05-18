from __future__ import annotations

from task_manager_desktop.core.filters import (
    ALL_PROJECTS_SENTINEL,
    is_active,
    matches,
)
from task_manager_desktop.core.models import Status, Task, TaskType


def _make_task(
    title: str = "task",
    projeto: str = "alpha",
    notes: str = "",
) -> Task:
    return Task(
        id="t1",
        title=title,
        status=Status.PENDING,
        type=TaskType.OFFLINE,
        projeto=projeto,
        deps=[],
        notes=notes,
        order_index=1,
        created_at="2026-05-17T10:00:00",
    )


def test_empty_query_and_sentinel_passes():
    assert matches(_make_task(), None, None)
    assert matches(_make_task(), "", ALL_PROJECTS_SENTINEL)


def test_query_substring_case_insensitive_on_title():
    t = _make_task(title="Refatorar UI Header")
    assert matches(t, "header", None)
    assert matches(t, "HEADER", None)
    assert matches(t, "refator", None)
    assert not matches(t, "footer", None)


def test_query_matches_notes_too():
    t = _make_task(title="Tarefa", notes="lembrar de revisar deps")
    assert matches(t, "revisar", None)
    assert matches(t, "DEPS", None)


def test_query_with_only_whitespace_is_inactive():
    t = _make_task(title="qualquer")
    assert matches(t, "   ", None)


def test_projeto_exact_case_insensitive():
    t = _make_task(projeto="Alpha")
    assert matches(t, None, "alpha")
    assert matches(t, None, "ALPHA")
    assert not matches(t, None, "beta")


def test_projeto_sentinel_does_not_filter():
    t = _make_task(projeto="alpha")
    assert matches(t, None, ALL_PROJECTS_SENTINEL)


def test_projeto_and_query_combined_and_semantics():
    t = _make_task(title="login bug", projeto="alpha", notes="")
    assert matches(t, "login", "alpha")
    assert not matches(t, "login", "beta")
    assert not matches(t, "checkout", "alpha")


def test_is_active_detects_query():
    assert is_active("x", None)
    assert is_active("x", ALL_PROJECTS_SENTINEL)


def test_is_active_detects_projeto():
    assert is_active(None, "alpha")
    assert is_active("", "alpha")


def test_is_active_false_when_default_filters():
    assert not is_active(None, None)
    assert not is_active("", ALL_PROJECTS_SENTINEL)
    assert not is_active("   ", ALL_PROJECTS_SENTINEL)
