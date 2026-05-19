# Python Architecture Report — task-manager-desktop
Data: 2026-05-18 | Status: WARN (minor)

## Resumo

Arquitetura sólida e bem estruturada para aplicação desktop PySide6.
Camadas respeitam direção de dependência. Protocol-based DI em controllers é pattern excelente.

| Pilar | Status | Notes |
|-------|--------|-------|
| Separação de camadas | OK | core → repositories → controllers → ui |
| DI / Protocol | OK | `_protocols.py` + `ChangeStatusController` |
| Duplicação de código | OK | sem código duplicado estrutural |
| Dependências circulares | OK | nenhuma detectada |
| Single Responsibility | OK (minor gaps) | app.py composição root OK |
| Acesso a atributos privados | WARN | 3 ocorrências |

**Issues:** 5 (ARCH-001 Alto, ARCH-002..004 Médio, ARCH-005 Baixo)

## Arquivo Mais Afetado
- `app.py` (279 linhas): 3 das 5 issues passam por aqui

## Correções Aplicadas
Nenhuma — issues de arquitetura requerem decisões de design revisadas em separado.

## Próximos Passos
1. ARCH-001 (crítico): expor `generate_id` via repo ou método público
2. ARCH-002: `header.search_text()` método público
3. ARCH-003: criar `MainWindowLike` Protocol
4. ARCH-004: mover `_ErrorHandlerAdapter` para `ui/adapters.py`
