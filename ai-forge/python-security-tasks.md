# Python Security Tasks — task-manager-desktop
Data: 2026-05-18

## Resumo
Postura de segurança FORTE para aplicação desktop. Todos os itens abaixo são LOW.

## Alto / Médio
(nenhum)

## Baixo

### SEC-001 — `XDG_DATA_HOME` de `os.environ` sem sanitização de path traversal
- **Arquivo:** `task_manager_desktop/core/bootstrap.py:14`
- **Trecho:** `xdg = os.environ.get("XDG_DATA_HOME", "")`
- **Problema:** Um valor malicioso em `XDG_DATA_HOME` (ex: `../../etc`) poderia redirecionar o banco. Risco real apenas se o usuário for atacado via variável de ambiente — cenário improvável em desktop local.
- **Impacto:** Teórico. App roda como o próprio usuário.
- **Correção:** Adicionar `Path(xdg).resolve()` e verificar que está dentro de `Path.home()` ou é caminho absoluto válido.
- Status: [ ] — baixa prioridade

### SEC-002 — Sem SBOM ou `pip-audit` automatizado
- **Problema:** Dependências não auditadas automaticamente para CVEs.
- **Correção:** `make audit` (adicionado em CONF-003) + incluir em CI quando CICD-001 for resolvido.
- Status: [ ] — depende CICD-001

## Pontos Positivos (não são issues)
- Parameterized queries em todo `TaskRepository` — sem SQL injection
- Allowlist de colunas em `update()` — sem column injection via kwargs
- `mode=0o700` no diretório de dados — permissões corretas
- Sem subprocess calls, sem pickle, sem network
- Sem secrets no código-fonte
