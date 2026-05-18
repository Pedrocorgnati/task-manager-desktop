# suite: acceptance | module: module-2-setores-dependencias | task: TASK-3
# @tdd-locked: do not edit without /tdd:unlock
# covers: US-022 (cenarios 1-3) + AC-T-001..004 + renderizacao de 4 setores
# TIDs: TID-2-3-004, TID-2-3-005, TID-2-3-006, TID-2-3-007,
#        TID-2-3-008, TID-2-3-009, TID-2-3-010
#
# BDD fonte: TASK-3.md + MODULE-USER-STORIES.md US-022
# Fixtures: qtbot (pytest-qt), make_task
# Stack: PySide6 QListWidget com 4 setores fixos + separadores + placeholders
import pytest


# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------


@pytest.fixture
def make_task():
    """Factory canonica de Task para renderizacao de TaskList."""
    from task_manager_desktop.core.models import Status, Task

    def _factory(
        id: str = "t1",
        title: str = "Task",
        status: Status = Status.PENDING,
        deps: list | None = None,
        order_index: int = 1,
        completed_at=None,
    ) -> Task:
        return Task(
            id=id,
            title=title,
            status=status,
            deps=deps or [],
            order_index=order_index,
            completed_at=completed_at,
        )

    return _factory


# ---------------------------------------------------------------------------
# TID-2-3-004 | covers: US-022#cenario-1, AC-T-001 | bdd_type: SUCCESS
# ---------------------------------------------------------------------------


def test_empty_list_renders_4_separators_and_4_placeholders(qtbot):
    """[SUCCESS] Lista vazia exibe 4 separadores + 4 placeholders.

    Given o app esta aberto sem busca ativa e nenhuma task existe
    When TaskList e renderizado com lista vazia
    Then exatamente 4 itens separadores sao exibidos
    And exatamente 4 itens placeholder 'vazio' sao exibidos
    And o total de itens no QListWidget e 8 (4 sep + 4 placeholders)
    """
    from task_manager_desktop.ui.task_list import TaskList, _ROLE_TYPE

    tl = TaskList()
    qtbot.addWidget(tl)
    tl.refresh([])

    inner = tl._inner
    count = inner.count()
    assert count == 8

    types = [inner.item(i).data(_ROLE_TYPE) for i in range(count)]
    assert types.count("separator") == 4
    assert types.count("placeholder") == 4


# ---------------------------------------------------------------------------
# TID-2-3-005 | covers: AC-T-001 | bdd_type: INVARIANTE
# ---------------------------------------------------------------------------


def test_separator_text_never_contains_count(qtbot, make_task):
    """[INVARIANTE] Separador NUNCA exibe contador [N tasks].

    Given TaskList tem tasks em um ou mais setores
    When a lista e renderizada
    Then nenhum separador contem o padrao '[N tasks]' ou '(N)' no texto
    And separadores exibem apenas o rotulo do setor (ex: '— Em execucao —')
    """
    from task_manager_desktop.core.models import Status
    from task_manager_desktop.ui.task_list import TaskList, _ROLE_TYPE

    tl = TaskList()
    qtbot.addWidget(tl)
    tl.refresh([
        make_task(id="t1", status=Status.PENDING, order_index=1),
        make_task(id="t2", status=Status.IN_PROGRESS, order_index=1),
    ])

    inner = tl._inner
    for i in range(inner.count()):
        item = inner.item(i)
        if item.data(_ROLE_TYPE) == "separator":
            text = item.text()
            assert "[" not in text
            assert "(" not in text
            assert "tasks" not in text.lower()


# ---------------------------------------------------------------------------
# TID-2-3-006 | covers: AC-T-003 | bdd_type: SUCCESS
# ---------------------------------------------------------------------------


def test_tasks_sorted_by_sector_then_order_index(qtbot, make_task):
    """[SUCCESS] Tasks renderizadas em ordem (sector, order_index ASC).

    Given tasks: A(in_progress, order=2), B(pending, order=1), C(pending, deps=[A], order=1)
    When TaskList e renderizado
    Then a ordem dos cards na lista segue: setor Em execucao (A), setor Fila (B), setor Bloqueadas (C)
    And dentro de cada setor, cards aparecem em order_index ASC
    """
    from task_manager_desktop.core.models import Sector, Status
    from task_manager_desktop.ui.task_list import TaskList, _ROLE_TYPE

    tl = TaskList()
    qtbot.addWidget(tl)

    task_a = make_task(id="a", title="A", status=Status.IN_PROGRESS, order_index=2)
    task_b = make_task(id="b", title="B", status=Status.PENDING, order_index=1)
    task_c = make_task(id="c", title="C", status=Status.PENDING, deps=["a"], order_index=1)
    tl.refresh([task_a, task_b, task_c])

    inner = tl._inner
    task_rows = [
        (inner._task_id_at(i), inner._sector_for_row(i))
        for i in range(inner.count())
        if inner._type_at(i) == "task"
    ]
    assert task_rows[0] == ("a", Sector.ACTIVE.value)
    assert task_rows[1] == ("b", Sector.WAITING.value)
    assert task_rows[2] == ("c", Sector.BLOCKED.value)


# ---------------------------------------------------------------------------
# TID-2-3-007 | covers: AC-T-004 | bdd_type: EDGE
# ---------------------------------------------------------------------------


def test_click_on_separator_does_not_select(qtbot, make_task):
    """[EDGE] Click em separador nao seleciona item.

    Given TaskList renderizado com pelo menos 1 task
    When o usuario clica em um item separador (ex: '— A fazer —')
    Then nenhum item fica selecionado (currentItem() continua None ou inalterado)
    And o sinal task_selected NAO e emitido
    """
    from PySide6.QtCore import Qt
    from task_manager_desktop.ui.task_list import TaskList, _ROLE_TYPE

    tl = TaskList()
    qtbot.addWidget(tl)
    tl.refresh([make_task()])

    inner = tl._inner
    signals_emitted = []
    tl.task_selected.connect(signals_emitted.append)

    for i in range(inner.count()):
        if inner._type_at(i) == "separator":
            item = inner.item(i)
            # Separator must have NoItemFlags (not selectable)
            assert not (item.flags() & Qt.ItemFlag.ItemIsSelectable)
            # Setting as current does not emit task_selected
            inner.setCurrentItem(item)
            assert signals_emitted == []
            break


# ---------------------------------------------------------------------------
# TID-2-3-008 | covers: US-022#cenario-3, AC-T-002 | bdd_type: EDGE
# ---------------------------------------------------------------------------


def test_click_on_placeholder_does_not_select(qtbot):
    """[EDGE] Placeholder nao-selecionavel e nao-arrastavel.

    Given setor Bloqueadas exibe item 'vazio' (sem tasks naquele setor)
    When o usuario clica no item 'vazio'
    Then nenhum item fica selecionado
    And task_selected NAO emite Task
    And o item nao pode iniciar drag (ItemIsDragEnabled ausente)
    """
    from PySide6.QtCore import Qt
    from task_manager_desktop.ui.task_list import TaskList, _ROLE_TYPE

    tl = TaskList()
    qtbot.addWidget(tl)
    tl.refresh([])

    inner = tl._inner
    signals_emitted = []
    tl.task_selected.connect(signals_emitted.append)

    for i in range(inner.count()):
        if inner._type_at(i) == "placeholder":
            item = inner.item(i)
            assert not (item.flags() & Qt.ItemFlag.ItemIsSelectable)
            assert not (item.flags() & Qt.ItemFlag.ItemIsDragEnabled)
            inner.setCurrentItem(item)
            assert signals_emitted == []
            break


# ---------------------------------------------------------------------------
# TID-2-3-009 | covers: AC-T-004 | bdd_type: SUCCESS
# ---------------------------------------------------------------------------


def test_click_on_task_emits_task_selected(qtbot, make_task):
    """[SUCCESS] Click em card emite task_selected(Task).

    Given TaskList tem ao menos 1 task renderizada como card
    When o usuario clica no card da task
    Then o sinal task_selected e emitido com a Task correspondente
    And a Task emitida contem o id correto da task clicada
    """
    from PySide6.QtCore import Qt
    from task_manager_desktop.ui.task_list import TaskList, _ROLE_TYPE

    tl = TaskList()
    qtbot.addWidget(tl)
    task = make_task(id="t1", title="Test Task")
    tl.refresh([task])

    inner = tl._inner
    signals_emitted = []
    tl.task_selected.connect(signals_emitted.append)

    for i in range(inner.count()):
        if inner._type_at(i) == "task":
            card = inner.itemWidget(inner.item(i))
            qtbot.mouseClick(card, Qt.MouseButton.LeftButton)
            break

    assert len(signals_emitted) == 1
    assert signals_emitted[0].id == "t1"


# ---------------------------------------------------------------------------
# TID-2-3-010 | covers: US-022#cenario-2 | bdd_type: SUCCESS
# ---------------------------------------------------------------------------


def test_placeholder_disappears_when_task_added(qtbot, make_task):
    """[SUCCESS] Placeholder some ao adicionar task ao setor.

    Given setor Fila exibe placeholder 'vazio' (sem tasks pendentes)
    When uma nova task sem deps e adicionada (status=pending) e TaskList.refresh() e chamado
    Then o placeholder 'vazio' do setor Fila NAO aparece mais
    And o card da nova task aparece no setor Fila
    """
    from task_manager_desktop.ui.task_list import TaskList, _ROLE_TYPE

    tl = TaskList()
    qtbot.addWidget(tl)
    tl.refresh([])

    inner = tl._inner
    placeholders_before = sum(
        1 for i in range(inner.count()) if inner._type_at(i) == "placeholder"
    )
    assert placeholders_before == 4

    # Add a pending task (no deps → WAITING sector)
    tl.refresh([make_task(id="t1")])

    placeholders_after = sum(
        1 for i in range(inner.count()) if inner._type_at(i) == "placeholder"
    )
    assert placeholders_after == 3  # WAITING sector has task now, others still empty

    task_ids = [
        inner._task_id_at(i) for i in range(inner.count()) if inner._type_at(i) == "task"
    ]
    assert "t1" in task_ids
