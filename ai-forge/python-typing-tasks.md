# Python Typing Tasks — task-manager-desktop
Data: 2026-05-18

## Alto
(nenhum — núcleo do domínio bem tipado)

## Médio

### TYPING-001 — `create_task_controller._persist` sem type hint em `parent_widget`
- **Arquivo:** `task_manager_desktop/controllers/create_task_controller.py:49`
- **Trecho:** `def _persist(self, data: dict, parent_widget) -> bool:`
- **Problema:** `parent_widget` sem anotação. `data: dict` deveria ser `dict[str, Any]` ou TypedDict.
- **Correção:** `def _persist(self, data: dict[str, Any], parent_widget: QWidget | None) -> bool:`
- Status: [ ]

### TYPING-002 — `markdown_reader.py` propriedades com `# noqa: ANN201`
- **Arquivo:** `task_manager_desktop/ui/markdown_reader.py:56,60,65`
- **Problema:** Três `@property` sem return type, silenciados via `noqa`. Deveriam ter `-> QStackedWidget`, `-> MarkdownViewer`, `-> MarkdownEditor`.
- **Correção:** Adicionar return types e remover `noqa: ANN201`.
- Status: [ ]

### TYPING-003 — `TaskRepository.update(**fields)` sem tipo nos kwargs
- **Arquivo:** `task_manager_desktop/repositories/task_repository.py:57`
- **Trecho:** `def update(self, task_id: str, **fields) -> None:`
- **Problema:** `**fields` sem anotação. Mypy não valida os valores passados.
- **Correção:** `**fields: str | int | Status | TaskType | list[str] | None` ou criar TypedDict `TaskUpdateFields`.
- Status: [ ]

## Baixo

### TYPING-004 — `type: ignore[override]` em overrides de PySide6
- **Arquivos:** `main_window.py:80,88,132`, `task_list.py:62`, `task_card.py:252`, `dialogs/*.py`
- **Problema:** PySide6 não exporta stubs completos; `type: ignore[override]` é necessário. Aceitável.
- **Correção:** Documentar em `docs/typing.md` (se existir) como exceção conhecida. Não requer mudança no código.
- Status: [ ] — aceitar como tech-debt documentado

### TYPING-005 — mypy strict gradual para demais controllers
- **Referência:** CONF-001
- **Problema:** `create_task_controller`, `delete_task_controller`, `edit_task_controller` não têm override mypy strict.
- **Correção:** Adicionar `[[tool.mypy.overrides]]` para cada controller ao resolver TYPING-001.
- Status: [ ]
