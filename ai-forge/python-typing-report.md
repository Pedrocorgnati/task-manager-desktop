# Python Typing Report — task-manager-desktop
Data: 2026-05-18 | Status: WARN

## Resumo

| Módulo | Type Hints | Strictness | Notes |
|--------|-----------|------------|-------|
| core/models.py | Completo | OK | dataclass bem tipado |
| core/sector.py | Completo | OK | |
| core/filters.py | Completo | OK | |
| core/bootstrap.py | Completo | OK | |
| core/cleanup.py | Completo | OK | |
| controllers/_protocols.py | Completo | Strict | Excelente |
| controllers/change_status_controller.py | Completo | Strict | Excelente |
| controllers/create_task_controller.py | Parcial | Não-strict | `parent_widget` sem tipo |
| controllers/delete_task_controller.py | Quase completo | Não-strict | |
| repositories/task_repository.py | Quase completo | Não-strict | `**fields` sem tipo |
| ui/markdown_reader.py | Parcial | — | 3 properties sem return type |
| ui/*.py (restante) | Variável | — | `type: ignore` PySide6 OK |

**type: ignore count:** ~8 (maioria justificada por PySide6 stubs)
**Issues:** 5 (TYPING-001..005)

## Correções Aplicadas
Nenhuma (mudanças de typing requerem maior revisão para não quebrar mypy overrides existentes)

## Próximos Passos
1. TYPING-001: Tipar `create_task_controller._persist`
2. TYPING-002: Adicionar return types nas properties de `markdown_reader.py`
3. TYPING-003: TypedDict para `TaskRepository.update(**fields)`
4. Expandir `[[tool.mypy.overrides]]` para demais controllers após TYPING-001
