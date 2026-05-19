# Python Packaging Tasks — task-manager-desktop
Data: 2026-05-18

## Baixo

### PKG-001 — `classifiers` e upper bound de PySide6 adicionados
- **Arquivo:** `pyproject.toml`
- **Status:** [x] EXECUTADO — adicionados `classifiers` e `PySide6>=6.4,<7.0`

### PKG-002 — Sem `CHANGELOG.md`
- **Arquivo:** raiz
- **Problema:** Sem registro de versões. Útil para distribuição futura.
- **Correção:** Criar `CHANGELOG.md` seguindo `Keep a Changelog`.
- Status: [ ] — baixa prioridade, projeto em v0.1.0

### PKG-003 — Entry point funcional e bem declarado
- **Arquivo:** `pyproject.toml:24-25`
- **Trecho:** `task-manager = "task_manager_desktop.__main__:main"`
- **Status:** OK — entry point correto.

### PKG-004 — `[tool.setuptools.packages.find]` correto
- **Arquivo:** `pyproject.toml:27-29`
- **Status:** OK — `where = ["."]` com `include = ["task_manager_desktop*"]`.

## Pontos Positivos
- `pyproject.toml` como fonte única (setuptools, pytest, ruff, mypy todos configurados aqui)
- Versão semântica presente (`0.1.0`)
- `requires-python = ">=3.10"` definido
