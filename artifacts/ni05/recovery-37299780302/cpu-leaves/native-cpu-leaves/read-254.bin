"""The episodic write chokepoint must refuse embeddings an outage would produce.

The original TaskEmbedder fallback and the former parallel-pool fallback used
two different deterministic pseudo-vector algorithms. Both must be recognized
at the write boundary. The parallel pool now fails upward instead of returning
its fallback, allowing TaskEmbedder to try its other real embedding paths.

    all-zero        89.0%   float32 norm overflows to inf; v/inf == 0
    contains NaN     2.8%   permanently unretrievable (FAISS scores it -inf)
    unit-normalised  8.1%   well-formed but semantically meaningless

The first two are text-independent. The third passes every cheap check and is
caught only by exact comparison against the deterministic fallback.
"""
from __future__ import annotations

import warnings

import numpy as np
import pytest

from orchestration.repl_memory.embedder import (
    EmbeddingConfig,
    TaskEmbedder,
    hash_fallback_embedding,
    is_degenerate_embedding,
    is_hash_fallback_embedding,
)
from orchestration.repl_memory.episodic_store import (
    DegenerateEmbeddingError,
    EpisodicStore,
)
from orchestration.repl_memory.memory_record import (
    build_memory_record,
    record_from_legacy_context,
)
from orchestration.repl_memory.parallel_embedder import (
    EmbedderPoolConfig,
    is_parallel_hash_fallback_embedding,
    parallel_hash_fallback_embedding,
)

warnings.filterwarnings("ignore")
DIM = 1024


@pytest.fixture
def fallback_embedder():
    return TaskEmbedder(
        EmbeddingConfig(use_server=False, use_fallback=True, allow_subprocess=False)
    )


@pytest.fixture
def store(tmp_path):
    return EpisodicStore(
        db_path=tmp_path / "e.db", embeddings_path=tmp_path / "emb", use_faiss=True
    )


def ctx_for(objective: str) -> dict:
    return build_memory_record(objective=objective, task_type="coder").to_context()


def unit_vector(seed: int = 0) -> np.ndarray:
    v = np.random.default_rng(seed).standard_normal(DIM).astype(np.float32)
    return v / np.linalg.norm(v)


class TestFallbackIsMeasurablyBroken:
    """Pins the measured distribution — if the fallback is ever 'fixed' to
    produce well-formed vectors, that is MORE dangerous, not less, and these
    tests should be revisited deliberately rather than silently passing."""

    def test_majority_of_fallback_vectors_are_all_zero(self, fallback_embedder):
        vs = [fallback_embedder._generate_embedding_fallback(f"objective:t {i}") for i in range(500)]
        zeros = sum(1 for v in vs if not np.any(v))
        assert zeros > 400, f"expected ~89% all-zero, got {zeros}/500"

    def test_some_fallback_vectors_are_non_finite(self, fallback_embedder):
        vs = [fallback_embedder._generate_embedding_fallback(f"objective:t {i}") for i in range(2000)]
        assert any(not np.all(np.isfinite(v)) for v in vs)

    def test_free_function_reproduces_the_method_bug_for_bug(self, fallback_embedder):
        for i in range(300):
            t = f"objective:t {i}"
            a = fallback_embedder._generate_embedding_fallback(t)
            b = hash_fallback_embedding(t, embedding_dim=DIM)
            assert np.allclose(a, b, equal_nan=True), f"diverged on {t!r}"


class TestDetectors:
    def test_all_zero_and_non_finite_are_caught_without_text(self):
        assert is_degenerate_embedding(np.zeros(DIM, dtype=np.float32)) == "all_zero"
        assert is_degenerate_embedding(np.full(DIM, np.nan, dtype=np.float32)) == "non_finite"
        assert is_degenerate_embedding(np.full(DIM, np.inf, dtype=np.float32)) == "non_finite"
        assert is_degenerate_embedding(None) == "missing"
        assert is_degenerate_embedding(unit_vector()) is None

    def test_every_fallback_vector_is_caught_by_one_detector_or_the_other(self, fallback_embedder):
        missed = []
        for i in range(1000):
            t = f"objective:t {i}"
            v = fallback_embedder._generate_embedding_fallback(t)
            if not (is_degenerate_embedding(v) or is_hash_fallback_embedding(t, v)):
                missed.append(t)
        assert not missed, f"{len(missed)} fallback vectors evaded detection"

    def test_no_false_positives_on_real_unit_vectors(self):
        """The cosine version of this detector had a 45% false-positive rate."""
        for i in range(1000):
            v = unit_vector(i)
            assert is_degenerate_embedding(v) is None
            assert not is_hash_fallback_embedding(f"objective:t {i}", v)

    def test_hash_detection_is_text_specific(self, fallback_embedder):
        """A fallback vector for text A must not read as the fallback for B.

        The well-formed case must be *searched* for, not hardcoded: which texts
        land in the 8.1% bucket depends on the exact string, so a literal picked
        under one embedding-text convention silently stops being well-formed
        under another.
        """
        ta = next(
            t
            for t in (f"objective:t {i}" for i in range(4000))
            if is_degenerate_embedding(fallback_embedder._generate_embedding_fallback(t)) is None
        )
        va = fallback_embedder._generate_embedding_fallback(ta)
        assert is_hash_fallback_embedding(ta, va)
        assert not is_hash_fallback_embedding(ta + " (different)", va)

    def test_parallel_fallback_detection_is_exact_and_text_specific(self):
        text = "type:chat | objective:target task | priority:interactive"
        vector = parallel_hash_fallback_embedding(text)

        assert is_parallel_hash_fallback_embedding(text, vector)
        assert not is_parallel_hash_fallback_embedding(text + "!", vector)
        assert is_degenerate_embedding(vector) is None

    def test_parallel_pool_fallback_is_disabled_by_default(self):
        assert EmbedderPoolConfig().use_fallback is False


class TestChokepointRefuses:
    @pytest.mark.parametrize(
        "vec,reason",
        [
            (np.zeros(DIM, dtype=np.float32), "all_zero"),
            (np.full(DIM, np.nan, dtype=np.float32), "non_finite"),
        ],
    )
    def test_degenerate_vectors_are_refused(self, store, vec, reason):
        with pytest.raises(DegenerateEmbeddingError, match=reason):
            store.store(vec, "route", "routing", ctx_for("sort a list"))

    def test_well_formed_hash_fallback_is_refused(self, store, fallback_embedder):
        """The 8.1% case: norm 1.0, finite, passes every cheap check."""
        for i in range(4000):
            obj = f"task variant {i}"
            text = record_from_legacy_context(ctx_for(obj)).embedding_text()
            v = fallback_embedder._generate_embedding_fallback(text)
            if is_degenerate_embedding(v) is None:
                assert abs(float(np.linalg.norm(v)) - 1.0) < 1e-3
                with pytest.raises(DegenerateEmbeddingError, match="hash_fallback"):
                    store.store(v, "route", "routing", ctx_for(obj))
                return
        pytest.fail("no well-formed fallback vector found in 4000 tries")

    def test_parallel_pool_fallback_is_refused(self, store):
        objective = "target task"
        context = ctx_for(objective)
        text = record_from_legacy_context(context).embedding_text()
        vector = parallel_hash_fallback_embedding(text)

        with pytest.raises(DegenerateEmbeddingError, match="parallel_hash_fallback"):
            store.store(vector, "route", "routing", context)

    def test_a_real_embedding_stores_normally(self, store):
        mid = store.store(unit_vector(), "route", "routing", ctx_for("sort a list"))
        store.flush()
        assert mid and store.count() == 1

    def test_store_immediate_inherits_the_guard(self, store):
        """It delegates to store(), so the guarantee must not be bypassable."""
        with pytest.raises(DegenerateEmbeddingError):
            store.store_immediate(
                np.zeros(DIM, dtype=np.float32), "route", "routing", ctx_for("x")
            )

    def test_override_permits_a_deliberate_degraded_write(self, store, monkeypatch, caplog):
        monkeypatch.setenv("EPISODIC_ALLOW_DEGRADED_EMBEDDINGS", "1")
        import logging

        with caplog.at_level(logging.ERROR):
            mid = store.store(
                np.zeros(DIM, dtype=np.float32), "route", "routing", ctx_for("x")
            )
        store.flush()
        assert mid and store.count() == 1
        assert any("DEGENERATE" in r.message for r in caplog.records), (
            "a deliberate degraded write must still be loud"
        )

    def test_guard_never_breaks_a_write_on_a_weird_context(self, store):
        """The guard must fail open on context it cannot parse, not crash."""
        mid = store.store(unit_vector(), "route", "routing", {"not": "a record"})
        store.flush()
        assert mid and store.count() == 1


class TestUniversalFAISSGuard:
    """F1 (2026-07-28 audit): the guard must hold at FAISSEmbeddingStore.add —
    the single function every vector passes to reach ANY index — so the skill
    and strategy stores (which bypass EpisodicStore.store entirely) are covered
    by construction, not by convention."""

    def _store(self, tmp_path, dim=64):
        from orchestration.repl_memory.faiss_store import FAISSEmbeddingStore

        return FAISSEmbeddingStore(path=tmp_path, dim=dim)

    def test_zero_and_nonfinite_vectors_are_refused_at_add(self, tmp_path):
        from orchestration.repl_memory.faiss_store import DegenerateVectorError

        st = self._store(tmp_path)
        for bad in (np.zeros(64, dtype=np.float32), np.full(64, np.nan, dtype=np.float32)):
            with pytest.raises(DegenerateVectorError):
                st.add("id-x", bad)
        assert st.index.ntotal == 0 and len(st.id_map) == 0, "a refused add must not desync"

    def test_real_vector_still_adds(self, tmp_path):
        st = self._store(tmp_path)
        v = np.random.default_rng(0).standard_normal(64).astype(np.float32)
        assert st.add("id-ok", v) == 0
        assert st.index.ntotal == 1 == len(st.id_map)

    def test_override_env_permits_with_loud_error(self, tmp_path, monkeypatch, caplog):
        import logging

        monkeypatch.setenv("EPISODIC_ALLOW_DEGRADED_EMBEDDINGS", "1")
        st = self._store(tmp_path)
        with caplog.at_level(logging.ERROR):
            st.add("id-z", np.zeros(64, dtype=np.float32))
        assert any("DEGENERATE" in r.message for r in caplog.records)


class TestStrategyStoreFailsClosed:
    """F2: the strategy store's own two fallback paths are refused at the source."""

    def test_no_embedder_refuses_hash_pseudo_embedding(self, tmp_path, monkeypatch):
        from orchestration.repl_memory.strategy_store import StrategyStore

        monkeypatch.delenv("EPISODIC_ALLOW_DEGRADED_EMBEDDINGS", raising=False)
        s = StrategyStore(path=tmp_path / "strat", embedding_dim=64, embedder=None)
        s._embedder = None  # simulate TaskEmbedder construction failure
        with pytest.raises(RuntimeError, match="hash pseudo-embeddings are refused"):
            s._embed("some strategy text")

    def test_owned_embedder_hash_fallback_output_is_refused(self, tmp_path, monkeypatch):
        from orchestration.repl_memory.strategy_store import StrategyStore

        monkeypatch.delenv("EPISODIC_ALLOW_DEGRADED_EMBEDDINGS", raising=False)

        class FallbackOnlyEmbedder:
            def embed_text(self, text):
                return hash_fallback_embedding(text)

        s = StrategyStore(path=tmp_path / "strat", embedding_dim=1024,
                          embedder=FallbackOnlyEmbedder())
        s._owns_embedder = True  # what a bare TaskEmbedder() during a BGE outage is
        # find a text whose fallback is the dangerous well-formed kind
        text = next(t for t in (f"strategy {i}" for i in range(4000))
                    if is_degenerate_embedding(hash_fallback_embedding(t)) is None)
        with pytest.raises(RuntimeError, match="hash fallback"):
            s._embed(text)

    def test_injected_test_embedder_is_untouched(self, tmp_path):
        from orchestration.repl_memory.strategy_store import StrategyStore

        class MockEmbedder:
            def embed_text(self, text):
                v = np.random.default_rng(abs(hash(text)) % 2**32).standard_normal(64)
                return (v / np.linalg.norm(v)).astype(np.float32)

        s = StrategyStore(path=tmp_path / "strat", embedding_dim=64, embedder=MockEmbedder())
        assert s._embed("anything").shape == (64,)


class TestSkillEmbeddingConvention:
    """F3: one skill-embedding convention, shared by every writer."""

    def test_canonical_convention_shape(self):
        from orchestration.repl_memory.skill_bank import skill_embedding_text

        assert (
            skill_embedding_text("Use grep first", "searching code", ["coder", "chat"])
            == "skill:Use grep first | when:searching code | task_types:coder,chat"
        )

    def test_backfill_imports_the_canonical_one(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "backfill_skill_embeddings",
            "scripts/maintenance/backfill_skill_embeddings.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        from orchestration.repl_memory.skill_bank import skill_embedding_text

        assert mod.skill_embedding_text is skill_embedding_text

    def test_pipeline_embeds_canonical_text_and_refuses_fallback(self):
        from orchestration.repl_memory.distillation.pipeline import DistillationPipeline
        from orchestration.repl_memory.skill_bank import Skill, skill_embedding_text

        seen = {}

        class Recorder:
            def embed_text(self, text):
                seen["text"] = text
                v = np.random.default_rng(0).standard_normal(1024)
                return (v / np.linalg.norm(v)).astype(np.float32)

        class FallbackEmbedder:
            def embed_text(self, text):
                return np.zeros(1024, dtype=np.float32)

        skill = Skill(id="gen_001", title="Use grep first", skill_type="general",
                      principle="p", when_to_apply="searching code",
                      task_types=["coder"])
        pipe = DistillationPipeline(teacher=None, skill_bank=None, embedder=Recorder())
        vec = pipe._embed_skill(skill)
        assert vec is not None
        assert seen["text"] == skill_embedding_text("Use grep first", "searching code", ["coder"])

        pipe_bad = DistillationPipeline(teacher=None, skill_bank=None, embedder=FallbackEmbedder())
        assert pipe_bad._embed_skill(skill) is None, "fallback vectors must not be indexed"
