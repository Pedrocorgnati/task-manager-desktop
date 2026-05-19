# Python Error Handling Tasks — task-manager-desktop
Data: 2026-05-18

## Médio

### ERR-001 — `app.py:63` swallowa erro de cleanup silenciosamente com `pass`
- **Arquivo:** `task_manager_desktop/app.py:63`
- **Trecho:**
  ```python
  except Exception as exc:  # noqa: BLE001
      print(f"[cleanup] Falha nao critica: {exc}", file=sys.stderr)
  ```
- **Problema:** Erro de cleanup é logado apenas em `stderr` sem nível de logging. Em produção com stdout/stderr redirecionados, erro seria perdido.
- **Correção:** Substituir `print` por `logging.getLogger(__name__).warning(...)`.
- Status: [ ]

### ERR-002 — `markdown_pane.py` tem 5 blocos `except Exception: pass`
- **Arquivo:** `task_manager_desktop/ui/markdown_pane.py:197,218,225,235,247`
- **Problema:** Erros swallowados sem logging. Falhas de renderização de markdown ficam invisíveis.
- **Impacto:** Dificulta debugging de issues de renderização.
- **Correção:** Substituir `pass` por `_logger.debug("...", exc_info=True)` onde razoável.
- Status: [ ]

### ERR-003 — Ausência de configuração centralizada de logging
- **Arquivo:** projeto inteiro
- **Problema:** Apenas `ChangeStatusController` usa `logging.getLogger(__name__)`. Demais módulos usam `print` para stderr. Sem `basicConfig` ou `dictConfig` no bootstrap.
- **Impacto:** Logs inconsistentes; impossível filtrar por nível em produção.
- **Correção:** Adicionar `logging.basicConfig(level=logging.WARNING)` em `app.py` antes de inicializar Qt, ou criar `core/logging_setup.py`.
- Status: [ ]

## Baixo

### ERR-004 — `app.py` múltiplos `except Exception: pass` em callbacks de evento
- **Arquivo:** `task_manager_desktop/app.py:141,203,214,275`
- **Problema:** Callbacks de UI swallowam exceções genéricas. Risco baixo (são operações não-críticas: filtro de projeto, toast, reconcile).
- **Correção:** Usar `_logger.debug("...", exc_info=True)` para pelo menos deixar rastro em modo debug.
- Status: [ ]
