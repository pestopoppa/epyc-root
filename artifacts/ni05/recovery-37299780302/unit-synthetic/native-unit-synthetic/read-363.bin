#!/usr/bin/env python3
"""Unit tests for src/repl_environment/file_recency.py."""

from __future__ import annotations

import math
import threading
import time

import pytest

from src.repl_environment.file_recency import FrecencyStore


class TestFrecencyStore:
    """Tests for FrecencyStore."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a FrecencyStore backed by a temporary database."""
        db = tmp_path / "test_recency.db"
        s = FrecencyStore(db_path=db)
        yield s
        s.close()

    @pytest.fixture
    def memory_store(self):
        """Create an in-memory FrecencyStore."""
        s = FrecencyStore(db_path=":memory:")
        yield s
        s.close()

    def test_score_computation(self, memory_store):
        """Known inputs produce expected outputs using the formula."""
        store = memory_store
        # Manually verify: access_count=5, age_hours=0 (just now)
        now = time.time()
        score = store._compute_score(5, now)
        expected = 1.0 * math.log(6) + 2.0 * math.exp(0.0)
        assert abs(score - expected) < 0.01

        # With some age
        one_day_ago = now - 3600 * 24
        score_old = store._compute_score(5, one_day_ago)
        expected_old = 1.0 * math.log(6) + 2.0 * math.exp(-24.0 / 24.0)
        assert abs(score_old - expected_old) < 0.01

    def test_score_decay(self, memory_store):
        """Score decreases as age_hours increases."""
        store = memory_store
        now = time.time()
        score_now = store._compute_score(3, now)
        score_1h = store._compute_score(3, now - 3600)
        score_24h = store._compute_score(3, now - 3600 * 24)
        score_72h = store._compute_score(3, now - 3600 * 72)
        assert score_now > score_1h > score_24h > score_72h

    def test_access_count_increases_score(self, memory_store):
        """More accesses produce a higher score."""
        store = memory_store
        now = time.time()
        scores = [store._compute_score(n, now) for n in [1, 5, 20, 100]]
        for i in range(len(scores) - 1):
            assert scores[i] < scores[i + 1]

    def test_combo_boost(self, memory_store):
        """Repeated (query, file) pair increases boost multiplier."""
        store = memory_store
        path = "/some/file.py"
        query = "search term"

        # Before any access, boost is 1.0
        assert store.get_combo_boost(query, path) == 1.0

        # Record several accesses with the same query
        for _ in range(5):
            store.record_access(path, query=query)

        boost = store.get_combo_boost(query, path)
        assert boost > 1.0
        expected = 1.0 + 0.5 * math.log(5 + 1)
        assert abs(boost - expected) < 0.01

    def test_combo_boost_no_query(self, memory_store):
        """Returns 1.0 when no query was recorded."""
        store = memory_store
        store.record_access("/file.py")
        assert store.get_combo_boost("any_query", "/file.py") == 1.0

    def test_sqlite_persistence(self, tmp_path):
        """Write, close, reopen, read back, verify."""
        db = tmp_path / "persist.db"
        store1 = FrecencyStore(db_path=db)
        store1.record_access("/a.py", query="q")
        store1.record_access("/a.py", query="q")
        score1 = store1.get_score("/a.py")
        boost1 = store1.get_combo_boost("q", "/a.py")
        store1.close()

        store2 = FrecencyStore(db_path=db)
        score2 = store2.get_score("/a.py")
        boost2 = store2.get_combo_boost("q", "/a.py")
        store2.close()

        # Scores should be very close (tiny time difference between reads)
        assert abs(score1 - score2) < 0.1
        assert abs(boost1 - boost2) < 0.01

    def test_batch_lookup(self, memory_store):
        """get_scores() returns correct dict for multiple paths."""
        store = memory_store
        store.record_access("/a.py")
        store.record_access("/b.py")
        store.record_access("/b.py")

        scores = store.get_scores(["/a.py", "/b.py", "/missing.py"])
        assert set(scores.keys()) == {"/a.py", "/b.py", "/missing.py"}
        assert scores["/a.py"] > 0.0
        assert scores["/b.py"] > scores["/a.py"]
        assert scores["/missing.py"] == 0.0

    def test_unknown_path_returns_zero(self, memory_store):
        """get_score('nonexistent') returns 0.0."""
        assert memory_store.get_score("nonexistent") == 0.0

    def test_record_access_creates_entry(self, memory_store):
        """First access creates the row."""
        store = memory_store
        assert store.get_score("/new.py") == 0.0
        store.record_access("/new.py")
        assert store.get_score("/new.py") > 0.0

    def test_thread_safety(self, tmp_path):
        """Concurrent writes don't crash."""
        db = tmp_path / "threads.db"
        store = FrecencyStore(db_path=db)
        errors: list[Exception] = []

        def writer(thread_id: int):
            try:
                for i in range(50):
                    store.record_access(f"/file_{thread_id}_{i}.py", query=f"q{thread_id}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(tid,)) for tid in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        store.close()
        assert errors == [], f"Thread errors: {errors}"
