from __future__ import annotations

from task_manager_desktop.ui.theme import PALETTE as _P

APP_ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none">'
    f'<rect width="32" height="32" rx="6" fill="{_P["COLOR_PRIMARY"]}"/>'
    f'<rect x="8" y="10" width="16" height="2" rx="1" fill="{_P["BG_BASE"]}"/>'
    f'<rect x="8" y="15" width="12" height="2" rx="1" fill="{_P["BG_BASE"]}"/>'
    f'<rect x="8" y="20" width="14" height="2" rx="1" fill="{_P["BG_BASE"]}"/>'
    "</svg>"
)

WIFI_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
    f' stroke="{_P["TEXT_PRIMARY"]}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M5 12.55a11 11 0 0 1 14.08 0"/>'
    '<path d="M1.42 9a16 16 0 0 1 21.16 0"/>'
    '<path d="M8.53 16.11a6 6 0 0 1 6.95 0"/>'
    '<line x1="12" y1="20" x2="12.01" y2="20"/>'
    "</svg>"
)

WIFI_OFF_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
    f' stroke="{_P["TEXT_MUTED"]}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="1" y1="1" x2="23" y2="23"/>'
    '<path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"/>'
    '<path d="M5 12.55a11 11 0 0 1 5.17-2.39"/>'
    '<path d="M10.71 5.05A16 16 0 0 1 22.56 9"/>'
    '<path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"/>'
    '<path d="M8.53 16.11a6 6 0 0 1 6.95 0"/>'
    '<line x1="12" y1="20" x2="12.01" y2="20"/>'
    "</svg>"
)

TRASH_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
    f' stroke="{_P["COLOR_DANGER"]}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="3 6 5 6 21 6"/>'
    '<path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>'
    '<path d="M10 11v6"/>'
    '<path d="M14 11v6"/>'
    '<path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>'
    "</svg>"
)

PLUS_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
    f' stroke="{_P["COLOR_PRIMARY"]}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="12" y1="5" x2="12" y2="19"/>'
    '<line x1="5" y1="12" x2="19" y2="12"/>'
    "</svg>"
)
