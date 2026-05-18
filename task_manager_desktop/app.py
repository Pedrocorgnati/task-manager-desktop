from __future__ import annotations

import sys

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from .core.bootstrap import ensure_data_dir_and_db
from .ui.dialogs import ErrorDialog
from .ui.icons import APP_ICON_SVG
from .ui.main_window import MainWindowShell
from .ui.theme import THEME_QSS_PATH

WINDOW_DEF_W = 1400
WINDOW_DEF_H = 900


def _build_app_icon() -> QIcon:
    svg_bytes = QByteArray(APP_ICON_SVG.encode("utf-8"))
    renderer = QSvgRenderer(svg_bytes)
    pixmap = QPixmap(128, 128)
    pixmap.fill()
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def _show_error_and_exit(exception: BaseException, path: str = "") -> None:
    ErrorDialog.show_io_error(parent=None, exception=exception, db_path=path)
    sys.exit(1)


def main() -> None:
    _existing = QApplication.instance()
    app: QApplication = (
        _existing if isinstance(_existing, QApplication) else QApplication(sys.argv)
    )
    app.setOrganizationName("task-manager-desktop")
    app.setApplicationName("task-manager-desktop")
    app.setWindowIcon(_build_app_icon())

    if THEME_QSS_PATH.exists():
        app.setStyleSheet(THEME_QSS_PATH.read_text(encoding="utf-8"))

    try:
        db_path = ensure_data_dir_and_db()
    except PermissionError as exc:
        _show_error_and_exit(exc, str(exc.args[0]) if exc.args else "")
        return
    except OSError as exc:
        _show_error_and_exit(exc, "")
        return

    try:
        from .core.cleanup import run_cleanup_on_boot
        from .core.db import get_connection

        conn = get_connection(db_path)
        run_cleanup_on_boot(conn)
    except Exception as exc:  # noqa: BLE001
        print(f"[cleanup] Falha nao critica: {exc}", file=sys.stderr)

    from .core.db import get_connection as _get_conn

    conn = _get_conn(db_path)

    from .repositories.task_repository import TaskRepository

    repo = TaskRepository(conn, db_path=str(db_path))

    window = MainWindowShell()

    from .ui.header import HeaderBar

    header = HeaderBar(window)
    header.install_shortcut(window)
    window.set_header_widget(header)

    from .ui.task_list import TaskList

    task_list = TaskList(window)
    task_list.set_repo(repo)
    task_list.set_main_window(window)

    from .controllers.change_status_controller import ChangeStatusController
    from .controllers.create_task_controller import CreateTaskController
    from .controllers.delete_task_controller import DeleteTaskController
    from .controllers.edit_task_controller import EditTaskController
    from .core.sector import compute_sector, compute_sector_change_propagation, count_open_deps

    class _ErrorHandlerAdapter:
        def __init__(self, parent_widget):
            self._parent = parent_widget

        def show_io_error(self, message: str, db_path: str) -> None:
            from task_manager_desktop.ui.dialogs import ErrorDialog
            ErrorDialog.show_io_error(self._parent, Exception(message), db_path)

    _PROP_THRESHOLD = 20

    def _refresh_card(task):
        all_tasks = {t.id: t for t in repo.list_active()}
        propagated = compute_sector_change_propagation(task.id, all_tasks)
        if 1 + len(propagated) >= _PROP_THRESHOLD:
            task_list.refresh(list(all_tasks.values()))
            return
        changed = all_tasks.get(task.id)
        if changed is not None:
            has_open = count_open_deps(changed.deps, all_tasks) > 0
            new_sector, _ = compute_sector(changed.status, has_open)
            task_list.move_card_to_sector(task.id, new_sector.value)
        for dep_task_id, dep_sector, _ in propagated:
            task_list.move_card_to_sector(dep_task_id, dep_sector.value)

    change_status_ctrl = ChangeStatusController(
        repo=repo,
        all_tasks_provider=lambda: {t.id: t for t in repo.list_active()},
        error_handler=_ErrorHandlerAdapter(window),
        refresh_card=_refresh_card,
    )
    edit_ctrl = EditTaskController(repo, task_list, window, parent=window)
    delete_ctrl = DeleteTaskController(repo, task_list, window, parent=window)
    create_ctrl = CreateTaskController(repo, task_list, window, parent=window)

    callbacks = {
        "on_status_change": change_status_ctrl.handle,
        "on_edit": edit_ctrl.handle_edit,
        "on_delete": delete_ctrl.handle,
    }
    task_list.set_callbacks(callbacks)

    header.new_task_requested.connect(create_ctrl.handle)
    task_list.task_selected.connect(lambda task: window.select_task(task.id))

    # Load existing tasks
    task_list.refresh(repo.list_active())

    window.set_left_widget(task_list)

    from .ui.empty_state import EmptyStateLabel

    right_empty = EmptyStateLabel(text="Selecione uma task para ver as notas.")
    window.set_right_widget(right_empty)

    window.show()
    sys.exit(app.exec())
