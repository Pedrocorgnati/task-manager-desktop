from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings, Qt
from PySide6.QtGui import QAction, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.ui.empty_state import EmptyStateLabel
from task_manager_desktop.ui.theme import (
    SPLITTER_COLLAPSED_RATIOS,
    SPLITTER_RATIOS,
    SPLITTER_RATIO,
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
_SETTINGS_SPLITTER_COUNT = "MainWindow/splitter_count"
_SETTINGS_SPLITTER_SCHEMA = "MainWindow/splitter_schema"
_SETTINGS_MIDDLE_COLLAPSED = "MainWindow/middle_collapsed"
_SPLITTER_SCHEMA_VERSION = 3


class MiddleColumnPane(QWidget):
    """Coluna central colapsavel entre lista e editor."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("middleColumnPane")
        self.setAccessibleName("Painel intermediário colapsável")
        self.setProperty("testid", "middle-pane")

        self.btn_toggle = QPushButton("[<]", self)
        self.btn_toggle.setObjectName("middleColumnToggle")
        self.btn_toggle.setAccessibleName("Colapsar painel intermediário")
        self.btn_toggle.setFixedHeight(32)

        self._title = QLabel("Contexto", self)
        self._title.setObjectName("middleColumnTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._hint = QLabel("Painel auxiliar", self)
        self._hint.setObjectName("middleColumnHint")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(8)
        layout.addWidget(self.btn_toggle)
        layout.addWidget(self._title)
        layout.addWidget(self._hint)
        layout.addStretch()

    def set_collapsed(self, collapsed: bool) -> None:
        self.btn_toggle.setText("[>]" if collapsed else "[<]")
        self.btn_toggle.setAccessibleName(
            "Expandir painel intermediário"
            if collapsed
            else "Colapsar painel intermediário"
        )
        self._title.setVisible(not collapsed)
        self._hint.setVisible(not collapsed)


class MainWindowShell(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Task Manager Desktop")
        self.setMinimumSize(WINDOW_MIN_W, WINDOW_MIN_H)
        self.setAccessibleName("Task Manager Desktop")
        self.setProperty("testid", "main-window")

        self._load_qss()
        self._register_window_actions()

        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._splitter.setHandleWidth(4)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setProperty("testid", "main-splitter")
        self._middle_collapsed = False
        self._normalizing_splitter = False

        # Empty states iniciais — substituidos por feature modules via set_*_widget
        self._left_widget: QWidget = EmptyStateLabel(
            "Sem tasks. Clique em + para criar a primeira.",
            "Atalho: Ctrl+N",
        )
        self._left_widget.setProperty("testid", "task-list-pane")

        self._right_widget: QWidget = EmptyStateLabel("Selecione uma task para ver as notas.")
        self._right_widget.setProperty("testid", "task-reader-pane")

        self._middle_widget = MiddleColumnPane(self)
        self._middle_widget.btn_toggle.clicked.connect(self._toggle_middle_pane)

        self._splitter.addWidget(self._left_widget)
        self._splitter.addWidget(self._middle_widget)
        self._splitter.addWidget(self._right_widget)

        self.setCentralWidget(self._splitter)
        self._restore_settings()
        self._splitter.splitterMoved.connect(self._on_splitter_moved)

        self._header_widget: QWidget | None = None
        self._current_task_id: str | None = None

    def _load_qss(self) -> None:
        if THEME_QSS_PATH.exists():
            self.setStyleSheet(THEME_QSS_PATH.read_text(encoding="utf-8"))

    def _register_window_actions(self) -> None:
        sair = QAction("Sair", self)
        sair.setShortcut(QKeySequence("Ctrl+Q"))
        sair.triggered.connect(self.close)
        self.addAction(sair)

    def _show_about(self) -> None:
        QMessageBox.about(self, "Sobre", "Task Manager Desktop v0.1")

    def set_left_widget(self, widget: QWidget) -> None:
        old = self._splitter.widget(0)
        if old is not None:
            old.setParent(None)  # type: ignore[arg-type]
            old.deleteLater()
        self._splitter.insertWidget(0, widget)
        self._left_widget = widget
        self._apply_splitter_ratios()

    def set_right_widget(self, widget: QWidget) -> None:
        old = self._splitter.widget(2)
        if old is not None:
            old.setParent(None)  # type: ignore[arg-type]
            old.deleteLater()
        self._splitter.insertWidget(2, widget)
        self._right_widget = widget
        self._apply_splitter_ratios()

    def set_middle_widget(self, widget: QWidget) -> None:
        old = self._splitter.widget(1)
        if old is not None:
            old.setParent(None)  # type: ignore[arg-type]
            old.deleteLater()
        self._splitter.insertWidget(1, widget)
        self._middle_widget = widget
        if hasattr(widget, "btn_toggle"):
            widget.btn_toggle.clicked.connect(self._toggle_middle_pane)  # type: ignore[attr-defined]
        self._apply_splitter_ratios()

    def is_middle_collapsed(self) -> bool:
        return self._middle_collapsed

    def set_middle_collapsed(self, collapsed: bool) -> None:
        self._middle_collapsed = collapsed
        if hasattr(self._middle_widget, "set_collapsed"):
            self._middle_widget.set_collapsed(collapsed)  # type: ignore[attr-defined]
        self._apply_splitter_ratios()

    def _toggle_middle_pane(self) -> None:
        self.set_middle_collapsed(not self._middle_collapsed)

    def _apply_splitter_ratios(self) -> None:
        total_w = max(self._splitter.width(), self.width(), WINDOW_DEF_W)
        left_w = int(SPLITTER_SIZES[0])
        if self._middle_collapsed:
            collapsed_width_fn = getattr(self._middle_widget, "collapsed_width", None)
            if callable(collapsed_width_fn):
                middle_w = int(collapsed_width_fn())
                remaining = max(0, total_w - left_w - middle_w)
                self._splitter.setSizes([left_w, middle_w, remaining])
                return
        middle_ratio = (
            SPLITTER_COLLAPSED_RATIOS[1] if self._middle_collapsed else SPLITTER_RATIOS[1]
        )
        middle_w = int(total_w * middle_ratio)
        remaining = max(0, total_w - left_w - middle_w)
        self._splitter.setSizes([left_w, middle_w, remaining])

    def _on_splitter_moved(self, _pos: int, _index: int) -> None:
        self._normalize_fixed_splitter_columns()
        self._save_splitter_state()

    def _normalize_fixed_splitter_columns(self) -> None:
        if self._normalizing_splitter:
            return
        sizes = self._splitter.sizes()
        if len(sizes) != 3:
            return

        left = self._splitter.widget(0)
        middle = self._splitter.widget(1)
        if left is None or middle is None:
            return

        total_w = sum(sizes)
        target_left = sizes[0]
        target_middle = sizes[1]
        lock = False

        if left.minimumWidth() == left.maximumWidth():
            target_left = int(left.minimumWidth())
            lock = True
        if middle.minimumWidth() == middle.maximumWidth():
            target_middle = int(middle.minimumWidth())
            lock = True

        if not lock:
            return

        target_right = max(0, total_w - target_left - target_middle)
        target = [target_left, target_middle, target_right]
        if target == sizes:
            return

        self._normalizing_splitter = True
        try:
            self._splitter.setSizes(target)
        finally:
            self._normalizing_splitter = False

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
        splitter_count = settings.value(_SETTINGS_SPLITTER_COUNT, type=int)
        splitter_schema = settings.value(_SETTINGS_SPLITTER_SCHEMA, type=int)
        middle_collapsed = settings.value(_SETTINGS_MIDDLE_COLLAPSED, False, type=bool)

        if geometry and isinstance(geometry, (bytes, bytearray, QByteArray)):
            self.restoreGeometry(geometry)
        else:
            self.resize(WINDOW_DEF_W, WINDOW_DEF_H)
            self._center_on_primary_screen()

        if state and isinstance(state, (bytes, bytearray, QByteArray)):
            self.restoreState(state)

        self._middle_collapsed = bool(middle_collapsed)
        if hasattr(self._middle_widget, "set_collapsed"):
            self._middle_widget.set_collapsed(self._middle_collapsed)

        if (
            splitter_schema == _SPLITTER_SCHEMA_VERSION
            and
            splitter_count == 3
            and splitter_state
            and isinstance(splitter_state, (bytes, bytearray, QByteArray))
        ):
            self._splitter.restoreState(splitter_state)
        else:
            self._apply_splitter_ratios()

    def _save_splitter_state(self) -> None:
        QSettings().setValue(_SETTINGS_SPLITTER, self._splitter.saveState())
        QSettings().setValue(_SETTINGS_SPLITTER_COUNT, self._splitter.count())
        QSettings().setValue(_SETTINGS_SPLITTER_SCHEMA, _SPLITTER_SCHEMA_VERSION)
        QSettings().setValue(_SETTINGS_MIDDLE_COLLAPSED, self._middle_collapsed)

    def _center_on_primary_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def closeEvent(self, event) -> None:  # type: ignore[override]
        settings = QSettings()
        settings.setValue(_SETTINGS_GEOMETRY, self.saveGeometry())
        settings.setValue(_SETTINGS_STATE, self.saveState())
        settings.setValue(_SETTINGS_SPLITTER, self._splitter.saveState())
        settings.setValue(_SETTINGS_SPLITTER_COUNT, self._splitter.count())
        settings.setValue(_SETTINGS_SPLITTER_SCHEMA, _SPLITTER_SCHEMA_VERSION)
        settings.setValue(_SETTINGS_MIDDLE_COLLAPSED, self._middle_collapsed)
        super().closeEvent(event)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
