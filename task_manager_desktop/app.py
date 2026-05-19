from __future__ import annotations

import sys

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from .core.bootstrap import ensure_data_dir_and_db
from .core.constants import PROPAGATION_THRESHOLD
from .ui.dialogs import ErrorDialog
from .ui.icons import APP_ICON_SVG
from .ui.main_window import MainWindowShell
from .ui.theme import THEME_QSS_PATH


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

    def _refresh_card(task):
        all_tasks = {t.id: t for t in repo.list_active()}
        propagated = compute_sector_change_propagation(task.id, all_tasks)
        if 1 + len(propagated) >= PROPAGATION_THRESHOLD:
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

    def _update_clear_done_button_state() -> None:
        """Update 'Limpar concluídas' button enabled state based on visible done tasks."""
        try:
            from task_manager_desktop.core.models import Status
            all_tasks = repo.list_active()
            has_visible_done = any(
                task.status == Status.DONE for task in all_tasks
            )
            header.set_clear_done_enabled(has_visible_done)
        except Exception:  # noqa: BLE001
            pass

    def _on_search_changed(query: str) -> None:
        task_list.set_filters(query, header.current_project())
        _reconcile_reader_visibility()

    def _on_project_filter_changed(_projeto: str | None) -> None:
        task_list.set_filters(header._search.text(), header.current_project())
        _reconcile_reader_visibility()

    header.search_text_changed.connect(_on_search_changed)
    header.project_filter_changed.connect(_on_project_filter_changed)

    def _on_clear_completed() -> None:
        import sqlite3 as _sql

        try:
            n = repo.hide_all_done()
        except (_sql.OperationalError, _sql.IntegrityError) as exc:
            ErrorDialog.show_io_error(window, exc, repo.db_path)
            return
        if n > 0:
            task_list.refresh(repo.list_active())
            _reconcile_reader_visibility()

    def _on_trash_clicked() -> None:
        from .ui.dialogs.trash_dialog import TrashDialog

        dlg = TrashDialog(repo, parent=window)
        dlg.restore_requested.connect(lambda _tid: task_list.refresh(repo.list_active()))
        dlg.exec()
        task_list.refresh(repo.list_active())

    header.clear_completed_clicked.connect(_on_clear_completed)
    header.trash_clicked.connect(_on_trash_clicked)

    _orig_refresh = task_list.refresh

    def _refresh_with_projects(tasks=None):
        _orig_refresh(tasks)
        _refresh_project_filter()
        _update_clear_done_button_state()

    task_list.refresh = _refresh_with_projects  # type: ignore[method-assign]

    # Load existing tasks
    task_list.refresh(repo.list_active())

    window.set_left_widget(task_list)

    from .ui.markdown_reader import MarkdownReader

    reader = MarkdownReader(repo, parent=window)
    window.set_right_widget(reader)

    def _on_task_selected_for_reader(task):
        reader.show_task(task)

    def _on_enter_pressed_on_task(task):
        reader.show_task(task)
        try:
            reader._viewer.setFocus(Qt.FocusReason.OtherFocusReason)
        except Exception:  # noqa: BLE001
            reader.setFocus(Qt.FocusReason.OtherFocusReason)

    task_list.task_selected.connect(_on_task_selected_for_reader)
    task_list.enter_pressed_on_selection.connect(_on_enter_pressed_on_task)

    def _on_switch_blocked(msg: str) -> None:
        try:
            from .ui.toast import ToastWidget
            toast = ToastWidget(window)
            toast.show_message(msg)
        except Exception:  # noqa: BLE001
            pass

    reader.switch_blocked.connect(_on_switch_blocked)

    from .core.models import Status
    from .ui.shortcuts import ControllerBundle, register_all

    def _edit_selected() -> None:
        t = task_list.get_selected_task()
        if t is not None:
            edit_ctrl.handle_edit(t)

    def _mark_done_selected() -> None:
        t = task_list.get_selected_task()
        if t is not None:
            change_status_ctrl.handle(t, Status.DONE.value, None)

    def _delete_selected() -> None:
        t = task_list.get_selected_task()
        if t is not None:
            delete_ctrl.handle(t)

    def _esc_handler() -> None:
        # 1. Close topmost modal dialog
        modal = QApplication.activeModalWidget()
        if modal is not None:
            modal.close()
            return
        # 2. Unfocus search field
        if header.search_has_focus():
            header.clear_search_focus()
            return
        # 3. Deselect task in list
        if task_list.has_selection():
            task_list.clear_selection()
            return
        # 4. No-op

    bundle = ControllerBundle(
        edit_selected=_edit_selected,
        mark_done_selected=_mark_done_selected,
        focus_search=header.focus_search,
        clear_search=header.clear_search,
        select_prev=task_list.select_prev,
        select_next=task_list.select_next,
        open_selected=task_list.open_selected,
        delete_selected=_delete_selected,
        esc_handler=_esc_handler,
    )
    window._shortcuts = register_all(window, bundle)

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
