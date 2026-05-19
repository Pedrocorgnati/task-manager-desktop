# Python Async Tasks — task-manager-desktop
Data: 2026-05-18

## Status: N/A — PySide6 Qt Desktop

Projeto usa Qt event loop (PySide6), não Python `asyncio`. Padrão correto para apps desktop Qt.

## Observações

- `ChangeStatusController._busy` flag corretamente previne re-entrant calls no Qt single-thread.
- Operações DB são síncronas no thread principal Qt — aceitável para SQLite local com latência de microsegundos.
- Sem `async def`, sem `await`, sem `asyncio.run()` — design intencional.
- Se futuramente adicionado worker thread (ex: import/export pesado), usar `QThread` + signals/slots, não `asyncio`.

## Recomendações

- Não introduzir `asyncio` no projeto. Qt tem seu próprio event loop e os dois são incompatíveis sem bridge (`qasync`).
- Para operações longas futuras, usar `QThread` com `Worker` QObject + `moveToThread`.

**Issues: 0**
