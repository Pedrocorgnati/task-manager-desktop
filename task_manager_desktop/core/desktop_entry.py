from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

_ICON_NAME = "task-manager-desktop"
_DESKTOP_NAME = "task-manager-desktop"

ICON_PATH = Path.home() / ".local" / "share" / "icons" / f"{_ICON_NAME}.svg"
DESKTOP_PATH = Path.home() / ".local" / "share" / "applications" / f"{_DESKTOP_NAME}.desktop"


def _resolve_exec_cmd() -> str:
    found = shutil.which("task-manager")
    if found:
        return found
    return f"{sys.executable} -m task_manager_desktop"


def install_icon(svg: str) -> bool:
    """Grava SVG em ~/.local/share/icons/. Idempotente — retorna True se escreveu."""
    ICON_PATH.parent.mkdir(parents=True, mode=0o755, exist_ok=True)
    if ICON_PATH.exists() and ICON_PATH.read_text(encoding="utf-8") == svg:
        return False
    ICON_PATH.write_text(svg, encoding="utf-8")
    ICON_PATH.chmod(0o644)
    return True


def install_desktop_entry(exec_cmd: str) -> bool:
    """Grava .desktop em ~/.local/share/applications/. Idempotente — retorna True se escreveu."""
    content = (
        "[Desktop Entry]\n"
        "Name=Task Manager Desktop\n"
        f"Exec={exec_cmd}\n"
        f"Icon={_ICON_NAME}\n"
        "Type=Application\n"
        "Categories=Utility;Office;\n"
        "Terminal=false\n"
        "Comment=Gerenciador pessoal de tasks offline-first\n"
    )
    DESKTOP_PATH.parent.mkdir(parents=True, mode=0o755, exist_ok=True)
    if DESKTOP_PATH.exists() and DESKTOP_PATH.read_text(encoding="utf-8") == content:
        return False
    DESKTOP_PATH.write_text(content, encoding="utf-8")
    DESKTOP_PATH.chmod(0o644)
    return True


def ensure_desktop_integration() -> None:
    """Orquestra gravacao de icon + .desktop. Silencioso em re-execucoes. Nao aborta boot."""
    try:
        from task_manager_desktop.ui.icons import APP_ICON_SVG

        install_icon(APP_ICON_SVG)
    except OSError as exc:
        print(f"[desktop-entry] Nao foi possivel instalar icone: {exc}", file=sys.stderr)

    try:
        exec_cmd = _resolve_exec_cmd()
        install_desktop_entry(exec_cmd)
    except OSError as exc:
        print(f"[desktop-entry] Nao foi possivel instalar .desktop: {exc}", file=sys.stderr)

    # Notifica freedesktop para atualizar menus (best-effort, ignora falhas)
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        try:
            import subprocess

            subprocess.run(
                ["xdg-desktop-menu", "forceupdate"],
                check=False,
                capture_output=True,
                timeout=5,
            )
        except Exception:  # noqa: BLE001
            pass
