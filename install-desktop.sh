#!/bin/bash
# Script de instalação do Task Manager Desktop no Ubuntu/Gnome

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Task Manager Desktop — Instalação para Ubuntu/Linux           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Detectar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Instale com:"
    echo "   sudo apt install python3"
    exit 1
fi

PYTHON=$(command -v python3)
echo "✓ Python encontrado: $PYTHON"

# Diretórios de instalação
ICON_DIR="$HOME/.local/share/icons"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_FILE="$ICON_DIR/task-manager-desktop.svg"
DESKTOP_FILE="$DESKTOP_DIR/task-manager-desktop.desktop"

# Criar diretórios
mkdir -p "$ICON_DIR" "$DESKTOP_DIR"
echo "✓ Diretórios criados"

# Obter ícone do código
ICON_SVG=$(python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from task_manager_desktop.ui.icons import APP_ICON_SVG
    print(APP_ICON_SVG)
except Exception as e:
    print(f'Erro ao carregar ícone: {e}', file=sys.stderr)
    sys.exit(1)
")

if [ $? -ne 0 ]; then
    echo "❌ Falha ao extrair ícone"
    exit 1
fi

# Instalar ícone
echo "$ICON_SVG" > "$ICON_FILE"
chmod 644 "$ICON_FILE"
echo "✓ Ícone instalado em: $ICON_FILE"

# Detectar comando de execução
if command -v task-manager &> /dev/null; then
    EXEC_CMD="task-manager"
    echo "✓ Executável encontrado: task-manager"
else
    EXEC_CMD="$PYTHON -m task_manager_desktop"
    echo "✓ Usando execução via Python: $EXEC_CMD"
fi

# Criar .desktop
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Task Manager Desktop
GenericName=Task Manager
Comment=Gerenciador pessoal de tasks offline-first
Exec=$EXEC_CMD
Icon=task-manager-desktop
Terminal=false
Categories=Utility;Office;ProjectManagement;
Keywords=task;todo;manager;planner;productivity;
StartupNotify=true
X-GNOME-Autostart-enabled=false
DBusActivatable=false
EOF

chmod 644 "$DESKTOP_FILE"
echo "✓ Arquivo .desktop instalado em: $DESKTOP_FILE"

# Atualizar banco de dados de ícones (se disponível)
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache "$ICON_DIR" 2>/dev/null || true
    echo "✓ Cache de ícones atualizado"
fi

# Notificar freedesktop (se disponível)
if command -v xdg-desktop-menu &> /dev/null; then
    xdg-desktop-menu forceupdate 2>/dev/null || true
    echo "✓ Menu do desktop atualizado"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ✓ INSTALAÇÃO CONCLUÍDA COM SUCESSO                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "O app agora está disponível em:"
echo "  • Menu de Aplicativos"
echo "  • Barra de Favoritos (fixar após abrir uma vez)"
echo ""
echo "Para iniciar, procure por 'Task Manager' no menu de aplicativos"
echo "ou execute:"
echo "  $EXEC_CMD"
echo ""
echo "Para adicionar à barra de favoritos:"
echo "  1. Abra o aplicativo pelo menu"
echo "  2. Clique com botão direito na janela do app"
echo "  3. Selecione 'Adicionar aos Favoritos' (ou similar)"
echo ""
