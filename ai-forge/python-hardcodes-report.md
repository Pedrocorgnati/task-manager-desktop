# Python Hardcodes Report — task-manager-desktop
Data: 2026-05-18 | Status: OK (após correções)

## Resumo

| Issue | Severidade | Status |
|-------|-----------|--------|
| `app.py` WINDOW_DEF_W/H duplicados | Alto | [x] REMOVIDO |
| `app.py` _PROP_THRESHOLD duplicado | Alto | [x] SUBSTITUÍDO por import |
| Toast message hardcoded | Baixo | Pendente |

## Correções Aplicadas

### HARD-001 — Removido código morto de `app.py`
Antes:
```python
WINDOW_DEF_W = 1400
WINDOW_DEF_H = 900
```
Depois: removidas as duas linhas. `main_window.py` já importava de `ui/theme.py`.

### HARD-002 — `_PROP_THRESHOLD` substituído por `PROPAGATION_THRESHOLD`
Antes:
```python
_PROP_THRESHOLD = 20
...
if 1 + len(propagated) >= _PROP_THRESHOLD:
```
Depois:
```python
from .core.constants import PROPAGATION_THRESHOLD
...
if 1 + len(propagated) >= PROPAGATION_THRESHOLD:
```
Agora há única fonte de verdade para o threshold.

## Issues Pendentes
- HARD-003: centralizar mensagens UI em `core/messages.py` (baixa prioridade)
