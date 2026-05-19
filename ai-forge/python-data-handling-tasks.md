# Python Data Handling Tasks — task-manager-desktop
Data: 2026-05-18

## Médio

### DATA-001 — `Task.created_at` e `completed_at` armazenados como string ISO em vez de `datetime`
- **Arquivo:** `task_manager_desktop/core/models.py:65-66`
- **Trecho:** `created_at: str = ""` / `completed_at: str | None = None`
- **Problema:** Strings ISO não têm tipagem semântica; comparações e ordenações são string-based. TODO em `change_status_controller.py:82` documenta a dívida ("migrar schema para aware UTC").
- **Impacto:** Lógica de cleanup (`core/cleanup.py`) delega comparação de datas ao SQL — funciona, mas dificulta testes unitários de tempo.
- **Correção:** Migrar gradualmente para `datetime | None` com `datetime.fromisoformat()` em `_row_to_task`. Separar em sprint futuro (depende de migration DB).
- Status: [ ] — tech-debt documentado

### DATA-002 — `deps` armazenado como string CSV em vez de JSON array
- **Arquivo:** `task_manager_desktop/core/models.py:62` / `repositories/task_repository.py:48`
- **Trecho:** `deps=",".join(task.deps)` / `deps=parse_deps(row["deps"] or "")`
- **Problema:** Separador vírgula em IDs com vírgula causaria bug silencioso (porém IDs gerados por `id_gen` provavelmente não contêm vírgulas).
- **Impacto:** Baixo dado o gerador de IDs. Mas `parse_deps` pode ser enganado por whitespace em IDs vindos de outras fontes.
- **Correção:** Considerar JSON storage para `deps` em migration futura, ou adicionar validação em `parse_deps`.
- Status: [ ] — baixa prioridade

## Baixo

### DATA-003 — `TaskRepository.update(**fields)` open kwargs sem validação de tipos
- **Arquivo:** `task_manager_desktop/repositories/task_repository.py:57`
- **Problema:** `**fields` aceita qualquer chave/valor; o allowlist protege contra injeção de coluna, mas valores não são validados quanto ao tipo.
- **Correção:** Criar `TypedDict TaskUpdateFields` e mudar assinatura para `update(self, task_id: str, fields: TaskUpdateFields) -> None`. Referência: TYPING-003.
- Status: [ ]
