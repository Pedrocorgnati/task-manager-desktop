from __future__ import annotations

from pathlib import Path

WINDOW_DEF_W: int = 1400
WINDOW_DEF_H: int = 900
WINDOW_MIN_W: int = 900
WINDOW_MIN_H: int = 600

SPLITTER_SIZES: list[int] = [560, 840]

FONT_FAMILY_BODY = "Inter, Segoe UI, system-ui, sans-serif"
FONT_FAMILY_MONO = "JetBrains Mono, Cascadia Code, Consolas, monospace"

TOAST_DURATION_MS: int = 4000
TOAST_FADE_IN_MS: int = 200
TOAST_FADE_OUT_MS: int = 400
TOAST_OFFSET: int = 24

PALETTE: dict[str, str] = {
    "BG_BASE": "#18181B",
    "BG_PANEL": "#1F1F23",
    "BG_CARD": "#27272A",
    "BORDER_STRONG": "#3F3F46",
    "TEXT_PRIMARY": "#FAFAFA",
    "TEXT_SECONDARY": "#A1A1AA",
    "TEXT_MUTED": "#71717A",
    "COLOR_SUCCESS": "#16A34A",
    "COLOR_WARNING": "#EAB308",
    "COLOR_DANGER": "#FB7185",
    "ACCENT_LIME": "#84CC16",
    "ACCENT_GOLD": "#D4AF37",
    "COLOR_PRIMARY": "#FBBF24",
}

THEME_QSS_PATH: Path = Path(__file__).parent / "theme.qss"
