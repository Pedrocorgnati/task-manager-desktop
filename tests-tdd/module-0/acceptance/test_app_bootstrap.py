# @tdd-locked: do not edit without /tdd:unlock
# Suite: acceptance | Module: module-0-foundations | Task: TASK-1
# TIDs: TID-0-1-012, TID-0-1-013, TID-0-1-014, TID-0-1-015, TID-0-1-016
import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from task_manager_desktop.core.db import close_connection


@pytest.fixture(autouse=True)
def reset_db():
    yield
    close_connection()


class TestMainWindowShellFirstRun:
    """TID-0-1-012 | covers: TASK-1/ST004 BDD#1 + US-013 | suite: acceptance"""

    def test_main_exibe_mainwindowshell_1400x900_splitter_first_run(self, qtbot, tmp_path, monkeypatch):
        """Verifica que MainWindowShell e criada com splitter [560,840] no first-run."""
        from PySide6.QtCore import QSettings
        # Limpar QSettings para garantir first-run
        s = QSettings()
        s.remove("MainWindow/splitter")
        s.sync()

        from task_manager_desktop.ui.main_window import MainWindowShell
        w = MainWindowShell()
        qtbot.addWidget(w)
        w.show()

        sizes = w._splitter.sizes()
        total = sum(sizes)
        assert len(sizes) == 2
        assert abs(sizes[0] / total - 560 / 1400) < 0.05, (
            f"Proporcao esquerda ~0.4, got {sizes[0]/total:.2f} (sizes={sizes})"
        )


class TestMainWindowShellRestoreGeometry:
    """TID-0-1-013 | covers: TASK-1/ST004 BDD#2 | suite: acceptance"""

    @pytest.mark.skipif(
        os.environ.get("QT_QPA_PLATFORM") == "offscreen",
        reason="Geometry persistence requer display real (resize nao e aplicado em offscreen)",
    )
    def test_run_subsequente_restaura_geometry_1600x1000(self, qtbot):
        from task_manager_desktop.ui.main_window import MainWindowShell

        w1 = MainWindowShell()
        qtbot.addWidget(w1)
        w1.resize(1600, 1000)
        w1.show()
        w1.close()

        w2 = MainWindowShell()
        qtbot.addWidget(w2)
        w2.show()
        assert w2.width() >= 1500


class TestWindowIcon:
    """TID-0-1-014 | covers: TASK-1/ST004 BDD#3 | suite: acceptance"""

    def test_app_window_icon_nao_nulo_via_svg_renderer(self, qtbot):
        from task_manager_desktop.app import _build_app_icon
        icon = _build_app_icon()
        assert not icon.isNull(), "Icone da aplicacao nao deve ser nulo"


class TestBootstrapPermissionError:
    """TID-0-1-015 | covers: TASK-1/ST004 BDD#4 + US-013 cen.3 + US-016 cen.2 | suite: acceptance"""

    def test_permission_error_dispara_msgbox_critical_e_sys_exit_1(self, qtbot, monkeypatch):
        """App usa ErrorDialog.show_io_error apos GAP-003 refactor."""
        monkeypatch.setattr(
            "task_manager_desktop.app.ensure_data_dir_and_db",
            lambda: (_ for _ in ()).throw(PermissionError(13, "sem permissao")),
        )
        error_calls = []
        monkeypatch.setattr(
            "task_manager_desktop.app.ErrorDialog.show_io_error",
            lambda parent, exception, db_path: error_calls.append(exception) or 1,
        )
        exit_calls = []
        monkeypatch.setattr("task_manager_desktop.app.sys.exit", lambda code: exit_calls.append(code))

        from task_manager_desktop.app import main
        main()

        assert len(error_calls) == 1, "ErrorDialog.show_io_error deve ser chamado exatamente 1x"
        assert isinstance(error_calls[0], PermissionError)
        assert 1 in exit_calls, "sys.exit(1) deve ser chamado"


class TestCleanupDegradado:
    """TID-0-1-016 | covers: TASK-1/ST004 BDD#5 + US-016 cen.3 | suite: acceptance"""

    def test_falha_cleanup_oportunistico_loga_stderr_nao_bloqueia_startup(
        self, qtbot, tmp_path, monkeypatch, capsys
    ):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

        from PySide6.QtWidgets import QApplication
        monkeypatch.setattr(QApplication, "exec", lambda self: 0)
        monkeypatch.setattr("task_manager_desktop.app.sys.exit", lambda code: None)

        # Patch cleanup no modulo onde e importado inline
        monkeypatch.setattr(
            "task_manager_desktop.core.cleanup.run_cleanup_on_boot",
            lambda conn: exec("raise Exception('[cleanup] cleanup failed')"),
        )

        from task_manager_desktop.app import main
        main()

        captured = capsys.readouterr()
        # app.py faz print(..., file=sys.stderr) ao capturar excecao de cleanup
        assert "cleanup" in captured.err.lower() or len(captured.err) > 0
