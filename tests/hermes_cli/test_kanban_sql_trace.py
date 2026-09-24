from __future__ import annotations

import logging
import sqlite3

from hermes_cli import kanban_sql_trace as trace


def test_trace_is_enabled_by_default(monkeypatch):
    monkeypatch.delenv("HERMES_KANBAN_SQL_TRACE", raising=False)
    assert trace._enabled() is True


def test_trace_can_be_explicitly_disabled(monkeypatch):
    for value in ("0", "false", "no", "off", " FALSE "):
        monkeypatch.setenv("HERMES_KANBAN_SQL_TRACE", value)
        assert trace._enabled() is False


def _db(tmp_path):
    conn = sqlite3.connect(tmp_path / "trace.db")
    conn.execute(
        "CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT, body TEXT, status TEXT)"
    )
    conn.execute("CREATE TABLE other (id TEXT, value TEXT)")
    return conn


def test_task_write_trace_logs_shape_stack_and_context_without_values(
    tmp_path, monkeypatch, caplog
):
    conn = _db(tmp_path)
    monkeypatch.setenv("HERMES_PROFILE", "mara")
    monkeypatch.setenv("HERMES_KANBAN_BOARD", "default")
    trace._install_connection_trace(conn, tmp_path / "trace.db")

    caplog.set_level(logging.WARNING, logger=trace.logger.name)
    conn.execute(
        "INSERT INTO tasks (id, title, body, status) VALUES (?, ?, ?, ?)",
        ("t_deadbeef", "secret title", "very secret body", "running"),
    )

    text = caplog.text
    assert "[kanban-sql-trace] tasks write" in text
    assert "INSERT INTO tasks" in text
    assert "profile_env='mara'" in text
    assert "board_env='default'" in text
    assert "test_kanban_sql_trace.py" in text
    assert "t_deadbeef" not in text
    assert "secret title" not in text
    assert "very secret body" not in text
    conn.close()


def test_trace_ignores_reads_and_other_tables(tmp_path, caplog):
    conn = _db(tmp_path)
    trace._install_connection_trace(conn, tmp_path / "trace.db")
    caplog.set_level(logging.WARNING, logger=trace.logger.name)

    conn.execute("SELECT * FROM tasks").fetchall()
    conn.execute("INSERT INTO other (id, value) VALUES (?, ?)", ("x", "hidden"))

    assert "[kanban-sql-trace]" not in caplog.text
    conn.close()


def test_redaction_removes_string_blob_and_numeric_literals():
    shaped = trace._redacted_sql_shape(
        "UPDATE tasks SET body='don''t leak', priority=42, result=X'CAFE' "
        "WHERE id='t_deadbeef'"
    )
    assert "don't leak" not in shaped
    assert "42" not in shaped
    assert "CAFE" not in shaped
    assert "t_deadbeef" not in shaped
    assert shaped.startswith("UPDATE tasks SET")
