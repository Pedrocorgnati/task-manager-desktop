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

    def _refresh_project_filter() -> None:
        try:
            header.set_projects(repo.list_projetos())
        except Exception:  # noqa: BLE001
            pass

    def _on_search_changed(query: str) -> None:
        task_list.set_filters(query, header.current_project())
        _reconcile_reader_visibility()

    def _on_project_filter_changed(_projeto: str) -> None:
        task_list.set_filters(header._search.text(), header.current_project())
        _reconcile_reader_visibility()

    header.search_changed.connect(_on_search_changed)
    header.project_filter_changed.connect(_on_project_filter_changed)

    _orig_refresh = task_list.refresh

    def _refresh_with_projects(tasks=None):
        _orig_refresh(tasks)
        _refresh_project_filter()

    task_list.refresh = _refresh_with_projects  # type: ignore[method-assign]

    # Load existing tasks
    task_list.refresh(repo.list_active())

    window.set_left_widget(task_list)

    from .ui.markdown_reader import MarkdownReader

    reader = MarkdownReader(repo, parent=window)
    window.set_right_widget(reader)

    def _on_task_selected_for_reader(task):
        # Edge: trocar de task durante edit mode bloqueia switch.
        # MarkdownReader.show_task emite switch_blocked se ja em edicao.
        reader.show_task(task)

    task_list.task_selected.connect(_on_task_selected_for_reader)

    def _on_switch_blocked(msg: str) -> None:
        try:
            from .ui.toast import ToastWidget
            toast = ToastWidget(window)
            toast.show_message(msg)
        except Exception:  # noqa: BLE001
            pass

    reader.switch_blocked.connect(_on_switch_blocked)

    def _reconcile_reader_visibility() -> None:
        if reader.is_editing():
            return
        current_id = reader.current_task_id()
        if not current_id:
            return
        if current_id not in task_list.visible_task_ids():
            try:
                reader.clear()
            except Exception:  # noqa: BLE001
                pass

    window.show()
    sys.exit(app.exec())
