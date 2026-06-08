# suite: unit | loop: 05-20-decisoes-favorito-permanente-task-manager | task: task-005
# covers: core/models.py — campos favorito/permanente em Task + Sector.PERMANENT
# target: task_manager_desktop/core/models.py
from __future__ import annotations

from dataclasses import asdict

import pytest

from task_manager_desktop.core.models import Sector, Status, Task

# ---------------------------------------------------------------------------
# Defaults — Task(...) sem os novos campos continua valido
# ---------------------------------------------------------------------------


def test_task_defaults_favorito_permanente_false():
    """Task construida sem favorito/permanente aplica defaults False."""
    task = Task(id="t-1", title="Minha task")
    assert task.favorito is False
    assert task.permanente is False


def test_task_legacy_kwargs_still_valid():
    """Construcao legacy (sem os novos campos) permanece valida e completa."""
    task = Task(
        id="t-2",
        title="Legacy",
        status=Status.IN_PROGRESS,
        deps=["t-1"],
        notes="nota",
        order_index=3,
        created_at="2026-05-20T00:00:00Z",
    )
    assert task.favorito is False
    assert task.permanente is False


def test_task_accepts_explicit_new_fields():
    """Os dois novos campos sao aceitos explicitamente no __init__."""
    task = Task(id="t-3", title="Flagged", favorito=True, permanente=True)
    assert task.favorito is True
    assert task.permanente is True


# ---------------------------------------------------------------------------
# Round-trip de serializacao — asdict -> Task(**d) preserva os dois campos
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("favorito", "permanente"),
    [
        (False, False),
        (True, False),
        (False, True),
        (True, True),
    ],
)
def test_serialization_round_trip_preserves_new_fields(favorito, permanente):
    """asdict() -> Task(**d) preserva favorito e permanente em todas as combinacoes."""
    original = Task(
        id="t-rt",
        title="Round trip",
        status=Status.DONE,
        deps=["a", "b"],
        notes="round trip",
        order_index=7,
        created_at="2026-05-20T12:00:00Z",
        completed_at="2026-05-21T12:00:00Z",
        hidden_at=None,
        favorito=favorito,
        permanente=permanente,
    )

    data = asdict(original)
    assert data["favorito"] is favorito
    assert data["permanente"] is permanente

    restored = Task(**data)
    assert restored.favorito is favorito
    assert restored.permanente is permanente
    assert restored == original


def test_eq_considers_new_fields():
    """__eq__ gerado pela dataclass considera favorito e permanente."""
    base = Task(id="t-eq", title="Eq")
    same = Task(id="t-eq", title="Eq")
    diff_favorito = Task(id="t-eq", title="Eq", favorito=True)
    diff_permanente = Task(id="t-eq", title="Eq", permanente=True)

    assert base == same
    assert base != diff_favorito
    assert base != diff_permanente
    assert diff_favorito != diff_permanente


# ---------------------------------------------------------------------------
# Sector.PERMANENT — adicionado sem renumerar setores existentes
# ---------------------------------------------------------------------------


def test_sector_permanent_value_is_5():
    """Sector.PERMANENT existe e vale 5."""
    assert Sector.PERMANENT == 5
    assert Sector.PERMANENT.value == 5


def test_existing_sectors_not_renumbered():
    """Setores existentes mantem seus valores originais (sem renumeracao)."""
    assert Sector.ACTIVE == 1
    assert Sector.WAITING == 2
    assert Sector.BLOCKED == 3
    assert Sector.DONE == 4


# ---------------------------------------------------------------------------
# label_pt() — cobre 100% dos valores de Sector
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sector", list(Sector))
def test_label_pt_covers_all_sectors(sector):
    """label_pt() retorna um label nao-vazio para todo valor de Sector (cobertura 100%)."""
    label = sector.label_pt()
    assert isinstance(label, str)
    assert label != ""


def test_label_pt_permanent_returns_permanentes():
    """label_pt() de Sector.PERMANENT retorna exatamente 'Permanentes'."""
    assert Sector.PERMANENT.label_pt() == "Permanentes"


def test_label_pt_exact_labels():
    """label_pt() devolve o label canonico de cada setor."""
    assert Sector.ACTIVE.label_pt() == "Em andamento"
    assert Sector.WAITING.label_pt() == "A fazer"
    assert Sector.BLOCKED.label_pt() == "Bloqueada"
    assert Sector.DONE.label_pt() == "Concluída"
    assert Sector.PERMANENT.label_pt() == "Permanentes"
