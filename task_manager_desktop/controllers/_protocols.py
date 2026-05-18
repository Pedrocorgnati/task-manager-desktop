"""Protocols (PEP 544) consumidos pelos controllers do task-manager-desktop.

Definicoes deliberadamente minimas — apenas os metodos que os controllers
chamam. Isso evita acoplamento com PySide6/QWidget concreto e permite
dublar componentes em testes sem dependencia de Qt.
"""

from __future__ import annotations

from typing import Protocol


class ErrorHandler(Protocol):
    """Contrato minimo de tratamento de erros de I/O exibidos ao usuario."""

    def show_io_error(self, message: str, db_path: str) -> None: ...


class TaskListLike(Protocol):
    """Contrato minimo do widget de lista de tasks usado pelos controllers."""

    def refresh(self) -> None: ...

    def move_card_to_sector(self, dep_id: str, new_sector: int) -> None: ...


class SegmentedControlLike(Protocol):
    """Contrato minimo do StatusSegmentedControl visto pelo ChangeStatusController."""

    def setEnabled(self, enabled: bool) -> None: ...

    def setValue(self, value: str) -> None: ...
