# Python Dependencies Tasks — task-manager-desktop
Data: 2026-05-18

## Alto
(nenhum)

## Médio

### DEP-001 — Sem lock file reproducível
- **Arquivo:** `requirements.txt:4`
- **Problema:** `PySide6>=6.4` sem pin superior. Builds diferentes podem ter versões distintas do PySide6.
- **Impacto:** Regressões silenciosas se PySide6 quebrar ABI em versão major.
- **Correção:** Usar `pip-compile` para gerar `requirements.lock` com hashes, OU documentar processo de upgrade controlado.
- **Prioridade:** Médio
- Status: [ ]

### DEP-002 — Sem auditoria de vulnerabilidades (`pip-audit`)
- **Arquivo:** `.github/workflows/` (ausente), `Makefile`
- **Problema:** Nenhuma automação verifica CVEs nas dependências.
- **Impacto:** PySide6 ou dependências transitivas podem ter vulnerabilidades não detectadas.
- **Correção:** Adicionar `pip-audit` ao Makefile (`make audit`) e, quando CI for criado (CICD-001), incluir no pipeline.
- **Prioridade:** Médio
- Status: [ ]

### DEP-003 — `PySide6>=6.4` sem upper bound
- **Arquivo:** `pyproject.toml:13`, `requirements.txt:4`
- **Problema:** Sem limite superior. Uma versão major futura do PySide6 pode quebrar a API.
- **Correção:** `PySide6>=6.4,<7.0` — ou ao menos documentar a política de upgrade.
- **Prioridade:** Médio
- Status: [ ]

## Baixo

### DEP-004 — `requirements-dev.txt` mantido como legado sem data de remoção
- **Arquivo:** `requirements-dev.txt`
- **Problema:** Tem comentário `DEPRECATED (2026-05-18)` mas sem prazo de remoção.
- **Correção:** Remover arquivo e atualizar `Makefile` (coberto por CONF-003).
- **Prioridade:** Baixo
- Status: [ ]

### DEP-005 — Dev deps sem upper bound (`pytest>=7`, `mypy>=1`)
- **Arquivo:** `pyproject.toml:17-21`
- **Problema:** Open ranges para ferramentas de dev. Risco baixo mas pode causar surpresas.
- **Correção:** Adicionar `<9`, `<2` respectivamente. Opcional para ferramentas de dev.
- **Prioridade:** Baixo
- Status: [ ]
