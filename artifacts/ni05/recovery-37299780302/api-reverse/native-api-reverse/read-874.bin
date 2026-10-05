"""UTM-P1: cross-harness pairing keys on the unified trace event schema.

Covers the v2 columns (harness / seed / turn_ordinal / task_key / schema_version),
the additive migration of a v1 store, the NULL-projecting read path over an
unmigrated store, content-key identity for live emits, and ``paired_runs``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.trace import EVENT_SCHEMA_VERSION, Event, EventSource, ensure_schema, paired_runs, query, upsert_events
from src.trace.emit import ReviewTracingProcessor, Span, Trace, _content_key, emit
from src.trace.store import _SCHEMA as _store_schema
from src.trace.store import EVENT_PAIRING_COLUMNS, event_columns, migrate_event_pairing_columns

# The store exactly as T1 created it, before UTM-P1: the current DDL (event
# table, FTS5 mirror, triggers) with the v2 column lines removed.
_V2_COLUMN_LINES = (
    "  harness TEXT,\n",
    "  seed INTEGER,\n",
    "  turn_ordinal INTEGER,\n",
    "  task_key TEXT,\n",
    "  schema_version INTEGER,\n",
)
_V1_EVENT_DDL = _store_schema
for _line in _V2_COLUMN_LINES:
    assert _line in _V1_EVENT_DDL, _line
    _V1_EVENT_DDL = _V1_EVENT_DDL.replace(_line, "")

_PAIRING_NAMES = [n for n, _ in EVENT_PAIRING_COLUMNS]


def _make_v1_store(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(_V1_EVENT_DDL)
    conn.execute(
        "INSERT INTO event (ts_utc, source, source_path, source_line, summary) "
        "VALUES ('2026-01-01T00:00:00+00:00', 'agent_audit', '/log', 1, 'legacy row')"
    )
    conn.commit()
    conn.close()


def _ev(harness: str | None, turn: int | None, *, line: int, seed: int | None = 7, **kw) -> Event:
    return Event(
        ts_utc=f"2026-09-17T00:00:{line:02d}+00:00",
        source=EventSource.AUTOPILOT_LIVE,
        source_path=f"/runs/{harness}",
        source_line=line,
        summary=f"{harness} turn {turn}",
        harness=harness,
        seed=seed,
        turn_ordinal=turn,
        task_key=kw.pop("task_key", "task-A"),
        **kw,
    )


# ── schema / dataclass ────────────────────────────────────────────────────────


def test_fresh_store_has_pairing_columns_and_index(tmp_path: Path) -> None:
    conn = ensure_schema(tmp_path / "e.sqlite")
    assert set(_PAIRING_NAMES) <= event_columns(conn)
    idx = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert "event_pairing" in idx
    conn.close()


def test_new_event_is_stamped_with_current_schema_version() -> None:
    ev = Event(ts_utc="t", source="s", source_path="/p")
    assert ev.schema_version == EVENT_SCHEMA_VERSION == 2
    assert ev.pairing_key() == (None, None, None)


def test_event_coerces_and_validates_pairing_keys() -> None:
    ev = Event(ts_utc="t", source="s", source_path="/p", seed="42", turn_ordinal="3", harness="  hermes ")
    assert (ev.seed, ev.turn_ordinal, ev.harness) == (42, 3, "hermes")
    with pytest.raises(TypeError):
        Event(ts_utc="t", source="s", source_path="/p", seed=True)
    with pytest.raises(TypeError):
        Event(ts_utc="t", source="s", source_path="/p", seed=3.7)
    with pytest.raises(ValueError):
        Event(ts_utc="t", source="s", source_path="/p", turn_ordinal=-1)


def test_pairing_keys_round_trip(tmp_path: Path) -> None:
    db = tmp_path / "e.sqlite"
    conn = ensure_schema(db)
    upsert_events(conn, [_ev("orchestrator", 0, line=1)])
    conn.close()
    (row,) = query(db_path=db)
    assert (row["harness"], row["seed"], row["turn_ordinal"], row["task_key"]) == ("orchestrator", 7, 0, "task-A")
    assert row["schema_version"] == EVENT_SCHEMA_VERSION


# ── migration / backward compatibility ────────────────────────────────────────


def test_v1_store_migrates_additively_without_backfill(tmp_path: Path) -> None:
    db = tmp_path / "v1.sqlite"
    _make_v1_store(db)
    conn = ensure_schema(db)
    assert set(_PAIRING_NAMES) <= event_columns(conn)
    legacy = conn.execute(
        "SELECT summary, harness, seed, turn_ordinal, task_key, schema_version FROM event"
    ).fetchone()
    # Legacy rows are untouched: NULL schema_version means "never captured".
    assert legacy == ("legacy row", None, None, None, None, None)
    upsert_events(conn, [_ev("hermes", 0, line=1)])
    assert conn.execute("SELECT COUNT(*) FROM event").fetchone()[0] == 2
    conn.close()
    # Idempotent: a second ensure_schema must not raise.
    ensure_schema(db).close()


def test_upsert_migrates_a_v1_connection_that_skipped_ensure_schema(tmp_path: Path) -> None:
    db = tmp_path / "v1.sqlite"
    _make_v1_store(db)
    conn = sqlite3.connect(str(db))
    ins, skp = upsert_events(conn, [_ev("hermes", 1, line=2)])
    assert (ins, skp) == (1, 0)
    assert set(_PAIRING_NAMES) <= event_columns(conn)
    conn.close()


def test_query_reads_unmigrated_v1_store_with_null_pairing_keys(tmp_path: Path) -> None:
    db = tmp_path / "v1.sqlite"
    _make_v1_store(db)
    (row,) = query(db_path=db)
    assert row["summary"] == "legacy row"
    assert all(row[n] is None for n in _PAIRING_NAMES)
    (row,) = query(db_path=db, text="legacy")  # FTS path
    assert row["harness"] is None
    # A pairing filter cannot match a store that never captured pairing keys.
    assert query(db_path=db, harness="hermes") == []
    # The read path must not have migrated the store.
    conn = sqlite3.connect(str(db))
    assert "harness" not in event_columns(conn)
    conn.close()


def test_migration_tolerates_read_only_connection(tmp_path: Path) -> None:
    db = tmp_path / "v1.sqlite"
    _make_v1_store(db)
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    assert migrate_event_pairing_columns(conn) is False
    conn.close()


# ── emit identity ─────────────────────────────────────────────────────────────


def test_content_key_unchanged_for_unpaired_events() -> None:
    """Pre-v2 live keys must stay byte-identical so re-emits remain no-ops."""
    import hashlib

    ev = Event(ts_utc="t", source="review_plane", source_path="", summary="x", detail_json="{}")
    legacy_material = "\x1f".join(str(x) for x in ("t", "review_plane", None, None, None, None, None, "x", "{}"))
    assert _content_key(ev) == hashlib.sha1(legacy_material.encode()).hexdigest()[:16]


def test_emit_keeps_two_harnesses_with_identical_content_apart(tmp_path: Path) -> None:
    db = tmp_path / "e.sqlite"
    base = dict(ts_utc="2026-09-17T00:00:00+00:00", source="review_plane", source_path="", summary="same")
    assert emit(Event(**base, harness="orchestrator", task_key="T"), db_path=db) == (1, 0)
    assert emit(Event(**base, harness="hermes", task_key="T"), db_path=db) == (1, 0)
    assert emit(Event(**base, harness="hermes", task_key="T"), db_path=db) == (0, 1)


def test_tracing_processor_threads_pairing_keys(tmp_path: Path) -> None:
    db = tmp_path / "e.sqlite"
    proc = ReviewTracingProcessor(db_path=db)
    trace = Trace(trace_id="tr1", metadata={"harness": "hermes", "seed": 5, "task_key": "T"})
    proc.on_trace_start(trace)
    proc.on_span_end(Span(span_id="s1", trace_id="tr1", span_data={"summary": "turn", "turn_ordinal": 2}))
    proc.on_trace_end(trace)
    proc.shutdown()
    rows = query(db_path=db, task_key="T", seed=5, harness="hermes")
    assert len(rows) == 3
    assert {r["turn_ordinal"] for r in rows} == {None, 2}
    span_row = next(r for r in rows if r["turn_ordinal"] == 2)
    assert '"turn_ordinal"' not in span_row["detail_json"]


# ── pairing query ─────────────────────────────────────────────────────────────


def test_paired_runs_groups_by_turn_then_harness(tmp_path: Path) -> None:
    db = tmp_path / "e.sqlite"
    conn = ensure_schema(db)
    upsert_events(
        conn,
        [
            _ev("orchestrator", 0, line=1),
            _ev("hermes", 0, line=2),
            _ev("orchestrator", 1, line=3),
            _ev("hermes", 1, line=4),
            _ev("hermes", 1, line=5, seed=8),  # other seed: not paired with seed 7
            _ev("hermes", 0, line=6, task_key="task-B"),  # other task
            _ev(None, 0, line=7),  # unattributed: cannot be one side of a pair
        ],
    )
    conn.close()
    pairs = paired_runs("task-A", db_path=db, seed=7)
    assert set(pairs) == {0, 1}
    assert set(pairs[0]) == {"orchestrator", "hermes"}
    assert [r["summary"] for r in pairs[1]["hermes"]] == ["hermes turn 1"]
    only = paired_runs("task-A", db_path=db, seed=7, harnesses=["hermes"])
    assert all(set(v) == {"hermes"} for v in only.values())
    assert paired_runs("task-A", db_path=tmp_path / "missing.sqlite") == {}
