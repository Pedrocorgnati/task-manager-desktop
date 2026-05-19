# Python CI/CD Tasks — task-manager-desktop
Data: 2026-05-18

## Alto

### CICD-001 — Sem pipeline de CI configurado (GitHub Actions ausente)
- **Arquivo:** `.github/workflows/` (ausente)
- **Problema:** Repositório sem qualquer automação de CI. Pushes e PRs não são validados automaticamente.
- **Impacto:** Regressões podem entrar em main sem detecção; `ruff`, `mypy` e testes não rodam automaticamente.
- **Correção:** Criar `.github/workflows/ci.yml` com jobs:
  1. `lint`: `ruff check .`
  2. `typecheck`: `mypy task_manager_desktop --ignore-missing-imports`
  3. `test`: `pytest tests/ tests-tdd/ --cov=task_manager_desktop --cov-fail-under=70`
  4. Opcional: `audit`: `pip-audit`
- **Template sugerido:**
  ```yaml
  name: CI
  on: [push, pull_request]
  jobs:
    quality:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: "3.10"
        - run: pip install -e .[dev]
        - run: ruff check .
        - run: mypy task_manager_desktop --ignore-missing-imports
        - run: pytest tests/ tests-tdd/ -x --cov=task_manager_desktop --cov-fail-under=70
          env:
            QT_QPA_PLATFORM: offscreen
  ```
- **Nota:** `pytest-qt` requer `QT_QPA_PLATFORM=offscreen` em headless CI.
- **Prioridade:** Alto
- Status: [ ]

## Médio

### CICD-002 — Makefile `test-cov` sem `--cov-fail-under`
- **Arquivo:** `Makefile:31`
- **Problema:** `make test-cov` gera relatório mas não falha se cobertura cair.
- **Correção:** Adicionar `--cov-fail-under=70` ao comando `test-cov`. Ver TEST-002.
- Status: [ ]

## Baixo

### CICD-003 — `scripts/bootstrap.sh` não verificado para CI
- **Arquivo:** `scripts/bootstrap.sh`
- **Problema:** Script de setup não foi inspecionado para problemas de portabilidade em runners Linux/macOS.
- **Status:** [ ] — inspecionar quando CICD-001 for implementado
