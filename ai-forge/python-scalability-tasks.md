# Python Scalability Tasks — task-manager-desktop
Data: 2026-05-18

## Status: N/A — Aplicação Desktop Single-User

Escalabilidade horizontal (filas, workers distribuídos, connection pooling) não se aplica.

## Baixo

### SCALE-001 — Sem limite documentado de tasks
- **Arquivo:** `task_manager_desktop/repositories/task_repository.py:104`
- **Problema:** `list_active()` sem LIMIT. Performance aceitável até ~5000 tasks em SQLite local; acima disso, UI pode ficar lenta.
- **Correção:** Documentar limite recomendado no README. Adicionar paginação ou lazy-load apenas se usuários reportarem lentidão com >5000 tasks.
- Status: [ ] — monitorar via feedback de usuário

## Pontos Positivos
- SQLite é single-file, zero configuração de servidor — correto para desktop
- `hide_all_done()` + `VACUUM` mantém o banco compacto
- `PROPAGATION_THRESHOLD` previne operações de UI em lote excessivas

**Issues críticos/altos: 0**
