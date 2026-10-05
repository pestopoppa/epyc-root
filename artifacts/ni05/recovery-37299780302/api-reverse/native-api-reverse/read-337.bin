"""Hybrid eval should default to the decision-grade T1 instrument."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import eval_tower_trace_feedback  # type: ignore[import-not-found]
from eval_tower import EvalTower  # type: ignore[import-not-found]
from safety_gate import EvalResult  # type: ignore[import-not-found]


class FakeTower(EvalTower):
    def __init__(self, t0_quality: float = 0.0) -> None:
        self.calls: list[tuple[str, int | None, int | None]] = []
        self.t0_quality = t0_quality

    def eval_t0(self) -> EvalResult:
        self.calls.append(("t0", None, None))
        return EvalResult(tier=0, quality=self.t0_quality, speed=10.0, cost=0.5, reliability=1.0)

    def eval_t1(self, n: int = 100, seed: int = 42) -> EvalResult:
        self.calls.append(("t1", n, seed))
        return EvalResult(tier=1, quality=1.7, speed=50.0, cost=0.2, reliability=0.98)

    def eval_t2(self, n: int = 500, seed: int = 42) -> EvalResult:
        self.calls.append(("t2", n, seed))
        return EvalResult(tier=2, quality=1.7, speed=50.0, cost=0.2, reliability=0.98)

    def eval_t3(self, n: int = 160, seed: int = 42, **_kwargs) -> EvalResult:
        self.calls.append(("t3", n, seed))
        return EvalResult(tier=3, quality=1.2, speed=45.0, cost=0.2, reliability=0.98)


def test_hybrid_eval_skips_t0_by_default(monkeypatch) -> None:
    monkeypatch.delenv("AUTOPILOT_HYBRID_T0_GATE", raising=False)
    tower = FakeTower(t0_quality=0.0)

    result = tower.hybrid_eval(seed=7, t1_n=43)

    assert result.tier == 1
    assert tower.calls == [("t1", 43, 7)]


def test_hybrid_eval_legacy_t0_gate_is_env_opt_in(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPILOT_HYBRID_T0_GATE", "1")
    tower = FakeTower(t0_quality=0.0)

    result = tower.hybrid_eval(seed=7, t1_n=43)

    assert result.tier == 0
    assert tower.calls == [("t0", None, None)]


def test_evaluate_t1_uses_server_side_question_spec() -> None:
    tower = FakeTower()

    result = tower.evaluate(tier=1, n=7, seed=999)

    assert result.tier == 1
    assert tower.calls == [("t1", 100, 42)]


def test_evaluate_t2_uses_server_side_question_spec() -> None:
    tower = FakeTower()

    result = tower.evaluate(tier=2, n=7, seed=999)

    assert result.tier == 2
    assert tower.calls == [("t2", 500, 42)]


def test_evaluate_t3_uses_server_side_hard_question_spec() -> None:
    tower = FakeTower()

    result = tower.evaluate(tier=3, n=7, seed=999)

    assert result.tier == 3
    assert tower.calls == [("t3", 160, 42)]


def test_contrastive_trace_bank_formats_success_and_failure_examples() -> None:
    bank = EvalTower.update_contrastive_trace_bank(
        None,
        trace_text="ROLE=worker_general\nPROMPT:\nok prompt\nRESPONSE:\nok",
        outcome="success",
        trial_id=10,
        species="prompt_forge",
        action_type="prompt_mutation",
        reason="T1 frontier q=2.100 s=42.0",
    )
    bank = EvalTower.update_contrastive_trace_bank(
        bank,
        trace_text="ROLE=frontdoor\nPROMPT:\nbad prompt\nRESPONSE:\nbad",
        outcome="failure",
        trial_id=11,
        species="prompt_forge",
        action_type="prompt_mutation",
        reason="VIOLATIONS: quality floor",
    )

    text = FakeTower().capture_contrastive_traces(
        k_success=2,
        k_failure=2,
        trace_bank=bank,
    )

    assert "## Contrastive Execution Traces" in text
    assert "### Success Examples" in text
    assert "trial #10" in text
    assert "T1 frontier q=2.100 s=42.0" in text
    assert "### Failure Examples" in text
    assert "trial #11" in text
    assert "VIOLATIONS: quality floor" in text


def test_critic_trace_ir_preserves_labeled_examples_deterministically() -> None:
    bank = EvalTower.update_contrastive_trace_bank(
        None,
        trace_text="ROLE=worker_general\nPROMPT:\nok prompt\nRESPONSE:\nok",
        outcome="success",
        trial_id=10,
        species="prompt_forge",
        action_type="prompt_mutation",
        reason="T1 frontier q=2.100 s=42.0",
    )
    bank = EvalTower.update_contrastive_trace_bank(
        bank,
        trace_text="ROLE=frontdoor\nPROMPT:\nbad prompt\nRESPONSE:\nbad",
        outcome="failure",
        trial_id=11,
        species="prompt_forge",
        action_type="prompt_mutation",
        reason="VIOLATIONS: quality floor",
    )

    first = EvalTower.build_critic_trace_ir(trace_bank=bank, trial_id=12)
    second = EvalTower.build_critic_trace_ir(trace_bank=bank, trial_id=12)

    assert first == second
    assert first["schema_version"] == "harness_trace_ir.v1"
    assert first["observe_only"] is True
    assert first["acceptance_effect"] == "none_observe_only"
    assert first["source"] == "contrastive_trace_bank"
    assert [entry["outcome"] for entry in first["trace_examples"]] == [
        "success",
        "failure",
    ]
    assert first["trace_examples"][0]["steps"][0]["kind"] == "role"
    assert first["trace_examples"][0]["steps"][1]["kind"] == "prompt"
    assert first["trace_examples"][0]["steps"][2]["kind"] == "response"

    prompt = EvalTower.format_critic_trace_ir(first)
    assert "## Harness Trace IR (MH-11 observe-only)" in prompt
    assert "\"schema_version\": \"harness_trace_ir.v1\"" in prompt
    assert "not an acceptance score or quality gate" in prompt


def test_critic_trace_ir_uses_raw_tail_fallback() -> None:
    trace_ir = EvalTower.build_critic_trace_ir(
        raw_trace_text="ROLE=frontdoor\nPROMPT:\nlegacy prompt\nRESPONSE:\nlegacy",
        trial_id=22,
    )

    assert trace_ir["source"] == "raw_recent_traces"
    assert trace_ir["trace_examples"][0]["outcome"] == "unlabeled"
    assert trace_ir["trace_examples"][0]["trial_id"] == 22
    assert [step["kind"] for step in trace_ir["trace_examples"][0]["steps"]] == [
        "role",
        "prompt",
        "response",
    ]


def test_contrastive_trace_bank_caps_per_outcome() -> None:
    bank = None
    for trial_id in range(5):
        bank = EvalTower.update_contrastive_trace_bank(
            bank,
            trace_text=f"ROLE=worker_general\nRESPONSE:\n{trial_id}",
            outcome="success",
            trial_id=trial_id,
            max_examples_per_outcome=2,
        )

    text = FakeTower().capture_contrastive_traces(
        k_success=5,
        k_failure=0,
        trace_bank=bank,
    )

    assert "trial #0" not in text
    assert "trial #1" not in text
    assert "trial #2" not in text
    assert "trial #3" in text
    assert "trial #4" in text


def test_trace_feedback_module_matches_eval_tower_wrappers() -> None:
    trace_text = "ROLE=worker_general\nPROMPT:\nok prompt\nRESPONSE:\nok"

    tower_bank = EvalTower.update_contrastive_trace_bank(
        None,
        trace_text=trace_text,
        outcome="success",
        trial_id=10,
        species="prompt_forge",
        action_type="prompt_mutation",
        reason="T1 frontier q=2.100 s=42.0",
    )
    module_bank = eval_tower_trace_feedback.update_contrastive_trace_bank(
        None,
        trace_text=trace_text,
        outcome="success",
        trial_id=10,
        species="prompt_forge",
        action_type="prompt_mutation",
        reason="T1 frontier q=2.100 s=42.0",
    )
    assert tower_bank == module_bank

    tower_ir = EvalTower.build_critic_trace_ir(trace_bank=tower_bank, trial_id=12)
    module_ir = eval_tower_trace_feedback.build_critic_trace_ir(
        trace_bank=module_bank,
        trial_id=12,
    )
    assert tower_ir == module_ir
    assert EvalTower.format_critic_trace_ir(tower_ir) == (
        eval_tower_trace_feedback.format_critic_trace_ir(module_ir)
    )
    assert FakeTower().capture_contrastive_traces(trace_bank=tower_bank) == (
        eval_tower_trace_feedback.format_contrastive_traces(trace_bank=module_bank)
    )


def test_trace_feedback_capture_recent_traces_tails_file(tmp_path) -> None:
    tap_path = tmp_path / "inference_tap.log"
    tap_path.write_text("\n".join(f"line {i}" for i in range(6)))

    assert eval_tower_trace_feedback.capture_recent_traces(tap_path, n_lines=3) == (
        "line 3\nline 4\nline 5"
    )
    assert eval_tower_trace_feedback.capture_recent_traces(
        tmp_path / "missing.log",
        n_lines=3,
    ) == ""
