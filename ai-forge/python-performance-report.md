# Python Performance Report — task-manager-desktop
Data: 2026-05-18 | Status: OK

## Resumo

| Área | Status |
|------|--------|
| Índices SQLite | OK (4 índices: status, completed_at, hidden_at, projeto) |
| N+1 queries | WARN (2 queries por status change — aceitável) |
| Memory usage | OK (all-tasks in-memory aceitável até ~5000) |
| PROPAGATION_THRESHOLD | OK (limita UI updates em lote) |
| VACUUM | OK (após bulk delete) |
| Benchmark tests | OK (@pytest.mark.perf) |

**Issues:** 2 (PERF-001 Médio, PERF-002 Baixo — ambos aceitáveis para desktop)

## Próximos Passos
PERF-001 é micro-otimização de baixa prioridade. Resolver apenas se usuários reportarem lentidão.
