# Python Configuration Tasks — task-manager-desktop
Data: 2026-05-18

## Crítico
(nenhum)

## Alto
(nenhum)

## Médio

### CONF-001 — mypy `strict = false` em quase todos os módulos
- **Arquivo:** `pyproject.toml:51`
- **Tipo:** tool config
- **Problema:** Apenas `change_status_controller` e `_protocols` estão em zona estrita. Restante do código aceita funções sem type hints sem erro.
- **Impacto:** Erros de tipo latentes não detectados pelo CI.
- **Correção:** Migrar módulos gradualmente para `disallow_untyped_defs = true`. Ver TYPING-001..003. Referência: `/python:typing`
- **Prioridade:** Médio
- Status: [ ]

### CONF-002 — Sem `pre-commit` configurado
- **Arquivo:** raiz do projeto
- **Tipo:** tool config
- **Problema:** Nenhum `.pre-commit-config.yaml`. Desenvolvedores podem commitar sem ruff/mypy localmente.
- **Impacto:** Inconsistências de estilo e erros de tipo podem entrar no histórico.
- **Correção:** Criar `.pre-commit-config.yaml` com hooks: `ruff`, `ruff-format`, `mypy`.
- **Prioridade:** Médio
- Status: [ ]

### CONF-003 — Makefile `venv` target usa `requirements-dev.txt` deprecated
- **Arquivo:** `Makefile:51` e `Makefile:56-57`
- **Tipo:** tool config
- **Problema:** `make venv` e `make install-dev` referenciam `requirements-dev.txt` que tem comentário `DEPRECATED`. A fonte da verdade é `pyproject.toml[project.optional-dependencies.dev]`.
- **Impacto:** Novo desenvolvedor pode usar caminho errado.
- **Correção:** Atualizar `make venv` para `pip install -e .[dev]` e `make install-dev` para o mesmo.
- **Prioridade:** Médio
- Status: [x] EXECUTADO

## Baixo

### CONF-004 — `pyproject.toml` sem `classifiers` e sem campo `readme`
- **Arquivo:** `pyproject.toml:6-14`
- **Tipo:** pyproject
- **Problema:** Campos `classifiers` e `readme` ausentes. PyPI e ferramentas de empacotamento esperam esses metadados.
- **Impacto:** Publicação no PyPI incompleta (não crítico pois é app desktop interno).
- **Correção:** Adicionar `classifiers` e `readme = "README.md"`. Ver PKG-001.
- **Prioridade:** Baixo
- Status: [x] EXECUTADO

### CONF-005 — Sem lock file gerado (sem `poetry.lock`, `requirements.txt` não pinado)
- **Arquivo:** raiz do projeto
- **Tipo:** dependências
- **Problema:** `requirements.txt` tem `PySide6>=6.4` (sem pin). Sem `pip-compile` ou `poetry.lock`.
- **Impacto:** Builds não reproducíveis. Referência: DEP-001.
- **Correção:** Recomendação para `/python:dependencies`.
- **Prioridade:** Baixo (app desktop, deploy manual)
- Status: [ ]
