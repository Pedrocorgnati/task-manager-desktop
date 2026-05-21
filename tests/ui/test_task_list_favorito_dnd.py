"""Testes de UI/modelo de lista para favorito: sort determinista e drop invalido.

Cobre a "Saida esperada" da task-010 (source.md secao 3.6):
- `RENDER_ORDER` explicito com `Sector.PERMANENT` por ultimo;
- sort `(favorito DESC, order_index ASC, id ASC)` determinista (AC-13);
- rejeicao de drop que cruza a fronteira do bloco favorito (AC-8).
"""

from __future__ import annotations

import logging

import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt
from PySide6.QtGui import QDropEvent

from task_manager_desktop.core.db import run_migrations
from task_manager_desktop.core.models import Sector, Status, Task, TaskType
from task_manager_desktop.repositories.task_repository import TaskRepository
from task_manager_desktop.ui.task_list import (
    _ROLE_TASK_ID,
    _ROLE_TYPE,
    RENDER_ORDER,
    TaskList,
    is_cross_block_drop,
    sort_sector_tasks,
)


@pytest.fixture
def repo(in_memory_db):
    run_migrations(in_memory_db)
    return TaskRepository(in_memory_db, db_path=":memory:")


def _task(tid: str, *, favorito: bool = False, order_index: int = 1) -> Task:
    return Task(
        id=tid,
        title=f"Task {tid}",
        status=Status.PENDING,
        type=TaskType.HUMAN,
        deps=[],
        order_index=order_index,
        created_at="2026-05-21T10:00:00",
        favorito=favorito,
    )


# ---------------------------------------------------------------------------
# RENDER_ORDER
# ---------------------------------------------------------------------------


def test_render_order_cobre_todos_os_setores():
    assert set(RENDER_ORDER) == set(Sector)


def test_render_order_tem_permanent_por_ultimo():
    assert RENDER_ORDER[-1] is Sector.PERMANENT
    assert RENDER_ORDER == [
        Sector.ACTIVE,
        Sector.WAITING,
        Sector.BLOCKED,
        Sector.DONE,
        Sector.PERMANENT,
    ]


# ---------------------------------------------------------------------------
# sort_sector_tasks — favorito DESC, order_index ASC, id ASC
# ---------------------------------------------------------------------------


def test_sort_coloca_favoritos_no_topo():
    tasks = [
        _task("a", favorito=False, order_index=1),
        _task("b", favorito=True, order_index=2),
        _task("c", favorito=False, order_index=3),
    ]
    ordered = [t.id for t in sort_sector_tasks(tasks)]
    assert ordered == ["b", "a", "c"]


def test_sort_ordena_por_order_index_dentro_do_bloco():
    tasks = [
        _task("a", favorito=True, order_index=3),
        _task("b", favorito=True, order_index=1),
        _task("c", favorito=True, order_index=2),
    ]
    ordered = [t.id for t in sort_sector_tasks(tasks)]
    assert ordered == ["b", "c", "a"]


def test_sort_desempata_por_id_ascendente():
    # AC-13: order_index identico -> desempate determinista pelo id.
    tasks = [
        _task("t-30", favorito=False, order_index=5),
        _task("t-10", favorito=False, order_index=5),
        _task("t-20", favorito=False, order_index=5),
    ]
    ordered = [t.id for t in sort_sector_tasks(tasks)]
    assert ordered == ["t-10", "t-20", "t-30"]


def test_sort_e_deterministico_em_duas_execucoes():
    tasks = [
        _task("c", favorito=True, order_index=2),
        _task("a", favorito=False, order_index=2),
        _task("b", favorito=True, order_index=2),
        _task("d", favorito=False, order_index=1),
    ]
    run1 = [t.id for t in sort_sector_tasks(list(tasks))]
    run2 = [t.id for t in sort_sector_tasks(list(tasks))]
    assert run1 == run2 == ["b", "c", "d", "a"]


def test_sort_nao_muta_a_lista_de_entrada():
    tasks = [_task("b", favorito=True), _task("a", favorito=False)]
    original = list(tasks)
    sort_sector_tasks(tasks)
    assert tasks == original


# ---------------------------------------------------------------------------
# is_cross_block_drop — fronteira do bloco favorito
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "flags",
    [
        [],
        [True],
        [False],
        [True, True, False, False],
        [True, False],
        [False, False, False],
        [True, True],
    ],
)
def test_drop_valido_quando_bloco_favorito_e_contiguo(flags):
    assert is_cross_block_drop(flags) is False


@pytest.mark.parametrize(
    "flags",
    [
        [False, True],
        [True, False, True],
        [False, True, False],
        [True, True, False, True],
    ],
)
def test_drop_invalido_quando_favoritos_interleaved(flags):
    assert is_cross_block_drop(flags) is True


# ---------------------------------------------------------------------------
# Render integrado: favoritos no topo do setor
# ---------------------------------------------------------------------------


def _visible_task_ids(task_list: TaskList) -> list[str]:
    inner = task_list._inner
    return [
        inner.item(r).data(_ROLE_TASK_ID)
        for r in range(inner.count())
        if inner.item(r).data(_ROLE_TYPE) == "task"
    ]


def test_task_list_renderiza_favoritos_no_topo_do_setor(qtbot, repo):
    # Tres tasks no mesmo setor (PENDING, sem deps -> Fila). O favorito 'b'
    # tem order_index maior, mas deve renderizar antes dos nao-favoritos.
    for t in (
        _task("a", favorito=False, order_index=1),
        _task("b", favorito=True, order_index=9),
        _task("c", favorito=False, order_index=2),
    ):
        repo.create(t)

    task_list = TaskList()
    task_list.set_repo(repo)
    qtbot.addWidget(task_list)
    task_list.refresh(repo.list_active())

    assert _visible_task_ids(task_list) == ["b", "a", "c"]


# ---------------------------------------------------------------------------
# Drop cross-block end-to-end: rejeicao nao muta order_index e e logada
# ---------------------------------------------------------------------------


def _task_row(task_list: TaskList, task_id: str) -> int:
    """Row do item 'task' com o id dado dentro do _InnerList."""
    inner = task_list._inner
    for r in range(inner.count()):
        if inner.item(r).data(_ROLE_TYPE) == "task" and (
            inner.item(r).data(_ROLE_TASK_ID) == task_id
        ):
            return r
    raise AssertionError(f"task row nao encontrada: {task_id}")


def test_drop_cross_block_rejeitado_nao_altera_order_index(qtbot, repo, caplog):
    # AC-8: dragar o favorito 'a' (topo do setor) e soltar abaixo do
    # nao-favorito 'b' cruza a fronteira do bloco. O drop deve ser ignorado,
    # sem mutar order_index de nenhuma das pontas, e registrado em log debug
    # com task_id, from_block e to_block (source.md secao 1.6 e secao 9).
    repo.create(_task("a", favorito=True, order_index=1))
    repo.create(_task("b", favorito=False, order_index=2))

    task_list = TaskList()
    task_list.set_repo(repo)
    qtbot.addWidget(task_list)
    task_list.refresh(repo.list_active())
    # Geometria real e necessaria para _nearest_task_row / visualItemRect.
    task_list.resize(360, 600)
    task_list.show()
    qtbot.waitExposed(task_list)

    inner = task_list._inner
    fav_row = _task_row(task_list, "a")
    non_fav_row = _task_row(task_list, "b")
    inner.setCurrentRow(fav_row)

    # Ponto de drop abaixo do centro do card nao-favorito: o favorito cairia
    # apos 'b', produzindo a ordem [nao-favorito, favorito] -> cross-block.
    non_fav_rect = inner.visualItemRect(inner.item(non_fav_row))
    drop_y = non_fav_rect.bottom()

    mime: QMimeData = inner.model().mimeData(
        [inner.model().index(fav_row, 0)]
    )
    event = QDropEvent(
        QPointF(100, float(drop_y)),
        Qt.DropAction.MoveAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    with caplog.at_level(logging.DEBUG, logger="task_manager_desktop.ui.task_list"):
        inner.dropEvent(event)

    # (a) drop rejeitado: order_index de ambas as pontas inalterado.
    assert event.isAccepted() is False
    assert repo.get_by_id("a").order_index == 1
    assert repo.get_by_id("b").order_index == 2

    # (b) rejeicao logada com os tres campos exigidos pela secao 9.
    rejection_logs = [
        rec.getMessage() for rec in caplog.records if "dnd.drop_rejected" in rec.getMessage()
    ]
    assert len(rejection_logs) == 1
    message = rejection_logs[0]
    assert "task_id=a" in message
    assert "from_block=favorito" in message
    assert "to_block=nao-favorito" in message


def test_drop_rejected_log_is_structured(qtbot, repo):
    """source.md secao 9: o evento dnd.drop_rejected e emitido como payload
    estruturado (campos no `extra=` do LogRecord), consistente com os demais
    eventos de observabilidade, em nivel debug e sem toast."""
    repo.create(_task("a", favorito=True, order_index=1))
    repo.create(_task("b", favorito=False, order_index=2))

    task_list = TaskList()
    task_list.set_repo(repo)
    qtbot.addWidget(task_list)
    task_list.refresh(repo.list_active())
    task_list.resize(360, 600)
    task_list.show()
    qtbot.waitExposed(task_list)

    inner = task_list._inner
    fav_row = _task_row(task_list, "a")
    non_fav_row = _task_row(task_list, "b")
    inner.setCurrentRow(fav_row)

    non_fav_rect = inner.visualItemRect(inner.item(non_fav_row))
    drop_y = non_fav_rect.bottom()
    mime: QMimeData = inner.model().mimeData([inner.model().index(fav_row, 0)])
    event = QDropEvent(
        QPointF(100, float(drop_y)),
        Qt.DropAction.MoveAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    # Handler dedicado: captura os LogRecord crus para inspecionar o `extra=`.
    captured: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    logger = logging.getLogger("task_manager_desktop.ui.task_list")
    handler = _Capture()
    prev_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        inner.dropEvent(event)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(prev_level)

    records = [r for r in captured if "dnd.drop_rejected" in r.getMessage()]
    assert len(records) == 1
    record = records[0]

    # Nivel debug, sem escalonar para warning/error (nao gera toast).
    assert record.levelno == logging.DEBUG

    # Payload estruturado: os tres campos canonicos + event/reason no LogRecord.
    assert record.event == "dnd.drop_rejected"
    assert record.reason == "cross-block"
    assert record.task_id == "a"
    assert record.from_block == "favorito"
    assert record.to_block == "nao-favorito"
