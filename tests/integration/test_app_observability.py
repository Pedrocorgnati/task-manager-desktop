# suite: integration | loop: 05-20-decisoes-favorito-permanente-task-manager | task: hardening
# covers: source.md secao 9 — observabilidade, evento vassoura.hide_all_done
"""Hardening: o evento estruturado ``vassoura.hide_all_done`` (source.md secao 9).

A vassoura ("Limpar concluídas") tem de emitir um evento de observabilidade
estruturado carregando ``affected_count`` E ``excluded_permanente_count``. Antes
deste hardening o evento NAO era emitido — violacao da regra Zero Silencio.

Duas seams sao testadas:

1. O helper de modulo ``_log_vassoura_hide_all_done`` — prova que o evento
   dispara com os campos certos.
2. A funcao de modulo ``_perform_clear_completed`` — o seam real onde o defeito
   Codex BLOCK vivia: o evento §9 tem de disparar EXATAMENTE UMA VEZ nos 3
   caminhos (sucesso, erro de DB tratado, excecao inesperada). Extraida do
   closure ``_on_clear_completed`` justamente para ser testavel sem subir a
   janela Qt completa (impraticavel headless de forma estavel).
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from unittest.mock import patch

import pytest

from task_manager_desktop.app import (
    _extract_broom_counts,
    _log_vassoura_hide_all_done,
    _perform_clear_completed,
)

_EVENT = "vassoura.hide_all_done"


@dataclass
class _StructuredResult:
    """Espelha o retorno estruturado que o repositorio passou a devolver."""

    affected_count: int
    excluded_permanente_count: int


def _find_event_record(caplog: pytest.LogCaptureFixture) -> logging.LogRecord:
    """Retorna o LogRecord do evento vassoura.hide_all_done (falha se ausente)."""
    matches = [
        rec
        for rec in caplog.records
        if getattr(rec, "event", None) == _EVENT
    ]
    assert len(matches) == 1, (
        f"esperava exatamente 1 evento {_EVENT}, encontrei {len(matches)}"
    )
    return matches[0]


# --------------------------------------------------------------------------
# Evento emitido com ambos os campos — contrato estruturado (objeto)
# --------------------------------------------------------------------------
def test_event_emitted_with_both_fields_from_structured_object(caplog):
    """Resultado estruturado (objeto) -> evento com affected + excluded."""
    result = _StructuredResult(affected_count=3, excluded_permanente_count=2)

    with caplog.at_level(logging.INFO, logger="task_manager_desktop.app"):
        affected = _log_vassoura_hide_all_done(result)

    assert affected == 3
    record = _find_event_record(caplog)
    assert record.affected_count == 3
    assert record.excluded_permanente_count == 2
    assert record.getMessage() == _EVENT


# --------------------------------------------------------------------------
# Evento emitido com ambos os campos — contrato estruturado (dict)
# --------------------------------------------------------------------------
def test_event_emitted_with_both_fields_from_dict(caplog):
    """Resultado estruturado (dict) -> evento com affected + excluded."""
    result = {"affected_count": 5, "excluded_permanente_count": 1}

    with caplog.at_level(logging.INFO, logger="task_manager_desktop.app"):
        affected = _log_vassoura_hide_all_done(result)

    assert affected == 5
    record = _find_event_record(caplog)
    assert record.affected_count == 5
    assert record.excluded_permanente_count == 1


# --------------------------------------------------------------------------
# Fallback de compatibilidade — retorno int legado
# --------------------------------------------------------------------------
def test_event_emitted_with_legacy_int_return(caplog):
    """Retorno int legado -> evento ainda emitido; excluded degrada para 0."""
    with caplog.at_level(logging.INFO, logger="task_manager_desktop.app"):
        affected = _log_vassoura_hide_all_done(7)

    assert affected == 7
    record = _find_event_record(caplog)
    assert record.affected_count == 7
    assert record.excluded_permanente_count == 0


# --------------------------------------------------------------------------
# O evento SEMPRE dispara, mesmo quando nada foi afetado
# --------------------------------------------------------------------------
def test_event_emitted_even_when_zero_affected(caplog):
    """Zero Silencio: o evento dispara mesmo com 0 tasks afetadas."""
    result = _StructuredResult(affected_count=0, excluded_permanente_count=4)

    with caplog.at_level(logging.INFO, logger="task_manager_desktop.app"):
        affected = _log_vassoura_hide_all_done(result)

    assert affected == 0
    record = _find_event_record(caplog)
    assert record.affected_count == 0
    assert record.excluded_permanente_count == 4


# --------------------------------------------------------------------------
# outcome="ok" e o default e NAO carrega campo ``error``
# --------------------------------------------------------------------------
def test_event_default_outcome_is_ok_without_error_field(caplog):
    """Caminho de sucesso: outcome='ok' por default, sem campo error."""
    result = _StructuredResult(affected_count=2, excluded_permanente_count=0)

    with caplog.at_level(logging.INFO, logger="task_manager_desktop.app"):
        _log_vassoura_hide_all_done(result)

    record = _find_event_record(caplog)
    assert record.outcome == "ok"
    assert not hasattr(record, "error")


# --------------------------------------------------------------------------
# Caminho de erro — o evento secao 9 AINDA dispara (regressao Codex BLOCK)
# --------------------------------------------------------------------------
def test_event_emitted_on_error_path_with_outcome_and_error(caplog):
    """Zero Silencio: vassoura que falha no repositorio ainda emite o evento.

    Regressao do achado Codex BLOCK (seam 6): o caminho de erro de
    ``_on_clear_completed`` retornava antes de logar, deixando ``vassoura.
    hide_all_done`` com zero emissoes. O contrato exige emissao EXATAMENTE
    UMA VEZ por acao — inclusive quando ``hide_all_done`` levanta.
    """
    exc = RuntimeError("database is locked")

    with caplog.at_level(logging.INFO, logger="task_manager_desktop.app"):
        affected = _log_vassoura_hide_all_done(None, outcome="error", error=exc)

    assert affected == 0
    record = _find_event_record(caplog)
    assert record.outcome == "error"
    assert record.error == repr(exc)
    assert record.affected_count == 0
    assert record.excluded_permanente_count == 0


# --------------------------------------------------------------------------
# _extract_broom_counts — normalizacao defensiva das tres formas
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (_StructuredResult(3, 2), (3, 2)),
        ({"affected_count": 9, "excluded_permanente_count": 8}, (9, 8)),
        (4, (4, 0)),
        (0, (0, 0)),
        (None, (0, 0)),
        (True, (0, 0)),  # bool nunca conta como dado estruturado
        ({}, (0, 0)),  # dict sem as chaves degrada para zeros
        (object(), (0, 0)),  # forma inesperada nunca levanta
    ],
)
def test_extract_broom_counts_normalizes_all_shapes(result, expected):
    assert _extract_broom_counts(result) == expected


# ==========================================================================
# Seam real: _perform_clear_completed — o evento §9 dispara EXATAMENTE UMA VEZ
# nos 3 caminhos. Regressao direta do achado Codex BLOCK (seam 6).
# ==========================================================================
class _FakeRepo:
    """Repo minimo para exercitar o seam ``_perform_clear_completed``."""

    def __init__(self, *, raises: Exception | None = None, result=None):
        self._raises = raises
        self._result = result
        self.db_path = "/tmp/fake.db"
        self.calls = 0

    def hide_all_done(self):
        self.calls += 1
        if self._raises is not None:
            raise self._raises
        return self._result


def test_seam_success_emits_event_once_and_runs_on_success(caplog):
    """Caminho de sucesso: evento uma vez (outcome=ok) + on_success disparado."""
    repo = _FakeRepo(
        result=_StructuredResult(affected_count=2, excluded_permanente_count=1)
    )
    success_calls: list[int] = []

    with caplog.at_level(logging.INFO, logger="task_manager_desktop.app"):
        _perform_clear_completed(repo, None, lambda: success_calls.append(1))

    record = _find_event_record(caplog)  # _find_event_record exige exatamente 1
    assert record.outcome == "ok"
    assert not hasattr(record, "error")
    assert record.affected_count == 2
    assert record.excluded_permanente_count == 1
    assert success_calls == [1]


def test_seam_success_zero_affected_skips_on_success(caplog):
    """Sucesso com 0 afetadas: evento dispara, mas on_success NAO roda."""
    repo = _FakeRepo(
        result=_StructuredResult(affected_count=0, excluded_permanente_count=3)
    )
    success_calls: list[int] = []

    with caplog.at_level(logging.INFO, logger="task_manager_desktop.app"):
        _perform_clear_completed(repo, None, lambda: success_calls.append(1))

    record = _find_event_record(caplog)
    assert record.outcome == "ok"
    assert record.affected_count == 0
    assert success_calls == []  # 0 afetadas => sem refresh de UI


@pytest.mark.parametrize(
    "exc_cls", [sqlite3.OperationalError, sqlite3.IntegrityError]
)
def test_seam_caught_db_error_emits_event_once_and_no_reraise(caplog, exc_cls):
    """Erro de DB tratado: evento uma vez (outcome=error), dialog mostrado,
    on_success NAO roda, e a excecao NAO propaga (e tratada)."""
    exc = exc_cls("database is locked")
    repo = _FakeRepo(raises=exc)
    success_calls: list[int] = []

    with caplog.at_level(logging.INFO, logger="task_manager_desktop.app"):
        with patch("task_manager_desktop.app.ErrorDialog") as mock_dlg:
            # NAO deve levantar — erro de DB e capturado e tratado.
            _perform_clear_completed(repo, None, lambda: success_calls.append(1))

    record = _find_event_record(caplog)  # exatamente 1
    assert record.outcome == "error"
    assert record.error == repr(exc)
    assert record.affected_count == 0
    assert success_calls == []
    mock_dlg.show_io_error.assert_called_once()


def test_seam_unexpected_exception_emits_event_before_propagating(caplog):
    """Excecao inesperada: o evento §9 e emitido no ``finally`` ANTES de a
    excecao propagar — Zero Silencio mesmo num crash nao previsto."""
    exc = RuntimeError("kaboom inesperado")
    repo = _FakeRepo(raises=exc)
    success_calls: list[int] = []

    with caplog.at_level(logging.INFO, logger="task_manager_desktop.app"):
        with pytest.raises(RuntimeError, match="kaboom inesperado"):
            _perform_clear_completed(repo, None, lambda: success_calls.append(1))

    # O finally rodou antes da propagacao => evento presente apesar do raise.
    record = _find_event_record(caplog)  # exatamente 1
    assert record.outcome == "error"
    assert record.error == repr(exc)
    assert success_calls == []
