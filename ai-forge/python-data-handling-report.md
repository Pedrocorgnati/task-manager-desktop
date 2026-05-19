# Python Data Handling Report — task-manager-desktop
Data: 2026-05-18 | Status: OK (dívidas técnicas documentadas)

## Resumo

| Área | Status |
|------|--------|
| Validação de input | OK (allowlist em update()) |
| Sanitização SQLite | OK (parameterized queries) |
| Serialização de dados | WARN (datas como string) |
| Modelos Pydantic/dataclasses | OK (dataclasses bem tipadas) |
| Deps CSV storage | WARN (funcional, mas fragil) |

**Issues:** 3 (DATA-001 Médio, DATA-002..003 Baixo)

## Pontos Fortes
- `TaskRepository` com allowlist de colunas e parameterized queries
- `_row_to_task` com fallbacks defensivos para NULL
- `normalize_projeto` previne projetos `None`/vazio
- `parse_deps` com strip de whitespace

## Issues Pendentes
- DATA-001: datas como ISO string — migrar para `datetime` quando schema migration for planejada
- DATA-002: deps como CSV — baixa prioridade (IDs gerados nunca têm vírgulas)
- DATA-003: TypedDict para `update(**fields)`

## Próximos Passos
DATA-001 e DATA-002 devem ser resolvidos juntos em uma migration DB, quando necessário.
