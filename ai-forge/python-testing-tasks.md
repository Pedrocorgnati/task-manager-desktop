# Python Testing Tasks — task-manager-desktop
Data: 2026-05-18

## Alto

### TEST-001 — Sem CI configurado (sem GitHub Actions)
- **Arquivo:** `.github/workflows/` (ausente)
- **Problema:** Testes não rodam automaticamente em push/PR. Regressões podem passar para main.
- **Impacto:** Alto — cobre todos os testes existentes.
- **Correção:** Ver CICD-001 (cria `.github/workflows/ci.yml`).
- Status: [ ] — depende de CICD-001

## Médio

### TEST-002 — Sem threshold de cobertura configurado
- **Arquivo:** `pyproject.toml:31-39` (tool.pytest.ini_options)
- **Problema:** `make test-cov` gera relatório mas não falha em cobertura baixa. Sem `--cov-fail-under`.
- **Impacto:** Cobertura pode cair sem alerta.
- **Correção:** Adicionar ao `pyproject.toml`:
  ```toml
  [tool.pytest.ini_options]
  addopts = "--cov-fail-under=70"
  ```
  Ou adicionar `--cov-fail-under=70` ao target `test-cov` do Makefile.
- Status: [ ]

### TEST-003 — Estrutura de testes fragmentada: `tests/`, `tests-tdd/`, sub-categorias inconsistentes
- **Arquivo:** raiz do projeto
- **Problema:** Testes divididos em `tests/acceptance`, `tests/contracts`, `tests/benchmark`, `tests/integration` e `tests-tdd/repositories`, `tests-tdd/ui`. Limites entre `tests/contracts` e `tests-tdd/repositories` sobrepostos.
- **Impacto:** Baixo, mas dificulta contribuidores novos a entender onde adicionar testes.
- **Correção:** Documentar no README ou `tests/README.md` as categorias e quando usar cada uma. Não mover arquivos sem necessidade.
- Status: [ ]

## Baixo

### TEST-004 — Fixtures de `conftest.py` não compartilhadas com `tests-tdd/`
- **Arquivo:** `tests/conftest.py`
- **Problema:** `conftest.py` está em `tests/`, não na raiz. Fixtures `in_memory_db` e `tmp_data_home` não estão disponíveis em `tests-tdd/` automaticamente.
- **Correção:** Mover `conftest.py` para raiz do projeto ou duplicar fixtures necessárias em `tests-tdd/conftest.py`.
- Status: [ ]
