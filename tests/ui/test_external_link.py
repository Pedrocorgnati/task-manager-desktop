from __future__ import annotations

import subprocess

from PySide6.QtCore import QUrl

from task_manager_desktop.ui._external_link import _open_external_link


def test_http_url_invokes_xdg_open(monkeypatch):
    captured = {}

    def fake_popen(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    result = _open_external_link(QUrl("https://example.com/path?q=1"))
    assert result is True
    assert captured["args"] == ["xdg-open", "https://example.com/path?q=1"]
    assert captured["kwargs"].get("start_new_session") is True


def test_https_scheme_uppercase_normalized(monkeypatch):
    called = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: called.append(a) or object())
    assert _open_external_link(QUrl("HTTPS://example.com")) is True
    assert len(called) == 1


def test_missing_xdg_open_logs_and_returns_false(monkeypatch, capsys):
    def raise_fnf(*args, **kwargs):
        raise FileNotFoundError("xdg-open")

    monkeypatch.setattr(subprocess, "Popen", raise_fnf)
    result = _open_external_link(QUrl("https://example.com"))
    assert result is False
    err = capsys.readouterr().err
    assert "xdg-open" in err
    assert "https://example.com" in err


def test_file_scheme_is_filtered(monkeypatch):
    called = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: called.append(a) or object())
    assert _open_external_link(QUrl("file:///etc/passwd")) is False
    assert called == []


def test_mailto_scheme_is_filtered(monkeypatch):
    called = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: called.append(a) or object())
    assert _open_external_link(QUrl("mailto:user@example.com")) is False
    assert called == []


def test_ftp_scheme_is_filtered(monkeypatch):
    called = []
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: called.append(a) or object())
    assert _open_external_link(QUrl("ftp://example.com/file")) is False
    assert called == []
