"""Debug overlay para exibir testid (objectName) de widgets em modo desenvolvimento.

Implementação baseada no sistema DataTest do workflow-app (PySide6/Qt6).
Exibe labels flutuantes vermelhos com o testid de cada widget, permitindo
copiar para clipboard ao clicar.
"""

from typing import Optional
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
    QAbstractButton,
    QMainWindow,
)


class DataTestOverlay:
    """Gerenciador de overlays de testid para debug visual de widgets."""

    # Estilos dos overlays
    _STYLE_NORMAL = (
        "background-color: rgba(220, 38, 38, 0.9); color: white;"
        " font-size: 10px; font-weight: 700; padding: 2px 5px;"
        " border-radius: 3px; border: none;"
    )
    _STYLE_COPIED = (
        "background-color: rgba(34, 197, 94, 0.9); color: white;"
        " font-size: 10px; font-weight: 700; padding: 2px 5px;"
        " border-radius: 3px; border: none;"
    )

    def __init__(self, main_window: QMainWindow):
        """Inicializa o gerenciador de overlays.

        Args:
            main_window: Janela principal (QMainWindow) onde os overlays serão ancorados.
        """
        self.main_window = main_window
        self._testid_overlays: list[QLabel] = []
        self._overlay_mode = "off"  # "off", "all", "body", "buttons"

    def set_mode(self, mode: str) -> None:
        """Define o modo de exibição dos overlays.

        Args:
            mode: "off" (desligado), "all" (todos), "body" (exceto botões), "buttons" (apenas botões).
        """
        self._overlay_mode = mode
        if mode == "off":
            self.hide_all()
        else:
            self.show_all()

    def show_all(self) -> None:
        """Exibe overlays para todos os widgets com testid."""
        self.hide_all()
        central = self.main_window.centralWidget()
        if not central:
            return

        used_positions: list[tuple[int, int, int, int]] = []  # x, y, w, h

        # Coletar todos os widgets
        scan_widgets: list[QWidget] = [central]
        scan_widgets.extend(central.findChildren(QWidget))

        for widget in scan_widgets:
            testid = widget.property("testid")
            if not testid or widget.property("_is_testid_overlay"):
                continue

            testid_str = str(testid)

            # Filtrar por modo
            is_button = isinstance(widget, QAbstractButton)
            if self._overlay_mode == "body" and is_button:
                continue
            if self._overlay_mode == "buttons" and not is_button:
                continue

            # Pular widgets não visíveis
            if not widget.isVisible() or not widget.isVisibleTo(central):
                continue

            # Mapear posição do widget para as coordenadas da janela central
            try:
                pos = widget.mapTo(central, QPoint(0, 0))
            except RuntimeError:
                continue

            x, y = pos.x(), pos.y() - 14

            # Ajustar posição se houver sobreposição com overlay anterior
            for ux, uy, uw, uh in used_positions:
                if abs(x - ux) < max(uw, 30) and abs(y - uy) < max(uh, 18):
                    y = uy + uh + 2

            # Criar overlay label
            overlay = QLabel(testid_str, central)
            overlay.setStyleSheet(self._STYLE_NORMAL)
            overlay.setProperty("_is_testid_overlay", True)
            overlay.setCursor(Qt.CursorShape.PointingHandCursor)
            overlay.setToolTip(f"Clique para copiar: {testid_str}")

            # Conectar clique para copiar para clipboard
            self._setup_overlay_click(overlay, testid_str)

            overlay.adjustSize()
            overlay.move(x, y)
            overlay.show()
            overlay.raise_()
            used_positions.append((x, y, overlay.width(), overlay.height()))
            self._testid_overlays.append(overlay)

    def _setup_overlay_click(self, overlay: QLabel, testid_str: str) -> None:
        """Configura o evento de clique do overlay para copiar testid.

        Args:
            overlay: Label do overlay.
            testid_str: Texto do testid a copiar.
        """

        def handler(event):
            # Copiar para clipboard
            QApplication.clipboard().setText(f'objectName="{testid_str}"')

            # Feedback visual: mudar cor para verde por 600ms
            overlay.setStyleSheet(self._STYLE_COPIED)
            QTimer.singleShot(
                600, lambda: overlay.setStyleSheet(self._STYLE_NORMAL)
            )

        overlay.mousePressEvent = handler

    def hide_all(self) -> None:
        """Remove todos os overlays."""
        for overlay in self._testid_overlays:
            overlay.hide()
            overlay.deleteLater()
        self._testid_overlays.clear()

    def toggle(self) -> None:
        """Alterna entre modo "off" e "all"."""
        if self._overlay_mode == "off":
            self.set_mode("all")
        else:
            self.set_mode("off")
