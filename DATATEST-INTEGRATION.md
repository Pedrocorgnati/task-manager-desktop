# DataTest Overlay Integration Guide

Este guia descreve como integrar o sistema DataTest (debug overlay) no task-manager-desktop, replicando exatamente a funcionalidade do workflow-app.

## Componentes

### 1. Debug Overlay Module
**Arquivo:** `task_manager_desktop/ui/debug_overlay.py`

Módulo responsável por exibir overlays vermelhos flutuantes com o `testid` (objectName) de cada widget.

**Funcionalidades:**
- Exibe labels flutuantes com o objectName de widgets
- Modos: "off", "all", "body", "buttons"
- Click-to-copy para clipboard
- Feedback visual (muda para verde ao copiar)
- Detecção automática de sobreposição de overlays

## Integração no Aplicativo

### Passo 1: Adicionar objectName aos widgets

Todos os widgets principais devem ter um `testid` (objectName em Qt):

```python
# Em task_manager_desktop/ui/main_window.py
self.central_widget.setProperty("testid", "main-content")
self.header_widget.setProperty("testid", "header")
self.task_list_widget.setProperty("testid", "task-list")
self.reader_panel.setProperty("testid", "reader-panel")

# Em task_manager_desktop/ui/task_list.py
self.list_widget.setProperty("testid", "task-list-container")
for sector_name, sector_widget in self.sectors.items():
    sector_widget.setProperty("testid", f"sector-{sector_name}")

# Em task_manager_desktop/ui/task_card.py
self.card_widget.setProperty("testid", f"task-card-{task_id}")
self.title_button.setProperty("testid", f"task-title-button-{task_id}")
self.status_dropdown.setProperty("testid", f"task-status-{task_id}")
```

### Passo 2: Instanciar DataTestOverlay na MainWindowShell

```python
# Em task_manager_desktop/ui/main_window.py

from .debug_overlay import DataTestOverlay

class MainWindowShell(QMainWindow):
    def __init__(self):
        super().__init__()
        # ... código existente ...
        
        # Inicializar DataTestOverlay após a janela estar completamente construída
        self._datatest_overlay = DataTestOverlay(self)
        self._datatest_mode = "off"
    
    def set_datatest_mode(self, mode: str) -> None:
        """Define o modo de exibição do overlay.
        
        Args:
            mode: "off", "all", "body", "buttons"
        """
        self._datatest_mode = mode
        self._datatest_overlay.set_mode(mode)
    
    def toggle_datatest(self) -> None:
        """Alterna entre modo off e all."""
        self._datatest_overlay.toggle()
        self._datatest_mode = "off" if self._datatest_overlay._overlay_mode == "off" else "all"
```

### Passo 3: Adicionar botão de controle (opcional)

Você pode adicionar um botão no header ou em uma barra de ferramentas para controlar o overlay:

```python
# Em task_manager_desktop/ui/header.py (ou novo arquivo para toolbar)

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt

class DebugToolbar(QWidget):
    def __init__(self, main_window: MainWindowShell):
        super().__init__()
        self.main_window = main_window
        
        # Criar botão DataTest
        self.btn_datatest = QPushButton("DataTest")
        self.btn_datatest.setFixedSize(68, 32)
        self.btn_datatest.setCheckable(True)
        self.btn_datatest.setToolTip("Exibir objectNames em todos os componentes")
        self.btn_datatest.setProperty("testid", "datatest-toggle-button")
        self.btn_datatest.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_datatest.setStyleSheet(
            "QPushButton { background-color: transparent; color: #A1A1AA;"
            "  border: 1px solid #52525B; border-radius: 6px;"
            "  font-size: 11px; font-weight: 600; padding: 0 6px; }"
            "QPushButton:hover { color: #FAFAFA; background-color: #3F3F46;"
            "  border-color: #71717A; }"
            "QPushButton:checked { background-color: #DC2626; color: #FAFAFA;"
            "  border-color: #DC2626; font-weight: 700; }"
        )
        
        # Conectar clique
        self.btn_datatest.clicked.connect(self._on_datatest_clicked)
        
        # Adicionar ao layout
        layout = QHBoxLayout(self)
        layout.addWidget(self.btn_datatest)
    
    def _on_datatest_clicked(self):
        """Handler do botão DataTest."""
        if self.btn_datatest.isChecked():
            self.main_window.set_datatest_mode("all")
        else:
            self.main_window.set_datatest_mode("off")
```

### Passo 4: Atalho de teclado (opcional)

Você pode adicionar um atalho global para ativar/desativar o overlay:

```python
# Em task_manager_desktop/ui/main_window.py ou em app.py

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QShortcut

# Adicionar atalho Ctrl+Shift+D para alternar DataTest
shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), window)
shortcut.activated.connect(window.toggle_datatest)
```

## Convenção de Naming para testid

Siga o padrão do workflow-app:

```
{regiao}-{componente}-{variante}

Exemplos:
- header-title
- header-menu-button
- sidebar-nav-item-tasks
- main-content
- task-list-container
- task-card-{id}
- task-title-button-{id}
- task-status-dropdown-{id}
- modal-confirm-delete
- modal-close-button
- form-task-title-input
- form-task-description-textarea
- footer-copyright
```

## Modos de Overlay

### "off" (padrão)
Overlays desligados. Nenhuma exibição visual.

### "all"
Exibe overlays para todos os widgets com `testid` definido.

### "body"
Exibe overlays para TODOS OS WIDGETS EXCETO botões (QAbstractButton).
Útil para debugar layout e containers.

### "buttons"
Exibe overlays APENAS para botões e widgets clicáveis.
Útil para debugar ações e interações.

## Exemplo de Uso Completo

```python
# Em app.py, após criar a janela principal

from task_manager_desktop.ui.main_window import MainWindowShell
from task_manager_desktop.ui.header import DebugToolbar

window = MainWindowShell()

# (... resto do setup existente ...)

# Adicionar toolbar de debug (opcional)
# debug_toolbar = DebugToolbar(window)
# Ou simplesmente adicionar atalho de teclado:

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QShortcut

QShortcut(QKeySequence("Ctrl+Shift+D"), window).activated.connect(window.toggle_datatest)

window.show()
```

## Comportamento Visual

1. **Estado Normal (overlay visível)**
   - Fundo vermelho escuro (DC2626)
   - Texto branco
   - Fonte pequena (10px) e negrita
   - Arredondado (border-radius: 3px)

2. **Feedback ao Clicar**
   - Fundo muda para verde (16A34A) por 600ms
   - Texto "Copiado!" aparece brevemente (opcional)
   - Volta ao estado normal após 600ms

3. **Posicionamento**
   - Levemente acima do widget (offset -14px vertical)
   - Detecta sobreposição e reposiciona automaticamente
   - Sempre visível acima de outros elementos (z-index alto)

## Checklist de Implementação

- [ ] Copiar `debug_overlay.py` para `task_manager_desktop/ui/`
- [ ] Adicionar `from .debug_overlay import DataTestOverlay` em `main_window.py`
- [ ] Instanciar `DataTestOverlay(self)` em `MainWindowShell.__init__()`
- [ ] Adicionar método `set_datatest_mode()` em `MainWindowShell`
- [ ] Adicionar método `toggle_datatest()` em `MainWindowShell`
- [ ] Adicionar `testid` property a widgets principais
- [ ] (Opcional) Criar botão visual ou atalho de teclado
- [ ] Testar modos "off", "all", "body", "buttons"
- [ ] Verificar click-to-copy funciona
- [ ] Verificar feedback visual ao copiar

## Referência: workflow-app

A implementação aqui é baseada em:
- `ai-forge/workflow-app/src/workflow_app/ui/debug_overlay.py`
- `ai-forge/workflow-app/src/workflow_app/main_window.py` (linhas 3019-3117)
- `ai-forge/workflow-app/src/workflow_app/metrics_bar/metrics_bar.py` (linhas 673-687)
