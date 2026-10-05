"""CLI coverage for read-only trace navigation tools."""

from __future__ import annotations

import json

from src.trace import Event, EventSource, ensure_schema, upsert_events
from src.trace import cli as trace_cli


def _seed_trace(db_path):
    conn = ensure_schema(db_path)
    upsert_events(
        conn,
        [
            Event(
                ts_utc="2026-07-11T12:00:00+00:00",
                source=EventSource.AGENT_AUDIT,
                source_path="/trace/audit.log",
                source_line=1,
                session_id="session-a",
                trial_id=7,
                category="task_start",
                summary="alpha trace setup",
                detail_json='{"body":"alpha details"}',
            ),
            Event(
                ts_utc="2026-07-11T12:01:00+00:00",
                source=EventSource.AGENT_AUDIT,
                source_path="/trace/audit.log",
                source_line=2,
                session_id="session-a",
                trial_id=7,
                category="task_end",
                summary="beta trace result",
                detail_json='{"body":"beta details"}',
            ),
        ],
    )
    conn.close()


def test_search_records_cli_outputs_json(tmp_path, capsys):
    db_path = tmp_path / "events.sqlite"
    _seed_trace(db_path)

    rc = trace_cli.main(["--db", str(db_path), "search-records", "--text", "alpha", "--json"])

    assert rc == 0
    rows = json.loads(capsys.readouterr().out)
    assert rows[0]["summary"] == "alpha trace setup"


def test_search_and_get_conversation_cli_outputs_json(tmp_path, capsys):
    db_path = tmp_path / "events.sqlite"
    _seed_trace(db_path)

    rc = trace_cli.main(
        [
            "--db",
            str(db_path),
            "search-conversation",
            "--text",
            "result",
            "--session",
            "session-a",
            "--json",
        ]
    )
    assert rc == 0
    rows = json.loads(capsys.readouterr().out)
    assert [row["summary"] for row in rows] == ["beta trace result"]

    rc = trace_cli.main(
        [
            "--db",
            str(db_path),
            "get-conversation",
            "--session",
            "session-a",
            "--json",
        ]
    )
    assert rc == 0
    conversation = json.loads(capsys.readouterr().out)
    assert [row["summary"] for row in conversation["timeline"]] == [
        "alpha trace setup",
        "beta trace result",
    ]


def test_get_records_cli_preserves_order(tmp_path, capsys):
    db_path = tmp_path / "events.sqlite"
    _seed_trace(db_path)
    rows = json.loads(
        _run_json(capsys, ["--db", str(db_path), "search-records", "--text", "trace", "--json"])
    )
    by_summary = {row["summary"]: row["id"] for row in rows}

    rc = trace_cli.main(
        [
            "--db",
            str(db_path),
            "get-records",
            str(by_summary["beta trace result"]),
            str(by_summary["alpha trace setup"]),
            "--json",
        ]
    )

    assert rc == 0
    fetched = json.loads(capsys.readouterr().out)
    assert [row["summary"] for row in fetched] == ["beta trace result", "alpha trace setup"]


def test_read_file_cli_is_allowlisted(tmp_path, capsys):
    root = tmp_path / "allowed"
    root.mkdir()
    path = root / "note.md"
    path.write_text("hello trace\n", encoding="utf-8")

    rc = trace_cli.main(
        [
            "read-file",
            str(path),
            "--allowed-root",
            str(root),
            "--max-bytes",
            "100",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["content"] == "hello trace\n"
    assert payload["truncated"] is False


def _run_json(capsys, argv: list[str]) -> str:
    assert trace_cli.main(argv) == 0
    return capsys.readouterr().out
