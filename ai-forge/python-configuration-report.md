# Python Configuration Report — task-manager-desktop
Data: 2026-05-18 | Status: WARN

## Resumo

| Categoria | Issues | Corrigidos |
|-----------|--------|------------|
| pyproject | 1 (classifiers, readme) | 1 |
| tool config (mypy) | 1 | 0 |
| pre-commit | 1 | 0 |
| Makefile/venv | 1 | 1 |
| lock file | 1 | 0 |

**Total Issues:** 5 | **Corrigidos:** 2 | **Pendentes:** 3

## Arquivos Inspecionados
- `pyproject.toml` (1709 bytes)
- `requirements.txt` (4 linhas)
- `requirements-dev.txt` (10 linhas — deprecated)
- `Makefile` (82 linhas)

## Correções Aplicadas
- `pyproject.toml`: adicionado `classifiers` (Python versions, license, OS, env Qt) e `PySide6>=6.4,<7.0` com upper bound
- `Makefile`: `venv`, `install`, `install-dev` migrados para `pip install -e .[dev]`; adicionado target `audit`

## Issues Pendentes
- CONF-001: mypy strict parcial — expandir zona estrita para demais controllers
- CONF-002: adicionar `.pre-commit-config.yaml` com ruff + mypy
- CONF-005: adicionar `pip-compile` ou lock file estratégia

## Próximos Passos
1. Resolver CICD-001 (GitHub Actions) — inclui lint/typecheck automático
2. Expandir zona mypy strict após resolver TYPING-001..003
3. Avaliar `.pre-commit-config.yaml` para equipe
