"""DAR-L491 append-only consolidation migration.

Pins the migration's core guarantees:
  * replay equivalence — consolidated Q == the incremental TD result a live store
    would have produced (episodic_store.update_q_value), decay off
  * temporal decay is applied over the created_at gap
  * idempotency — re-running rebuilds byte-identical consolidated tables
  * --dry-run writes nothing
  * --exclude-memory-ids drops rows before replay
  * uc>0 and objective-NULL rows pass through verbatim
  * refuses to WRITE the live sessions store
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

from orchestration.repl_memory.episodic_store import EpisodicStore

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts" / "maintenance" / "consolidate_q_append_only.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("consolidate_q_append_only", MIGRATION_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mig = _load_migration()

_COLS = (
    "id, embedding_idx, action, action_type, context, outcome, q_value, "
    "created_at, updated_at, update_count, model_id, assigned_role, sub_decision"
)


def _make_db(tmp_path) -> Path:
    db = tmp_path / "episodic.db"
    con = sqlite3.connect(db)
    con.execute(
        """
        CREATE TABLE memories (
            id TEXT PRIMARY KEY,
            embedding_idx INTEGER NOT NULL,
            action TEXT NOT NULL,
            action_type TEXT NOT NULL,
            context TEXT NOT NULL,
            outcome TEXT,
            q_value REAL DEFAULT 0.5,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            update_count INTEGER DEFAULT 0,
            model_id TEXT,
            assigned_role TEXT,
            sub_decision TEXT
        )
        """
    )
    con.commit()
    con.close()
    return db


def _insert(db, *, rid, action, objective, q, created_at, update_count=0,
            action_type="routing", outcome="success"):
    if objective is None:
        context = json.dumps({"task_description": "no-objective row"})
    else:
        context = json.dumps({"task_type": "chat", "objective": objective, "priority": "normal"})
    con = sqlite3.connect(db)
    con.execute(
        f"INSERT INTO memories ({_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (rid, 0, action, action_type, context, outcome, q, created_at, created_at,
         update_count, None, None, None),
    )
    con.commit()
    con.close()


def _consolidated_rows(db):
    con = sqlite3.connect(db)
    rows = con.execute(
        f"SELECT {_COLS} FROM memories_consolidated ORDER BY id"
    ).fetchall()
    con.close()
    return rows


def _table_exists(db, name):
    con = sqlite3.connect(db)
    r = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    con.close()
    return r is not None


def test_replay_equivalence_matches_update_q_value(tmp_path):
    """Consolidated Q == what a live EpisodicStore would compute via TD (decay off)."""
    db = _make_db(tmp_path)
    qs = [0.7, 0.6, 0.9]
    for i, q in enumerate(qs):
        _insert(db, rid=f"r{i}", action="worker_general", objective="obj",
                q=q, created_at=f"2026-01-0{i + 1}T00:00:00+00:00")

    mig.run(db, dry_run=False, temporal_decay_rate=None)

    rows = _consolidated_rows(db)
    assert len(rows) == 1  # three observations -> one consolidated row
    consolidated_q = rows[0][6]
    consolidated_uc = rows[0][9]

    # Oracle: drive the real live update path with the recovered rewards.
    store = EpisodicStore(db_path=tmp_path / "oracle", use_faiss=True)
    import numpy as np
    # A non-degenerate placeholder: this test is about Q-value replay, so the
    # vector is irrelevant to what it asserts — but store() now refuses all-zero
    # embeddings, since that is exactly what an embedder outage writes.
    placeholder = np.full(1024, 1.0 / 32.0, dtype=np.float32)
    mid = store.store(placeholder, "worker_general", "routing",
                      {"objective": "obj"}, initial_q=qs[0])
    for q in qs[1:]:
        store.update_q_value(mid, 2.0 * q - 1.0, 0.1, temporal_decay_rate=None)
    oracle = store.get_by_id(mid)
    store.close()

    assert consolidated_q == pytest.approx(oracle.q_value)
    assert consolidated_uc == oracle.update_count == 2


def test_replay_applies_temporal_decay(tmp_path):
    db = _make_db(tmp_path)
    _insert(db, rid="a", action="worker_general", objective="obj",
            q=0.8, created_at="2026-01-01T00:00:00+00:00")
    _insert(db, rid="b", action="worker_general", objective="obj",
            q=0.6, created_at="2026-01-11T00:00:00+00:00")  # +10 days

    mig.run(db, dry_run=False, temporal_decay_rate=0.99)
    q = _consolidated_rows(db)[0][6]

    from orchestration.repl_memory.episodic_store import apply_td_update
    expected = apply_td_update(0.8, 2.0 * 0.6 - 1.0, 0.1,
                               days_elapsed=10.0, temporal_decay_rate=0.99)
    assert q == pytest.approx(expected)


def test_idempotent(tmp_path):
    db = _make_db(tmp_path)
    for i, q in enumerate([0.7, 0.6, 0.9]):
        _insert(db, rid=f"r{i}", action="worker_general", objective="obj",
                q=q, created_at=f"2026-01-0{i + 1}T00:00:00+00:00")
    _insert(db, rid="p", action="architect_general", objective="obj2",
            q=0.9, created_at="2026-02-01T00:00:00+00:00", update_count=3)

    mig.run(db, dry_run=False)
    first = _consolidated_rows(db)
    mig.run(db, dry_run=False)
    second = _consolidated_rows(db)
    assert first == second


def test_dry_run_writes_nothing(tmp_path):
    db = _make_db(tmp_path)
    _insert(db, rid="r0", action="worker_general", objective="obj",
            q=0.7, created_at="2026-01-01T00:00:00+00:00")
    mig.run(db, dry_run=True)
    assert not _table_exists(db, mig.CONSOLIDATED_TABLE)
    assert not _table_exists(db, mig.META_TABLE)


def test_exclude_memory_ids(tmp_path):
    db = _make_db(tmp_path)
    qs = [0.7, 0.6, 0.9]
    for i, q in enumerate(qs):
        _insert(db, rid=f"r{i}", action="worker_general", objective="obj",
                q=q, created_at=f"2026-01-0{i + 1}T00:00:00+00:00")
    # Exclude the middle observation -> replay only r0, r2.
    mig.run(db, dry_run=False, temporal_decay_rate=None, exclude_ids={"r1"})
    rows = _consolidated_rows(db)
    assert len(rows) == 1
    assert rows[0][9] == 1  # two surviving observations -> update_count 1

    from orchestration.repl_memory.episodic_store import apply_td_update
    expected = apply_td_update(0.7, 2.0 * 0.9 - 1.0, 0.1, temporal_decay_rate=None)
    assert rows[0][6] == pytest.approx(expected)


def test_passthrough_uc_gt0_and_null_objective(tmp_path):
    db = _make_db(tmp_path)
    # append-only group (consolidated)
    _insert(db, rid="g0", action="worker_general", objective="obj",
            q=0.7, created_at="2026-01-01T00:00:00+00:00")
    _insert(db, rid="g1", action="worker_general", objective="obj",
            q=0.6, created_at="2026-01-02T00:00:00+00:00")
    # already-TD-updated row (passthrough)
    _insert(db, rid="learned", action="architect_general", objective="obj2",
            q=0.83, created_at="2026-01-03T00:00:00+00:00", update_count=4)
    # objective-NULL row (passthrough)
    _insert(db, rid="noobj", action="worker_general", objective=None,
            q=0.55, created_at="2026-01-04T00:00:00+00:00")

    mig.run(db, dry_run=False)

    ids = {r[0] for r in _consolidated_rows(db)}
    # one consolidated (g0 representative) + two passthrough
    assert "g0" in ids and "learned" in ids and "noobj" in ids
    assert "g1" not in ids  # collapsed into g0

    con = sqlite3.connect(db)
    prov = dict(con.execute(
        f"SELECT consolidated_id, method FROM {mig.PROVENANCE_TABLE}"
    ).fetchall())
    con.close()
    assert prov["g0"] == "td_replay"
    assert prov["learned"] == "passthrough"
    assert prov["noobj"] == "passthrough"


def test_refuses_live_write(tmp_path, monkeypatch):
    db = _make_db(tmp_path)
    _insert(db, rid="r0", action="worker_general", objective="obj",
            q=0.7, created_at="2026-01-01T00:00:00+00:00")
    # Pretend this copy IS the live store.
    monkeypatch.setattr(mig, "LIVE_SESSIONS_DIR", db.parent)
    with pytest.raises(SystemExit):
        mig.run(db, dry_run=False)
    # dry-run against the "live" path is allowed (read-only).
    mig.run(db, dry_run=True)
