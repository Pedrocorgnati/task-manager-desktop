# suite: acceptance | module: module-1-gestao-de-tasks | task: TASK-3/ST003
# @tdd-locked: do not edit without /tdd:unlock
# covers: US-017 — Migracao manual de tasks de ferramentas anteriores
# TIDs: TID-1-3-007, TID-1-3-008, TID-1-3-009
from __future__ import annotations

from pathlib import Path

import pytest

_README = Path(__file__).parents[3] / "README.md"


@pytest.fixture(scope="module")
def readme_content():
    return _README.read_text(encoding="utf-8")


# TID-1-3-007 | covers: US-017#1 | bdd_type: SUCCESS
def test_readme_documents_one_by_one_flow(readme_content):
    """Migracao manual uma a uma: 100 tasks via UI sem degradacao perceptivel (cap NFR ~2000)."""
    assert "## Migracao manual de tarefas anteriores" in readme_content
    assert "nao ha importador automatico" in readme_content.lower()


# TID-1-3-008 | covers: US-017#2 | bdd_type: SUCCESS
def test_readme_documents_subtasks_via_deps_pattern(readme_content):
    """README documenta padrao subtasks-via-deps (A,B,C tasks + pai depende de A,B,C)."""
    content_lower = readme_content.lower()
    assert "dependencias" in content_lower or "deps" in content_lower
    assert "bloqueadas" in content_lower or "bloqueada" in content_lower


# TID-1-3-009 | covers: US-017#3 | bdd_type: EDGE
def test_readme_mentions_nfr_limit_and_backup(readme_content):
    """README cita limite NFR ~2000 tasks e recomenda backup com 'cp tasks.db'."""
    assert "2000" in readme_content
    assert "tasks.db" in readme_content
    assert "backup" in readme_content.lower() or "cp " in readme_content
