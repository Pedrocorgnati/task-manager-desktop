# Python Hardcodes Tasks — task-manager-desktop
Data: 2026-05-18

## Alto

### HARD-001 — `app.py` define `WINDOW_DEF_W` e `WINDOW_DEF_H` duplicando `ui/theme.py`
- **Arquivo:** `task_manager_desktop/app.py:16-17`
- **Trecho:**
  ```python
  WINDOW_DEF_W = 1400
  WINDOW_DEF_H = 900
  ```
- **Problema:** `ui/theme.py` já define `WINDOW_DEF_W = 1400` e `WINDOW_DEF_H = 900` com type annotation. `main_window.py` importa de `theme.py`. As constantes em `app.py` são código morto — jamais usadas dentro de `app.py`.
- **Impacto:** Risco de divergência silenciosa se alguém mudar somente uma das cópias.
- **Correção:** Remover as duas linhas de `app.py`.
- **Prioridade:** Alto
- Status: [x] EXECUTADO

### HARD-002 — `app.py:main()` define `_PROP_THRESHOLD = 20` duplicando `core/constants.PROPAGATION_THRESHOLD`
- **Arquivo:** `task_manager_desktop/app.py:102`
- **Trecho:** `_PROP_THRESHOLD = 20`
- **Problema:** `core/constants.py` já tem `PROPAGATION_THRESHOLD = 20`. O `ChangeStatusController` usa a constante do `core`. O `_refresh_card` em `app.py` usa a cópia local. Valores iguais hoje, mas podem divergir.
- **Impacto:** Bug sutil se `PROPAGATION_THRESHOLD` for ajustado em `core/constants.py` mas não em `app.py`.
- **Correção:** Em `app.py`, importar `from task_manager_desktop.core.constants import PROPAGATION_THRESHOLD` e usar no `_refresh_card`.
- **Prioridade:** Alto
- Status: [x] EXECUTADO

## Baixo

### HARD-003 — Toast message em português hardcoded em `CreateTaskController`
- **Arquivo:** `task_manager_desktop/controllers/create_task_controller.py:85`
- **Trecho:** `"Ciclo de dependência detectado. Dependência mais antiga removida automaticamente."`
- **Problema:** Mensagem de UI hardcoded. Baixo impacto pois app é single-language (pt-BR).
- **Correção:** Centralizar mensagens em `core/messages.py` ou `core/constants.py` como `MSG_CYCLE_DETECTED`.
- **Prioridade:** Baixo
- Status: [ ]
