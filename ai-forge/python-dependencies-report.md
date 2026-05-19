# Python Dependencies Report — task-manager-desktop
Data: 2026-05-18 | Status: WARN

## Resumo

| Categoria | Status |
|-----------|--------|
| Fonte única (pyproject.toml) | OK |
| Lock file | AUSENTE |
| Ranges de versão | PARCIAL (PySide6 upper bound adicionado) |
| Separação dev/prod | OK |
| Auditoria de CVEs | AUSENTE |
| Virtualenv documentado | OK |
| CI usa lock file | N/A (sem CI) |

## Correções Aplicadas
- `pyproject.toml`: `PySide6>=6.4,<7.0` (upper bound adicionado)
- `Makefile`: adicionado target `make audit` (chama `pip-audit`)

## Issues Pendentes
- DEP-001: Sem `requirements.lock` gerado por pip-compile
- DEP-002: `pip-audit` não roda automaticamente (aguarda CICD-001)
- DEP-004: `requirements-dev.txt` pode ser removido após CICD-001 estabilizar

## Próximos Passos
1. Executar `pip-audit` manualmente: `make audit`
2. Considerar `pip-compile requirements.in` para gerar lock file reproducível
3. Remover `requirements-dev.txt` após CICD-001
