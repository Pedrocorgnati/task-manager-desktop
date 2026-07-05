from __future__ import annotations

from task_manager_desktop.ui.theme import PALETTE as _P

APP_ICON_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <defs>
    <linearGradient id="bg" x1="18" y1="12" x2="112" y2="120" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#2A1A10"/>
      <stop offset="0.45" stop-color="#111217"/>
      <stop offset="1" stop-color="#07080B"/>
    </linearGradient>
    <linearGradient id="ring" x1="22" y1="22" x2="106" y2="106" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#F97316"/>
      <stop offset="0.45" stop-color="#FBBF24"/>
      <stop offset="1" stop-color="#E95420"/>
    </linearGradient>
    <linearGradient id="node" x1="34" y1="28" x2="92" y2="96" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#FFE08A"/>
      <stop offset="1" stop-color="#F97316"/>
    </linearGradient>
  </defs>

  <rect x="8" y="8" width="112" height="112" rx="28" fill="url(#bg)"/>
  <rect x="9" y="9" width="110" height="110" rx="27" fill="none" stroke="#3B2A16" stroke-width="2"/>

  <circle cx="64" cy="64" r="38" fill="none" stroke="#2B1D12" stroke-width="18"/>
  <path d="M35 39a39 39 0 0 1 52-5" fill="none" stroke="url(#ring)" stroke-width="13" stroke-linecap="round"/>
  <path d="M99 58a39 39 0 0 1-23 39" fill="none" stroke="url(#ring)" stroke-width="13" stroke-linecap="round"/>
  <path d="M53 101A39 39 0 0 1 28 55" fill="none" stroke="url(#ring)" stroke-width="13" stroke-linecap="round"/>

  <circle cx="35" cy="39" r="12" fill="#111217" stroke="url(#node)" stroke-width="7"/>
  <circle cx="99" cy="58" r="12" fill="#111217" stroke="url(#node)" stroke-width="7"/>
  <circle cx="53" cy="101" r="12" fill="#111217" stroke="url(#node)" stroke-width="7"/>

  <rect x="45" y="42" width="38" height="44" rx="11" fill="#F8FAFC"/>
  <rect x="53" y="52" width="22" height="4" rx="2" fill="#18181B"/>
  <rect x="53" y="62" width="22" height="4" rx="2" fill="#18181B"/>
  <path d="M52 75l8 8 17-20" fill="none" stroke="#16A34A" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

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
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<path d="M8 8.25h8l-.55 9.3A2.7 2.7 0 0 1 12.76 20h-1.52a2.7 2.7 0 0 1-2.69-2.45L8 8.25Z" '
    'fill="#F8FAFC" fill-opacity="0.14" stroke="#F8FAFC" stroke-width="1.9" stroke-linejoin="round"/>'
    '<path d="M9.5 8.25V6.9A2.9 2.9 0 0 1 12.4 4h.2a2.9 2.9 0 0 1 2.9 2.9v1.35" '
    'stroke="#F8FAFC" stroke-width="1.9" stroke-linecap="round"/>'
    '<path d="M5.75 8.25h12.5" stroke="#F8FAFC" stroke-width="2.3" stroke-linecap="round"/>'
    '<path d="M10.6 11.6v4.9M13.4 11.6v4.9" stroke="#F8FAFC" stroke-width="1.55" stroke-linecap="round" opacity="0.92"/>'
    "</svg>"
)

CLOCK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<circle cx="12" cy="12" r="8.4" fill="#F8FAFC" fill-opacity="0.14" '
    'stroke="#F8FAFC" stroke-width="1.9"/>'
    '<path d="M12 7.2v5.1l3.5 2.1" stroke="#F8FAFC" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M7.2 3.9 4.8 6.2M16.8 3.9l2.4 2.3" '
    'stroke="#F8FAFC" stroke-width="1.8" stroke-linecap="round"/>'
    "</svg>"
)

# Icone 1:1 do botao "Em preparação": prancheta com linhas (estrategia sendo
# escrita). Tracos brancos para casar com os demais icones de acao do card.
STRATEGY_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<rect x="5" y="4.5" width="14" height="16" rx="2.2" '
    'fill="#F8FAFC" fill-opacity="0.14" stroke="#F8FAFC" stroke-width="1.8"/>'
    '<rect x="9" y="2.8" width="6" height="3.4" rx="1.1" '
    'fill="#F8FAFC" fill-opacity="0.22" stroke="#F8FAFC" stroke-width="1.6"/>'
    '<path d="M8.4 10.5h7.2M8.4 13.7h7.2M8.4 16.9h4.4" '
    'stroke="#F8FAFC" stroke-width="1.8" stroke-linecap="round"/>'
    "</svg>"
)

PENCIL_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    f'<path d="M4 16.8V20h3.2L18.7 8.5l-3.2-3.2L4 16.8Z" '
    f'fill="{_P["COLOR_PRIMARY"]}" opacity="0.22" stroke="{_P["COLOR_PRIMARY"]}" stroke-width="1.8" stroke-linejoin="round"/>'
    f'<path d="M14.4 6.4l3.2 3.2" stroke="{_P["COLOR_PRIMARY"]}" stroke-width="1.8" stroke-linecap="round"/>'
    f'<path d="M13.7 5.6l1.8-1.8a1.8 1.8 0 0 1 2.6 0l2.1 2.1a1.8 1.8 0 0 1 0 2.6l-1.8 1.8" '
    f'stroke="{_P["COLOR_PRIMARY"]}" stroke-width="1.8" stroke-linejoin="round"/>'
    "</svg>"
)

# Variante branca do lapis usada no botao de editar do card (combina com a
# lixeira ao lado). PENCIL_SVG segue amarelo no editor toolbar.
PENCIL_WHITE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<path d="M4 16.8V20h3.2L18.7 8.5l-3.2-3.2L4 16.8Z" '
    'fill="#F8FAFC" opacity="0.14" stroke="#F8FAFC" stroke-width="1.8" stroke-linejoin="round"/>'
    '<path d="M14.4 6.4l3.2 3.2" stroke="#F8FAFC" stroke-width="1.8" stroke-linecap="round"/>'
    '<path d="M13.7 5.6l1.8-1.8a1.8 1.8 0 0 1 2.6 0l2.1 2.1a1.8 1.8 0 0 1 0 2.6l-1.8 1.8" '
    'stroke="#F8FAFC" stroke-width="1.8" stroke-linejoin="round"/>'
    "</svg>"
)

# Seta de "play" usada no botao de colar workspace root do card (mesma
# identidade branca translucida do lapis/lixeira ao lado).
PLAY_ARROW_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<path d="M7 5l11 7-11 7V5Z" '
    'fill="#F8FAFC" opacity="0.16" stroke="#F8FAFC" stroke-width="1.8" '
    'stroke-linejoin="round"/>'
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

CLEAR_DONE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
    f' stroke="{_P["COLOR_SUCCESS"]}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="20 6 9 17 4 12"/>'
    '<polyline points="3 20 13 20"/>'
    "</svg>"
)

# Check usado para confirmar a criacao de uma subtask no modal de nova task.
CHECK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
    f' stroke="{_P["COLOR_SUCCESS"]}" stroke-width="2.6"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="20 6 9 17 4 12"/>'
    "</svg>"
)

# Estrela de favorito no card. Variante preenchida (favorito=True, dourada) e
# variante contorno (favorito=False, cinza). source.md secao 3.6 item 1.
_STAR_PATH = (
    "M12 2.6l2.9 5.9 6.5.95-4.7 4.58 1.1 6.47L12 17.97 6.2 21l1.1-6.47"
    "L2.6 9.95l6.5-.95L12 2.6Z"
)
STAR_FILLED_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"'
    ' fill="#FBBF24" stroke="#F59E0B" stroke-width="1.4" stroke-linejoin="round">'
    f'<path d="{_STAR_PATH}"/>'
    "</svg>"
)
STAR_OUTLINE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
    ' stroke="#A1A1AA" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
    f'<path d="{_STAR_PATH}"/>'
    "</svg>"
)

COIN_FILLED_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<circle cx="12" cy="12" r="8.3" fill="#FDE68A" stroke="#F59E0B" stroke-width="1.7"/>'
    '<path d="M9.3 9.1h5.2a1.9 1.9 0 0 1 0 3.8H10.2a1.9 1.9 0 0 0 0 3.8h4.9" '
    'stroke="#B45309" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
    '<path d="M12 7.6v8.8" stroke="#B45309" stroke-width="1.6" stroke-linecap="round"/>'
    "</svg>"
)

COIN_OUTLINE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
    ' stroke="#A1A1AA" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="8.2"/>'
    '<path d="M9.3 9.1h5.2a1.9 1.9 0 0 1 0 3.8H10.2a1.9 1.9 0 0 0 0 3.8h4.9"/>'
    '<path d="M12 7.6v8.8"/>'
    "</svg>"
)

# Bolinha simples de favorito no card — terceiro marcador de ranqueamento, na
# primeira posicao (antes da estrela e da moeda). Variante preenchida (favorito,
# azul) e contorno (nao favorito, cinza), espelhando STAR_*/COIN_*.
DOT_FILLED_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<circle cx="12" cy="12" r="6.4" fill="#60A5FA" stroke="#2563EB" stroke-width="1.7"/>'
    "</svg>"
)

DOT_OUTLINE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
    ' stroke="#A1A1AA" stroke-width="1.7">'
    '<circle cx="12" cy="12" r="6.4"/>'
    "</svg>"
)

BROOM_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <path d="M14.7 3.4 21 9.7" stroke="#FBBF24" stroke-width="2.2" stroke-linecap="round"/>
  <path d="M13.2 5 19.4 11.2 11.1 19.5a3.4 3.4 0 0 1-4.8 0l-1.8-1.8a1.5 1.5 0 0 1 0-2.1L13.2 5Z"
        fill="#F97316" fill-opacity="0.22" stroke="#F97316" stroke-width="1.8" stroke-linejoin="round"/>
  <path d="M4.2 17.2c2.1.3 3.8-.2 5.2-1.6M6.2 19.3c1.7-.1 3.2-.7 4.5-2"
        stroke="#FBBF24" stroke-width="1.7" stroke-linecap="round"/>
  <path d="M16 8.2 8.4 15.8" stroke="#FED7AA" stroke-width="1.7" stroke-linecap="round" opacity="0.9"/>
</svg>
"""

LAYOUT_STACK_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <rect x="13.2" y="3.2" width="7.6" height="17.6" rx="1.5"
        fill="#F8FAFC" fill-opacity="0.14" stroke="#D4D4D8" stroke-width="1.4"/>
  <rect x="3.2" y="15.2" width="8.8" height="5.6" rx="1.5"
        fill="#F8FAFC" fill-opacity="0.14" stroke="#D4D4D8" stroke-width="1.4"/>
  <path d="M4.2 12.3c.8-3.3 2.8-5.2 6-5.8" stroke="#D4D4D8" stroke-width="1.5" stroke-linecap="round"/>
  <path d="m10.5 4.7 2.7 1.9-2.7 1.9" stroke="#D4D4D8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

TOOLS_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <path d="M14.4 4.2a4.2 4.2 0 0 0 5.4 5.4l-4.1 4.1-2.6-2.6 1.3-1.3-1.8-1.8-7 7a1.8 1.8 0 1 0 2.6 2.6l7-7-1.8-1.8 1.3-1.3 2.6 2.6 4.1-4.1a4.2 4.2 0 0 0-5.4-5.4l2.1 2.1-2.4 2.4-2.1-2.1Z"
        fill="#F8FAFC" fill-opacity="0.14" stroke="#F8FAFC" stroke-width="1.5" stroke-linejoin="round"/>
</svg>
"""

# Icone do botao de documentos do header (atalhos para arquivos do SystemForge).
# Folha de papel com cabecalho dobrado e linhas de texto, tracos brancos para
# casar com TOOLS_SVG/LAYOUT_STACK_SVG ao lado.
DOCUMENT_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <path d="M6 3.2h7.2L19 9v10.6a1.6 1.6 0 0 1-1.6 1.6H6a1.6 1.6 0 0 1-1.6-1.6V4.8A1.6 1.6 0 0 1 6 3.2Z"
        fill="#F8FAFC" fill-opacity="0.14" stroke="#F8FAFC" stroke-width="1.7" stroke-linejoin="round"/>
  <path d="M13 3.4V9h5.6" stroke="#F8FAFC" stroke-width="1.7" stroke-linejoin="round"/>
  <path d="M8 12.6h8M8 15.6h8M8 18.6h5" stroke="#F8FAFC" stroke-width="1.6" stroke-linecap="round"/>
</svg>
"""

# Icone do botao de prompts do Lessie no header. Balao de conversa com linhas de
# texto e um brilho (sparkle) no canto, sinalizando prompts de IA. Tracos
# brancos para casar com DOCUMENT_SVG/TOOLS_SVG ao lado, mas com silhueta
# distinta (balao != folha) para nao colidir com o botao de documentos.
PROMPT_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <path d="M4.4 5.2h10.4a1.6 1.6 0 0 1 1.6 1.6v6a1.6 1.6 0 0 1-1.6 1.6H9.1l-3.8 3.1v-3.1h-.9a1.6 1.6 0 0 1-1.6-1.6v-6A1.6 1.6 0 0 1 4.4 5.2Z"
        fill="#F8FAFC" fill-opacity="0.14" stroke="#F8FAFC" stroke-width="1.7" stroke-linejoin="round"/>
  <path d="M6.6 8.6h7M6.6 11.2h4.4" stroke="#F8FAFC" stroke-width="1.5" stroke-linecap="round"/>
  <path d="M19 3.1l.66 1.63 1.64.66-1.64.66L19 8.28l-.66-1.63-1.64-.66 1.64-.66Z"
        fill="#F8FAFC" stroke="#F8FAFC" stroke-width="0.7" stroke-linejoin="round"/>
</svg>
"""

SEND_ARROW_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <path d="M4.1 11.7 20 4.5 12.8 20.4l-2.3-7.1-6.4-1.6Z"
        fill="#FFFFFF" stroke="#FFFFFF" stroke-width="1.7" stroke-linejoin="round"/>
  <path d="m10.7 13.1 4.4-4.3" stroke="#2563EB" stroke-width="1.7"
        stroke-linecap="round"/>
</svg>
"""

SUN_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <defs>
    <radialGradient id="sunGlow" cx="50%" cy="50%" r="55%">
      <stop offset="0" stop-color="#FEF3C7"/>
      <stop offset="0.55" stop-color="#FBBF24"/>
      <stop offset="1" stop-color="#F97316"/>
    </radialGradient>
  </defs>
  <g fill="none" stroke="#FBBF24" stroke-width="2" stroke-linecap="round">
    <path d="M12 2.5v2.1M12 19.4v2.1M2.5 12h2.1M19.4 12h2.1"/>
    <path d="M5.3 5.3l1.5 1.5M17.2 17.2l1.5 1.5M18.7 5.3l-1.5 1.5M6.8 17.2l-1.5 1.5"/>
  </g>
  <circle cx="12" cy="12" r="5.4" fill="url(#sunGlow)" stroke="#FED7AA" stroke-width="1.2"/>
</svg>
"""

MOON_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
  <defs>
    <linearGradient id="moonFill" x1="5" y1="3" x2="19" y2="21" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#E0F2FE"/>
      <stop offset="0.55" stop-color="#93C5FD"/>
      <stop offset="1" stop-color="#64748B"/>
    </linearGradient>
  </defs>
  <path d="M18.7 15.5A8.1 8.1 0 0 1 8.5 5.3 8.8 8.8 0 1 0 18.7 15.5Z"
        fill="url(#moonFill)" stroke="#BFDBFE" stroke-width="1.4" stroke-linejoin="round"/>
  <circle cx="15.8" cy="8" r="1" fill="#F8FAFC" opacity="0.9"/>
  <circle cx="18.2" cy="11" r="0.7" fill="#F8FAFC" opacity="0.75"/>
</svg>
"""


# Icones de tipo de task (substituem a badge textual AGENT/DEV/HUMAN no card).
ROBOT_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
 stroke="#3B82F6" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <rect x="4.5" y="8" width="15" height="11" rx="3.2"/>
  <line x1="12" y1="8" x2="12" y2="4.5"/>
  <circle cx="12" cy="3.4" r="1.5" fill="#3B82F6" stroke="none"/>
  <circle cx="9.2" cy="13" r="1.4" fill="#3B82F6" stroke="none"/>
  <circle cx="14.8" cy="13" r="1.4" fill="#3B82F6" stroke="none"/>
  <line x1="9.5" y1="16.3" x2="14.5" y2="16.3"/>
  <line x1="4.5" y1="11.5" x2="2.6" y2="11.5"/>
  <line x1="19.5" y1="11.5" x2="21.4" y2="11.5"/>
</svg>
"""

PROFILE_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
 stroke="#F8FAFC" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="12" cy="8.2" r="3.7"/>
  <path d="M5.5 19.4a6.5 6.5 0 0 1 13 0"/>
</svg>
"""

COMPUTER_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
 stroke="#18181B" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
  <rect x="3" y="4.8" width="18" height="12" rx="2"/>
  <line x1="8.5" y1="20" x2="15.5" y2="20"/>
  <line x1="12" y1="16.8" x2="12" y2="20"/>
</svg>
"""


# Mapa canonico tipo-de-task -> SVG do icone. Fonte unica consumida pelo card
# principal (TaskCard) e pelo card de subtask (_SubtaskRow), garantindo que o
# icone de tipo seja identico nos dois lugares.
def type_icon_svg(task_type) -> str:
    """Retorna o SVG do icone para o tipo de task/subtask informado.

    Aceita TaskType ou a string canonica ('agent'/'dev'/'human'). Importa
    TaskType de forma tardia para evitar acoplar icons.py ao modulo de modelos
    no import-time. Valores desconhecidos caem no icone de AGENT.
    """
    from task_manager_desktop.core.models import TaskType

    mapping = {
        TaskType.AGENT: ROBOT_SVG,
        TaskType.DEV: COMPUTER_SVG,
        TaskType.HUMAN: PROFILE_SVG,
    }
    if not isinstance(task_type, TaskType):
        try:
            task_type = TaskType(task_type)
        except ValueError:
            task_type = TaskType.AGENT
    return mapping.get(task_type, ROBOT_SVG)


def svg_to_icon(svg: str, size: int = 20, opacity: float = 1.0):
    from PySide6.QtGui import QIcon

    return QIcon(svg_to_pixmap(svg, size, opacity))


def svg_to_pixmap(svg: str, size: int = 20, opacity: float = 1.0):
    from PySide6.QtCore import QByteArray, QSize
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt_transparent())
    painter = QPainter(pixmap)
    # `opacity` < 1.0 esmaece o glifo sem recorrer a um QGraphicsEffect no
    # widget. Efeitos aninhados (card com drop-shadow + filho com opacity
    # effect) quebram a renderizacao do filho no Qt; baked-in alpha evita isso.
    if opacity < 1.0:
        painter.setOpacity(opacity)
    renderer.render(painter)
    painter.end()
    return pixmap


def Qt_transparent():
    from PySide6.QtCore import Qt

    return Qt.GlobalColor.transparent
