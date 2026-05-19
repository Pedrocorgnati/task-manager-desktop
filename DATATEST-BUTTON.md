# Botão DataTest — Guia Visual

## 📍 Localização do Botão

O botão **DataTest** está no **header** (barra superior) da aplicação, ao lado direito.

```
┌─────────────────────────────────────────────────────────┐
│ [+] [Buscar...] [Todos ▼] [Limpar...] [🗑️] [DataTest]  │  ← Header
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Task List                          │  Task Reader        │
│                                      │                     │
│                                      │                     │
└─────────────────────────────────────────────────────────┘
```

## 🎨 Visual do Botão

**Desativado (Estado Normal):**
- Fundo: Transparente
- Cor do texto: Cinza (#A1A1AA)
- Borda: Cinza claro (#52525B)
- Aparência: Suave, desativado

**Ativado (Overlays Visíveis):**
- Fundo: Vermelho (#DC2626)
- Cor do texto: Branco
- Borda: Vermelho (#DC2626)
- Fonte: Negrita

**Ao passar o mouse:**
- Fundo: Cinza escuro (#3F3F46)
- Cor do texto: Branco
- Borda: Cinza (#71717A)

## 🔌 Como Usar

### Opção 1: Clicar no Botão (Mais Fácil)

1. **Localize o botão** `DataTest` no header (lado direito)
2. **Clique uma vez** para ativar
   - O botão fica **vermelho**
   - Overlays aparecem na janela
3. **Clique novamente** para desativar
   - O botão volta ao cinza
   - Overlays desaparecem

### Opção 2: Atalho de Teclado

Pressione **Ctrl + Shift + D** em qualquer momento

### Resultado

Quando ativado, você verá:
- **Labels flutuantes vermelhos** sobre cada widget
- **Texto branco** com o objectName
- **Clique em qualquer label** para copiar para clipboard
- A label **muda para verde** por 600ms confirmando a cópia

## 💡 Exemplo

```
┌─────────────────────────────────────┐
│ ┌─────────────┐    ┌──────────┐     │
│ │ header-new-task-button │ [Data...]  │  ← Overlays em vermelho
│ │  (clique me!) └──────────┘     │
│ └─────────────┘                  │
│                                  │
│ ┌──────────────────┐            │
│ │ header-search-input (foco)    │
│ └──────────────────┘            │
│                                  │
│ ┌──────────────────────────┐    │
│ │ header-project-filter-select │ ← Overlay também aqui
│ └──────────────────────────┘    │
└─────────────────────────────────┘
```

## 🎯 Checklist de Uso

- [ ] Localizou o botão `DataTest` no header
- [ ] Clicou uma vez e o botão ficou **vermelho**
- [ ] Viu aparecer **labels vermelhos** nos widgets
- [ ] Clicou em um label e ele **ficou verde**
- [ ] O texto foi **copiado para clipboard**
- [ ] Clicou novamente no botão para **desativar** (voltou ao cinza)
- [ ] Pressionou **Ctrl+Shift+D** para confirmar que o atalho também funciona

## 🔧 Troubleshooting

### "Não vejo o botão DataTest"

**Solução:**
1. Verifique se está na **versão mais recente** do app
2. Rode: `git pull origin main` na pasta do projeto
3. Inicie o app novamente

### "Clicei mas nada acontece"

**Solução:**
1. Verifique se há mensagens de erro no terminal
2. Tente o atalho: **Ctrl+Shift+D**
3. Se nada funcionar, reabra o app

### "Botão está lá mas está desbotado"

**Solução:**
- Isso é normal quando está desativado
- Clique uma vez para ativar (fica vermelho)

## 📚 Modo de Debug

Quando o botão está **ativo (vermelho)**, você pode:

1. **Ver o objectName de cada widget** (útil para testes)
2. **Clicar em qualquer label** para copiar: `objectName="..."`
3. **Usar em testes automatizados** via Playwright/Cypress

Exemplo de uso em teste:
```python
# Com Playwright
page.locator('[data-testid="header-new-task-button"]').click()

# Ou com objectName (Qt)
# from PySide6.QtWidgets import QApplication
# button = app.findChild(QAbstractButton, "headerNewTaskButton")
# button.click()
```

## 🎨 Estilo CSS Completo

```css
QPushButton {
  background-color: transparent;
  color: #A1A1AA;
  border: 1px solid #52525B;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  padding: 0 6px;
}

QPushButton:hover {
  color: #FAFAFA;
  background-color: #3F3F46;
  border-color: #71717A;
}

QPushButton:checked {
  background-color: #DC2626;
  color: #FAFAFA;
  border-color: #DC2626;
  font-weight: 700;
}
```

---

**Pronto! Agora você pode:**
- ✅ Localizar o botão `DataTest`
- ✅ Ativar/desativar overlays
- ✅ Ver objectName de todos os widgets
- ✅ Copiar para usar em testes

**Aproveite! 🎉**
