"""Unit tests for src/trace/."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

import pytest

from src.trace import (
    Event,
    EventCategory,
    EventSource,
    ensure_schema,
    upsert_events,
    query,
    trial_context,
)
from src.trace import ingest_agent_audit, ingest_autopilot, ingest_progress


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "events.sqlite"


# ─── store / schema ───────────────────────────────────────────────────────────

def test_ensure_schema_creates_tables(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    tables = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','index')"
        ).fetchall()
    }
    conn.close()
    assert "event" in tables
    assert "event_fts" in tables
    assert "event_ts" in tables
    assert "event_session" in tables


def test_ensure_schema_idempotent(db_path: Path) -> None:
    ensure_schema(db_path).close()
    # Second call must not raise even though triggers/tables exist.
    ensure_schema(db_path).close()


def test_upsert_dedup_by_source_line(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    ev = Event(
        ts_utc="2026-05-06T12:00:00+00:00",
        source=EventSource.AGENT_AUDIT,
        source_path="/tmp/log.log",
        source_line=42,
        summary="hello",
        detail_json='{"x": 1}',
    )
    ins, skp = upsert_events(conn, [ev])
    assert (ins, skp) == (1, 0)
    ins, skp = upsert_events(conn, [ev])
    assert (ins, skp) == (0, 1)
    # Different line: counts as new.
    ev2 = Event(**{**ev.__dict__, "source_line": 43})
    ins, skp = upsert_events(conn, [ev2])
    assert (ins, skp) == (1, 0)
    conn.close()


def test_fts_search_returns_matching_rows(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    upsert_events(
        conn,
        [
            Event(
                ts_utc="2026-05-06T12:00:00+00:00",
                source=EventSource.AGENT_AUDIT,
                source_path="/x",
                source_line=1,
                summary="auroras over Norway",
                detail_json='{"detail": "text"}',
            ),
            Event(
                ts_utc="2026-05-06T12:01:00+00:00",
                source=EventSource.AGENT_AUDIT,
                source_path="/x",
                source_line=2,
                summary="cooking pasta",
                detail_json='{"detail": "text"}',
            ),
        ],
    )
    conn.close()

    rows = query(db_path=db_path, text="auroras")
    assert len(rows) == 1
    assert rows[0]["summary"] == "auroras over Norway"

    # Prefix search via FTS5 syntax.
    rows = query(db_path=db_path, text="aurora*")
    assert len(rows) == 1


# ─── agent_audit parser ───────────────────────────────────────────────────────

def test_parse_json_line() -> None:
    line = (
        '{"ts":"2026-05-06T12:00:00+00:00","session":"ses_test",'
        '"level":"INFO","cat":"TASK_END","msg":"do thing","details":"outcome=success"}'
    )
    events = list(ingest_agent_audit.parse_lines([line], "/path/log"))
    assert len(events) == 1
    ev = events[0]
    assert ev.session_id == "ses_test"
    assert ev.category == EventCategory.TASK_END
    assert ev.status == "success"
    assert ev.summary == "do thing"
    assert ev.source == EventSource.AGENT_AUDIT
    assert ev.source_line == 1


def test_parse_text_line() -> None:
    line = '[2026-05-06T12:00:00+00:00] TASK_END: Run benchmark | status=success | dur=12s'
    events = list(ingest_agent_audit.parse_lines([line], "/path/log"))
    assert len(events) == 1
    ev = events[0]
    assert ev.category == EventCategory.TASK_END
    assert ev.status == "success"
    assert ev.summary == "Run benchmark"
    detail = json.loads(ev.detail_json)
    assert detail["extras"]["dur"] == "12s"


def test_parse_skips_blank_and_malformed_lines() -> None:
    lines = [
        "",
        "   ",
        "garbage line not in any format",
        '[1, 2, 3]',  # JSON array, not a dict — _parse_json_line returns None
        "[no-format-match] random text without ALL_CAPS category",
        '{"ts":"2026-01-01T00:00:00Z","cat":"OBSERVE","msg":"ok","session":"s"}',
    ]
    events = list(ingest_agent_audit.parse_lines(lines, "/p"))
    # Only the last line should parse.
    assert len(events) == 1
    assert events[0].summary == "ok"


def test_parse_file_returns_empty_for_missing_path(tmp_path: Path) -> None:
    assert ingest_agent_audit.parse_file(tmp_path / "nope.log") == []


# ─── autopilot parser (no-op-when-absent) ─────────────────────────────────────

def test_autopilot_emits_unavailable_when_files_missing(tmp_path: Path) -> None:
    events = ingest_autopilot.parse_all(
        tsv_path=tmp_path / "missing.tsv",
        jsonl_path=tmp_path / "missing.jsonl",
        state_path=tmp_path / "missing.json",
    )
    assert len(events) == 3
    assert all(ev.category == EventCategory.SOURCE_UNAVAILABLE for ev in events)
    assert all(ev.status == "absent" for ev in events)


def test_autopilot_parses_tsv_and_jsonl(tmp_path: Path) -> None:
    tsv = tmp_path / "j.tsv"
    tsv.write_text(
        "trial_id\tts\trole\tstatus\tnote\n"
        "1\t2026-05-06T12:00:00+00:00\tcoder\tsuccess\tfirst trial\n"
        "2\t2026-05-06T12:05:00+00:00\tarchitect\tfail\tregression\n"
    )
    jsonl = tmp_path / "j.jsonl"
    jsonl.write_text(
        '{"trial_id": 1, "ts": "2026-05-06T12:00:30+00:00", "event": "mutation", "summary": "applied X"}\n'
    )
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"current_trial": 2, "ts": "2026-05-06T12:05:30+00:00"}))

    events = ingest_autopilot.parse_all(tsv, jsonl, state)
    assert len(events) >= 4  # 2 tsv + 1 jsonl + 1 state (no unavailable since all exist)
    trial_ids = {ev.trial_id for ev in events if ev.trial_id is not None}
    assert trial_ids == {1, 2}


# ─── progress parser ──────────────────────────────────────────────────────────

def test_progress_parses_headings(tmp_path: Path) -> None:
    md_root = tmp_path / "progress" / "2026-05"
    md_root.mkdir(parents=True)
    md = md_root / "2026-05-06.md"
    md.write_text(
        dedent(
            """
            # 2026-05-06 progress

            Some intro paragraph.

            ## Session 1 — refactor

            Refactored the foo module.

            ## Session 2 — bench

            Ran benchmarks.
            """
        ).strip()
    )

    events = ingest_progress.walk_progress_root(tmp_path / "progress")
    summaries = [ev.summary for ev in events]
    # At least: file-level + 2 ## headings.
    assert "progress 2026-05-06" in summaries
    assert "Session 1 — refactor" in summaries
    assert "Session 2 — bench" in summaries


def test_progress_returns_empty_when_root_absent(tmp_path: Path) -> None:
    assert ingest_progress.walk_progress_root(tmp_path / "no_such_dir") == []


# ─── query filters ────────────────────────────────────────────────────────────

def test_query_filter_combinations(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    upsert_events(
        conn,
        [
            Event(
                ts_utc="2026-05-01T00:00:00+00:00",
                source=EventSource.AGENT_AUDIT,
                source_path="/x",
                source_line=1,
                session_id="A",
                category="task_start",
                status="running",
                summary="early",
            ),
            Event(
                ts_utc="2026-05-05T00:00:00+00:00",
                source=EventSource.AGENT_AUDIT,
                source_path="/x",
                source_line=2,
                session_id="B",
                category="task_end",
                status="success",
                summary="recent",
            ),
        ],
    )
    conn.close()

    # Filter by date range.
    rows = query(db_path=db_path, from_ts="2026-05-04T00:00:00+00:00")
    assert len(rows) == 1
    assert rows[0]["summary"] == "recent"

    # Filter by session_id.
    rows = query(db_path=db_path, session_id="A")
    assert len(rows) == 1
    assert rows[0]["summary"] == "early"

    # Filter by category.
    rows = query(db_path=db_path, category="task_end")
    assert len(rows) == 1
    assert rows[0]["status"] == "success"

    # Limit.
    rows = query(db_path=db_path, limit=1)
    assert len(rows) == 1
    # Order: most recent first.
    assert rows[0]["summary"] == "recent"


def test_trial_context_includes_nearby_cross_source_rows(db_path: Path) -> None:
    conn = ensure_schema(db_path)
    upsert_events(
        conn,
        [
            Event(
                ts_utc="2026-05-06T11:45:00+00:00",
                source=EventSource.AGENT_AUDIT,
                source_path="/audit",
                source_line=1,
                session_id="S",
                category=EventCategory.TASK_START,
                summary="prepare trial",
            ),
            Event(
                ts_utc="2026-05-06T12:00:00+00:00",
                source=EventSource.AUTOPILOT_JOURNAL,
                source_path="/journal",
                source_line=1,
                trial_id=7,
                category="trial_summary",
                summary="trial 7 summary",
            ),
            Event(
                ts_utc="2026-05-06T12:04:00+00:00",
                source=EventSource.AUTOPILOT_JOURNAL,
                source_path="/journal-jsonl",
                source_line=1,
                trial_id=7,
                category="mutation",
                summary="trial 7 mutation",
            ),
            Event(
                ts_utc="2026-05-06T12:15:00+00:00",
                source=EventSource.PROGRESS,
                source_path="/progress",
                source_line=1,
                category=EventCategory.SESSION_SUMMARY,
                summary="nearby progress note",
            ),
            Event(
                ts_utc="2026-05-06T14:00:00+00:00",
                source=EventSource.PROGRESS,
                source_path="/progress",
                source_line=2,
                category=EventCategory.SESSION_SUMMARY,
                summary="outside window",
            ),
        ],
    )
    conn.close()

    ctx = trial_context(db_path=db_path, trial_id=7, window_minutes=20, limit=20)

    assert ctx["counts"] == {"trial_events": 2, "context_events": 2, "timeline": 4}
    assert [row["summary"] for row in ctx["trial_events"]] == [
        "trial 7 summary",
        "trial 7 mutation",
    ]
    timeline = [row["summary"] for row in ctx["timeline"]]
    assert timeline == [
        "prepare trial",
        "trial 7 summary",
        "trial 7 mutation",
        "nearby progress note",
    ]
    assert "outside window" not in timeline


def test_trial_context_handles_missing_trial(db_path: Path) -> None:
    ensure_schema(db_path).close()

    ctx = trial_context(db_path=db_path, trial_id=404)

    assert ctx["trial_id"] == 404
    assert ctx["from_ts"] is None
    assert ctx["counts"] == {"trial_events": 0, "context_events": 0, "timeline": 0}
