# DataTest Snippets — Código Pronto para Copiar/Colar

## Snippet 1: Modificar MainWindowShell para adicionar DataTestOverlay

**Arquivo:** `task_manager_desktop/ui/main_window.py`

Adicione estas linhas após a classe ser definida ou no `__init__`:

```python
# No início do arquivo, adicione o import:
from .debug_overlay import DataTestOverlay

# Na classe MainWindowShell.__init__(), adicione (após super().__init__()):
class MainWindowShell(QMainWindow):
    def __init__(self):
        super().__init__()
        # ... código existente ...
        
        # ─── DataTest Debug Overlay ───────────────────────────
        self._datatest_overlay = DataTestOverlay(self)
        self._datatest_mode = "off"

    # Adicione estes métodos à classe:
    def set_datatest_mode(self, mode: str) -> None:
        """Define o modo de exibição do overlay.
        
        Args:
            mode: "off", "all", "body", "buttons"
        """
        self._datatest_mode = mode
        self._datatest_overlay.set_mode(mode)
    
    def toggle_datatest(self) -> bool:
        """Alterna entre modo off e all.
        
        Returns:
            True se agora está em "all", False se está em "off"
        """
        self._datatest_overlay.toggle()
        is_on = self._datatest_overlay._overlay_mode == "all"
        self._datatest_mode = "all" if is_on else "off"
        return is_on
```

## Snippet 2: Atalho de Teclado

**Arquivo:** `task_manager_desktop/app.py` (antes de `window.show()`)

```python
# Adicionar atalho global para DataTest (Ctrl+Shift+D)
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QShortcut

datatest_shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), window)
datatest_shortcut.activated.connect(window.toggle_datatest)
```

## Snippet 3: Adicionar testid aos Widgets

Use este padrão em qualquer lugar onde cria widgets:

```python
# Em task_manager_desktop/ui/main_window.py
self.central_widget = QWidget()
self.central_widget.setProperty("testid", "main-content")
self.setCentralWidget(self.central_widget)

# Em task_manager_desktop/ui/header.py
self.title_label = QLabel("Task Manager")
self.title_label.setProperty("testid", "header-title")

self.new_task_button = QPushButton("+ Nova Tarefa")
self.new_task_button.setProperty("testid", "header-new-task-button")

# Em task_manager_desktop/ui/task_list.py
self.container = QWidget()
self.container.setProperty("testid", "task-list-container")

# Em task_manager_desktop/ui/task_card.py
self.card = QWidget()
self.card.setProperty("testid", f"task-card-{task.id}")
```

## Snippet 4: Botão Visual no Header (Opcional)

**Arquivo:** `task_manager_desktop/ui/header.py`

Adicione no header para controle visual:

```python
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt

# No HeaderBar.__init__():
self.main_window = main_window  # armazene a referência

# Criar botão DataTest
self._btn_datatest = QPushButton("DataTest")
self._btn_datatest.setFixedSize(68, 32)
self._btn_datatest.setCheckable(True)
self._btn_datatest.setToolTip("Exibir objectNames em todos os componentes")
self._btn_datatest.setProperty("testid", "header-datatest-toggle")
self._btn_datatest.setCursor(Qt.CursorShape.PointingHandCursor)

# Estilo (red quando ativo)
self._btn_datatest.setStyleSheet(
    "QPushButton { background-color: transparent; color: #A1A1AA;"
    "  border: 1px solid #52525B; border-radius: 6px;"
    "  font-size: 11px; font-weight: 600; padding: 0 6px; }"
    "QPushButton:hover { color: #FAFAFA; background-color: #3F3F46;"
    "  border-color: #71717A; }"
    "QPushButton:checked { background-color: #DC2626; color: #FAFAFA;"
    "  border-color: #DC2626; font-weight: 700; }"
)

# Conectar handler
self._btn_datatest.toggled.connect(self._on_datatest_toggled)

# Adicionar ao layout (em qualquer lugar do header que faça sentido)
header_layout.addWidget(self._btn_datatest)

# Handler do botão
def _on_datatest_toggled(self, checked: bool) -> None:
    """Ativa/desativa o overlay ao clicar no botão."""
    if checked:
        self.main_window.set_datatest_mode("all")
    else:
        self.main_window.set_datatest_mode("off")
```

## Snippet 5: Adicionar testid Dinâmico em Listas

Para widgets criados dinamicamente (ex: task cards em lista):

```python
# Em task_manager_desktop/ui/task_list.py

def _create_task_card(self, task):
    """Cria um card para a tarefa com testid dinâmico."""
    from .task_card import TaskCard
    
    card = TaskCard(task, self)
    
    # Adicionar testid que identifica univocamente este card
    card.card_widget.setProperty("testid", f"task-card-{task.id}")
    card.title_button.setProperty("testid", f"task-title-{task.id}")
    card.status_button.setProperty("testid", f"task-status-{task.id}")
    card.edit_button.setProperty("testid", f"task-edit-{task.id}")
    card.delete_button.setProperty("testid", f"task-delete-{task.id}")
    
    return card

# Ao adicionar card à lista:
for task in tasks:
    card = self._create_task_card(task)
    self.card_container.addWidget(card.card_widget)
```

## Snippet 6: Padrão de Naming Recomendado

Use estes padrões para manter consistência:

```python
# Layout e estrutura
"main-content"              # Container principal
"header"                    # Header
"sidebar" ou "task-list"    # Sidebar/lista principal
"footer"                    # Footer

# Header components
"header-title"              # Título
"header-new-task-button"    # Botão principal de ação
"header-menu-button"        # Menu

# Task list
"task-list-container"       # Container da lista
"task-card-{id}"           # Card individual
"task-title-{id}"          # Título do card
"task-status-{id}"         # Status do card
"task-edit-{id}"           # Botão editar
"task-delete-{id}"         # Botão deletar
"sector-{name}"            # Seção (ex: sector-open)

# Modais/Dialogs
"modal-confirm-delete"      # Modal de confirmação
"modal-close-button"        # Botão fechar
"modal-confirm-button"      # Botão confirmar
"modal-cancel-button"       # Botão cancelar

# Formulários
"form-task-title-input"     # Input de título
"form-task-desc-textarea"   # Textarea de descrição
"form-submit-button"        # Botão submit
"form-cancel-button"        # Botão cancelar
```

## Snippet 7: Verificação de Cobertura

Após integrar, rode este script para verificar quantos widgets têm testid:

```python
# Em um script separado ou no console do app:

def check_testid_coverage(widget):
    """Verifica e imprime a cobertura de testid."""
    all_widgets = [widget] + widget.findChildren(QWidget)
    has_testid = sum(1 for w in all_widgets if w.property("testid"))
    
    print(f"Cobertura de testid:")
    print(f"  Total widgets: {len(all_widgets)}")
    print(f"  Com testid: {has_testid}")
    print(f"  Cobertura: {100 * has_testid / len(all_widgets):.1f}%")
    
    # Listar widgets SEM testid
    print("\nWidgets SEM testid:")
    for w in all_widgets:
        if not w.property("testid") and w.isVisible():
            class_name = w.__class__.__name__
            obj_name = w.objectName() or "(sem objectName)"
            print(f"  - {class_name}: {obj_name}")

# Usar:
# check_testid_coverage(window.centralWidget())
```

## Snippet 8: Testar no Console

Para testar DataTest sem precisar integrar botão/atalho:

```python
# Em qualquer ponto do código (ex: em uma função de teste)

# Ativar overlay
window.set_datatest_mode("all")

# Desativar
window.set_datatest_mode("off")

# Alternar
window.toggle_datatest()

# Apenas botões
window.set_datatest_mode("buttons")

# Apenas não-botões
window.set_datatest_mode("body")
```

## Snippet 9: Integração com Teste Automatizado

Se você usar Pytest + QTest:

```python
# Em tests/test_datatest.py

import pytest
from PySide6.QtWidgets import QApplication
from task_manager_desktop.ui.main_window import MainWindowShell

def test_datatest_overlay():
    """Testa se o DataTest overlay funciona corretamente."""
    app = QApplication.instance() or QApplication([])
    window = MainWindowShell()
    
    # Ativar overlay
    window.set_datatest_mode("all")
    assert window._datatest_overlay._overlay_mode == "all"
    assert len(window._datatest_overlay._testid_overlays) > 0
    
    # Desativar
    window.set_datatest_mode("off")
    assert window._datatest_overlay._overlay_mode == "off"
    assert len(window._datatest_overlay._testid_overlays) == 0
    
    # Testar toggle
    is_on = window.toggle_datatest()
    assert is_on == True
    is_on = window.toggle_datatest()
    assert is_on == False
```

## Debug: Se os overlays não aparecerem

1. **Verificar se o widget tem testid:**
   ```python
   widget.property("testid")  # Deve retornar uma string, não None
   ```

2. **Verificar se o widget é visível:**
   ```python
   widget.isVisible()  # Deve ser True
   widget.isVisibleTo(window.centralWidget())  # Deve ser True
   ```

3. **Verificar se o overlay foi criado:**
   ```python
   len(window._datatest_overlay._testid_overlays)  # Deve ser > 0
   ```

4. **Imprimir debug info:**
   ```python
   # Adicione no _show_testid_overlays() para debug
   print(f"[DataTest] Criados {len(self._testid_overlays)} overlays")
   for overlay in self._testid_overlays:
       print(f"  - {overlay.text()} em ({overlay.x()}, {overlay.y()})")
   ```
