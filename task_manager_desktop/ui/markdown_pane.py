from __future__ import annotations

import dataclasses
import os
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QHideEvent, QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from task_manager_desktop.core.exceptions import TaskNotFoundError
from task_manager_desktop.ui import external_paste
from task_manager_desktop.ui.editor_toolbar import EditorToolbar
from task_manager_desktop.ui.markdown_editor import MarkdownEditor
from task_manager_desktop.ui.markdown_viewer import MarkdownViewer

if TYPE_CHECKING:
    from task_manager_desktop.core.models import Task
    from task_manager_desktop.repositories.task_repository import TaskRepository


# Aliases de retrocompatibilidade: a logica canonica vive em external_paste.py
# (compartilhada com outros apps do AI Forge); testes/codigo antigo monkeypatcham
# estes nomes no namespace deste modulo.
_EXTERNAL_PASTE_DELAY_MS = external_paste.EXTERNAL_PASTE_DELAY_MS
_SETTINGS_READER_FONT_DELTA = "MarkdownReader/font_delta"
_READER_FONT_DELTA_MIN = -4
_READER_FONT_DELTA_MAX = 8
_EDITOR_BASE_FONT_SIZE = 13
_VIEWER_BASE_FONT_SIZE = 14

# Teto de tamanho para o modo documento (arquivos do SystemForge). Carregar um
# arquivo enorme/binário no editor congelaria a UI; o maior alvo curado tem
# ~435 KB, então 10 MB é folga ampla e ainda protege contra acidentes futuros.
_MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


def _atomic_write_text(path: Path, text: str) -> None:
    """Grava ``text`` em ``path`` de forma atômica (temp file + os.replace + fsync).

    Protege arquivos canônicos do SystemForge: uma falha/queda no meio da escrita
    deixa o arquivo original intacto em vez de truncado. Preserva o modo (bits de
    permissão) do arquivo original quando ele já existe.
    """
    directory = path.parent
    fd, tmp_name = tempfile.mkstemp(
        dir=str(directory), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            original_mode = os.stat(path).st_mode
            os.chmod(tmp_name, original_mode)
        except OSError:
            # Arquivo novo ou stat/chmod indisponível: mantém o modo default do temp.
            pass
        os.replace(tmp_name, str(path))
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise

_TERMINAL_WM_CLASS_MARKERS = external_paste.TERMINAL_WM_CLASS_MARKERS


class MarkdownPane(QWidget):
    """Painel direito de notas Markdown.

    O fluxo principal e editor-first: ao selecionar uma task, as notas ficam
    editaveis imediatamente. O viewer existe como preview alternavel.
    """

    notes_saved = Signal(str, str)   # (task_id, new_notes)
    editing_changed = Signal(bool)   # True = modo editor
    toggle_terminal_collapse_requested = Signal()
    send_to_terminal_requested = Signal(str)  # texto atual do editor → terminal

    _IDX_VIEWER = 0
    _IDX_EDITOR = 1

    def __init__(
        self,
        repo: TaskRepository | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("testid", "markdown-pane")
        self._repo = repo
        self._current_task: Task | None = None
        # Modo documento: arquivo arbitrário do SystemForge (sem vínculo com Task).
        # Mutuamente exclusivo com _current_task — só um dos dois fica ativo.
        self._current_doc_path: Path | None = None
        self._current_doc_text = ""
        self._reader_light_mode = False
        self._reader_font_delta = self._load_reader_font_delta()

        self.setObjectName("markdownPane")
        self.setAccessibleName("Painel de notas")

        # Botao mantido apenas como alias de retrocompatibilidade para testes/codigo antigo.
        # Ele nao entra no layout visual: a edicao agora e sempre direta.
        self._edit_btn = QPushButton("Editar", self)
        self._edit_btn.setObjectName("editButton")
        self._edit_btn.setProperty("class", "edit-btn")
        self._edit_btn.setProperty("testid", "markdown-edit-button")
        self._edit_btn.setToolTip("Editar notas desta task")
        self._edit_btn.setAccessibleName("Entrar no modo editor de notas")
        self._edit_btn.setVisible(False)

        # --- Header + pages ---
        self._toolbar = EditorToolbar(self)
        self._viewer = MarkdownViewer(self)
        self._editor = MarkdownEditor(self)
        self._external_paste_button = QPushButton(self)
        self._configure_external_paste_button()

        # --- Stack ---
        self._stack = QStackedWidget(self)
        self._stack.setProperty("testid", "markdown-stack")
        self._stack.addWidget(self._viewer)   # index 0
        self._stack.addWidget(self._editor)   # index 1

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._toolbar)
        outer.addWidget(self._stack, 1)

        # Wire-up
        self._edit_btn.clicked.connect(self._enter_editor)
        self._toolbar.save_requested.connect(self._save)
        self._toolbar.cancel_requested.connect(self._cancel)
        self._toolbar.toggle_preview_requested.connect(self._toggle_preview)
        self._toolbar.toggle_reader_theme_requested.connect(self._toggle_reader_theme)
        self._toolbar.increase_reader_font_requested.connect(self._increase_reader_font)
        self._toolbar.decrease_reader_font_requested.connect(self._decrease_reader_font)
        self._external_paste_button.clicked.connect(self._schedule_external_paste)

        self._save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self._editor)
        self._save_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._save_shortcut.activated.connect(self._save)

        self._apply_reader_theme()
        self.set_task(None)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_task(self, task: Task | None) -> None:
        """Define a task ativa. Faz save implicito se havia edicao pendente."""
        self._maybe_implicit_save()

        # Selecionar uma task encerra o modo documento (são mutuamente exclusivos).
        self._current_doc_path = None
        self._current_doc_text = ""
        self._toolbar.set_title("Notas Markdown")
        self._current_task = task
        self._viewer.set_task(task)
        self._editor.setPlainText(task.notes if task else "")
        self._edit_btn.setVisible(False)
        self._editor.setEnabled(task is not None)
        self._toolbar.set_task_enabled(task is not None)
        if task is None:
            self._stack.setCurrentIndex(self._IDX_VIEWER)
            self._toolbar.set_preview_mode(True)
            self.editing_changed.emit(False)
            self._external_paste_button.hide()
        else:
            self._stack.setCurrentIndex(self._IDX_EDITOR)
            self._toolbar.set_preview_mode(False)
            self.editing_changed.emit(True)
            self._external_paste_button.show()
            self._external_paste_button.raise_()
            self._position_external_paste_button()

    def show_document(self, path: str | Path) -> None:
        """Abre um arquivo arbitrário do SystemForge no leitor (modo documento).

        Reaproveita o editor de notas: o conteúdo fica imediatamente editável e
        Ctrl+S grava de volta no arquivo em disco. Não há vínculo com a lista de
        tasks — selecionar um card depois encerra o modo documento.

        Save é SEMPRE explícito (Ctrl+S). Esses arquivos são canônicos e ficam
        FORA do task-manager — nunca os gravamos sem ação direta do usuário.
        """
        doc_path = Path(path)
        # Guard de tamanho: arquivos grandes/binários acidentais congelariam a UI
        # ao carregar no editor. Lê o tamanho antes de puxar o conteúdo.
        try:
            size = doc_path.stat().st_size
        except OSError as exc:
            self._show_toast_warning(f"Erro ao abrir {doc_path.name}: {exc}")
            return
        if size > _MAX_DOCUMENT_BYTES:
            mb = _MAX_DOCUMENT_BYTES / (1024 * 1024)
            self._show_toast_warning(
                f"{doc_path.name} é grande demais para o leitor (limite {mb:.0f} MB)."
            )
            return
        try:
            text = doc_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            self._show_toast_warning(
                f"{doc_path.name} não é um arquivo de texto UTF-8 e não pode ser aberto."
            )
            return
        except OSError as exc:
            self._show_toast_warning(f"Erro ao abrir {doc_path.name}: {exc}")
            return

        # Persiste/descarta edição pendente do alvo anterior antes de trocar.
        self._maybe_implicit_save()

        self._current_task = None
        self._current_doc_path = doc_path
        self._current_doc_text = text
        is_markdown = doc_path.suffix.lower() in (".md", ".markdown")

        self._editor.setPlainText(text)
        self._editor.setEnabled(True)
        self._viewer.set_document(text, is_markdown=is_markdown)
        self._toolbar.set_task_enabled(True)
        self._toolbar.set_title(doc_path.name)

        # Editor-first, espelhando o fluxo de notas: edição direta + Ctrl+S.
        self._stack.setCurrentIndex(self._IDX_EDITOR)
        self._toolbar.set_preview_mode(False)
        self.editing_changed.emit(True)
        self._external_paste_button.show()
        self._external_paste_button.raise_()
        self._position_external_paste_button()

    def _maybe_implicit_save(self) -> None:
        """Resolve edição pendente do alvo ativo antes de trocar de alvo.

        - Notas de task: save implícito (comportamento histórico; notas são
          pessoais e seguras de auto-salvar).
        - Documentos: NUNCA auto-gravam (são arquivos canônicos do SystemForge).
          Edições não salvas são descartadas, mas com aviso (Zero Silencio) —
          re-abrir o arquivo recarrega o conteúdo do disco.
        """
        if self._current_doc_path is not None:
            if self._editor.toPlainText() != self._current_doc_text:
                self._show_toast_warning(
                    f"Alterações não salvas em {self._current_doc_path.name} foram "
                    "descartadas. Use Ctrl+S para salvar antes de trocar."
                )
        elif (
            self._current_task is not None
            and self._editor.toPlainText() != (self._current_task.notes or "")
        ):
            self._implicit_save()

    def is_editing(self) -> bool:
        return (
            self._current_task is not None
            and self._editor.toPlainText() != (self._current_task.notes or "")
        )

    def current_task_id(self) -> str | None:
        return self._current_task.id if self._current_task is not None else None

    def clear(self) -> None:
        self.set_task(None)

    def reader_light_mode(self) -> bool:
        return self._reader_light_mode

    def reader_font_delta(self) -> int:
        return self._reader_font_delta

    def hideEvent(self, event: QHideEvent) -> None:
        self._editor.clearFocus()
        super().hideEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_external_paste_button()

    # ------------------------------------------------------------------
    # Public accessors (used by tests and external observers)
    # ------------------------------------------------------------------
    @property
    def stack(self) -> QStackedWidget:
        return self._stack

    @property
    def viewer(self) -> MarkdownViewer:
        return self._viewer

    @property
    def editor(self) -> MarkdownEditor:
        return self._editor

    @property
    def toolbar(self) -> EditorToolbar:
        return self._toolbar

    @property
    def btn_edit(self) -> QPushButton:
        return self._edit_btn

    @property
    def external_paste_button(self) -> QPushButton:
        return self._external_paste_button

    # ------------------------------------------------------------------
    # Internal transitions
    # ------------------------------------------------------------------
    def _enter_editor(self) -> None:
        if self._current_task is None:
            return
        self._stack.setCurrentIndex(self._IDX_EDITOR)
        self._toolbar.set_preview_mode(False)
        self._editor.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.editing_changed.emit(True)

    def _toggle_preview(self) -> None:
        if self._current_task is None:
            return
        if self._stack.currentIndex() == self._IDX_EDITOR:
            preview_task = dataclasses.replace(
                self._current_task,
                notes=self._editor.toPlainText(),
            )
            self._viewer.set_task(preview_task)
            self._editor.clearFocus()
            self._stack.setCurrentIndex(self._IDX_VIEWER)
            self._toolbar.set_preview_mode(True)
            self.editing_changed.emit(False)
        else:
            self._enter_editor()

    def _toggle_reader_theme(self) -> None:
        self._reader_light_mode = not self._reader_light_mode
        self._apply_reader_theme()

    def _send_notes_to_terminal(self) -> None:
        """Emite o texto atual do editor para ser colado no terminal embarcado."""
        self.send_to_terminal_requested.emit(self._editor.toPlainText())

    def _load_reader_font_delta(self) -> int:
        value = QSettings().value(_SETTINGS_READER_FONT_DELTA, 0, type=int)
        try:
            delta = int(value)
        except (TypeError, ValueError):
            delta = 0
        return max(_READER_FONT_DELTA_MIN, min(_READER_FONT_DELTA_MAX, delta))

    def _save_reader_font_delta(self) -> None:
        QSettings().setValue(_SETTINGS_READER_FONT_DELTA, self._reader_font_delta)

    def _increase_reader_font(self) -> None:
        if self._reader_font_delta >= _READER_FONT_DELTA_MAX:
            return
        self._reader_font_delta += 1
        self._save_reader_font_delta()
        self._apply_reader_theme()

    def _decrease_reader_font(self) -> None:
        if self._reader_font_delta <= _READER_FONT_DELTA_MIN:
            return
        self._reader_font_delta -= 1
        self._save_reader_font_delta()
        self._apply_reader_theme()

    def _configure_external_paste_button(self) -> None:
        external_paste.style_external_paste_button(self._external_paste_button)
        self._external_paste_button.hide()

    def _position_external_paste_button(self) -> None:
        button = self._external_paste_button
        if button.isHidden():
            return
        margin = 24
        stack_rect = self._stack.geometry()
        x = stack_rect.right() - button.width() - margin + 1
        y = stack_rect.bottom() - button.height() - margin + 1
        button.move(max(margin, x), max(self._toolbar.height() + margin, y))
        button.raise_()

    def _schedule_external_paste(self) -> None:
        text = self._editor.toPlainText()
        if not text:
            self._show_toast_warning("Nao ha markdown para colar.")
            return
        self._external_paste_button.setEnabled(False)
        QTimer.singleShot(
            _EXTERNAL_PASTE_DELAY_MS,
            self,
            lambda captured=text: self._paste_markdown_to_focused_window(captured),
        )

    def _detect_paste_shortcut(self) -> str:
        """Escolhe a combinacao de paste conforme a janela focada.

        Logica canonica em ``external_paste.detect_paste_shortcut`` (compartilhada
        com outros apps do AI Forge). Mantido como metodo para permitir override
        em testes/subclasses; o global ``_TERMINAL_WM_CLASS_MARKERS`` deste modulo
        e lido em call time, preservando o seam de monkeypatch historico.
        """
        return external_paste.detect_paste_shortcut(_TERMINAL_WM_CLASS_MARKERS)

    def _paste_markdown_to_focused_window(self, text: str) -> None:
        self._external_paste_button.setEnabled(True)
        shortcut = self._detect_paste_shortcut()
        external_paste.paste_text_to_focused_window(
            text,
            shortcut,
            owner=self,
            on_warning=self._show_toast_warning,
            # Roteia pela instancia para manter o hook override-avel
            # (mesmo contrato de _detect_paste_shortcut).
            on_check=self._check_paste_result,
        )

    def _check_paste_result(self, proc: subprocess.Popen) -> None:
        external_paste._check_paste_result(proc, self._show_toast_warning)

    def _apply_reader_theme(self) -> None:
        editor_font_size = _EDITOR_BASE_FONT_SIZE + self._reader_font_delta
        viewer_font_size = _VIEWER_BASE_FONT_SIZE + self._reader_font_delta
        if self._reader_light_mode:
            editor_style = (
                "QPlainTextEdit[class='md-editor'] {"
                "background: #FAFAF7; color: #111116; border: none;"
                "padding: 30px 38px;"
                "font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace;"
                f"font-size: {editor_font_size}px;"
                "selection-background-color: #FBBF24;"
                "selection-color: #111116;"
                "}"
                "QPlainTextEdit[class='md-editor']:focus { border: none; outline: none; }"
            )
            browser_style = (
                "QTextBrowser#markdownBrowser {"
                "background: #FAFAF7; color: #111116; border: none;"
                "padding: 30px 38px;"
                "font-family: 'Ubuntu Sans', 'Noto Sans', 'DejaVu Sans', sans-serif;"
                f"font-size: {viewer_font_size}px;"
                "selection-background-color: #FBBF24;"
                "selection-color: #111116;"
                "}"
            )
        else:
            editor_style = (
                "QPlainTextEdit[class='md-editor'] {"
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #101116, stop:1 #0D0E12);"
                "color: #F8FAFC; border: none; padding: 30px 38px;"
                "font-family: 'JetBrains Mono', 'Ubuntu Mono', monospace;"
                f"font-size: {editor_font_size}px;"
                "selection-background-color: #FBBF24;"
                "selection-color: #111116;"
                "}"
                "QPlainTextEdit[class='md-editor']:focus { border: none; outline: none; }"
            )
            browser_style = (
                "QTextBrowser#markdownBrowser {"
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #101116, stop:0.55 #0D0E12, stop:1 #14120A);"
                "color: #F8FAFC; border: none; padding: 30px 38px;"
                "font-family: 'Ubuntu Sans', 'Noto Sans', 'DejaVu Sans', sans-serif;"
                f"font-size: {viewer_font_size}px;"
                "selection-background-color: #FBBF24;"
                "selection-color: #111116;"
                "}"
            )
        self._editor.setStyleSheet(editor_style)
        self._editor.set_reader_font_size(editor_font_size)
        bg = QColor("#FAFAF7" if self._reader_light_mode else "#0D0E12")
        fg = QColor("#111116" if self._reader_light_mode else "#F8FAFC")
        palette = self._editor.palette()
        palette.setColor(QPalette.ColorRole.Base, bg)
        palette.setColor(QPalette.ColorRole.Text, fg)
        palette.setColor(QPalette.ColorRole.Window, bg)
        palette.setColor(QPalette.ColorRole.WindowText, fg)
        self._editor.setPalette(palette)
        self._editor.viewport().setAutoFillBackground(True)
        self._editor.viewport().setPalette(palette)
        self._editor.set_reader_theme(self._reader_light_mode)
        self._viewer.set_reader_font_size(viewer_font_size)
        self._viewer.setStyleSheet(browser_style)
        self._viewer.set_reader_theme(self._reader_light_mode)
        try:
            self._viewer._browser.setStyleSheet(browser_style)
        except Exception:  # noqa: BLE001
            pass
        self._toolbar.set_reader_light_mode(self._reader_light_mode)
        self._toolbar.set_reader_font_delta(
            self._reader_font_delta,
            _READER_FONT_DELTA_MIN,
            _READER_FONT_DELTA_MAX,
        )

    def _save(self) -> None:
        if self._current_doc_path is not None:
            self._save_document()
            return
        if self._current_task is None:
            return
        current_index = self._stack.currentIndex()
        new_notes = self._editor.toPlainText()
        self._editor.setReadOnly(True)
        try:
            if self._repo is not None:
                self._repo.update_notes(self._current_task.id, new_notes)
        except (TaskNotFoundError, sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as exc:
            # CL-085: erros de save de nota mostram Toast nao-bloqueante; editor permanece aberto
            self._show_save_error_toast(exc)
            return  # mantem stack em IDX_EDITOR
        finally:
            self._editor.setReadOnly(False)
        try:
            self._current_task = dataclasses.replace(self._current_task, notes=new_notes)
        except Exception:  # noqa: BLE001
            pass
        self._viewer.set_task(self._current_task)
        self._stack.setCurrentIndex(current_index)
        self._toolbar.set_preview_mode(current_index == self._IDX_VIEWER)
        self.editing_changed.emit(current_index == self._IDX_EDITOR)
        self.notes_saved.emit(self._current_task.id, new_notes)

    def _save_document(self) -> None:
        """Grava o conteúdo do editor de volta no arquivo em disco (modo documento)."""
        path = self._current_doc_path
        if path is None:
            return
        new_text = self._editor.toPlainText()
        self._editor.setReadOnly(True)
        try:
            _atomic_write_text(path, new_text)
        except OSError as exc:
            self._show_save_error_toast(exc)
            return
        finally:
            self._editor.setReadOnly(False)
        self._current_doc_text = new_text
        self._show_toast_warning(f"Salvo: {path.name}")

    def _cancel(self) -> None:
        if self._current_doc_path is not None:
            self._editor.setPlainText(self._current_doc_text)
            self._editor.clearFocus()
            self.editing_changed.emit(False)
            return
        self._editor.setPlainText(self._current_task.notes if self._current_task else "")
        self._editor.clearFocus()
        self._stack.setCurrentIndex(self._IDX_VIEWER)
        self._toolbar.set_preview_mode(True)
        self.editing_changed.emit(False)

    def _implicit_save(self) -> None:
        if self._current_task is None or self._repo is None:
            return
        task_id = self._current_task.id
        new_notes = self._editor.toPlainText()
        try:
            self._repo.update_notes(task_id, new_notes)
        except Exception:  # noqa: BLE001
            self._show_toast_warning("Falha ao salvar notas da task anterior.")
            return
        try:
            self._current_task = dataclasses.replace(
                self._current_task, notes=new_notes
            )
        except Exception:  # noqa: BLE001
            pass
        self.notes_saved.emit(task_id, new_notes)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _show_save_error_toast(self, exc: BaseException) -> None:
        """Toast nao-bloqueante para falhas de save de notas (CL-085)."""
        self._show_toast_warning(f"Erro ao salvar: {exc}")

    def _show_io_error(self, exc: BaseException) -> None:
        """ErrorDialog modal para erros criticos irrecuperaveis de I/O do banco."""
        try:
            from task_manager_desktop.ui.dialogs import ErrorDialog
        except Exception:  # noqa: BLE001
            return
        db_path = getattr(self._repo, "db_path", "") if self._repo else ""
        ErrorDialog.show_io_error(self, exc, str(db_path))

    def _show_toast_warning(self, message: str) -> None:
        try:
            from task_manager_desktop.ui.toast import ToastWidget
            top = self.window()
            if isinstance(top, QWidget):
                toast = ToastWidget(top)
                toast.show_message(message)
        except Exception:  # noqa: BLE001
            pass
