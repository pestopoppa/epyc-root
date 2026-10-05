"""A gate that never DECIDED must not be reported as a failed check.

Before CJ-8, three events produced `passed=False`, exactly like a genuine lint
failure:

  * the gate timed out,
  * the gate's subprocess raised,
  * the gate NAME did not exist.

That boolean became `EventType.GATE_FAILED`, and `q_reward.compute_reward`
charges -0.1 per GATE_FAILED. So a harness timeout was converted into negative
learning signal ABOUT THE MODEL — a subject that was never checked at all.

THE SAFETY RULE, pinned below: an undecidable gate STILL BLOCKS. `passed` is
still False, `all_passed` is still False, the required-gate stop still fires.
Out-of-coverage is renamed, never downgraded to a pass.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestration.repl_memory.progress_logger import EventType  # noqa: E402
from src.gate_runner import GateConfig, GateResult, GateRunner, GateRunnerError  # noqa: E402
from src.proactive_delegation.gold_labels import outcome_from_gate_result  # noqa: E402
from src.proactive_delegation.verifier_adapter import _gate_result_to_check  # noqa: E402

OOC = "out-of-coverage"


def _runner(tmp_path, command: str, name: str = "g") -> GateRunner:
    cfg = tmp_path / "gates.yaml"
    cfg.write_text(
        f"gates:\n  - name: {name}\n    command: {command}\n    timeout: 1\n"
        f"    required: true\n"
    )
    return GateRunner(config_path=cfg, working_dir=tmp_path)


# --------------------------------------------------------------------------- #
# THE SAFETY RULE
# --------------------------------------------------------------------------- #
def test_undecided_gate_still_blocks() -> None:
    r = GateResult("g", False, -1, "", 0.0, verdict=OOC, cause="timeout")
    assert r.passed is False, "out-of-coverage must NOT become a pass"
    assert r.decided is False


def test_an_undecided_gate_can_never_be_passed() -> None:
    with pytest.raises(GateRunnerError):
        GateResult("g", True, 0, "", 0.0, verdict=OOC, cause="timeout")


def test_out_of_coverage_requires_a_registered_cause() -> None:
    with pytest.raises(GateRunnerError):
        GateResult("g", False, -1, "", 0.0, verdict=OOC)
    with pytest.raises(GateRunnerError):
        GateResult("g", False, -1, "", 0.0, verdict=OOC, cause="because")
    with pytest.raises(GateRunnerError):
        GateResult("g", False, 1, "", 0.0, cause="timeout")  # decided + cause


# --------------------------------------------------------------------------- #
# Back-compat: a decided gate is untouched
# --------------------------------------------------------------------------- #
def test_ordinary_pass_and_fail_keep_their_verdicts(tmp_path) -> None:
    ok = _runner(tmp_path, "true").run_gate(GateConfig("ok", "true", timeout=5))
    bad = _runner(tmp_path, "false").run_gate(GateConfig("bad", "false", timeout=5))
    assert (ok.passed, ok.verdict, ok.cause, ok.decided) == (True, "pass", None, True)
    assert (bad.passed, bad.verdict, bad.cause, bad.decided) == (False, "fail", None, True)


# --------------------------------------------------------------------------- #
# The three converted sites
# --------------------------------------------------------------------------- #
def test_timeout_is_out_of_coverage_not_a_failed_check(tmp_path) -> None:
    runner = _runner(tmp_path, "true")
    result = runner.run_gate(GateConfig("slow", "sleep 30", timeout=1))
    assert result.verdict == OOC
    assert result.cause == "timeout"
    assert result.passed is False  # still blocking
    assert "NOT-DECIDED" in result.summary


def test_checker_exception_is_out_of_coverage(tmp_path, monkeypatch) -> None:
    runner = _runner(tmp_path, "true")

    def boom(*a, **kw):
        raise OSError("ptrace: no such process")

    monkeypatch.setattr(subprocess, "run", boom)
    result = runner.run_gate(GateConfig("g", "true", timeout=5))
    assert result.verdict == OOC
    assert result.cause == "checker_error"
    assert result.passed is False


def test_unknown_gate_name_is_out_of_coverage(tmp_path) -> None:
    runner = _runner(tmp_path, "true")
    (result,) = runner.run_gates_by_name(["no_such_gate"])
    assert result.verdict == OOC
    assert result.cause == "unsupported"
    assert result.passed is False
    assert "Unknown gate" in result.errors[0]


# --------------------------------------------------------------------------- #
# What now happens that previously did not: the reward writer
# --------------------------------------------------------------------------- #
def test_undecided_gate_logs_inconclusive_not_gate_failed(tmp_path) -> None:
    logger = MagicMock()
    runner = _runner(tmp_path, "true")
    runner.progress_logger = logger
    runner.run_gate(GateConfig("slow", "sleep 30", timeout=1), task_id="t1")

    kwargs = logger.log_gate_result.call_args.kwargs
    assert kwargs["verdict"] == OOC
    assert kwargs["cause"] == "timeout"
    assert kwargs["passed"] is False


def test_progress_logger_writes_the_third_event_type() -> None:
    from orchestration.repl_memory.progress_logger import ProgressLogger

    written = []
    logger = ProgressLogger.__new__(ProgressLogger)
    logger._disabled = True
    logger._buffer = []
    logger.log = written.append  # type: ignore[method-assign]

    logger.log_gate_result("t", "g", False, "tier", "role", verdict=OOC, cause="timeout")
    logger.log_gate_result("t", "g", False, "tier", "role")
    logger.log_gate_result("t", "g", True, "tier", "role")

    assert written[0].event_type == EventType.GATE_INCONCLUSIVE
    assert written[0].outcome == "inconclusive"
    assert written[0].data["cause"] == "timeout"
    # Mutation guard: without the verdict the SAME call must still produce the
    # old two-valued behaviour, or this test would pass for the wrong reason.
    assert written[1].event_type == EventType.GATE_FAILED
    assert written[2].event_type == EventType.GATE_PASSED


def test_inconclusive_gate_is_not_charged_by_the_reward() -> None:
    """The point of the whole conversion: -0.1 no longer fires for a timeout."""
    from orchestration.repl_memory.q_reward import compute_reward
    from orchestration.repl_memory.q_scorer import ScoringConfig

    class E:
        def __init__(self, et):
            self.event_type = et
            self.data = {}
            self.outcome = "failure"

    outcome = E(EventType.TASK_COMPLETED)
    outcome.outcome = "success"
    cfg = ScoringConfig()

    def reward(gates):
        return compute_reward(outcome, gates, [], [], None, config=cfg)

    baseline = reward([])
    with_failure = reward([E(EventType.GATE_FAILED)])
    with_inconclusive = reward([E(EventType.GATE_INCONCLUSIVE)])

    # Mutation guard: a real gate failure MUST still be charged, or the
    # assertion below would hold for a reward function that charges nothing.
    assert with_failure < baseline
    assert with_inconclusive == baseline


# --------------------------------------------------------------------------- #
# The two downstream normalizers
# --------------------------------------------------------------------------- #
def test_verification_bridge_reads_the_carried_verdict() -> None:
    r = GateResult("g", False, -1, "boom", 0.0, errors=["Gate execution error: x"],
                   verdict=OOC, cause="checker_error")
    check = _gate_result_to_check("g", r)
    assert check["outcome"] == "inconclusive"
    # The schema closed `inconclusive_reason` to the cause registry; the prose
    # rides `errors`, where it is preserved rather than dropped.
    assert check["inconclusive_reason"] == "checker_error"
    assert any("did not decide" in e for e in check["errors"])
    assert "certificate" not in check, (
        "an undecided gate must not emit a failing-assertion certificate"
    )
    # Mutation guard: a genuinely failing gate still produces `fail`.
    decided = GateResult("g", False, 1, "lint error", 0.0, errors=["E501"])
    assert _gate_result_to_check("g", decided)["outcome"] == "fail"


def test_gold_label_oracle_is_inconclusive_not_fail() -> None:
    ooc = outcome_from_gate_result(
        GateResult("g", False, -1, "", 0.0, verdict=OOC, cause="timeout").to_dict())
    assert ooc.verdict == "inconclusive"
    assert ooc.conclusive is False
    assert ooc.detail["cause"] == "timeout"

    # Mutation guard: a real failure is still a conclusive `fail` oracle.
    real = outcome_from_gate_result(GateResult("g", False, 1, "", 0.0).to_dict())
    assert real.verdict == "fail"
    assert real.conclusive is True


def test_summary_counts_undecided_separately(tmp_path) -> None:
    runner = _runner(tmp_path, "true")
    results = [
        GateResult("a", True, 0, "", 0.0),
        GateResult("b", False, 1, "", 0.0),
        GateResult("c", False, -1, "", 0.0, verdict=OOC, cause="timeout"),
    ]
    text = runner.get_summary(results)
    assert "1/3 passed" in text
    assert "1 failed" in text  # NOT 2 — the timeout is no longer a failure
    assert "1 not decided" in text
