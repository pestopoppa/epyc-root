"""ETR-2 producers: the quality_measured flag must be SET TRUTHFULLY at the source.

Reading the flag in SafetyGate (test_safety_gate_quality_measured.py) is only half the
contract. The other half is that every producer of an EvalResult whose `quality` is a
PLACEHOLDER says so — a fail-closed gate that is fed `quality_measured=True` by a producer
that never scored a question is worse than no gate, because the lie is now load-bearing.

The audit found eleven early-return placeholders in eval_tower.py (designed-core
misconfiguration / activation / load failure, W6 audit-block misconfiguration / load
failure, T2 promotion-eval misconfiguration, T1-core exclusion failure, T2 zero-draw, T2
insufficient promotion draw, T3 missing pool, T3 zero-draw) that constructed `quality=0`
and left the flag at its `True` default. The AST guard below is deliberately structural so
a NEW placeholder return cannot reintroduce the defect.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

EVAL_TOWER = REPO_ROOT / "scripts" / "autopilot" / "eval_tower.py"


def _is_literal_zero(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value in (0, 0.0) and not isinstance(
        node.value, bool
    )


def _eval_result_calls_with_literal_zero_quality() -> list[tuple[int, dict[str, ast.AST]]]:
    tree = ast.parse(EVAL_TOWER.read_text())
    found: list[tuple[int, dict[str, ast.AST]]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name != "EvalResult":
            continue
        kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        quality = kwargs.get("quality")
        if quality is not None and _is_literal_zero(quality):
            found.append((node.lineno, kwargs))
    return found


def test_the_guard_actually_sees_the_placeholder_constructions():
    """Fixture sanity: if the AST walk found nothing, the assertions below are vacuous."""
    calls = _eval_result_calls_with_literal_zero_quality()
    assert len(calls) >= 10, f"expected the placeholder EvalResult sites, found {len(calls)}"


def test_every_literal_zero_quality_eval_result_declares_it_unmeasured():
    offenders = []
    for lineno, kwargs in _eval_result_calls_with_literal_zero_quality():
        measured = kwargs.get("quality_measured")
        if not (isinstance(measured, ast.Constant) and measured.value is False):
            offenders.append(lineno)
    assert not offenders, (
        "eval_tower.py builds EvalResult(quality=0) without quality_measured=False at "
        f"line(s) {offenders}: a quality of 0 that nothing measured is a PLACEHOLDER, and "
        "the SafetyGate quality axis fails closed on the flag, not on the number."
    )


def test_every_unmeasured_placeholder_carries_a_reason():
    missing = []
    for lineno, kwargs in _eval_result_calls_with_literal_zero_quality():
        reason = kwargs.get("quality_unmeasured_reason")
        literal = (
            isinstance(reason, ast.Constant)
            and isinstance(reason.value, str)
            and bool(reason.value)
        )
        # An f-string reason (e.g. f"loader_error:{source}") is equally attributable.
        if not (literal or isinstance(reason, ast.JoinedStr)):
            missing.append(lineno)
    assert not missing, (
        f"placeholder EvalResult at line(s) {missing} has no quality_unmeasured_reason; "
        "the refusal must be attributable to a named cause, not to a bare False."
    )


def test_loader_error_result_is_unmeasured():
    from eval_tower import _loader_error_eval_result  # type: ignore[import-not-found]

    result = _loader_error_eval_result(
        tier=1,
        source="question_pool",
        error="no_valid_question_pool",
        core_id="legacy_pool_seed_1_n10",
        test_profile={},
    )
    assert result.quality_measured is False
    assert result.quality_unmeasured_reason == "loader_error:question_pool"


def test_aggregate_with_no_rows_is_unmeasured():
    from eval_tower import EvalTower  # type: ignore[import-not-found]

    tower = EvalTower.__new__(EvalTower)  # no I/O, no pool loading
    result = EvalTower._aggregate(tower, [], tier=1)
    assert result.quality == 0.0
    assert result.quality_measured is False
    assert result.quality_unmeasured_reason == "no_question_results"


def test_consult_gate_probe_without_turns_is_unmeasured():
    from actions import (  # type: ignore[import-not-found]
        _consult_gate_result_from_summary,
    )

    empty = _consult_gate_result_from_summary({"summary": {}}, elapsed_s=1.0, tier=1)
    assert empty.quality == 0.0
    assert empty.quality_measured is False
    assert empty.quality_unmeasured_reason == "consult_gate_no_turns"

    ran = _consult_gate_result_from_summary(
        {"summary": {"gated": {"turns": 4, "quality": 0.5, "passes": 4}}},
        elapsed_s=10.0,
        tier=1,
    )
    assert ran.quality_measured is True
    assert ran.quality_unmeasured_reason == ""


def test_journal_row_carries_the_measured_distinction():
    """Write-side honesty: the flag must ride the journal row, not only the live object."""
    import autopilot  # type: ignore[import-not-found]
    from safety_gate import EvalResult  # type: ignore[import-not-found]

    placeholder = EvalResult(
        tier=1,
        quality=0,
        speed=0,
        cost=0,
        reliability=0,
        quality_measured=False,
        quality_unmeasured_reason="all_rows_infra_failed",
    )
    payload = autopilot._eval_details_from_result(placeholder)
    assert payload["quality_measured"] is False
    assert payload["quality_unmeasured_reason"] == "all_rows_infra_failed"

    measured = EvalResult(tier=1, quality=2.4, speed=10.0, cost=0.1, reliability=0.99)
    payload = autopilot._eval_details_from_result(measured)
    assert payload["quality_measured"] is True
    assert payload["quality_unmeasured_reason"] == ""
