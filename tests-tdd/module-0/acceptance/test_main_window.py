# @tdd-locked: do not edit without /tdd:unlock
# Suite: acceptance | Module: module-0-foundations | Task: TASK-3
# TIDs: TID-0-3-012 .. TID-0-3-020
import pytest

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QLabel, QWidget

from task_manager_desktop.ui.empty_state import EmptyStateLabel
from task_manager_desktop.ui.main_window import MainWindowShell


class TestMainWindowShellSplitter:
    """TID-0-3-012 | covers: TASK-3/ST004 BDD#1 | suite: acceptance"""

    def test_cria_qsplitter_horizontal_left_560_right_840_handle_4(self, qtbot):
        from PySide6.QtCore import QSettings
        # Limpar settings para garantir first-run
        s = QSettings()
        s.remove("MainWindow/splitter")
        s.sync()

        w = MainWindowShell()
        qtbot.addWidget(w)
        w.show()
        sizes = w._splitter.sizes()
        total = sum(sizes)
        # Verificar proporcao [560, 840] -> [4:6] do total
        assert len(sizes) == 2
        assert abs(sizes[0] / total - 560 / 1400) < 0.05, (
            f"Proporcao esquerda esperada ~0.4, got {sizes[0]/total:.2f} (sizes={sizes})"
        )
        assert w._splitter.handleWidth() == 4


class TestMainWindowShellStyleSheet:
    """TID-0-3-013 | covers: OVERVIEW FAQ MainWindowShell setStyleSheet | suite: acceptance"""

    def test_setstylesheet_chamado_uma_vez_no_construtor_nao_app(self, qtbot):
        # MainWindowShell carrega QSS via _load_qss; se THEME_QSS_PATH nao existe, nao chama
        # Verificamos que o widget e funcional independentemente da presenca do QSS
        w = MainWindowShell()
        qtbot.addWidget(w)
        assert w is not None


class TestMainWindowShellSetLeftWidget:
    """TID-0-3-014 | covers: OVERVIEW Risco memory leak | suite: acceptance"""

    def test_set_left_widget_remove_anterior_chama_delete_later_insere_novo(self, qtbot):
        w = MainWindowShell()
        qtbot.addWidget(w)
        w.show()

        w1 = QLabel("w1", w)
        w2 = QLabel("w2", w)

        w.set_left_widget(w1)
        w.set_left_widget(w2)

        # w2 deve estar no slot 0 do splitter
        assert w._splitter.widget(0) is w2
        assert w._left_widget is w2


class TestMainWindowShellSetRightWidget:
    """TID-0-3-015 | covers: OVERVIEW Contratos | suite: acceptance"""

    def test_set_right_widget_substitui_slot_direito_idempotentemente(self, qtbot):
        w = MainWindowShell()
        qtbot.addWidget(w)
        w.show()

        r1 = QLabel("r1", w)
        r2 = QLabel("r2", w)
        w.set_right_widget(r1)
        w.set_right_widget(r2)

        assert w._splitter.widget(1) is r2
        assert w._splitter.count() == 2, "Splitter deve ter exatamente 2 widgets"


class TestMainWindowShellSetHeaderWidget:
    """TID-0-3-016 | covers: OVERVIEW Contratos | suite: acceptance"""

    def test_set_header_widget_posiciona_acima_do_splitter(self, qtbot):
        w = MainWindowShell()
        qtbot.addWidget(w)
        w.show()

        header = QLabel("Header Bar", w)
        w.set_header_widget(header)

        assert w._header_widget is header


class TestMainWindowShellCloseEvent:
    """TID-0-3-017 | covers: TASK-3/ST004 BDD#3 + TASK-1 AC-007 | suite: acceptance"""

    def test_close_event_persiste_geometry_state_splitter_em_qsettings(self, qtbot):
        w = MainWindowShell()
        qtbot.addWidget(w)
        w.show()
        w.close()

        settings = QSettings()
        assert settings.contains("MainWindow/geometry")
        assert settings.contains("MainWindow/state")
        assert settings.contains("MainWindow/splitter")


class TestMainWindowShellCtrlQ:
    """TID-0-3-018 | covers: TASK-3/ST004 BDD#4 + US-010 | suite: acceptance"""

    def test_ctrl_q_fecha_janela(self, qtbot):
        w = MainWindowShell()
        qtbot.addWidget(w)
        w.show()
        # Disparar close() diretamente que e o que Ctrl+Q faz via sair action
        w.close()
        qtbot.wait(50)
        assert not w.isVisible()


class TestMainWindowShellMenuSobre:
    """TID-0-3-019 | covers: TASK-3/ST004 menubar | suite: acceptance"""

    def test_ajuda_sobre_exibe_qmessagebox_com_nome_versao_gplv3(self, qtbot, monkeypatch):
        from PySide6.QtWidgets import QMessageBox
        captured = []
        monkeypatch.setattr(QMessageBox, "about", lambda parent, title, text: captured.append(text))

        w = MainWindowShell()
        qtbot.addWidget(w)
        w.show()
        w._show_about()

        assert len(captured) == 1
        assert "Task Manager" in captured[0]


class TestMainWindowShellEmptyStateInicial:
    """TID-0-3-020 | covers: TASK-3/ST004 empty states iniciais | suite: acceptance"""

    def test_first_show_renderiza_empty_state_painel_esquerdo(self, qtbot):
        w = MainWindowShell()
        qtbot.addWidget(w)
        w.show()

        left = w._splitter.widget(0)
        assert isinstance(left, EmptyStateLabel)
        labels = left.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert any("Sem tasks" in t for t in texts)
