"""Tests for the orchestration sub-decision axis on episodic store.

Mirror of `test_episodic_store_assigned_role.py` (TR-2.2 precedent) for the
intake-548 5-class sub-decision taxonomy. Covers:

- Schema migration adds the column on a fresh DB.
- Schema migration is idempotent on a pre-existing DB.
- Writers persist `sub_decision` round-trip through retrieve_by_similarity,
  get_by_id, and get_all_memories.
- Legacy rows with NULL sub_decision survive read paths.
- Backfill heuristic classifies + writes correctly + is idempotent.

The polarity differs from `assigned_role`: NULL is the legitimate "this event
is not a sub-decision" answer, not a default. The backfill therefore leaves
many rows NULL on purpose. Tests assert that explicitly.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest

from orchestration.repl_memory.episodic_store import EpisodicStore
from scripts.memory.backfill_sub_decision import backfill, classify_sub_decision
from src.classifiers.subdecision_taxonomy import (
    DEFAULT_SUBDECISION,
    OrchestrationSubDecision,
    VALID_SUBDECISIONS,
    normalise_subdecision,
    subdecision_labelling_enabled,
)


@pytest.fixture
def tmp_store(tmp_path):
    store = EpisodicStore(db_path=tmp_path / "sessions", use_faiss=True)
    yield store
    store.close()


@pytest.fixture
def db_path(tmp_path) -> Path:
    return tmp_path / "sessions" / "episodic.db"


# ---------------------------------------------------------------------------
# Sub-decision taxonomy module
# ---------------------------------------------------------------------------
class TestSubDecisionTaxonomy:
    def test_default_is_none(self):
        # CRITICAL: opposite polarity to assigned_role. Default is NULL,
        # meaning "this event is not a sub-decision". Do NOT change this to
        # a sentinel string.
        assert DEFAULT_SUBDECISION is None

    def test_valid_set_has_five_classes(self):
        assert VALID_SUBDECISIONS == {
            "spawn",
            "delegate",
            "communicate",
            "aggregate",
            "stop",
        }

    def test_normalise_none_returns_none(self):
        assert normalise_subdecision(None) is None

    def test_normalise_empty_returns_none(self):
        assert normalise_subdecision("") is None
        assert normalise_subdecision("   ") is None

    def test_normalise_unknown_returns_none(self):
        # Unlike normalise_role, unknown values must NOT fall back to a
        # default — they return None.
        assert normalise_subdecision("supervisor") is None
        assert normalise_subdecision("planner") is None

    def test_normalise_uppercase_passthrough(self):
        assert normalise_subdecision("DELEGATE") == "delegate"

    def test_normalise_valid_passthrough(self):
        for d in OrchestrationSubDecision:
            assert normalise_subdecision(d.value) == d.value

    def test_feature_flag_default_off(self, monkeypatch):
        monkeypatch.delenv("ORCHESTRATOR_SUBDECISION_LABELLING", raising=False)
        assert subdecision_labelling_enabled() is False

    def test_feature_flag_on_with_truthy(self, monkeypatch):
        for val in ("1", "true", "yes", "on", "TRUE"):
            monkeypatch.setenv("ORCHESTRATOR_SUBDECISION_LABELLING", val)
            assert subdecision_labelling_enabled() is True


# ---------------------------------------------------------------------------
# Schema migration
# ---------------------------------------------------------------------------
class TestSchemaMigration:
    def test_sub_decision_column_present_on_fresh_db(self, tmp_store):
        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(memories)")}
        assert "sub_decision" in cols

    def test_index_created(self, tmp_store):
        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            indexes = {
                row[1]
                for row in conn.execute(
                    "SELECT type, name FROM sqlite_master "
                    "WHERE type='index' AND tbl_name='memories'"
                )
            }
        assert "idx_sub_decision" in indexes

    def test_migration_idempotent(self, tmp_path):
        p = tmp_path / "sessions"
        s1 = EpisodicStore(db_path=p, use_faiss=True)
        s1.close()
        s2 = EpisodicStore(db_path=p, use_faiss=True)
        s2.close()


# ---------------------------------------------------------------------------
# Writer round-trip
# ---------------------------------------------------------------------------
class TestWriterRoundTrip:
    def _emb(self, seed: int = 0) -> np.ndarray:
        return np.random.default_rng(seed).standard_normal(1024).astype(np.float32)

    def test_store_persists_sub_decision(self, tmp_store):
        mid = tmp_store.store(
            self._emb(),
            "delegate:worker_general",
            "routing",
            {"task_type": "code"},
            sub_decision="delegate",
        )
        mem = tmp_store.get_by_id(mid)
        assert mem.sub_decision == "delegate"

    def test_store_default_none(self, tmp_store):
        mid = tmp_store.store(
            self._emb(),
            "frontdoor:direct",
            "routing",
            {"task_type": "chat"},
        )
        mem = tmp_store.get_by_id(mid)
        assert mem.sub_decision is None

    def test_sub_decision_in_get_all_memories(self, tmp_store):
        rows = [
            ("delegate:coder", "delegate"),
            ("spawn:architect", "spawn"),
            ("aggregate:children_done", "aggregate"),
            ("repl_done:final", "stop"),
            ("tool_response:llm_query", "communicate"),
        ]
        for action, sd in rows:
            tmp_store.store(
                self._emb(hash(action) & 0xFFFF),
                action,
                "routing",
                {},
                sub_decision=sd,
            )
        all_mems = {m.action: m.sub_decision for m in tmp_store.get_all_memories()}
        for action, sd in rows:
            assert all_mems[action] == sd

    def test_sub_decision_in_retrieve_by_similarity(self, tmp_store):
        emb = self._emb(42)
        tmp_store.store(emb, "delegate:worker_general", "routing", {}, sub_decision="delegate")
        results = tmp_store.retrieve_by_similarity(emb, k=1)
        assert len(results) == 1
        assert results[0].sub_decision == "delegate"

    def test_legacy_null_row_round_trips(self, tmp_store):
        mid = tmp_store.store(self._emb(), "frontdoor:direct", "routing", {})
        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            conn.execute(
                "UPDATE memories SET sub_decision = NULL WHERE id = ?", (mid,)
            )
            conn.commit()
        mem = tmp_store.get_by_id(mid)
        assert mem is not None
        assert mem.sub_decision is None
        # Polarity check: NULL must NOT be coerced to a default value.
        assert normalise_subdecision(mem.sub_decision) is None

    def test_to_dict_round_trips_sub_decision(self, tmp_store):
        mid = tmp_store.store(
            self._emb(),
            "aggregate:children",
            "routing",
            {},
            sub_decision="aggregate",
        )
        mem = tmp_store.get_by_id(mid)
        d = mem.to_dict()
        assert d["sub_decision"] == "aggregate"


# ---------------------------------------------------------------------------
# Backfill heuristic and script
# ---------------------------------------------------------------------------
class TestClassifyHeuristic:
    def test_delegate_token_wins(self):
        assert classify_sub_decision("delegate:worker_general", "routing") == "delegate"
        assert classify_sub_decision("redel_delegate", None) == "delegate"

    def test_spawn_token(self):
        assert classify_sub_decision("subagent_spawn:alpha", "routing") == "delegate"
        assert classify_sub_decision("spawn:tier1", "routing") == "spawn"

    def test_aggregate_tokens(self):
        assert classify_sub_decision("aggregate:results", None) == "aggregate"
        assert classify_sub_decision("merge_results", None) == "aggregate"
        assert classify_sub_decision("child_return", None) == "aggregate"

    def test_stop_tokens(self):
        assert classify_sub_decision("repl_done", None) == "stop"
        assert classify_sub_decision("final_answer:emit", None) == "stop"
        assert classify_sub_decision("round_complete", None) == "stop"

    def test_communicate_tokens(self):
        assert classify_sub_decision("tool_response:llm_query", None) == "communicate"
        assert classify_sub_decision("inter_agent_msg", None) == "communicate"

    def test_escalation_action_type_maps_to_spawn(self):
        # escalation action_type with no specific child name → SPAWN
        assert classify_sub_decision("architect:plan", "escalation") == "spawn"
        # ...but if the action names a delegation, DELEGATE wins
        assert classify_sub_decision("delegate:architect", "escalation") == "delegate"

    def test_unrelated_action_returns_none(self):
        # Most events are NOT sub-decisions. Heuristic must preserve NULL.
        assert classify_sub_decision("frontdoor:direct", "routing") is None
        assert classify_sub_decision("q_score:update", "routing") is None
        assert classify_sub_decision(None, None) is None
        assert classify_sub_decision("", "") is None


class TestBackfillScript:
    def _emb(self, seed: int = 0) -> np.ndarray:
        return np.random.default_rng(seed).standard_normal(1024).astype(np.float32)

    def test_backfill_writes_labelled_rows_only(self, tmp_store):
        ids = [
            tmp_store.store(self._emb(0), "delegate:worker_general", "routing", {}),
            tmp_store.store(self._emb(1), "aggregate:children", "routing", {}),
            tmp_store.store(self._emb(2), "frontdoor:direct", "routing", {}),  # stays NULL
            tmp_store.store(self._emb(3), "repl_done", "routing", {}),
        ]
        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            conn.execute("UPDATE memories SET sub_decision = NULL")
            conn.commit()

        counts = backfill(Path(tmp_store.sqlite_path), dry_run=False)
        assert counts["scanned"] == 4
        assert counts["labelled"] == 3  # one stays NULL
        assert counts["updated"] == 3
        assert counts["skipped"] == 1
        assert counts["delegate"] == 1
        assert counts["aggregate"] == 1
        assert counts["stop"] == 1

        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            rows = dict(
                conn.execute(
                    "SELECT id, sub_decision FROM memories"
                ).fetchall()
            )
        assert rows[ids[0]] == "delegate"
        assert rows[ids[1]] == "aggregate"
        assert rows[ids[2]] is None  # explicitly NULL — polarity check
        assert rows[ids[3]] == "stop"

    def test_backfill_idempotent(self, tmp_store):
        tmp_store.store(self._emb(0), "delegate:worker_general", "routing", {})
        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            conn.execute("UPDATE memories SET sub_decision = NULL")
            conn.commit()

        first = backfill(Path(tmp_store.sqlite_path), dry_run=False)
        assert first["updated"] == 1

        second = backfill(Path(tmp_store.sqlite_path), dry_run=False)
        assert second["scanned"] == 0
        assert second["updated"] == 0

    def test_backfill_dry_run_does_not_write(self, tmp_store):
        tmp_store.store(self._emb(0), "delegate:worker", "routing", {})
        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            conn.execute("UPDATE memories SET sub_decision = NULL")
            conn.commit()

        counts = backfill(Path(tmp_store.sqlite_path), dry_run=True)
        assert counts["scanned"] == 1
        assert counts["labelled"] == 1
        assert counts["updated"] == 0  # nothing written

        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            row = conn.execute("SELECT sub_decision FROM memories").fetchone()
        assert row[0] is None

    def test_backfill_missing_db_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            backfill(tmp_path / "does_not_exist.db", dry_run=False)
