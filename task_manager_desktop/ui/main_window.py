from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QSplitter,
    QWidget,
)

from task_manager_desktop.ui.empty_state import EmptyStateLabel
from task_manager_desktop.ui.theme import (
    SPLITTER_SIZES,
    THEME_QSS_PATH,
    WINDOW_DEF_H,
    WINDOW_DEF_W,
    WINDOW_MIN_H,
    WINDOW_MIN_W,
)

_SETTINGS_GEOMETRY = "MainWindow/geometry"
_SETTINGS_STATE = "MainWindow/state"
_SETTINGS_SPLITTER = "MainWindow/splitter"


class MainWindowShell(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Task Manager Desktop")
        self.setMinimumSize(WINDOW_MIN_W, WINDOW_MIN_H)
        self.setAccessibleName("Task Manager Desktop")

        self._load_qss()
        self._build_menu()

        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._splitter.setHandleWidth(4)
        self._splitter.setChildrenCollapsible(False)

        # Empty states iniciais — substituidos por feature modules via set_*_widget
        self._left_widget: QWidget = EmptyStateLabel(
            "Sem tasks. Clique em + para criar a primeira.",
            "Atalho: Ctrl+N",
        )
        self._right_widget: QWidget = EmptyStateLabel(
            "Selecione uma task para ver as notas."
        )
        self._splitter.addWidget(self._left_widget)
        self._splitter.addWidget(self._right_widget)

        self.setCentralWidget(self._splitter)
        self._restore_settings()

        self._header_widget: QWidget | None = None
        self._current_task_id: str | None = None

    def _load_qss(self) -> None:
        if THEME_QSS_PATH.exists():
            self.setStyleSheet(THEME_QSS_PATH.read_text(encoding="utf-8"))

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        arquivo = menu_bar.addMenu("Arquivo")
        sair = QAction("Sair", self)
        sair.setShortcut(QKeySequence("Ctrl+Q"))
        sair.triggered.connect(self.close)
        arquivo.addAction(sair)

        ajuda = menu_bar.addMenu("Ajuda")
        sobre = QAction("Sobre", self)
        sobre.triggered.connect(self._show_about)
        ajuda.addAction(sobre)

    def _show_about(self) -> None:
        QMessageBox.about(self, "Sobre", "Task Manager Desktop v0.1")

    def set_left_widget(self, widget: QWidget) -> None:
        old = self._splitter.widget(0)
        if old is not None:
            old.setParent(None)  # type: ignore[arg-type]
            old.deleteLater()
        self._splitter.insertWidget(0, widget)
        self._left_widget = widget

    def set_right_widget(self, widget: QWidget) -> None:
        old = self._splitter.widget(1)
        if old is not None:
            old.setParent(None)  # type: ignore[arg-type]
            old.deleteLater()
        self._splitter.insertWidget(1, widget)
        self._right_widget = widget

    def set_header_widget(self, widget: QWidget) -> None:
        from PySide6.QtWidgets import QToolBar
        if self._header_widget is not None:
            tb = self.findChild(QToolBar, "header_toolbar")
            if isinstance(tb, QToolBar):
                self.removeToolBar(tb)
        toolbar = QToolBar("header_toolbar", self)
        toolbar.setObjectName("header_toolbar")
        toolbar.setMovable(False)
        toolbar.addWidget(widget)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        self._header_widget = widget

    def select_task(self, task_id: str) -> None:
        self._current_task_id = task_id

    def reset_viewer_to_empty(self) -> None:
        self._current_task_id = None

    def _restore_settings(self) -> None:
        settings = QSettings()
        geometry = settings.value(_SETTINGS_GEOMETRY)
        state = settings.value(_SETTINGS_STATE)
        splitter_state = settings.value(_SETTINGS_SPLITTER)

        if geometry and isinstance(geometry, (bytes, bytearray, QByteArray)):
            self.restoreGeometry(geometry)
        else:
            self.resize(WINDOW_DEF_W, WINDOW_DEF_H)

        if state and isinstance(state, (bytes, bytearray, QByteArray)):
            self.restoreState(state)

        if splitter_state and isinstance(splitter_state, (bytes, bytearray, QByteArray)):
            self._splitter.restoreState(splitter_state)
        else:
            self._splitter.setSizes(SPLITTER_SIZES)

    def closeEvent(self, event) -> None:  # type: ignore[override]
        settings = QSettings()
        settings.setValue(_SETTINGS_GEOMETRY, self.saveGeometry())
        settings.setValue(_SETTINGS_STATE, self.saveState())
        settings.setValue(_SETTINGS_SPLITTER, self._splitter.saveState())
        super().closeEvent(event)
