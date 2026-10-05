"""Tests for DAR-4 BilinearScorer."""

from pathlib import Path

import numpy as np
import pytest

from orchestration.repl_memory.bilinear_scorer import (
    BilinearScorer,
    ModelFeatures,
    extract_model_features,
    extract_prompt_features,
    PROMPT_FEATURE_DIM,
    MODEL_FEATURE_DIM,
)
from orchestration.repl_memory.q_scorer import ScoringConfig, PRIOR_SOURCE_DEGRADED_FALLBACK


class TestModelFeatures:
    """Test ModelFeatures vector extraction."""

    def test_to_vector_shape(self):
        mf = ModelFeatures(role="test", baseline_tps=10.0, baseline_quality=0.8)
        v = mf.to_vector()
        assert v.shape == (MODEL_FEATURE_DIM,)

    def test_to_vector_normalized(self):
        mf = ModelFeatures(
            role="test",
            baseline_tps=40.0,  # max → 1.0
            baseline_quality=1.0,
            memory_cost=5.0,  # max → 1.0
            param_count_log=10.0,  # max → 1.0
            is_moe=1.0,
            quant_bits=16.0,  # max → 1.0
        )
        v = mf.to_vector()
        assert all(v <= 1.0 + 1e-6)

    def test_extract_from_scoring_config(self):
        cfg = ScoringConfig()
        features = extract_model_features(cfg)
        assert "frontdoor" in features
        assert "architect_general" in features
        assert "worker_general" in features
        assert "worker_explore" not in features
        # The claim under test is that extract_model_features PLUMBS the
        # ScoringConfig priors into ModelFeatures untransformed. The priors
        # themselves are measured (frontdoor's throughput moved 24.3 -> 40.22
        # with the draft-MTP cutover), so derive the expectation from the same
        # source of truth the code reads instead of pinning a bench number.
        assert features["frontdoor"].baseline_tps == cfg.baseline_tps_by_role["frontdoor"]
        assert features["frontdoor"].baseline_quality == cfg.baseline_quality_by_role["frontdoor"]
        assert features["frontdoor"].is_moe == 1.0
        assert features["frontdoor"].quant_bits == 8.0
        # Live stack-prior values are measurements, so the tps mask is set.
        assert features["frontdoor"].tps_known == 1.0

    def test_tps_known_masks_fabricated_degraded_fallback(self, tmp_path: Path, caplog):
        """NIB2-57a: a DEGRADED_FALLBACK t/s prior (fabricated table, not a
        measurement) must not train the scorer as if it were evidence — the
        mask goes to 0 and the provenance is logged loudly."""
        cfg = ScoringConfig(
            baseline_tps_by_role={"worker_general": 60.7},
            baseline_quality_by_role={"worker_general": 0.745},
            memory_cost_by_role={"worker_general": 1.0},
            baseline_tps_source_by_role={"worker_general": PRIOR_SOURCE_DEGRADED_FALLBACK},
        )

        with caplog.at_level("WARNING", logger="orchestration.repl_memory.bilinear_scorer"):
            features = extract_model_features(cfg, stack_priors_path=tmp_path / "missing.yaml")

        assert features["worker_general"].baseline_tps == 60.7
        assert features["worker_general"].tps_known == 0.0
        assert any("DEGRADED" in record.message for record in caplog.records)

    def test_tps_known_vector_mask_is_separate_from_the_number(self):
        """The mask is a distinct feature dimension so the learner can ignore
        an unmeasured tps instead of learning the fabricated value as speed."""
        measured = ModelFeatures(role="a", baseline_tps=40.0, tps_known=1.0)
        masked = ModelFeatures(role="a", baseline_tps=40.0, tps_known=0.0)
        v_measured = measured.to_vector()
        v_masked = masked.to_vector()
        assert v_measured[0] == v_masked[0]  # same normalized number...
        assert v_measured[1] == 1.0 and v_masked[1] == 0.0  # ...but different mask

    def test_extract_from_stack_priors(self, tmp_path: Path):
        """`_stack_prior_model_features` reads its own given file, not a fallback.

        2026-09-24: this fixture was missing `deployment_status: live_stack` on
        both role blocks. `live_stack_role_records()` (src/registry/stack_priors.py)
        filters every record to that status, so with it absent
        `_stack_prior_model_features` silently returned `{}` for BOTH roles and
        `extract_model_features` fell through to the DEGRADED-fallback registry
        path (`registry_path` was also left at its DEFAULT_REGISTRY_PATH default)
        — this test was actually asserting on the real, live production registry
        the whole time, not on the synthetic priors it wrote. It read as passing
        only because production frontdoor's descriptor happened to already be
        35B/moe/Q8_0; worker_general's fixture literal (26B, the RETIRED
        gemma-4-26B-A4B) diverged from real degraded-fallback output once the
        2026-09-22 lineup cutover made worker_general an alias on frontdoor's
        35B process, and the test failed for a reason that had nothing to do
        with the code path its name and docstring claim to cover.

        Fixed at the fixture: declare `deployment_status: live_stack` so
        `_stack_prior_model_features` actually resolves from THIS file, and
        point `registry_path` at a nonexistent file so a future regression of
        the same kind (silently falling through to the real registry) fails
        loudly instead of passing by coincidence. The params_b/quant literals
        below are the test's own synthetic input, not a claim about production,
        so they need no re-derivation.
        """
        stack_priors = tmp_path / "stack_priors.yaml"
        stack_priors.write_text(
            """
roles:
  frontdoor:
    deployment_status: live_stack
    model:
      arch: moe-a3b
      params_b: 35
      active_b: 3
      quant: Q8_0
  worker_general:
    deployment_status: live_stack
    model:
      arch: moe-a4b
      params_b: 26
      active_b: 4
      quant: Q4_K_M
""",
            encoding="utf-8",
        )
        cfg = ScoringConfig(
            baseline_tps_by_role={"frontdoor": 24.3, "worker_general": 60.7},
            baseline_quality_by_role={"frontdoor": 0.9, "worker_general": 0.8},
            memory_cost_by_role={"frontdoor": 1.0, "worker_general": 1.0},
        )

        features = extract_model_features(
            cfg,
            stack_priors_path=stack_priors,
            registry_path=tmp_path / "unused_registry.yaml",
        )

        assert features["frontdoor"].param_count_log == pytest.approx(np.log2(35))
        assert features["frontdoor"].is_moe == 1.0
        assert features["frontdoor"].quant_bits == 8.0
        assert features["worker_general"].param_count_log == pytest.approx(np.log2(26))
        assert features["worker_general"].quant_bits == 4.0

    def test_extract_model_features_uses_degraded_fallback_when_priors_missing(
        self, tmp_path: Path
    ):
        """The DEGRADED-fallback path (no live stack priors) reads model specs
        off the registry descriptor compile.

        2026-09-24: this test left `registry_path` at its DEFAULT_REGISTRY_PATH
        default, so it was really asserting on the real production registry —
        the same defect as `test_extract_from_stack_priors` above, just via the
        opposite parameter. It passed only while production worker_general's
        descriptor still matched the hardcoded 26B/Q4_K_M gemma literal, and
        broke, for an unrelated reason, when the 2026-09-22 cutover moved
        worker_general onto frontdoor's 35B alias. Fixed the same way
        `test_extract_model_features_degraded_fallback_uses_registry_descriptors`
        below already does it: a synthetic, self-contained registry fixture, so
        the expected params/quant are the test's own input and cannot rot with
        a future lineup change.
        """
        registry = tmp_path / "model_registry.yaml"
        registry.write_text(
            """
roles:
  worker_general:
    model:
      name: TestWorker-26B-A4B-Q4_K_M
      quant: Q4_K_M
      size_gb: 26
      architecture: custom_moe
server_mode: {}
""",
            encoding="utf-8",
        )
        cfg = ScoringConfig(
            baseline_tps_by_role={"worker_general": 60.7},
            baseline_quality_by_role={"worker_general": 0.745},
            memory_cost_by_role={"worker_general": 1.0},
        )

        features = extract_model_features(
            cfg,
            stack_priors_path=tmp_path / "missing.yaml",
            registry_path=registry,
        )

        assert features["worker_general"].param_count_log == pytest.approx(np.log2(26))
        assert features["worker_general"].is_moe == 1.0
        assert features["worker_general"].quant_bits == 4.0

    def test_extract_model_features_degraded_fallback_uses_registry_descriptors(
        self,
        tmp_path: Path,
    ):
        registry = tmp_path / "model_registry.yaml"
        registry.write_text(
            """
roles:
  novel_router:
    model:
      name: NovelRouter-42B-MoE-Q5_K_M
      quant: Q5_K_M
      size_gb: 42
      architecture: custom_moe
server_mode: {}
""",
            encoding="utf-8",
        )
        cfg = ScoringConfig(
            baseline_tps_by_role={"novel_router": 12.5},
            baseline_quality_by_role={"novel_router": 0.81},
            memory_cost_by_role={"novel_router": 2.0},
        )

        features = extract_model_features(
            cfg,
            stack_priors_path=tmp_path / "missing.yaml",
            registry_path=registry,
        )

        assert features["novel_router"].param_count_log == pytest.approx(np.log2(42))
        assert features["novel_router"].is_moe == 1.0
        assert features["novel_router"].quant_bits == 5.0


class TestPromptFeatures:
    """Test prompt feature extraction."""

    def test_shape(self):
        task_ir = {"objective": "Write a function to sort a list", "task_type": "coding"}
        v = extract_prompt_features(task_ir)
        assert v.shape == (PROMPT_FEATURE_DIM,)

    def test_code_detection(self):
        code_ir = {"objective": "def sort_list(): implement the function"}
        plain_ir = {"objective": "What is the capital of France?"}
        code_feat = extract_prompt_features(code_ir)
        plain_feat = extract_prompt_features(plain_ir)
        # Code feature (index 1) should be higher for code task
        assert code_feat[1] > plain_feat[1]

    def test_math_detection(self):
        math_ir = {"objective": "Solve the integral of x^2 dx"}
        plain_ir = {"objective": "Tell me about dogs"}
        math_feat = extract_prompt_features(math_ir)
        plain_feat = extract_prompt_features(plain_ir)
        assert math_feat[2] > plain_feat[2]

    def test_empty_task_ir(self):
        v = extract_prompt_features({})
        assert v.shape == (PROMPT_FEATURE_DIM,)
        assert np.isfinite(v).all()


class TestBilinearScorer:
    """Test BilinearScorer core functionality."""

    def _make_scorer(self):
        features = {
            "frontdoor": ModelFeatures(
                role="frontdoor",
                baseline_tps=12.7,
                baseline_quality=0.895,
                memory_cost=1.0,
                param_count_log=5.13,
                is_moe=1.0,
                quant_bits=4.0,
            ),
            "architect_general": ModelFeatures(
                role="architect_general",
                baseline_tps=4.3,
                baseline_quality=0.94,
                memory_cost=3.0,
                param_count_log=6.93,
                is_moe=1.0,
                quant_bits=4.0,
            ),
            "worker_general": ModelFeatures(
                role="worker_general",
                baseline_tps=39.1,
                baseline_quality=0.745,
                memory_cost=0.5,
                param_count_log=4.91,
                is_moe=1.0,
                quant_bits=4.0,
            ),
        }
        return BilinearScorer(features)

    def test_predict_returns_valid_range(self):
        scorer = self._make_scorer()
        prompt = np.random.randn(PROMPT_FEATURE_DIM).astype(np.float32)
        q = scorer.predict(prompt, "frontdoor")
        assert 0.0 <= q <= 1.0

    def test_predict_unknown_role_returns_neutral(self):
        scorer = self._make_scorer()
        prompt = np.random.randn(PROMPT_FEATURE_DIM).astype(np.float32)
        q = scorer.predict(prompt, "unknown_role")
        assert q == 0.5

    def test_predict_all_returns_all_roles(self):
        scorer = self._make_scorer()
        prompt = np.random.randn(PROMPT_FEATURE_DIM).astype(np.float32)
        scores = scorer.predict_all(prompt)
        assert set(scores.keys()) == {"frontdoor", "architect_general", "worker_general"}
        for q in scores.values():
            assert 0.0 <= q <= 1.0

    def test_legacy_worker_explore_alias_canonicalizes_to_worker_general(self):
        scorer = self._make_scorer()
        prompt = extract_prompt_features({"objective": "Solve a complex proof"})

        for _ in range(10):
            scorer.update(prompt, "worker_explore", reward=1.0)

        assert "worker_explore" not in scorer.model_features
        assert scorer.predict(prompt, "worker_explore") == pytest.approx(
            scorer.predict(prompt, "worker_general")
        )
        assert scorer.predict_all(prompt).keys() == {
            "frontdoor",
            "architect_general",
            "worker_general",
        }

    def test_update_changes_prediction(self):
        scorer = self._make_scorer()
        prompt = extract_prompt_features({"objective": "Write a sort function"})

        q_before = scorer.predict(prompt, "frontdoor")

        # Strong positive signal
        for _ in range(50):
            scorer.update(prompt, "frontdoor", reward=1.0)

        q_after = scorer.predict(prompt, "frontdoor")
        assert q_after > q_before

    def test_update_with_negative_reward_decreases_q(self):
        scorer = self._make_scorer()
        prompt = extract_prompt_features({"objective": "Solve a complex proof"})

        # First push Q up
        for _ in range(20):
            scorer.update(prompt, "worker_general", reward=1.0)
        q_high = scorer.predict(prompt, "worker_general")

        # Then push Q down
        for _ in range(50):
            scorer.update(prompt, "worker_general", reward=-1.0)
        q_low = scorer.predict(prompt, "worker_general")

        assert q_low < q_high

    def test_get_best_role(self):
        scorer = self._make_scorer()
        prompt = extract_prompt_features({"objective": "Write code"})

        # Train one role to be clearly best, others clearly worst
        for _ in range(200):
            scorer.update(prompt, "frontdoor", reward=1.0)
            scorer.update(prompt, "worker_general", reward=-1.0)
            scorer.update(prompt, "architect_general", reward=-1.0)

        best = scorer.get_best_role(prompt)
        assert best == "frontdoor"

    def test_zero_cold_start_new_model(self):
        """New model with known specs can score immediately."""
        scorer = self._make_scorer()
        # Add a new model at runtime
        scorer.model_features["new_model"] = ModelFeatures(
            role="new_model",
            baseline_tps=25.0,
            baseline_quality=0.88,
            memory_cost=1.5,
            param_count_log=5.0,
            is_moe=False,
            quant_bits=8.0,
        )
        prompt = extract_prompt_features({"objective": "Translate text"})
        q = scorer.predict(prompt, "new_model")
        assert 0.0 <= q <= 1.0  # Can score without any training data

    def test_save_load_roundtrip(self, tmp_path):
        scorer = self._make_scorer()
        prompt = extract_prompt_features({"objective": "Test"})

        # Train
        for _ in range(10):
            scorer.update(prompt, "frontdoor", reward=0.8)

        q_before = scorer.predict(prompt, "frontdoor")
        path = str(tmp_path / "bilinear.npz")
        scorer.save(path)

        # Load into new scorer
        scorer2 = self._make_scorer()
        assert scorer2.load(path)
        q_after = scorer2.predict(prompt, "frontdoor")
        assert q_before == pytest.approx(q_after, abs=1e-6)

    def test_load_nonexistent_returns_false(self):
        scorer = self._make_scorer()
        assert scorer.load("/nonexistent/path.npz") is False
