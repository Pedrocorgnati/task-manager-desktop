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

## Plataformas suportadas

- Ubuntu 22.04 LTS (Jammy Jellyfish) — testado oficialmente
- Ubuntu 24.04 LTS (Noble Numbat) — testado oficialmente

Outras distros Linux com Qt 6.4+ e Python 3.10+ devem funcionar, mas nao sao testadas oficialmente.
Windows e macOS nao sao suportados no MVP.

---

## Requisitos

- Python 3.10+
- Ubuntu 22.04 LTS ou 24.04 LTS
- `xdg-utils` (pacote do SO para `xdg-open`)

Nota: PySide6 instala via pip e nao requer build-deps adicionais no Ubuntu.

---

## Instalacao

```bash
git clone git@github.com:Pedromurta/task-manager-desktop.git
cd task-manager-desktop
python3 -m venv .venv
.venv/bin/pip install -e .
```

Na primeira execucao com `task-manager` (ou `.venv/bin/task-manager`), o app:
1. Cria o diretorio de dados `~/.local/share/task-manager-desktop/` com permissoes `0700`
2. Instala o icone em `~/.local/share/icons/task-manager-desktop.svg`
3. Cria o atalho `~/.local/share/applications/task-manager-desktop.desktop`

Apos a primeira execucao, o app aparece no menu de aplicativos do GNOME com o icone correto.

**Instalacao manual do .desktop (alternativa global):**

```bash
# Copia para diretorio do sistema (requer sudo)
sudo cp ~/.local/share/applications/task-manager-desktop.desktop /usr/share/applications/
# Atualiza o banco de dados de menus
sudo update-desktop-database /usr/share/applications/
```

**Validacao do .desktop:**

```bash
desktop-file-validate ~/.local/share/applications/task-manager-desktop.desktop
# exit 0 esperado
```

---

## Bootstrap (copiar e colar)

```bash
git clone git@github.com:Pedromurta/task-manager-desktop.git
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

## Imagens em notas

O viewer de Markdown suporta imagens locais. Para referenciar uma imagem em uma nota:

1. Copie o arquivo para `~/.local/share/task-manager-desktop/notes-assets/`
2. Na nota, use `![descricao](nome-do-arquivo.png)`

Exemplo:

```markdown
![diagrama](fluxo.png)
```

Imagens ausentes renderizam o placeholder padrao do Qt (sem crash). Imagens externas (HTTP/HTTPS) nao sao carregadas automaticamente por seguranca.

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

## Undo e recuperação de tasks

O app oferece dois mecanismos para desfazer exclusões:

### Soft-delete (Lixeira)

Ao clicar **"Limpar concluídas"** no header, todas as tasks com status `done` visíveis são **ocultas** (não deletadas) e movidas para a Lixeira. Essas tasks ficam retidas por **30 dias** antes da remoção definitiva:

- **Visualizar:** Ícone "Lixeira" no header abre um dialog listando tasks ocultas nos últimos 30 dias
- **Restaurar:** Clique em "Restaurar" para trazer a task de volta (mantém o status original `done`)
- **Remoção automática:** Após 30 dias, a task é purgada automaticamente ao abrir o app

### Hard-delete (permanente)

Clique no **menu de três pontos** (⋮) em qualquer card de task → "Deletar" para remover permanentemente SEM passar pela Lixeira:

- **Irreversível:** Hard-delete não pode ser desfeito via Lixeira
- **Imediato:** Task desaparece do banco de dados no mesmo instante

### Recomendação

Para tarefas importantes, **use soft-delete** ("Limpar concluídas") e deixe na Lixeira até ter certeza de que não será necessário recuperá-las. Reserve hard-delete apenas para duplicatas óbvias ou erros de entrada.

**Backup manual (recomendado):**

```bash
cp ~/.local/share/task-manager-desktop/tasks.db \
   ~/backup/tasks.db.$(date +%Y%m%d)
```

A Lixeira é local e não tem redundância automática — backups periódicos são a única proteção contra perda de dados.

---

## Migracao manual de tarefas anteriores

Se voce vem de Todoist, Things, Notion ou outro gerenciador, **nao ha importador automatico no MVP**. A migracao eh manual e deliberada — abaixo, o fluxo recomendado.

### Fluxo recomendado

1. **Exportar a lista** da ferramenta de origem (CSV, OPML, Markdown — o que estiver disponivel).
2. **Filtrar so o que esta ativo** — tarefas concluidas ficam no historico antigo; nao recrie.
3. **Criar tasks no app** uma a uma, via `Ctrl+N` ou botao `+` no header.
4. **Preencher os 4 campos** do dialog: titulo, tipo (agent/human), projeto (opcional — vazio vira `outros`), dependencias (opcional — IDs separados por virgula).

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

Copyright (C) 2026 Pedro Murta
