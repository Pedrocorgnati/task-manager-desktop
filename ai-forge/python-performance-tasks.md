# Python Performance Tasks — task-manager-desktop
Data: 2026-05-18

## Médio

### PERF-001 — `_refresh_card` em `app.py` chama `repo.list_active()` + `compute_sector_change_propagation` + novo `_all_tasks_provider` em cada mudança de status
- **Arquivo:** `task_manager_desktop/app.py:102-116`
- **Problema:** Para cada mudança de status:
  1. `_refresh_card` chama `repo.list_active()` (1 query)
  2. `ChangeStatusController` chama `_all_tasks_provider()` = `repo.list_active()` (1 query) para propagação
  Total: 2 queries SQLite por ação simples.
- **Impacto:** Baixo para centenas de tasks. Pode ser perceptível com >1000 tasks.
- **Correção:** Unificar chamadas: `_refresh_card` poderia receber o snapshot `all_tasks` já carregado pelo controller, eliminando a segunda query.
- Status: [ ] — baixa prioridade, micro-otimização

## Baixo / Não-Aplicável

### PERF-002 — `list_active()` carrega todas as tasks em memória (sem paginação)
- **Arquivo:** `task_manager_desktop/repositories/task_repository.py:104`
- **Problema:** `SELECT * FROM tasks WHERE hidden_at IS NULL` sem LIMIT. Para app desktop com centenas de tasks, aceitável.
- **Impacto:** N/A para uso esperado. Referência: SCALE-001.
- Status: [ ] — aceitar, documentar limite recomendado (<5000 tasks)

## Pontos Positivos
- Índices SQLite: `idx_status`, `idx_completed_at`, `idx_hidden_at`, `idx_projeto` — todos presentes
- `PROPAGATION_THRESHOLD = 20` previne UI update storm em propagações grandes
- `VACUUM` após bulk delete em cleanup
- Benchmark tests com `@pytest.mark.perf` já existem
