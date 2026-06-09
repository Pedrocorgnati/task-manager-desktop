# Instalação do Task Manager Desktop no Ubuntu

## ⚡ Instalação Rápida (Automática)

### Opção 1: Script de Instalação

```bash
cd ai-forge/task-manager-desktop
./install-desktop.sh
```

Este script irá:
- ✓ Criar ícone em `~/.local/share/icons/`
- ✓ Criar arquivo .desktop em `~/.local/share/applications/`
- ✓ Atualizar o cache de ícones e menus
- ✓ Registrar o app no sistema

**Pronto!** O app agora aparecerá no menu de aplicativos.

### Opção 2: Instalação Manual

Se preferir fazer passo a passo:

```bash
# 1. Criar diretórios
mkdir -p ~/.local/share/icons
mkdir -p ~/.local/share/applications

# 2. Copiar ícone
cp task_manager_desktop/ui/icons/app-icon.svg ~/.local/share/icons/task-manager-desktop.svg

# 3. Criar arquivo .desktop
cat > ~/.local/share/applications/task-manager-desktop.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Task Manager Desktop
GenericName=Task Manager
Comment=Gerenciador pessoal de tasks offline-first
Exec=python3 -m task_manager_desktop
Icon=task-manager-desktop
Terminal=false
Categories=Utility;Office;ProjectManagement;
Keywords=task;todo;manager;planner;productivity;
StartupNotify=true
EOF

# 4. Tornar executável
chmod 644 ~/.local/share/applications/task-manager-desktop.desktop

# 5. Atualizar cache
gtk-update-icon-cache ~/.local/share/icons
xdg-desktop-menu forceupdate
```

## 📌 Adicionar à Barra de Favoritos

### GNOME (Ubuntu padrão)

1. **Abra o aplicativo:**
   - Pressione a tecla Super (Windows)
   - Digite "Task Manager"
   - Clique no ícone

2. **Fixar na barra:**
   - Clique com botão **direito** na janela do app
   - Selecione "**Adicionar aos Favoritos**" ou "**Pin**"
   - Ou arraste o ícone do Menu de Aplicativos para a barra

3. **Verificar:**
   - O ícone deve aparecer na barra lateral esquerda

### KDE Plasma

1. **Abra o aplicativo** do Menu de Aplicativos
2. **Clique com botão direito** na janela
3. Selecione "**Adicionar ao Painel**"

### XFCE

1. **Abra o aplicativo** do Menu de Aplicativos
2. **Clique com botão direito** no ícone da barra de tarefas
3. Selecione "**Fixar na Barra de Tarefas**"

## 🚀 Executar Aplicativo

### Pelo Menu de Aplicativos
- Pressione tecla **Super** (Windows)
- Digite "**Task Manager**"
- Clique no resultado

### Via Terminal
```bash
# Se instalado globalmente
task-manager

# Ou via Python
python3 -m task_manager_desktop

# Ou diretamente do repositório
cd ai-forge/task-manager-desktop
python3 -m task_manager_desktop
```

### Criar Atalho de Teclado (Opcional)

Para iniciar com Ctrl+Alt+T (customize conforme preferir):

**GNOME:**
1. Abra "Configurações" → "Teclado"
2. Vá para "Atalhos Personalizados"
3. Clique em "+"
4. Nome: "Task Manager"
5. Comando: `python3 -m task_manager_desktop`
6. Pressione a combinação de teclas desejada

## 🔍 Verificar Instalação

```bash
# Verificar se .desktop foi criado
ls -la ~/.local/share/applications/task-manager-desktop.desktop

# Verificar se ícone foi instalado
ls -la ~/.local/share/icons/task-manager-desktop.svg

# Testar arquivo .desktop
desktop-file-validate ~/.local/share/applications/task-manager-desktop.desktop
```

## 🛠️ Solução de Problemas

### "Aplicativo não aparece no Menu"

**Causa:** Cache não foi atualizado

**Solução:**
```bash
# Atualizar cache
gtk-update-icon-cache ~/.local/share/icons
xdg-desktop-menu forceupdate

# Reiniciar a sessão (Alt+F2, digite 'r', Enter)
# Ou logout/login
```

### "Ícone não aparece"

**Verificar:**
```bash
# Conferir se arquivo SVG é válido
file ~/.local/share/icons/task-manager-desktop.svg

# Deve retorger algo como:
# ...SVG Scalable Vector Graphics image
```

### "Aplicativo não inicia do menu"

**Debug:**
```bash
# Testar arquivo .desktop manualmente
dbus-launch gtk-launch task-manager-desktop.desktop

# Ou verificar erros
python3 -m task_manager_desktop
```

### "Desinstalar"

```bash
# Remover arquivo .desktop
rm ~/.local/share/applications/task-manager-desktop.desktop

# Remover ícone
rm ~/.local/share/icons/task-manager-desktop.svg

# Limpar cache
gtk-update-icon-cache ~/.local/share/icons
xdg-desktop-menu forceupdate
```

## 📝 Estrutura de Arquivos

Após instalação bem-sucedida:

```
~/.local/
├── share/
│   ├── applications/
│   │   └── task-manager-desktop.desktop
│   └── icons/
│       └── task-manager-desktop.svg
└── ... (diretórios de dados do app)
```

## 🔐 Permissões

Os arquivos são instalados com permissões:
- `.desktop`: `644` (rw-r--r--)
- `.svg`: `644` (rw-r--r--)

Se precisar alterar manualmente:
```bash
chmod 644 ~/.local/share/applications/task-manager-desktop.desktop
chmod 644 ~/.local/share/icons/task-manager-desktop.svg
```

## 🌍 Ambientes Suportados

- ✅ **GNOME** (Ubuntu 20.04+, 22.04, 24.04)
- ✅ **KDE Plasma** (Kubuntu)
- ✅ **XFCE** (Xubuntu)
- ✅ **MATE** (Linux Mint)
- ✅ **Cinnamon** (Linux Mint)
- ✅ Qualquer desktop Linux com freedesktop.org conformidade

## 📦 Dependências para Instalação

A instalação requer (geralmente já presentes):

```bash
# Verificar se estão instaladas
which gtk-update-icon-cache    # Geração de cache de ícones
which xdg-desktop-menu         # Atualização de menus
```

Se faltar, instale:
```bash
sudo apt install xdg-utils libgtk-3-0
```

## 🚀 Próximas Etapas

1. **Abra o app** e verifique se está funcionando
2. **Fixe na barra de favoritos** seguindo as instruções do seu desktop
3. **Configure atalhos de teclado** (opcional)
4. **Comece a usar!** 📋

---

**Suporte:**
- Reporte bugs em: https://github.com/Pedrocorgnati/task-manager-desktop/issues
- Documentação completa: Ver README.md

