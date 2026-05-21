from __future__ import annotations

import logging
import sys
from typing import Any, Callable

from PySide6.QtCore import QByteArray, Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from .core.bootstrap import ensure_data_dir_and_db
from .core.constants import PROPAGATION_THRESHOLD
from .ui.dialogs import ErrorDialog
from .ui.icons import APP_ICON_SVG
from .ui.main_window import MainWindowShell
from .ui.theme import THEME_QSS_PATH

_logger = logging.getLogger(__name__)


def _extract_broom_counts(result: Any) -> tuple[int, int]:
    """Normaliza o retorno de ``TaskRepository.hide_all_done`` em dois contadores.

    A vassoura (source.md secao 9, observabilidade) precisa de ``affected_count``
    e ``excluded_permanente_count`` para emitir o evento estruturado
    ``vassoura.hide_all_done``. O repositorio passou a devolver um resultado
    estruturado carregando esses dois campos; este helper aceita as tres formas
    possiveis sem quebrar:

      1. objeto com atributos ``affected_count`` / ``excluded_permanente_count``;
      2. dict com as mesmas chaves;
      3. ``int`` legado (apenas a contagem de afetados) — fallback de
         compatibilidade ate o sibling agent landar o retorno estruturado.

    Nunca levanta: qualquer forma inesperada degrada para ``(0, 0)``, para que a
    observabilidade jamais derrube a acao do usuario.
    """
    if result is None:
        return 0, 0
    # bool e subclasse de int — tratar como ausencia de dado estruturado.
    if isinstance(result, bool):
        return 0, 0
    # Forma 3: int legado (apenas affected_count).
    if isinstance(result, int):
        return result, 0
    # Forma 2: dict estruturado.
    if isinstance(result, dict):
        affected = result.get("affected_count", 0)
        excluded = result.get("excluded_permanente_count", 0)
    else:
        # Forma 1: objeto estruturado.
        affected = getattr(result, "affected_count", 0)
        excluded = getattr(result, "excluded_permanente_count", 0)
    try:
        return int(affected), int(excluded)
    except (TypeError, ValueError):
        return 0, 0


def _log_vassoura_hide_all_done(
    result: Any = None,
    *,
    outcome: str = "ok",
    error: Exception | None = None,
) -> int:
    """Emite o evento de observabilidade ``vassoura.hide_all_done`` (source.md secao 9).

    Consome o retorno de ``hide_all_done`` e loga, no idioma estruturado dos
    demais eventos da secao 9 (``extra={...}``), os dois contadores canonicos.
    Retorna ``affected_count`` para o caller decidir se precisa refrescar a UI.

    Emitido EXATAMENTE UMA VEZ por acao da vassoura — tanto no caminho de sucesso
    (``outcome="ok"``) quanto no de erro (``outcome="error"``, com ``error``
    populado) — espelhando o contrato dos eventos ``favorito.toggle`` /
    ``permanente.toggle``. Zero Silencio: uma vassoura que falha nao some do log.
    """
    affected_count, excluded_permanente_count = _extract_broom_counts(result)
    extra: dict[str, Any] = {
        "event": "vassoura.hide_all_done",
        "affected_count": affected_count,
        "excluded_permanente_count": excluded_permanente_count,
        "outcome": outcome,
    }
    if error is not None:
        extra["error"] = repr(error)
    _logger.info("vassoura.hide_all_done", extra=extra)
    return affected_count


def _perform_clear_completed(
    repo: Any,
    window: Any,
    on_success: Callable[[], None],
) -> None:
    """Executa a vassoura ("Limpar concluidas") como seam testavel.

    Chama ``repo.hide_all_done()``, emite o evento §9 ``vassoura.hide_all_done``
    EXATAMENTE UMA VEZ (sucesso, erro de DB tratado, ou excecao inesperada antes
    de propagar) e dispara ``on_success`` apenas no caminho de sucesso com tasks
    efetivamente ocultas. Extraido do closure ``_on_clear_completed`` para que o
    contrato de observabilidade §9 seja testavel sem subir a janela Qt inteira.
    """
    import sqlite3 as _sql

    result: Any = None
    outcome = "ok"
    error: Exception | None = None
    try:
        result = repo.hide_all_done()
    except (_sql.OperationalError, _sql.IntegrityError) as exc:
        outcome, error = "error", exc
        ErrorDialog.show_io_error(window, exc, repo.db_path)
    except Exception as exc:  # noqa: BLE001 - garante o evento secao 9 antes de propagar
        outcome, error = "error", exc
        raise
    finally:
        # Observabilidade source.md secao 9: vassoura.hide_all_done e emitido
        # EXATAMENTE UMA VEZ por acao da vassoura — sucesso, erro de DB tratado,
        # ou excecao inesperada (emitido antes de propagar).
        affected_count = _log_vassoura_hide_all_done(
            result, outcome=outcome, error=error
        )
    # So dispara o callback de sucesso com tasks efetivamente ocultas.
    if outcome == "ok" and affected_count > 0:
        on_success()


def _build_app_icon() -> QIcon:
    svg_bytes = QByteArray(APP_ICON_SVG.encode("utf-8"))
    renderer = QSvgRenderer(svg_bytes)
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
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
    app.setFont(QFont("Ubuntu Sans", 13))

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
        from .core.desktop_entry import ensure_desktop_integration
        ensure_desktop_integration()
    except Exception as exc:  # noqa: BLE001
        print(f"[desktop-entry] Falha nao critica: {exc}", file=sys.stderr)

    try:
        from .core.db import get_connection, validate_database

        _boot_conn = get_connection(db_path)
        validate_database(_boot_conn)
    except Exception as exc:  # noqa: BLE001
        _show_error_and_exit(exc, str(db_path))
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

    repo = TaskRepository(conn, db_path=db_path)

    window = MainWindowShell()

    from .ui.header import HeaderBar

    header = HeaderBar(window)
    header.install_shortcut(window)
    window.set_header_widget(header)

    from .ui.task_list import TaskList

    task_list = TaskList(window)
    task_list.set_repo(repo)
    task_list.set_main_window(window)
    task_list.set_header_widget(header.take_primary_controls())
    # Grid de test-mode ancorada como overlay no canto inferior direito da coluna 1.
    task_list.attach_test_mode_grid(header.take_test_mode_grid())

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
            # `permanente` e obrigatorio: omiti-lo renderiza uma task permanente
            # concluida no setor DONE em vez de PERMANENT (source.md secao 3.6).
            # getattr defende contra o estado de migracao em que o campo
            # `permanente` ainda nao landou no modelo Task (sibling agent).
            new_sector, _ = compute_sector(
                changed.status,
                has_open,
                permanente=getattr(changed, "permanente", False),
            )
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
        "on_title_save": edit_ctrl.handle_inline_title_edit,
        "on_favorite_toggle": edit_ctrl.handle_favorite_toggle,
    }
    task_list.set_callbacks(callbacks)

    header.new_task_requested.connect(create_ctrl.handle)
    task_list.task_selected.connect(lambda task: window.select_task(task.id))

    def _update_clear_done_button_state() -> None:
        """Update 'Limpar concluídas' button enabled state based on visible done tasks.

        Zero Silencio: nenhuma excecao e descartada silenciosamente. Se a
        consulta falhar, o estado seguro da vassoura e DESABILITADO — uma
        vassoura habilitada com estado obsoleto poderia disparar uma acao sobre
        um snapshot incoerente. A excecao e sempre logada com contexto.
        """
        from task_manager_desktop.core.models import Status

        try:
            all_tasks = repo.list_active()
            has_visible_done = any(
                task.status == Status.DONE for task in all_tasks
            )
        except Exception:
            _logger.exception(
                "vassoura.button_state_refresh_failed: desabilitando a vassoura "
                "(estado seguro) por falha ao consultar tasks ativas"
            )
            # Fallback seguro: vassoura desabilitada nunca fica obsoleta.
            try:
                header.set_clear_done_enabled(False)
            except Exception:
                _logger.exception(
                    "vassoura.button_state_disable_failed: nao foi possivel "
                    "forcar o estado desabilitado da vassoura"
                )
            return
        header.set_clear_done_enabled(has_visible_done)

    def _apply_header_filters() -> None:
        task_list.set_filters(
            task_types=header.current_task_types(),
        )
        _reconcile_reader_visibility()

    header.type_filter_changed.connect(lambda _types: _apply_header_filters())

    def _on_clear_completed() -> None:
        def _on_success() -> None:
            task_list.refresh(repo.list_active())
            _reconcile_reader_visibility()

        _perform_clear_completed(repo, window, _on_success)

    from .ui.dialogs.trash_dialog import TrashDialog as _TrashDialog

    _trash_dlg = _TrashDialog(repo, parent=window)

    def _on_restore_in_trash(_task_id: str) -> None:
        task_list.refresh(repo.list_active())
        _reconcile_reader_visibility()

    _trash_dlg.restore_requested.connect(_on_restore_in_trash)

    def _on_trash_clicked() -> None:
        _trash_dlg.reload()
        _trash_dlg.exec()
        task_list.refresh(repo.list_active())
        _reconcile_reader_visibility()

    header.clear_completed_clicked.connect(_on_clear_completed)
    header.trash_clicked.connect(_on_trash_clicked)

    _orig_refresh = task_list.refresh

    def _refresh_with_extras(tasks=None):
        _orig_refresh(tasks)
        _update_clear_done_button_state()

    task_list.refresh = _refresh_with_extras  # type: ignore[method-assign]

    # Load existing tasks
    task_list.refresh(repo.list_active())

    window.set_left_widget(task_list)

    from .ui.subtask_pane import SubtaskPane

    subtask_pane = SubtaskPane(repo, parent=window)
    window.set_middle_widget(subtask_pane)

    from PySide6.QtWidgets import QDockWidget, QSplitter, QVBoxLayout, QWidget

    from .ui.markdown_reader import MarkdownReader
    from .ui.terminal.terminal_panel import TerminalPanel

    reader = MarkdownReader(repo, parent=window)

    # Vertical splitter: markdown reader em cima, terminal embarcado embaixo.
    # Replica o mecanismo do workflow-app (data-testid="terminal-workspace-collapse").
    _right_pane = QWidget(window)
    _right_pane.setProperty("testid", "right-pane-vertical")
    _right_layout = QVBoxLayout(_right_pane)
    _right_layout.setContentsMargins(0, 0, 0, 0)
    _right_layout.setSpacing(0)

    _right_splitter = QSplitter(Qt.Orientation.Vertical, _right_pane)
    _right_splitter.setHandleWidth(4)
    _right_splitter.setChildrenCollapsible(False)
    _right_splitter.setProperty("testid", "right-vertical-splitter")

    _terminal_wrapper = QWidget(_right_splitter)
    _terminal_wrapper.setProperty("testid", "terminal-workspace")
    _terminal_layout = QVBoxLayout(_terminal_wrapper)
    _terminal_layout.setContentsMargins(0, 0, 0, 0)
    _terminal_layout.setSpacing(0)
    _terminal_panel = TerminalPanel(_terminal_wrapper)
    _terminal_layout.addWidget(_terminal_panel)

    _right_splitter.addWidget(reader)
    _right_splitter.addWidget(_terminal_wrapper)
    _right_layout.addWidget(_right_splitter)

    _terminal_dock = QDockWidget("Terminal", window)
    _terminal_dock.setObjectName("terminalBottomDock")
    _terminal_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
    _terminal_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
    _terminal_dock.setWidget(QWidget(_terminal_dock))
    _terminal_dock.hide()
    window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, _terminal_dock)

    # Estado inicial: terminal COLAPSADO (oculto). Chevron mostra ▲.
    # saved_sizes=None significa "primeira expansao → usa 50/50".
    _terminal_state: dict = {"collapsed": True, "saved_sizes": None}
    _terminal_wrapper.hide()
    reader.set_terminal_collapsed(True)
    header.set_terminal_collapsed(True)

    def _toggle_terminal_collapse() -> None:
        if _terminal_state["collapsed"]:
            # Expand: tamanhos salvos OU 50/50 na primeira vez.
            _terminal_wrapper.show()
            if _layout_state["column_mode"]:
                _terminal_dock.show()
            if _terminal_wrapper.parent() is _right_splitter:
                sizes = _terminal_state["saved_sizes"]
                if sizes is None:
                    total = max(_right_splitter.height(), 600)
                    sizes = [total // 2, total // 2]
                _right_splitter.setSizes(sizes)
            _terminal_state["collapsed"] = False
            QTimer.singleShot(0, _terminal_panel.focus_terminal)
        else:
            # Collapse: salva tamanhos atuais e oculta o wrapper.
            if _terminal_wrapper.parent() is _right_splitter:
                current = _right_splitter.sizes()
                if current and all(s > 0 for s in current):
                    _terminal_state["saved_sizes"] = current
            _terminal_wrapper.hide()
            if _layout_state["column_mode"]:
                _terminal_dock.hide()
            _terminal_state["collapsed"] = True
        reader.set_terminal_collapsed(_terminal_state["collapsed"])
        header.set_terminal_collapsed(_terminal_state["collapsed"])

    reader.toggle_terminal_collapse_requested.connect(_toggle_terminal_collapse)
    header.terminal_collapse_requested.connect(_toggle_terminal_collapse)

    def _send_notes_to_terminal(text: str) -> None:
        """Cola o texto atual das notas no terminal embarcado (sem Enter)."""
        if not text:
            return
        if _terminal_state["collapsed"]:
            _toggle_terminal_collapse()
        QTimer.singleShot(0, lambda: _terminal_panel.paste_text(text))
        QTimer.singleShot(0, _terminal_panel.focus_terminal)

    reader.send_to_terminal_requested.connect(_send_notes_to_terminal)
    _terminal_collapse_shortcut = QShortcut(QKeySequence("Ctrl+J"), window)
    _terminal_collapse_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
    _terminal_collapse_shortcut.activated.connect(_toggle_terminal_collapse)
    window._terminal_collapse_shortcut = _terminal_collapse_shortcut  # type: ignore[attr-defined]

    _layout_state: dict[str, bool] = {"column_mode": False}

    def _move_terminal_to_reader() -> None:
        if _terminal_wrapper.parent() is _right_splitter:
            return
        _terminal_wrapper.setParent(None)
        _right_splitter.addWidget(_terminal_wrapper)

    def _move_terminal_to_bottom_dock() -> None:
        dock_host = _terminal_dock.widget()
        if dock_host is None:
            return
        if _terminal_wrapper.parent() is dock_host:
            return
        _terminal_wrapper.setParent(None)
        host_layout = dock_host.layout()
        if host_layout is None:
            host_layout = QVBoxLayout(dock_host)
            host_layout.setContentsMargins(0, 0, 0, 0)
            host_layout.setSpacing(0)
        host_layout.addWidget(_terminal_wrapper)

    def _set_terminal_layout_column(enabled: bool) -> None:
        _layout_state["column_mode"] = enabled
        if enabled:
            _move_terminal_to_bottom_dock()
            if _terminal_state["collapsed"]:
                _terminal_wrapper.hide()
                _terminal_dock.hide()
                reader.set_terminal_collapsed(True)
            else:
                _terminal_wrapper.show()
                _terminal_dock.show()
                reader.set_terminal_collapsed(False)
        else:
            _terminal_dock.hide()
            _move_terminal_to_reader()
            if _terminal_state["collapsed"]:
                _terminal_wrapper.hide()
            else:
                _terminal_wrapper.show()
                sizes = _terminal_state["saved_sizes"]
                if sizes:
                    _right_splitter.setSizes(sizes)
            reader.set_terminal_collapsed(_terminal_state["collapsed"])

    header.terminal_layout_mode_toggled.connect(_set_terminal_layout_column)

    # Cleanup garantido do PTY no fechamento do app (widgets-filho nao
    # recebem closeEvent confiavelmente; aboutToQuit eh o caminho safe).
    app.aboutToQuit.connect(_terminal_panel.shutdown)

    window.set_right_widget(_right_pane)

    def _on_task_selected_for_reader(task):
        reader.show_task(task)
        subtask_pane.set_task(task)

    def _on_enter_pressed_on_task(task):
        reader.show_task(task)
        subtask_pane.set_task(task)
        try:
            reader._viewer.setFocus(Qt.FocusReason.OtherFocusReason)
        except Exception:
            # Fallback de foco: o viewer interno pode nao existir/estar pronto.
            # A excecao e recuperavel mas nunca descartada sem registro.
            _logger.debug(
                "reader._viewer.setFocus falhou; fallback para reader.setFocus",
                exc_info=True,
            )
            reader.setFocus(Qt.FocusReason.OtherFocusReason)

    task_list.task_selected.connect(_on_task_selected_for_reader)
    task_list.enter_pressed_on_selection.connect(_on_enter_pressed_on_task)

    def _on_switch_blocked(msg: str) -> None:
        try:
            from .ui.toast import ToastWidget
            toast = ToastWidget(window)
            toast.show_message(msg)
        except Exception:
            # O toast e a unica sinalizacao de "troca bloqueada"; se ele falhar
            # nao ha como recuperar o feedback visual, mas a falha NUNCA pode
            # passar silenciosa (Zero Silencio) — logar com a mensagem perdida.
            _logger.exception(
                "reader.switch_blocked: falha ao exibir toast (mensagem perdida: %r)",
                msg,
            )

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
        # 2. Deselect task in list
        if task_list.has_selection():
            task_list.clear_selection()
            return
        # 3. No-op

    bundle = ControllerBundle(
        edit_selected=_edit_selected,
        mark_done_selected=_mark_done_selected,
        select_prev=task_list.select_prev,
        select_next=task_list.select_next,
        open_selected=task_list.open_selected,
        delete_selected=_delete_selected,
        esc_handler=_esc_handler,
    )
    window._shortcuts = register_all(window, bundle)  # type: ignore[attr-defined]

    def _reconcile_reader_visibility() -> None:
        if reader.is_editing():
            return
        current_id = reader.current_task_id()
        if not current_id:
            return
        if current_id not in task_list.visible_task_ids():
            try:
                reader.clear()
            except Exception:
                # reader.clear() pode falhar se o widget ja foi destruido;
                # nao ha acao de recuperacao, mas a falha e sempre logada.
                _logger.exception(
                    "reader.clear falhou ao reconciliar visibilidade "
                    "(task oculta id=%s)",
                    current_id,
                )

    # ── DataTest Debug Overlay (3 modos: all / body / buttons) ─────
    try:
        from .ui.debug_overlay import DataTestOverlay

        datatest_overlay = DataTestOverlay(window)
        window._datatest_overlay = datatest_overlay  # type: ignore[attr-defined]

        # Header emite test_mode_changed -> overlay aplica modo.
        header.test_mode_changed.connect(datatest_overlay.set_mode)
        header.datatest_terminal_write_toggled.connect(datatest_overlay.set_terminal_write_enabled)

        def _write_selector_to_terminal(selector_text: str) -> None:
            _terminal_panel.focus_terminal()
            _terminal_panel.paste_text(selector_text)

        datatest_overlay.set_terminal_writer(_write_selector_to_terminal)
        datatest_overlay.set_terminal_write_enabled(header.is_terminal_write_enabled())

        # Atalhos: cada um alterna seu modo (click no botao correspondente).
        # Usar toggle_test_mode mantem o estado dos botoes sincronizado.
        _sc_all = QShortcut(QKeySequence("Ctrl+Shift+D"), window)
        _sc_all.activated.connect(lambda: header.toggle_test_mode("all"))

        _sc_body = QShortcut(QKeySequence("Ctrl+Shift+B"), window)
        _sc_body.activated.connect(lambda: header.toggle_test_mode("body"))

        _sc_btn = QShortcut(QKeySequence("Ctrl+Shift+T"), window)
        _sc_btn.activated.connect(lambda: header.toggle_test_mode("buttons"))

        print(
            "[DataTest] Overlays ativados — Ctrl+Shift+D (all), "
            "Ctrl+Shift+B (body), Ctrl+Shift+T (buttons)"
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[DataTest] Falha nao critica ao inicializar: {exc}", file=sys.stderr)

    window.show()
    sys.exit(app.exec())
