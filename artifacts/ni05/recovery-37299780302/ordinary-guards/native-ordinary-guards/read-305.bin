"""Tests for the Trinity tri-role `assigned_role` axis (TR-2).

Covers:
- Schema migration adds the column on a fresh DB.
- Schema migration is idempotent on a pre-existing DB (no error if column exists).
- Writers persist `assigned_role` round-trip through retrieve_by_similarity,
  get_by_id, and get_all_memories.
- Legacy rows with NULL assigned_role survive read paths.
- Backfill script classifies + writes correctly + is idempotent.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest

from orchestration.repl_memory.episodic_store import EpisodicStore
from scripts.memory.backfill_assigned_role import backfill, classify_role
from src.classifiers.role_taxonomy import (
    DEFAULT_TRINITY_ROLE,
    TrinityRole,
    normalise_role,
    role_aware_routing_enabled,
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
# Role taxonomy module
# ---------------------------------------------------------------------------
class TestRoleTaxonomy:
    def test_default_is_worker(self):
        assert DEFAULT_TRINITY_ROLE == "worker"

    def test_normalise_none(self):
        assert normalise_role(None) == "worker"

    def test_normalise_empty(self):
        assert normalise_role("") == "worker"
        assert normalise_role("   ") == "worker"

    def test_normalise_thinker_uppercase(self):
        assert normalise_role("THINKER") == "thinker"

    def test_normalise_unknown_falls_back(self):
        assert normalise_role("supervisor") == "worker"

    def test_normalise_valid_passthrough(self):
        for role in TrinityRole:
            assert normalise_role(role.value) == role.value

    def test_feature_flag_default_off(self, monkeypatch):
        monkeypatch.delenv("ORCHESTRATOR_ROLE_AWARE_ROUTING", raising=False)
        assert role_aware_routing_enabled() is False

    def test_feature_flag_on_with_truthy(self, monkeypatch):
        for val in ("1", "true", "yes", "on", "TRUE"):
            monkeypatch.setenv("ORCHESTRATOR_ROLE_AWARE_ROUTING", val)
            assert role_aware_routing_enabled() is True


# ---------------------------------------------------------------------------
# Schema migration
# ---------------------------------------------------------------------------
class TestSchemaMigration:
    def test_assigned_role_column_present_on_fresh_db(self, tmp_store):
        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(memories)")}
        assert "assigned_role" in cols

    def test_index_created(self, tmp_store):
        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            indexes = {
                row[1]
                for row in conn.execute(
                    "SELECT type, name FROM sqlite_master "
                    "WHERE type='index' AND tbl_name='memories'"
                )
            }
        assert "idx_assigned_role" in indexes

    def test_migration_idempotent(self, tmp_path):
        # Open + close + re-open the same path: no error from re-running
        # ALTER TABLE on existing column.
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

    def test_store_persists_assigned_role(self, tmp_store):
        mid = tmp_store.store(
            self._emb(),
            "architect:plan",
            "escalation",
            {"task_type": "code"},
            assigned_role="thinker",
        )
        mem = tmp_store.get_by_id(mid)
        assert mem.assigned_role == "thinker"

    def test_store_default_none(self, tmp_store):
        mid = tmp_store.store(
            self._emb(),
            "frontdoor:direct",
            "routing",
            {"task_type": "chat"},
        )
        mem = tmp_store.get_by_id(mid)
        assert mem.assigned_role is None

    def test_assigned_role_in_get_all_memories(self, tmp_store):
        ids_roles = [
            ("architect:plan", "thinker"),
            ("frontdoor:direct", "worker"),
            ("review_critic:judge", "verifier"),
        ]
        for action, role in ids_roles:
            tmp_store.store(
                self._emb(hash(action) & 0xFFFF),
                action,
                "routing",
                {},
                assigned_role=role,
            )
        all_mems = {m.action: m.assigned_role for m in tmp_store.get_all_memories()}
        assert all_mems["architect:plan"] == "thinker"
        assert all_mems["frontdoor:direct"] == "worker"
        assert all_mems["review_critic:judge"] == "verifier"

    def test_assigned_role_in_retrieve_by_similarity(self, tmp_store):
        emb = self._emb(42)
        tmp_store.store(emb, "verify:output", "routing", {}, assigned_role="verifier")
        results = tmp_store.retrieve_by_similarity(emb, k=1)
        assert len(results) == 1
        assert results[0].assigned_role == "verifier"

    def test_legacy_null_row_round_trips(self, tmp_store):
        # Simulate a row inserted before the column existed: write NULL and
        # confirm reads tolerate it without crashing.
        mid = tmp_store.store(self._emb(), "frontdoor:direct", "routing", {})
        # Force the column to NULL explicitly (it already is, but be defensive).
        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            conn.execute(
                "UPDATE memories SET assigned_role = NULL WHERE id = ?", (mid,)
            )
            conn.commit()
        mem = tmp_store.get_by_id(mid)
        assert mem is not None
        assert mem.assigned_role is None
        # Reader must produce a sane "worker" via normalise_role.
        assert normalise_role(mem.assigned_role) == "worker"


# ---------------------------------------------------------------------------
# Backfill script
# ---------------------------------------------------------------------------
class TestBackfill:
    def _emb(self, seed: int = 0) -> np.ndarray:
        return np.random.default_rng(seed).standard_normal(1024).astype(np.float32)

    def test_classify_role_examples(self):
        assert classify_role("frontdoor:direct", "routing") == "worker"
        assert classify_role("architect:plan", "escalation") == "thinker"
        assert classify_role("review:judge", "routing") == "verifier"
        assert classify_role(None, None) == "worker"

    def test_backfill_writes_to_null_rows(self, tmp_store):
        ids = [
            tmp_store.store(self._emb(0), "frontdoor:direct", "routing", {}),
            tmp_store.store(self._emb(1), "architect:plan", "escalation", {}),
            tmp_store.store(self._emb(2), "review:judge", "routing", {}),
        ]
        # Force NULL — the writer with default arg already writes NULL but be
        # explicit so the test asserts the backfill actually changes things.
        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            conn.execute("UPDATE memories SET assigned_role = NULL")
            conn.commit()

        counts = backfill(Path(tmp_store.sqlite_path), dry_run=False)
        assert counts["scanned"] == 3
        assert counts["updated"] == 3
        assert counts["worker"] == 1
        assert counts["thinker"] == 1
        assert counts["verifier"] == 1

        # Confirm rows are now non-NULL with expected roles.
        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            roles = dict(
                conn.execute(
                    "SELECT id, assigned_role FROM memories"
                ).fetchall()
            )
        assert roles[ids[0]] == "worker"
        assert roles[ids[1]] == "thinker"
        assert roles[ids[2]] == "verifier"

    def test_backfill_idempotent(self, tmp_store):
        tmp_store.store(self._emb(0), "frontdoor:direct", "routing", {})
        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            conn.execute("UPDATE memories SET assigned_role = NULL")
            conn.commit()

        # First run does the work.
        first = backfill(Path(tmp_store.sqlite_path), dry_run=False)
        assert first["updated"] == 1

        # Second run finds nothing to do.
        second = backfill(Path(tmp_store.sqlite_path), dry_run=False)
        assert second["scanned"] == 0
        assert second["updated"] == 0

    def test_backfill_dry_run_does_not_write(self, tmp_store):
        tmp_store.store(self._emb(0), "architect:plan", "escalation", {})
        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            conn.execute("UPDATE memories SET assigned_role = NULL")
            conn.commit()

        counts = backfill(Path(tmp_store.sqlite_path), dry_run=True)
        assert counts["scanned"] == 1

        # Row should still be NULL.
        with sqlite3.connect(tmp_store.sqlite_path) as conn:
            row = conn.execute("SELECT assigned_role FROM memories").fetchone()
        assert row[0] is None

    def test_backfill_missing_db_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            backfill(tmp_path / "does_not_exist.db", dry_run=False)
