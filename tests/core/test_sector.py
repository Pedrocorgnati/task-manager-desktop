import pytest

from task_manager_desktop.core.models import Color, Sector, Status, Task
from task_manager_desktop.core.sector import PERMANENT_ACCENT, compute_sector, count_open_deps


@pytest.mark.parametrize("status,has_open,expected", [
    (Status.IN_PROGRESS, False, (Sector(1), Color.GREEN)),
    (Status.IN_PROGRESS, True,  (Sector(1), Color.GRAY)),
    (Status.PENDING,     False, (Sector(2), Color.YELLOW)),
    (Status.PENDING,     True,  (Sector(3), Color.GRAY)),
    (Status.DONE,        False, (Sector(4), Color.NEUTRAL)),
    (Status.DONE,        True,  (Sector(4), Color.NEUTRAL)),
])
def test_compute_sector_all_combinations(status, has_open, expected):
    assert compute_sector(status, has_open) == expected


@pytest.mark.parametrize("has_open", [False, True])
def test_compute_sector_permanent_when_done_and_permanente(has_open):
    """status=DONE + permanente=True -> PERMANENT, independente de has_open_deps.

    Cobre source.md secao 3.2 e criterio de aceite 4. O caminho permanente nao
    consulta has_open_deps, logo o resultado e o mesmo para ambos os valores.
    """
    assert compute_sector(Status.DONE, has_open, permanente=True) == (
        Sector.PERMANENT,
        PERMANENT_ACCENT,
    )


@pytest.mark.parametrize("status", [Status.PENDING, Status.IN_PROGRESS])
@pytest.mark.parametrize("has_open", [False, True])
def test_compute_sector_non_done_ignores_permanente(status, has_open):
    """permanente=True com status!=DONE retorna o setor canonico.

    Cobre source.md secao 3.2 e criterio de aceite 5: permanente nunca leva ao
    setor PERMANENT fora de DONE — o resultado e identico a permanente=False.
    """
    canonical = compute_sector(status, has_open, permanente=False)
    assert compute_sector(status, has_open, permanente=True) == canonical
    assert canonical[0] is not Sector.PERMANENT


def test_compute_sector_done_non_permanente_stays_done():
    """status=DONE + permanente=False -> setor canonico DONE (nunca PERMANENT)."""
    assert compute_sector(Status.DONE, False, permanente=False) == (Sector.DONE, Color.NEUTRAL)
    assert compute_sector(Status.DONE, True, permanente=False) == (Sector.DONE, Color.NEUTRAL)


def test_permanent_accent_is_exported_constant():
    """PERMANENT_ACCENT e constante do modulo, retornada por referencia.

    Trocar o valor da constante nao deve exigir mudanca no chamador: o tuple
    retornado por compute_sector aponta para o mesmo objeto da constante.
    """
    from task_manager_desktop.core import sector as sector_mod

    assert hasattr(sector_mod, "PERMANENT_ACCENT")
    assert isinstance(PERMANENT_ACCENT, str)
    assert PERMANENT_ACCENT  # nao-vazio
    _, accent = compute_sector(Status.DONE, False, permanente=True)
    assert accent is PERMANENT_ACCENT


def test_compute_sector_is_pure_default_permanente():
    """A assinatura mantem permanente=False como default (chamada de 2 args)."""
    assert compute_sector(Status.DONE, False) == compute_sector(
        Status.DONE, False, permanente=False
    )


def test_count_open_deps_ignores_unknown_ids():
    a = Task(id="a", title="A", status=Status.PENDING)
    all_tasks = {"a": a}
    assert count_open_deps(["a", "xyz999"], all_tasks) == 1


def test_count_open_deps_excludes_done():
    a = Task(id="a", title="A", status=Status.DONE)
    b = Task(id="b", title="B", status=Status.PENDING)
    assert count_open_deps(["a", "b"], {"a": a, "b": b}) == 1


def test_count_open_deps_empty_list():
    assert count_open_deps([], {}) == 0


def test_count_open_deps_all_done():
    a = Task(id="a", title="A", status=Status.DONE)
    b = Task(id="b", title="B", status=Status.DONE)
    assert count_open_deps(["a", "b"], {"a": a, "b": b}) == 0
