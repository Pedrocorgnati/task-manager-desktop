"""Helpers de datetime canonicos para o task-manager-desktop.

Naive UTC e intencional: o schema SQLite armazena timestamps sem tzinfo para
manter compatibilidade com codigo legado. Migracao para aware UTC esta no
backlog (ver TASK-4/ST004 e _SCOPE-CONTRACT.json).
"""

from __future__ import annotations

from datetime import datetime, timezone


def utc_naive_now() -> datetime:
    """Retorna datetime UTC naive (tzinfo removido).

    Usar SEMPRE este helper ao gravar timestamps em colunas que ainda nao
    foram migradas para aware UTC. Comparacoes com aware datetimes lancarao
    TypeError — comportamento intencional para forcar consistencia.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
