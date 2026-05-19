# Python Testing Report — task-manager-desktop
Data: 2026-05-18 | Status: WARN

## Resumo

| Área | Status |
|------|--------|
| Estrutura de testes | OK (acceptance, contracts, benchmark, integration, TDD) |
| pytest configurado | OK (pyproject.toml) |
| pytest-qt | OK (instalado no dev deps) |
| Coverage report | OK (make test-cov) |
| Coverage threshold | AUSENTE |
| CI automático | AUSENTE |
| Fixtures compartilhadas | PARCIAL (conftest em tests/, não na raiz) |

**Issues:** 4 (TEST-001 Alto, TEST-002..003 Médio, TEST-004 Baixo)

## Contagem de Testes (estimada por arquivos)
- `tests/acceptance/`: 2 arquivos
- `tests/contracts/`: 6 arquivos
- `tests/benchmark/`: 1 arquivo
- `tests-tdd/repositories/`: 1 arquivo
- `tests-tdd/ui/`: 2 arquivos

## Pontos Fortes
- `@pytest.mark.perf` com opt-in `--run-perf` — design correto para performance gates
- `@pytest.mark.acceptance` mapeado a ACs do documento de user stories
- Contract tests para UI, repository e controllers
- `in_memory_db` fixture para isolamento de SQLite

## Próximos Passos
1. TEST-001 + CICD-001: criar CI com `QT_QPA_PLATFORM=offscreen`
2. TEST-002: adicionar `--cov-fail-under=70` em `make test-cov`
3. TEST-004: mover `conftest.py` para raiz do projeto
