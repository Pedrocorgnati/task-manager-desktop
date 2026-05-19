# Python CI/CD Report — task-manager-desktop
Data: 2026-05-18 | Status: FAIL

## Resumo

| Área | Status |
|------|--------|
| GitHub Actions | AUSENTE |
| Makefile (lint/test/typecheck) | OK |
| Quality gates automáticos | AUSENTE |
| Auditoria de deps | PARCIAL (make audit adicionado) |
| Deploy automatizado | N/A (app desktop, distribuição manual) |

**Issues:** 3 (CICD-001 Alto, CICD-002..003 Médio/Baixo)

## Ferramentas Disponíveis (Makefile)
- `make lint` → `ruff check .`
- `make typecheck` → `mypy task_manager_desktop`
- `make test` → `pytest tests/ tests-tdd/`
- `make test-cov` → `pytest --cov`
- `make audit` → `pip-audit` (adicionado nesta sessão)
- `make check` → lint + typecheck

## Ação Prioritária
CICD-001: criar `.github/workflows/ci.yml` — template fornecido em `python-ci-cd-tasks.md`.
Nota importante: adicionar `QT_QPA_PLATFORM=offscreen` para pytest-qt em runners headless.
