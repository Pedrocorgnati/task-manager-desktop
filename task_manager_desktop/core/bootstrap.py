from __future__ import annotations

import os
from pathlib import Path

from .db import get_connection, run_migrations

_APP_DATA_SUBDIR = "task-manager-desktop"
_DB_FILENAME = "tasks.db"
NOTES_ASSETS_DIRNAME = "notes-assets"


def _get_xdg_data_home() -> Path:
    """Resolve XDG_DATA_HOME ou ~/.local/share conforme especificacao XDG."""
    xdg = os.environ.get("XDG_DATA_HOME", "")
    if xdg:
        return Path(xdg)
    return Path.home() / ".local" / "share"


def _app_data_dir(data_home: Path | None = None) -> Path:
    base = data_home or _get_xdg_data_home()
    return base / _APP_DATA_SUBDIR


def notes_assets_path(data_home: Path | None = None) -> Path:
    """Retorna o path canonico do diretorio de assets para notas Markdown."""
    return _app_data_dir(data_home) / NOTES_ASSETS_DIRNAME


def ensure_data_dir_and_db(
    data_home: Path | None = None,
) -> Path:
    """
    Garante que o diretorio XDG, o tasks.db e o notes-assets existam.

    First-run: cria diretorio com mode=0o700 e executa schema v1.
    Runs subsequentes: abre banco existente sem alterar permissoes.

    Returns:
        Path absoluto do tasks.db.

    Raises:
        PermissionError: se o diretorio nao puder ser criado.
        OSError: para outros erros de filesystem.
    """
    base = data_home or _get_xdg_data_home()
    app_dir = base / _APP_DATA_SUBDIR
    db_path = app_dir / _DB_FILENAME

    if not app_dir.exists():
        # First-run: cria com permissoes restritas
        os.makedirs(str(app_dir), mode=0o700, exist_ok=False)
    # Runs subsequentes: NAO alterar permissoes do diretorio existente

    # Diretorio de assets para imagens em notas Markdown
    notes_assets_path(data_home).mkdir(mode=0o700, exist_ok=True)

    conn = get_connection(db_path)
    run_migrations(conn)

    return db_path.resolve()
