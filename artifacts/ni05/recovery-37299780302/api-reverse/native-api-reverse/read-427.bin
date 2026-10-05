"""An INFRA-FAILED row must never reach the MemRL reward writer.

`tests/unit/test_infra_failed_disposition.py` pins the CLASSIFIER: each of the
four failure shapes now classifies as ``infra_failed`` / ``"infrastructure"``.
This file pins the step AFTER it — the one that actually did the damage.

The seeding path gates reward emission on the string ``error_type ==
"infrastructure"``. Every row that gets past that gate has ``success_reward()``
computed for it and the result POSTed to ``/chat/reward`` → ``store_external_
reward`` → ``QScorer.score_external_result`` → a row in ``memories``. That write
records the reward but NOT the reason: the injected context carries
``question_id`` and timing telemetry and no disposition field, and the TD-update
branch overwrites ``q_value`` in place without leaving any per-reward record at
all. So a reward emitted for an infra failure is INDISTINGUISHABLE, after the
fact, from a reward emitted for a wrong answer — there is nothing in the store
to filter on.

That is why the guard belongs on emission and not on cleanup: this defect class
cannot be repaired downstream, only prevented.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
for _p in (
    str(_ROOT),
    str(_ROOT / "scripts" / "autopilot"),
    str(_ROOT / "scripts" / "benchmark"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import seeding_eval  # noqa: E402
import seeding_rewards  # noqa: E402
from seeding_types import RoleResult  # noqa: E402


# The four shapes named in the root-cause commit, each expressed as the
# response dict the transport actually hands the seeding row builder.
_INFRA_SHAPES = {
    "http_400_unstructured": {
        "answer": "",
        "error": "Client error '400 Bad Request' for url 'http://localhost:8000/chat'",
        "failure_reason": "http_status",
        "http_status": 400,
    },
    "http_400_structured": {
        "answer": "",
        "error": "bad request",
        "error_code": 400,
    },
    "empty_message_read_timeout": {
        "answer": "",
        "error": "",
        "failure_reason": "read_timeout",
        "failure_provenance": {"class": "client_transport_timeout"},
    },
    "unparseable_200_body": {
        "answer": "",
        "error": "Expecting value: line 1 column 1 (char 0)",
        "failure_reason": "invalid_json",
    },
    "empty_200_answer": {
        "answer": "",
        "tokens_generated": 0,
    },
}


def _role_result(resp, *, role="frontdoor", mode="repl", expected="4"):
    rr, _error_type = seeding_eval._build_role_result(
        role=role,
        mode=mode,
        resp=resp,
        elapsed=1.0,
        expected=expected,
        scoring_method="exact_match",
        scoring_config={},
        allow_delegation=False,
    )
    return rr


def _with_delegation(rr: RoleResult) -> RoleResult:
    """Attach a delegation event so the WORKER reward path is reachable."""
    rr.delegation_events = [{"to": "worker_general", "ok": False}]
    rr.delegation_success = False
    return rr


@pytest.mark.parametrize("shape", sorted(_INFRA_SHAPES))
def test_infra_shape_is_labelled_infrastructure_at_the_reward_gate(shape):
    """The gate compares the literal string ``"infrastructure"``.

    Pinning the disposition alone is not enough: the reward gate reads
    ``rr.error_type``, so the guard has to assert the value that gate sees.
    """
    rr = _role_result(_INFRA_SHAPES[shape])
    assert rr.error_type == "infrastructure", (
        f"{shape} would pass the reward gate and emit success_reward(False)"
    )


@pytest.mark.parametrize("shape", sorted(_INFRA_SHAPES))
def test_infra_shape_emits_no_worker_reward(shape):
    """``score_delegation_chain`` is the live, importable reward writer.

    An infra row that reached it would produce ``{"WORKER": 0.0}`` — a capacity
    fact written into the learned router as a quality signal.
    """
    rr = _with_delegation(_role_result(_INFRA_SHAPES[shape]))
    rewards = seeding_rewards.score_delegation_chain({"frontdoor:repl": rr})
    assert rewards == {}, f"{shape} emitted a reward: {rewards}"


def test_a_genuine_wrong_answer_still_emits_a_zero_reward():
    """Mutation guard on the guard.

    A fix that suppressed every failure would pass both tests above while
    destroying the router's only negative signal. A real wrong answer must
    still be scored and still emit 0.0.
    """
    rr = _with_delegation(
        _role_result({"answer": "5", "tokens_generated": 1}, expected="4")
    )
    assert rr.error_type == "none"
    assert rr.passed is False
    rewards = seeding_rewards.score_delegation_chain({"frontdoor:repl": rr})
    assert rewards == {seeding_rewards.ACTION_WORKER: 0.0}


def test_a_correct_answer_still_emits_a_positive_reward():
    rr = _with_delegation(
        _role_result({"answer": "4", "tokens_generated": 1}, expected="4")
    )
    rr.delegation_success = True
    rewards = seeding_rewards.score_delegation_chain({"frontdoor:repl": rr})
    assert rewards == {seeding_rewards.ACTION_WORKER: 1.0}


def _live_benchmark_sources():
    root = _ROOT / "scripts" / "benchmark"
    for path in sorted(root.rglob("*.py")):
        if "deprecated" in path.parts:
            continue
        if path.name == "seeding_rewards.py":  # the definition site
            continue
        yield path


def test_the_ungated_3way_reward_mapper_has_no_live_caller():
    """``compute_3way_rewards`` maps ``passed`` straight to ``success_reward``
    with NO ``error_type == "infrastructure"`` check — the 3-way infra gate
    lives inline in ``seeding_eval.evaluate_question_3way`` instead.

    It is currently imported but never called. Wiring it into a live path would
    reintroduce exactly the defect this file exists to prevent, so pin that it
    stays uncalled outside tests.
    """
    callers = []
    for path in _live_benchmark_sources():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - defensive
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = (
                fn.id if isinstance(fn, ast.Name)
                else fn.attr if isinstance(fn, ast.Attribute)
                else None
            )
            if name == "compute_3way_rewards":
                callers.append(f"{path.relative_to(_ROOT)}:{node.lineno}")
    assert callers == [], (
        "compute_3way_rewards has no infrastructure gate; a live caller would "
        f"emit rewards for infra-failed rows. Callers found: {callers}"
    )


def test_the_reward_gate_string_and_the_disposition_map_agree():
    """The gate is a string comparison against a value produced by a different
    module. If ``legacy_error_type`` ever stopped mapping ``infra_failed`` onto
    ``"infrastructure"``, every gate in the seeding path would silently open.
    """
    from src.autopilot_core.measurement_guards import (
        DISPOSITION_INFRA_FAILED,
        DISPOSITION_SCORING_FAILED,
        legacy_error_type,
    )

    assert legacy_error_type(DISPOSITION_INFRA_FAILED) == "infrastructure"
    assert legacy_error_type(DISPOSITION_SCORING_FAILED) == "infrastructure"
