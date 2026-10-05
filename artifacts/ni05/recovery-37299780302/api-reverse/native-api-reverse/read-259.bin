"""D-f3: graph snapshot writers must actually land, fenced, and fail loudly.

Before the fix, ``SQLiteStatePersistence._write`` and the turn snapshot in
``src.graph.helpers._log_state_snapshot`` called
``save_checkpoint(session_id=, data=, checkpoint_type=)`` (or three positionals)
against a store whose method is ``save_checkpoint(checkpoint, *, fencing_token)``.
The ``TypeError`` was swallowed at DEBUG, so every snapshot was silently lost.
These tests run against a REAL ``SQLiteSessionStore``, so they fail on that code.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.features import Features, reset_features, set_features
from src.graph.helpers import _log_state_snapshot
from src.graph.nodes import FrontdoorNode
from src.graph.persistence import SQLiteStatePersistence
from src.graph.state import TaskDeps, TaskState
from src.roles import Role
from src.session import Session, SQLiteSessionStore
from src.session.lease import StaleFencingToken

SRC = Path(__file__).resolve().parents[2] / "src"


@pytest.fixture
def store(tmp_path):
    s = SQLiteSessionStore(
        db_path=tmp_path / "sessions.db", embeddings_path=tmp_path / "emb.npy"
    )
    yield s
    s.close()


@pytest.fixture
def session_id(store):
    session = Session.create(name="df3", working_directory="/tmp")
    store.create_session(session)
    return session.id


@pytest.fixture(autouse=True)
def _flags():
    set_features(Features(state_history_snapshots=True))
    yield
    reset_features()


def _ctx(store, task_id="task-df3", **deps):
    state = TaskState(task_id=task_id, current_role=Role.FRONTDOOR, turns=2)
    return SimpleNamespace(state=state, deps=TaskDeps(session_store=store, **deps))


# ── SQLiteStatePersistence._write ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_persistence_snapshot_lands_in_graph_snapshots(store):
    with pytest.warns(DeprecationWarning):
        persistence = SQLiteStatePersistence(store, "run-1")
    await persistence.snapshot_node(TaskState(task_id="t"), FrontdoorNode())
    rows = store.get_graph_snapshots("run-1")
    assert len(rows) == 1
    assert rows[0]["snapshot_type"] == "graph_snapshot"
    assert rows[0]["data"]["node_class"] == "FrontdoorNode"


@pytest.mark.asyncio
async def test_persistence_fenced_write_under_lease(store, session_id):
    lease = store.leases.try_acquire(session_id, ttl_s=30)
    with pytest.warns(DeprecationWarning):
        fenced = SQLiteStatePersistence(
            store, session_id, fencing_token=lease.fencing_token
        )
        unfenced = SQLiteStatePersistence(store, session_id)
    await fenced.snapshot_node(TaskState(task_id="t"), FrontdoorNode())
    await unfenced.snapshot_node(TaskState(task_id="t"), FrontdoorNode())
    rows = store.get_graph_snapshots(session_id)
    assert [r["fencing_token"] for r in rows] == [lease.fencing_token]
    store.leases.release(lease)


# ── helpers._log_state_snapshot ───────────────────────────────────────────


def test_turn_snapshot_lands_run_scoped(store):
    _log_state_snapshot(_ctx(store), "frontdoor")
    rows = store.get_graph_snapshots("task-df3")
    assert len(rows) == 1
    assert rows[0]["snapshot_type"] == "state_snapshot"
    assert rows[0]["session_id"] is None
    assert rows[0]["data"]["turn"] == 2
    assert rows[0]["data"]["role"] == "frontdoor"


def test_turn_snapshot_session_scoped_and_fenced(store, session_id):
    lease = store.leases.try_acquire(session_id, ttl_s=30)
    ctx = _ctx(store, session_id=session_id, session_fencing_token=lease.fencing_token)
    _log_state_snapshot(ctx, "frontdoor")
    rows = store.get_graph_snapshots("task-df3")
    assert len(rows) == 1
    assert rows[0]["session_id"] == session_id
    assert rows[0]["fencing_token"] == lease.fencing_token
    # A snapshot must never shadow the REPL restore checkpoint.
    assert store.get_latest_checkpoint(session_id) is None
    store.leases.release(lease)


def test_turn_snapshot_failure_is_a_warning(store, session_id, caplog):
    lease = store.leases.try_acquire(session_id, ttl_s=30)
    ctx = _ctx(store, session_id=session_id, session_fencing_token=None)
    with caplog.at_level(logging.WARNING, logger="src.graph.helpers"):
        _log_state_snapshot(ctx, "frontdoor")
    assert store.get_graph_snapshots("task-df3") == []
    assert any(
        r.levelno == logging.WARNING and "snapshot" in r.getMessage()
        for r in caplog.records
    )
    store.leases.release(lease)


def test_persistence_failure_is_a_warning(caplog):
    broken = MagicMock()
    broken.save_graph_snapshot.side_effect = TypeError("boom")
    with pytest.warns(DeprecationWarning):
        persistence = SQLiteStatePersistence(broken, "run-x")
    with caplog.at_level(logging.WARNING, logger="src.graph.persistence"):
        persistence._write({"type": "node"})
    assert any(
        r.levelno == logging.WARNING and "boom" in r.getMessage() for r in caplog.records
    )


# ── store writer fencing ──────────────────────────────────────────────────


def test_stale_token_refused_without_half_write(store, session_id):
    old = store.leases.try_acquire(session_id, ttl_s=30)
    store.leases.release(old)
    new = store.leases.try_acquire(session_id, ttl_s=30)
    with pytest.raises(StaleFencingToken):
        store.save_graph_snapshot(
            "r", "{}", "state_snapshot",
            session_id=session_id, fencing_token=old.fencing_token,
        )
    assert store.get_graph_snapshots("r") == []
    store.leases.release(new)


# ── structural guard: every save_checkpoint call matches the real API ─────


def _bad_save_checkpoint_calls(tree: ast.AST) -> list[int]:
    bad = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "save_checkpoint"
        ):
            kw = {k.arg for k in node.keywords}
            if len(node.args) != 1 or not kw <= {"fencing_token"}:
                bad.append(node.lineno)
    return bad


def test_guard_flags_the_pre_fix_shapes():
    old = (
        "store.save_checkpoint(session_id=s, data=d, checkpoint_type='g')\n"
        "store.save_checkpoint(t, d, 'state_snapshot')\n"
    )
    assert _bad_save_checkpoint_calls(ast.parse(old)) == [1, 2]


def test_no_mismatched_save_checkpoint_calls_in_src():
    offenders = []
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        # PersistenceManager.save_checkpoint(repl_env, trigger=...) is a
        # different API (src/session/persister.py) and is excluded by name.
        text = path.read_text(encoding="utf-8")
        for lineno in _bad_save_checkpoint_calls(tree):
            line = text.splitlines()[lineno - 1]
            if "persister" in line or "self.save_checkpoint(repl_env" in line:
                continue
            offenders.append(f"{path.relative_to(SRC)}:{lineno}")
    assert offenders == []
