# Python Error Handling Report — task-manager-desktop
Data: 2026-05-18 | Status: WARN

## Resumo

| Área | Status |
|------|--------|
| Logging estruturado | PARCIAL (só ChangeStatusController) |
| Exceções específicas | OK (maioria usa exceções específicas) |
| Bare except | 0 ocorrências |
| Exception swallow (pass) | WARN — 9 ocorrências com noqa:BLE001 |
| Configuração de logging | AUSENTE |
| Retry com backoff | N/A (SQLite local, sem retries necessários) |

**Issues:** 4 (ERR-001 Médio, ERR-002 Médio, ERR-003 Médio, ERR-004 Baixo)

## Pontos Fortes
- `ChangeStatusController` com `logging.getLogger(__name__)` e `extra={}` estruturado
- `TaskNotFoundError` como exceção de domínio específica
- `cleanup.py` re-raise após print (visível no stderr)
- `ErrorDialog` para erros de I/O exibidos ao usuário

## Issues Pendentes
- ERR-001: substituir `print` por logging em app.py
- ERR-002: adicionar `_logger.debug` em markdown_pane.py
- ERR-003: configurar `logging.basicConfig` no bootstrap de app

## Próximos Passos
1. Criar `logging.basicConfig(level=logging.WARNING)` em `app.py` antes de Qt init
2. Propagar `logging.getLogger(__name__)` para demais módulos com operações críticas
