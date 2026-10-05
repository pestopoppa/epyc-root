"""Tests for EpisodicStore and RoutingClassifier."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from orchestration.repl_memory.episodic_store import (
    EpisodicStore,
    GraphEnhancedStore,
    extract_symptoms,
)
from src.roles import Role


@pytest.fixture
def tmp_store(tmp_path):
    """Create a temporary EpisodicStore."""
    store = EpisodicStore(db_path=tmp_path / "sessions", use_faiss=True)
    yield store
    store.close()


@pytest.fixture
def populated_store(tmp_store):
    """Store with 10 routing memories, varying Q-values and update counts."""
    actions = ["frontdoor:direct", "coder_escalation:repl", "architect_general:direct",
               "worker_explore:direct", "frontdoor:react", "frontdoor:direct"]
    for i in range(10):
        emb = np.random.default_rng(i).standard_normal(1024).astype(np.float32)
        action = actions[i % len(actions)]
        tmp_store.store(
            emb, action, "routing",
            {"task_type": "code" if i % 2 == 0 else "chat", "context_length": i * 100},
            outcome="success" if i % 3 != 0 else "failure",
            initial_q=0.3 + i * 0.07,
        )

    # Apply Q-value updates to first 5 memories
    all_mems = tmp_store.get_all_memories()
    for mem in all_mems[:5]:
        tmp_store.update_q_value(mem.id, 0.8)
        tmp_store.update_q_value(mem.id, 0.9)
    return tmp_store


# ---------------------------------------------------------------------------
# get_all_memories()
# ---------------------------------------------------------------------------
class TestGetAllMemories:
    def test_returns_all_memories(self, populated_store):
        mems = populated_store.get_all_memories()
        assert len(mems) == 10

    def test_returns_empty_for_empty_store(self, tmp_store):
        assert tmp_store.get_all_memories() == []

    def test_filter_by_action_type(self, populated_store):
        routing = populated_store.get_all_memories(action_type="routing")
        assert len(routing) == 10
        escalation = populated_store.get_all_memories(action_type="escalation")
        assert len(escalation) == 0

    def test_include_embeddings_false(self, populated_store):
        mems = populated_store.get_all_memories(include_embeddings=False)
        assert all(m.embedding is None for m in mems)

    def test_include_embeddings_true(self, populated_store):
        mems = populated_store.get_all_memories(include_embeddings=True)
        assert all(m.embedding is not None for m in mems)
        assert mems[0].embedding.shape == (1024,)

    def test_min_update_count_filter(self, populated_store):
        # First 5 have update_count=2, rest have 0
        updated = populated_store.get_all_memories(min_update_count=2)
        assert len(updated) == 5
        assert all(m.update_count >= 2 for m in updated)

    def test_combined_filters(self, populated_store):
        mems = populated_store.get_all_memories(
            action_type="routing",
            include_embeddings=True,
            min_update_count=2,
        )
        assert len(mems) == 5
        assert all(m.embedding is not None for m in mems)
        assert all(m.action_type == "routing" for m in mems)

    def test_ordered_by_created_at(self, populated_store):
        mems = populated_store.get_all_memories()
        for i in range(1, len(mems)):
            assert mems[i].created_at >= mems[i - 1].created_at

    def test_memory_entry_fields_populated(self, populated_store):
        mems = populated_store.get_all_memories()
        m = mems[0]
        assert m.id is not None
        assert m.action is not None
        assert m.action_type == "routing"
        assert isinstance(m.context, dict)
        assert isinstance(m.q_value, float)
        assert isinstance(m.update_count, int)


# ---------------------------------------------------------------------------
# GraphEnhancedStore delegates get_all_memories
# ---------------------------------------------------------------------------
class TestGraphEnhancedStoreDelegate:
    def test_delegates_get_all_memories(self, populated_store):
        enhanced = GraphEnhancedStore(populated_store)
        mems = enhanced.get_all_memories()
        assert len(mems) == 10

    def test_delegates_with_kwargs(self, populated_store):
        enhanced = GraphEnhancedStore(populated_store)
        mems = enhanced.get_all_memories(action_type="routing", min_update_count=2)
        assert len(mems) == 5


# ---------------------------------------------------------------------------
# Basic store/retrieve/update
# ---------------------------------------------------------------------------
class TestStoreBasics:
    def test_store_and_count(self, tmp_store):
        emb = np.random.randn(1024).astype(np.float32)
        mid = tmp_store.store(emb, "test_action", "routing", {"task_type": "code"})
        assert isinstance(mid, str)
        assert tmp_store.count() == 1

    def test_get_by_id(self, tmp_store):
        emb = np.random.randn(1024).astype(np.float32)
        mid = tmp_store.store(emb, "test_action", "routing", {"task_type": "code"})
        mem = tmp_store.get_by_id(mid)
        assert mem is not None
        assert mem.action == "test_action"
        assert mem.action_type == "routing"

    def test_update_q_value(self, tmp_store):
        emb = np.random.randn(1024).astype(np.float32)
        mid = tmp_store.store(emb, "test", "routing", {}, initial_q=0.5)
        new_q = tmp_store.update_q_value(mid, reward=1.0, learning_rate=0.1)
        assert new_q > 0.5
        mem = tmp_store.get_by_id(mid)
        assert mem.update_count == 1

    def test_retrieve_by_similarity(self, tmp_store):
        # Store 3 memories with different embeddings
        embs = [np.random.default_rng(i).standard_normal(1024).astype(np.float32) for i in range(3)]
        for i, emb in enumerate(embs):
            tmp_store.store(emb, f"action_{i}", "routing", {})
        # Query with first embedding — should find it with high similarity
        results = tmp_store.retrieve_by_similarity(embs[0], k=3)
        assert len(results) == 3
        assert results[0].action == "action_0"
        assert results[0].similarity_score > 0.9


# ---------------------------------------------------------------------------
# extract_symptoms
# ---------------------------------------------------------------------------
class TestExtractSymptoms:
    def test_timeout_detection(self):
        s = extract_symptoms({}, "Connection timed out after 30s")
        assert "timeout" in s

    def test_oom_detection(self):
        s = extract_symptoms({"error": "Out of memory"}, "")
        assert "OOM" in s

    def test_unknown_for_no_match(self):
        s = extract_symptoms({}, "Everything went fine")
        assert s == ["unknown"]


# ---------------------------------------------------------------------------
# RoutingClassifier
# ---------------------------------------------------------------------------
class TestRoutingClassifier:
    @pytest.fixture
    def classifier(self):
        from orchestration.repl_memory.routing_classifier import RoutingClassifier
        return RoutingClassifier(
            input_dim=1031,
            n_actions=4,
            label_map={0: "frontdoor", 1: "coder", 2: "architect", 3: "worker"},
        )

    def test_predict_returns_distribution(self, classifier):
        x = np.random.randn(1031).astype(np.float32)
        dist = classifier.predict(x)
        assert len(dist) == 4
        assert abs(sum(dist.values()) - 1.0) < 1e-5
        assert all(v >= 0 for v in dist.values())

    def test_predict_action_returns_best(self, classifier):
        x = np.random.randn(1031).astype(np.float32)
        action, conf = classifier.predict_action(x)
        assert action in ["frontdoor", "coder", "architect", "worker"]
        assert 0.0 <= conf <= 1.0

    def test_train_reduces_loss(self, classifier):
        rng = np.random.default_rng(42)
        X = rng.standard_normal((200, 1031)).astype(np.float32)
        y = rng.integers(0, 4, 200)
        q = np.ones(200, dtype=np.float32)
        history = classifier.train(X, y, q, epochs=50, lr=0.01, patience=100, batch_size=32)
        # Loss should decrease
        assert history["train_loss"][-1] < history["train_loss"][0]

    def test_save_load_roundtrip(self, classifier, tmp_path):
        x = np.random.randn(1031).astype(np.float32)
        dist1 = classifier.predict(x)

        path = tmp_path / "test_weights.npz"
        classifier.save(path)

        from orchestration.repl_memory.routing_classifier import RoutingClassifier
        loaded = RoutingClassifier.load(path)
        assert loaded is not None
        dist2 = loaded.predict(x)

        def _canonical(key: str) -> str:
            role = Role.from_string(key)
            return str(role) if role is not None else key

        for key, value in dist1.items():
            assert abs(value - dist2[_canonical(key)]) < 1e-5

    def test_load_canonicalizes_legacy_action_labels(self, tmp_path):
        from orchestration.repl_memory.routing_classifier import RoutingClassifier

        clf = RoutingClassifier(
            input_dim=1031,
            n_actions=3,
            label_map={0: "worker_explore", 1: "coder", 2: "frontdoor:direct"},
        )
        path = tmp_path / "legacy_labels.npz"
        clf.save(path)

        loaded = RoutingClassifier.load(path)
        assert loaded is not None
        assert loaded.label_map[0] == "worker_general"
        assert loaded.label_map[1] == "coder_escalation"
        assert loaded.label_map[2] == "frontdoor"

    def test_load_missing_returns_none(self):
        from orchestration.repl_memory.routing_classifier import RoutingClassifier
        assert RoutingClassifier.load(Path("/tmp/nonexistent_weights.npz")) is None

    def test_param_count(self, classifier):
        # Input(1031) -> Dense(128): 1031*128 + 128 = 132096
        # Dense(128) -> Dense(64): 128*64 + 64 = 8256
        # Dense(64) -> Dense(4): 64*4 + 4 = 260
        # Total = 140612
        assert classifier.param_count > 100000
        assert classifier.param_count < 200000

    def test_batch_forward(self, classifier):
        X = np.random.randn(16, 1031).astype(np.float32)
        probs, cache = classifier.forward(X)
        assert probs.shape == (16, 4)
        assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-5)

    def test_predict_action_with_class_thresholds(self):
        from orchestration.repl_memory.routing_classifier import RoutingClassifier
        clf = RoutingClassifier(
            input_dim=1031, n_actions=4,
            label_map={0: "frontdoor", 1: "coder", 2: "architect", 3: "worker"},
            class_thresholds={0: 0.99, 1: 0.99, 2: 0.99, 3: 0.99},  # Very high
        )
        x = np.random.randn(1031).astype(np.float32)
        # With near-impossible thresholds, most predictions should return None
        action, conf = clf.predict_action(x)
        # Either it's None (below threshold) or the model is extremely confident
        if action is not None:
            assert conf >= 0.99

    def test_predict_action_no_thresholds_always_returns_action(self, classifier):
        x = np.random.randn(1031).astype(np.float32)
        action, conf = classifier.predict_action(x)
        # Without thresholds, should always return an action
        assert action is not None
        assert action in ["frontdoor", "coder", "architect", "worker"]

    def test_calibrate_thresholds(self, classifier):
        rng = np.random.default_rng(42)
        X = rng.standard_normal((200, 1031)).astype(np.float32)
        y = rng.integers(0, 4, 200)
        q = np.ones(200, dtype=np.float32)
        classifier.train(X, y, q, epochs=30, lr=0.01, patience=100, batch_size=32)

        thresholds = classifier.calibrate_thresholds(X, y, target_precision=0.8)
        assert len(thresholds) == 4
        for cls_idx, thr in thresholds.items():
            assert 0.0 <= thr <= 1.0

    def test_save_load_roundtrip_with_thresholds(self, tmp_path):
        from orchestration.repl_memory.routing_classifier import RoutingClassifier
        clf = RoutingClassifier(
            input_dim=1031, n_actions=4,
            label_map={0: "a", 1: "b", 2: "c", 3: "d"},
            class_thresholds={0: 0.5, 1: 0.6, 2: 0.7, 3: 0.8},
        )
        path = tmp_path / "weights_with_thresholds.npz"
        clf.save(path)

        loaded = RoutingClassifier.load(path)
        assert loaded is not None
        assert len(loaded.class_thresholds) == 4
        for cls_idx in range(4):
            assert abs(loaded.class_thresholds[cls_idx] - clf.class_thresholds[cls_idx]) < 1e-5

    def test_save_canonicalizes_legacy_action_labels(self, tmp_path):
        from orchestration.repl_memory.routing_classifier import RoutingClassifier

        clf = RoutingClassifier(
            input_dim=1031,
            n_actions=3,
            label_map={0: "worker_explore", 1: "coder", 2: "frontdoor:direct"},
        )
        path = tmp_path / "saved_legacy_labels.npz"
        clf.save(path)

        data = np.load(path, allow_pickle=True)
        assert list(data["_label_map_vals"]) == [
            "worker_general",
            "coder_escalation",
            "frontdoor",
        ]
