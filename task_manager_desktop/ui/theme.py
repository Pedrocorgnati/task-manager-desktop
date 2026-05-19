from __future__ import annotations

from pathlib import Path

WINDOW_DEF_W: int = 1400
WINDOW_DEF_H: int = 900
WINDOW_MIN_W: int = 900
WINDOW_MIN_H: int = 600

SPLITTER_SIZES: list[int] = [560, 840]
SPLITTER_RATIO: float = 0.4

FONT_FAMILY_BODY = "Ubuntu Sans, Noto Sans, DejaVu Sans, sans-serif"
FONT_FAMILY_MONO = "JetBrains Mono, Ubuntu Mono, Fira Code, monospace"

TOOLBAR_H: int = 48

TOAST_DURATION_MS: int = 4000
TOAST_FADE_IN_MS: int = 200
TOAST_FADE_OUT_MS: int = 400
TOAST_OFFSET: int = 24

PALETTE: dict[str, str] = {
    "BG_BASE": "#0D0E12",
    "BG_PANEL": "#14151B",
    "BG_CARD": "#24262D",
    "BORDER_STRONG": "#3F3F46",
    "TEXT_PRIMARY": "#F8FAFC",
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
