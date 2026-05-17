# Task Manager Desktop

Gerenciador pessoal de tasks offline-first com SQLite local, PySide6 e dark mode exclusivo.
Ubuntu-first, sem CI/CD, sem PyInstaller no MVP e sem sync com servicos externos.

---

## Visao Geral

Task Manager Desktop e um aplicativo pessoal de gestao de tasks com:

- Armazenamento 100% local em SQLite (sem nuvem, sem servidor)
- Interface dark mode exclusiva (sem alternancia de tema)
- Setorizacao automatica: Ativo / Aguardando / Concluido
- Suporte a dependencias entre tasks com deteccao de ciclos
- Lixeira soft-delete com retencao de 30 dias

Restricoes do MVP: sem CI/CD, sem PyInstaller, sem sync com servicos externos.

---

## Requisitos

- Python 3.10+
- Ubuntu 22.04 LTS ou 24.04 LTS
- `xdg-utils` (pacote do SO para `xdg-open`)

Nota: PySide6 instala via pip e nao requer build-deps adicionais no Ubuntu.

---

## Bootstrap (copiar e colar)

```bash
git clone git@github.com:Pedrocorgnati/task-manager-desktop.git
cd task-manager-desktop
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m task_manager_desktop
```

Na primeira execucao o diretorio de dados e criado automaticamente com permissoes `0700`.

---

## Atalhos

| Atalho | Acao |
|--------|------|
| `Ctrl+N` | Abrir dialogo de nova task |
| `Ctrl+E` | Editar task selecionada |
| `Ctrl+D` | Marcar selecionada como done |
| `Ctrl+F` | Focar campo de busca |
| `Ctrl+Backspace` | Limpar busca atual |
| `Ctrl+S` | Salvar (no editor de notas) |
| `↑` / `↓`        | Navegar entre tasks (pulando separadores) |
| `Enter` | Abrir notas no viewer |
| `Delete` | Hard-delete sem confirmacao |
| `Esc` | Fechar dialogos / Lixeira / limpar foco de busca |

Sem selecao: no-op silencioso.

---

## Onde os Dados Ficam

- Banco de dados: `~/.local/share/task-manager-desktop/tasks.db`
- Diretorio criado automaticamente na primeira execucao com modo `0700`
- Preferencias de janela (geometry/window state): `~/.config/task-manager-desktop/`

---

## Desinstalacao Completa

```bash
# Dados do app (banco + diretorio XDG)
rm -rf ~/.local/share/task-manager-desktop/

# Atalho .desktop (apenas se foi criado manualmente)
rm -f ~/.local/share/applications/task-manager-desktop.desktop

# Preferencias QSettings (opcional)
rm -rf ~/.config/task-manager-desktop/

# Virtualenv local
rm -rf .venv/
```

Nao ha registry, syslog ou systemd-unit a limpar.

---

## Backup

Copiar periodicamente `~/.local/share/task-manager-desktop/tasks.db` para storage externo:

```bash
cp ~/.local/share/task-manager-desktop/tasks.db ~/backup/tasks-$(date +%Y%m%d).db
```

O arquivo `.db` e um banco SQLite3 padrao — abrivel com `sqlite3`, DB Browser for SQLite ou qualquer ferramenta compativel.

Hard-delete e permanente. A Lixeira (soft-delete) retem tasks por 30 dias antes da remocao definitiva.

Migracao de dados externos (Todoist/Things/Notion): subtasks importadas viram tasks independentes, e a task "pai" passa a depender delas.

---

## Migracao manual de tarefas anteriores

Se voce vem de Todoist, Things, Notion ou outro gerenciador, **nao ha importador automatico no MVP**. A migracao eh manual e deliberada — abaixo, o fluxo recomendado.

### Fluxo recomendado

1. **Exportar a lista** da ferramenta de origem (CSV, OPML, Markdown — o que estiver disponivel).
2. **Filtrar so o que esta ativo** — tarefas concluidas ficam no historico antigo; nao recrie.
3. **Criar tasks no app** uma a uma, via `Ctrl+N` ou botao `+` no header.
4. **Preencher os 4 campos** do dialog: titulo, tipo (online/offline), projeto (opcional — vazio vira `outros`), dependencias (opcional — IDs separados por virgula).

### Representando subtasks via dependencias

O app **nao tem subtasks aninhadas** (decisao deliberada — flat is better than nested). Para representar uma task composta como "Lancar v1.0" que tem subtarefas "Escrever release notes", "Tagear no git", "Publicar no GitHub":

1. Crie cada subtarefa como uma **task independente** (cada uma com seu proprio id curto).
2. Crie a task "pai" com `deps` apontando para os ids das subtarefas: `deps: a3f, b7c, d9e`.
3. A task "pai" entra automaticamente em **Bloqueadas** enquanto qualquer subtarefa estiver aberta; migra para **Fila** quando todas estiverem `done`.

### Limites de carga

O app suporta confortavelmente ate **~2000 tasks ativas** sem degradacao perceptivel no setor/busca/render. Acima disso, considere:

- **Arquivar manualmente** tasks antigas via lixeira (`Ctrl+Shift+L` no module-5).
- **Backup do banco antes de migrar volumes grandes**: copie `~/.local/share/task-manager-desktop/tasks.db` para um local seguro antes de comecar a migrar (assim voce pode reverter se algo der errado).

### Backup pre-migracao (recomendado)

```bash
cp ~/.local/share/task-manager-desktop/tasks.db ~/.local/share/task-manager-desktop/tasks.db.pre-migration-$(date +%Y%m%d)
```

Apos a migracao, valide visualmente que tudo esta correto e remova o backup quando se sentir confortavel.

---

## Licenca

Distribuido sob GNU General Public License v3.0. Veja [LICENSE](./LICENSE) para o texto completo.

Copyright (C) 2026 Pedro Corgnati
