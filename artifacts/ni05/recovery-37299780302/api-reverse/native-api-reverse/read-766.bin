"""Unit tests for benchmark seeding_scoring helper module."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "benchmark"
sys.path.insert(0, str(_ROOT))
_SPEC = importlib.util.spec_from_file_location("seeding_scoring_test", _ROOT / "seeding_scoring.py")
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["seeding_scoring_test"] = _MOD
_SPEC.loader.exec_module(_MOD)


def test_score_answer_deterministic_delegates_to_debug_scorer():
    calls = {}

    def _score(answer, expected, method, config):  # noqa: ANN001
        calls["answer"] = answer
        calls["expected"] = expected
        calls["method"] = method
        calls["config"] = config
        return True

    # score_answer_deterministic pins the orchestrator copy under a private
    # sys.modules key (see seeding_scoring._load_orchestrator_debug_scorer),
    # so stub that key rather than the bare "debug_scorer" name.
    stub = ModuleType("epyc_orch_debug_scorer")
    stub.score_answer = _score
    prev = sys.modules.get("epyc_orch_debug_scorer")
    sys.modules["epyc_orch_debug_scorer"] = stub
    try:
        assert _MOD.score_answer_deterministic("a", "b") is True
    finally:
        if prev is None:
            sys.modules.pop("epyc_orch_debug_scorer", None)
        else:
            sys.modules["epyc_orch_debug_scorer"] = prev

    assert calls == {
        "answer": "a",
        "expected": "b",
        "method": "exact_match",
        "config": {},
    }


def test_score_answer_deterministic_passes_explicit_config():
    calls = {}

    def _score(answer, expected, method, config):  # noqa: ANN001
        calls["config"] = config
        return False

    stub = ModuleType("epyc_orch_debug_scorer")
    stub.score_answer = _score
    prev = sys.modules.get("epyc_orch_debug_scorer")
    sys.modules["epyc_orch_debug_scorer"] = stub
    try:
        assert (
            _MOD.score_answer_deterministic(
                "a",
                "b",
                scoring_method="f1",
                scoring_config={"extract_patterns": ["x"]},
            )
            is False
        )
    finally:
        if prev is None:
            sys.modules.pop("epyc_orch_debug_scorer", None)
        else:
            sys.modules["epyc_orch_debug_scorer"] = prev

    assert calls["config"] == {"extract_patterns": ["x"]}


def test_score_answer_deterministic_f1_folds_diacritics():
    assert _MOD.score_answer_deterministic(
        "Dusan Lajovic",
        "Dušan Lajović",
        scoring_method="f1",
        scoring_config={"threshold": 1.0},
    ) is True


def test_classify_error_branches():
    assert _MOD._classify_error(None) == "none"
    assert _MOD._classify_error("Connection reset by peer") == "infrastructure"
    assert _MOD._classify_error("incorrect answer") == "task_failure"


def test_classify_error_inband_prefix_is_infrastructure():
    # REL-1: an in-band "[ERROR: ...]" banner is a backend/serving failure, so
    # it must classify as infrastructure (EXCLUDED), never task_failure — even
    # when the detail does not match an INFRA_PATTERNS substring.
    circuit = "[ERROR: Backend unavailable (circuit open): http://localhost:8082]"
    assert _MOD._classify_error(circuit) == "infrastructure"
    # generic in-band error (no infra substring) still excluded via prefix
    assert _MOD._classify_error("[ERROR: KeyError: 'foo']") == "infrastructure"
    # leading whitespace is tolerated (mirrors lstrip anchoring)
    assert _MOD._classify_error("  [ERROR: whatever]") == "infrastructure"


def test_inband_error_text_detects_prefix_and_ignores_normal():
    banner = "[ERROR: Backend unavailable (circuit open): http://localhost:8082]"
    assert _MOD._inband_error_text(banner) == banner
    # leading whitespace stripped, prefix still matched
    assert _MOD._inband_error_text("  " + banner) == banner
    # a normal answer is not an in-band error
    assert _MOD._inband_error_text("The final answer is 42.") is None
    # non-string inputs are safe
    assert _MOD._inband_error_text(None) is None
    assert _MOD._inband_error_text(42) is None


def test_forced_role_serving_mismatch():
    # routed_to differs from forced role -> the serving role is returned
    assert _MOD._forced_role_serving_mismatch(
        "worker_math", {"routed_to": "worker_general"}
    ) == "worker_general"
    # served by the forced role -> no mismatch
    assert _MOD._forced_role_serving_mismatch(
        "worker_math", {"routed_to": "worker_math"}
    ) is None
    # empty forced role -> None (avoid false positives)
    assert _MOD._forced_role_serving_mismatch("", {"routed_to": "x"}) is None
    # routed_to absent -> fall back to terminal role_history entry
    assert _MOD._forced_role_serving_mismatch(
        "frontdoor", {"role_history": ["frontdoor", "architect_general"]}
    ) == "architect_general"
    # serving role indeterminable -> None
    assert _MOD._forced_role_serving_mismatch("frontdoor", {}) is None


def _stub_scorer(**attrs):
    """Install a stub orchestrator scorer under the private sys.modules key."""
    stub = ModuleType("epyc_orch_debug_scorer")
    for k, v in attrs.items():
        setattr(stub, k, v)
    prev = sys.modules.get("epyc_orch_debug_scorer")
    sys.modules["epyc_orch_debug_scorer"] = stub
    return prev


def _restore_scorer(prev):
    if prev is None:
        sys.modules.pop("epyc_orch_debug_scorer", None)
    else:
        sys.modules["epyc_orch_debug_scorer"] = prev


def test_score_answer_or_error_normal_verdict():
    prev = _stub_scorer(
        ScoringUnavailableError=type("SUE", (RuntimeError,), {}),
        score_answer=lambda a, e, m, c: True,
    )
    try:
        assert _MOD.score_answer_or_error("42", "42", "exact_match") == (True, None)
    finally:
        _restore_scorer(prev)


def test_score_answer_or_error_scoring_unavailable_excluded():
    class SUE(RuntimeError):
        pass

    def _raise(a, e, m, c):  # noqa: ANN001
        raise SUE("math_verify library unavailable")

    prev = _stub_scorer(ScoringUnavailableError=SUE, score_answer=_raise)
    try:
        passed, reason = _MOD.score_answer_or_error("x", "y", "math_verify")
    finally:
        _restore_scorer(prev)
    # excluded, never raised: (None, reason)
    assert passed is None
    assert reason.startswith("scoring_unavailable:")


def test_score_answer_or_error_valueerror_excluded():
    class SUE(RuntimeError):
        pass

    def _raise(a, e, m, c):  # noqa: ANN001
        raise ValueError("Unknown scoring method: bogus")

    prev = _stub_scorer(ScoringUnavailableError=SUE, score_answer=_raise)
    try:
        passed, reason = _MOD.score_answer_or_error("x", "y", "bogus")
    finally:
        _restore_scorer(prev)
    assert passed is None
    assert reason.startswith("scoring_error:")


def test_is_coding_task_heuristic():
    assert _MOD._is_coding_task("Implement a Python function with unit tests") is True
    assert _MOD._is_coding_task("What is the capital of France?") is False


def test_adaptive_timeout_bounds():
    assert _MOD._adaptive_timeout_s(
        role="frontdoor",
        mode="direct",
        prompt="x",
        is_vl=False,
        hard_timeout_s=10,
    ) == 60
    assert _MOD._adaptive_timeout_s(
        role="frontdoor",
        mode="direct",
        prompt="x",
        is_vl=False,
        hard_timeout_s=120,
    ) == 120
    assert _MOD._adaptive_timeout_s(
        role="frontdoor",
        mode="direct",
        prompt="x",
        is_vl=False,
        hard_timeout_s=0,
    ) == max(60, int(_MOD.DEFAULT_TIMEOUT))


def test_bump_timeout_from_observed_branches():
    assert _MOD._bump_timeout_from_observed(
        current_s=90,
        observed_s=0,
        factor=2.0,
        slack_s=10,
        hard_timeout_s=200,
        role_cap_s=999,
    ) == 90

    # observed budget lower than current => unchanged
    assert _MOD._bump_timeout_from_observed(
        current_s=100,
        observed_s=20,
        factor=2.0,
        slack_s=5,
        hard_timeout_s=200,
        role_cap_s=999,
    ) == 100

    # observed budget larger => bumped but capped by hard timeout floor/ceiling logic
    assert _MOD._bump_timeout_from_observed(
        current_s=10,
        observed_s=500,
        factor=2.0,
        slack_s=0,
        hard_timeout_s=300,
        role_cap_s=999,
    ) == 300

    # hard_timeout_s fallback to DEFAULT_TIMEOUT path
    assert _MOD._bump_timeout_from_observed(
        current_s=10,
        observed_s=1000,
        factor=2.0,
        slack_s=0,
        hard_timeout_s=0,
        role_cap_s=999,
    ) == max(60, int(_MOD.DEFAULT_TIMEOUT))
