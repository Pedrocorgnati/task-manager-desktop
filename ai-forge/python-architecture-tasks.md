# Python Architecture Tasks — task-manager-desktop
Data: 2026-05-18

## Nota Geral
Arquitetura geral excelente: camadas claras (core → repositories → controllers → ui), Protocol-based DI em `controllers/_protocols.py`, composition root em `app.py`. Issues abaixo são pontuais e não indicam problema estrutural.

## Alto

### ARCH-001 — `CreateTaskController` acessa `self._repo._conn` (atributo privado)
- **Arquivo:** `task_manager_desktop/controllers/create_task_controller.py:55`
- **Trecho:** `conn = self._repo._conn`
- **Problema:** Viola encapsulamento do `TaskRepository`. O controller acessa infra interna do repo.
- **Impacto:** Quebra se `TaskRepository` mudar a implementação interna; impede mocks simples em testes.
- **Correção:** Expor método público `repo.get_raw_connection()` ou mover `generate_id` para receber apenas o repositório.
- Status: [ ]

## Médio

### ARCH-002 — `app.py` acessa `header._search.text()` (privado do widget)
- **Arquivo:** `task_manager_desktop/app.py:149`
- **Trecho:** `task_list.set_filters(header._search.text(), header.current_project())`
- **Problema:** `_search` é atributo interno de `HeaderBar`. Acoplamento frágil.
- **Correção:** Expor `header.search_text() -> str` como método público. Referência: `/python:api`.
- Status: [ ]

### ARCH-003 — `DeleteTaskController` acessa `_current_task_id` via `getattr` com fallback
- **Arquivo:** `task_manager_desktop/controllers/delete_task_controller.py:41`
- **Trecho:** `getattr(self._main_window, "_current_task_id", None)`
- **Problema:** `_current_task_id` é privado. `getattr` silencia o erro se o atributo for renomeado.
- **Correção:** Criar Protocol `MainWindowLike` com `current_task_id: str | None` e `reset_viewer_to_empty()`. Semelhante ao padrão já usado em `_protocols.py`.
- Status: [ ]

### ARCH-004 — `_ErrorHandlerAdapter` definido inline em `main()`
- **Arquivo:** `task_manager_desktop/app.py:94-100`
- **Problema:** Classe adaptadora de 7 linhas embutida na função de composição. Dificulta teste isolado.
- **Correção:** Mover para `task_manager_desktop/ui/adapters.py` ou `controllers/_protocols.py` como implementação concreta.
- Status: [ ]

## Baixo

### ARCH-005 — Inconsistência: `ChangeStatusController` não herda `QObject`; outros controllers sim
- **Arquivos:** `create_task_controller.py:19`, `delete_task_controller.py:13`, `edit_task_controller.py` (não lido)
- **Problema:** `ChangeStatusController` foi deliberadamente desacoplado de Qt (Protocol-based), enquanto os outros herdam `QObject`. Inconsistência não é erro, mas pode confundir.
- **Correção:** Documentar decisão de design no `_protocols.py` ou README de controllers. ARCH-003 inicia a migração.
- Status: [ ] — documentar
