from __future__ import annotations

import subprocess
import sys

from PySide6.QtCore import QUrl


def _open_external_link(url: QUrl) -> bool:
    """Abre links HTTP/HTTPS no browser padrão via xdg-open. Ignora outros schemes."""
    scheme = url.scheme().lower()
    if scheme not in ("http", "https"):
        return False
    try:
        subprocess.Popen(
            ["xdg-open", url.toString()],
            start_new_session=True,
        )
        return True
    except FileNotFoundError:
        print(
            f"xdg-open não encontrado; link não aberto: {url.toString()}",
            file=sys.stderr,
        )
        return False
