from __future__ import annotations


def test_permission_error_uses_error_dialog_not_qmessagebox(monkeypatch, tmp_path):
    """Quando first-run falha com PermissionError, ErrorDialog e disparado (nao QMessageBox)."""
    from task_manager_desktop.core.db import close_connection
    close_connection()

    error_dialog_calls = []
    qmessagebox_calls = []

    monkeypatch.setattr(
        "task_manager_desktop.app.ensure_data_dir_and_db",
        lambda: (_ for _ in ()).throw(PermissionError(13, "Permission denied", "/no/access")),
    )
    monkeypatch.setattr(
        "task_manager_desktop.app.ErrorDialog.show_io_error",
        lambda parent, exception, db_path: error_dialog_calls.append((exception, db_path)) or 1,
    )
    monkeypatch.setattr(
        "task_manager_desktop.app.sys.exit",
        lambda code: None,
    )

    from task_manager_desktop.app import main
    main()

    assert len(error_dialog_calls) == 1, "ErrorDialog.show_io_error deve ser chamado exatamente uma vez"
    assert len(qmessagebox_calls) == 0, "QMessageBox.critical NAO deve ser chamado"
    assert isinstance(error_dialog_calls[0][0], PermissionError)
