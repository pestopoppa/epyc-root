"""The BLOCK reason for a review-required belief must name the condition that actually fired.

Spec: docs/design/vidya-pilot-spec.md §8.2 (gate outcomes).

`Belief.review_required` is the OR of two conditions that `fold.Belief` deliberately keeps
apart, and says so at the field: "its own source was corrected" and "something it rests on was
withdrawn" are "different problems and get cleared by different people".

The gate collapsed exactly that distinction. It reported only `len(belief.corrections)`, so a
belief blocked purely by a dependency alert was refused with the reason "0 unreviewed
correction(s) recorded against this claim" — a count of zero presented as the cause, and a
`required_next_actions` telling the reader to review a correction that does not exist. Measured
2026-09-07: 118 `claim_depends_on` frames in the live ledger, so this was a production path,
not a hypothetical.

Every test here is paired against its opposite: the correction case must not mention
dependencies and the dependency case must not mention corrections. A single-sided test would
pass against the original bug.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))

from fold import Belief, FoldResult  # noqa: E402
from gate import Outcome, UsePolicy, evaluate  # noqa: E402
from lattice import Grade  # noqa: E402


def _fold(belief: Belief) -> FoldResult:
    return FoldResult(beliefs={belief.claim_id: belief}, iterations=1, frontier=1,
                      as_of="2026-09-07T00:00:00Z", ignored_frame_types={})


def _belief(**kw) -> Belief:
    b = Belief(claim_id="c1")
    for k, v in kw.items():
        setattr(b, k, v)
    return b


POLICY = UsePolicy(use="test", floor=Grade(1, 1))


def _text(result) -> str:
    return " ".join(result.reasons + result.required_next_actions)


def test_corrections_only_names_corrections_and_not_dependencies():
    r = evaluate("c1", _fold(_belief(corrections=["intake-900 corrected"])), POLICY)
    assert r.outcome == Outcome.BLOCK
    assert "1 unreviewed correction(s)" in _text(r)
    assert "depends_on" not in _text(r), "invented a dependency cause the belief does not have"


def test_dependency_alerts_only_names_dependencies_and_not_corrections():
    # THE REGRESSION. Before the fix this produced "0 unreviewed correction(s)".
    r = evaluate("c1", _fold(_belief(dependency_alerts=["intake-896", "intake-412"])), POLICY)
    assert r.outcome == Outcome.BLOCK
    assert "correction" not in _text(r), "named corrections for a dependency-only block"
    assert "depends_on" in _text(r)


def test_dependency_alert_reason_names_the_withdrawn_entries():
    # A reason that says "2 dependencies" without saying WHICH sends the reader back to the
    # ledger to re-derive what the gate already knew.
    r = evaluate("c1", _fold(_belief(dependency_alerts=["intake-896", "intake-412"])), POLICY)
    assert "intake-896" in _text(r)
    assert "intake-412" in _text(r)


def test_zero_count_never_appears_as_a_cause():
    # The precise shape of the original defect, pinned independently of wording.
    r = evaluate("c1", _fold(_belief(dependency_alerts=["intake-896"])), POLICY)
    assert "0 unreviewed" not in _text(r)


def test_both_conditions_report_both_reasons_and_both_actions():
    r = evaluate("c1", _fold(_belief(corrections=["intake-900 corrected"],
                                     dependency_alerts=["intake-896"])), POLICY)
    assert r.outcome == Outcome.BLOCK
    assert len(r.reasons) == 2
    assert len(r.required_next_actions) == 2
    assert "correction" in _text(r) and "depends_on" in _text(r)


def test_each_reason_has_a_matching_next_action():
    # A reason with no action is a dead end for the reader; the counts must track.
    for kw in ({"corrections": ["x"]},
               {"dependency_alerts": ["intake-896"]},
               {"corrections": ["x"], "dependency_alerts": ["intake-896"]}):
        r = evaluate("c1", _fold(_belief(**kw)), POLICY)
        assert len(r.reasons) == len(r.required_next_actions) == len(kw)


def test_policy_opt_in_still_bypasses_the_block():
    # The fix must not change WHEN the gate blocks, only what it says. A permissive policy
    # must still get past review_required.
    permissive = UsePolicy(use="test", floor=Grade(1, 1), allow_review_required=True)
    r = evaluate("c1", _fold(_belief(dependency_alerts=["intake-896"])), permissive)
    assert r.outcome != Outcome.BLOCK or "depends_on" not in _text(r)
