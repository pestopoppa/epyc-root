"""Two defects of the same class: a check that passed for the wrong reason.

Found by an audit of `scripts/vidya/` for that class alone, mutation-confirmed: every assertion
below fails against the pre-fix implementation, and the whole 889-test suite passed with both
defects live, which is the point.

1. `fold` collected a retraction target with `isinstance(target, str)` and no non-emptiness test.
   `fid` for a frame carrying no `frame_id` defaults to `""` (frames.validate_frame binds
   frame_id to content only when the key is PRESENT, so an id-less frame is valid), so one
   retraction naming `""` matched every id-less frame in the ledger. Shape: a type check standing
   in for a value check -- the same shape as SC58's presence-only replay-key validation.

2. `projection` reported every `review_required` omission as "unreviewed correction recorded
   against it". `review_required` is `corrections or dependency_alerts or dirty_inputs`. This is
   the identical disjunction-reported-as-one-cause defect fixed in the gate by 6491eccf, left
   standing on the projection's omissions lane and in its REVIEW freshness verdict.

Each positive below is paired with the mutation it exists to catch, named in the docstring.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

from fold import (  # noqa: E402
    FT_CLAIM, FT_RETRACT, FT_SUPPORT, Belief, FoldResult, fold,
)
from lattice import Grade  # noqa: E402
from projection import (  # noqa: E402
    Freshness, ProjectionManifest, SelectionPolicy, belief_version, freshness_of, select_beliefs,
)

NOW = "2026-01-02T00:00:00Z"
PUB = {"actor": "t", "authority_scope": "t", "created_at": "2026-01-01T00:00:00Z"}


def _frame(ftype, assertion, *, frame_id=None):
    f = {"frame_type": ftype, "assertion": assertion,
         "provenance": {"method": "test"}, "pubinfo": dict(PUB)}
    if frame_id is not None:
        f["frame_id"] = frame_id
    return f


def _corpus(retracts):
    """A claim, one support frame carrying NO frame_id, and a retraction naming `retracts`."""
    return [
        _frame(FT_CLAIM, {"claim_id": "C9", "source_id": "S9"}, frame_id="g1"),
        # No frame_id: legal, and the case the empty-string wildcard fed on.
        _frame(FT_SUPPORT, {"claim_id": "C9", "evidence_id": "E9", "source_id": "S9",
                            "grade": {"Q": "Verified", "T": "Anchored"}}),
        _frame(FT_RETRACT, {"retracts": retracts}, frame_id="g3"),
    ]


# --- 1. retraction scope ------------------------------------------------------------------


def test_a_retraction_naming_the_empty_string_retracts_nothing():
    """MUTATION CAUGHT: `if isinstance(target, str) and target:` -> `if isinstance(target, str):`.

    Under that mutation the id-less support frame is dropped and `retracted_support == [""]`.
    """
    b = fold(_corpus(""), as_of=NOW).beliefs["C9"]
    assert [label for label, _ in b.pro_paths] == ["E9"], \
        "an id-less support frame was retracted by a retraction that named nothing"
    assert b.retracted_support == []


def test_a_retraction_naming_a_real_frame_still_retracts_it():
    """The paired positive: the guard must not disarm retraction itself."""
    frames = _corpus("f-support")
    frames[1]["frame_id"] = "f-support"
    b = fold(frames, as_of=NOW).beliefs["C9"]
    assert b.pro_paths == []
    assert b.retracted_support == ["f-support"]


def test_an_unrelated_retraction_leaves_an_idless_frame_alone():
    """Mutation control for the above: `""` must not behave like a wildcard for ANY target."""
    b = fold(_corpus("some-other-frame"), as_of=NOW).beliefs["C9"]
    assert [label for label, _ in b.pro_paths] == ["E9"]


# --- 2. the review-cause disjunction ------------------------------------------------------


def _belief(**kw):
    return Belief(claim_id="C", pro=Grade(3, 3), pro_paths=[("e1", Grade(3, 3))], **kw)


def _result(b):
    return FoldResult(as_of=NOW, frontier=1, beliefs={"C": b}, iterations=1,
                      ignored_frame_types={})


POLICY = SelectionPolicy(policy_id="p", floor=Grade(1, 1))


def test_a_dependency_only_omission_does_not_claim_a_correction():
    """MUTATION CAUGHT: revert `_review_cause(b)` to the literal "unreviewed correction ...".

    A belief with `corrections == []` was omitted with a cause it does not have and a remedy
    (review the prose) that does not apply -- the actual remedy is re-verifying the dependency.
    """
    sel = select_beliefs(_result(_belief(dependency_alerts=["intake-42"])), POLICY)
    (cid, reason), = sel.omitted
    assert cid == "C"
    assert "correction" not in reason, reason
    assert "intake-42" in reason and "lost all support" in reason


def test_a_dirty_only_omission_names_the_moved_input_not_a_correction():
    """MUTATION CAUGHT: dropping the `dirty_inputs` branch from `_review_cause`."""
    sel = select_beliefs(_result(_belief(dirty_inputs=["spec.md@sha256:aa moved"])), POLICY)
    (_, reason), = sel.omitted
    assert "correction" not in reason, reason
    assert reason.startswith("dirty:")


def test_a_correction_only_omission_still_names_the_correction():
    """The paired positive -- the fix must not lose the cause it previously always reported."""
    sel = select_beliefs(_result(_belief(corrections=["corr-1"])), POLICY)
    (_, reason), = sel.omitted
    assert "1 unreviewed correction(s)" in reason
    assert "dependenc" not in reason and "dirty" not in reason


def test_all_three_causes_are_reported_together_not_first_match_wins():
    """MUTATION CAUGHT: an elif chain, or any `return` after the first matching branch."""
    sel = select_beliefs(
        _result(_belief(corrections=["c1"], dependency_alerts=["intake-42"],
                        dirty_inputs=["spec.md moved"])),
        POLICY,
    )
    (_, reason), = sel.omitted
    assert "correction" in reason and "intake-42" in reason and "dirty" in reason


def test_the_freshness_review_verdict_names_the_same_cause_as_the_omission():
    """MUTATION CAUGHT: reverting projection.py's REVIEW branch to its single-cause literal.

    The verdict and the omissions lane must not disagree about why a belief needs review.
    """
    b = _belief(dependency_alerts=["intake-42"])
    res = _result(b)
    man = ProjectionManifest(
        projection_id="p1", artifact_path="a.md", content_hash="sha256:x",
        rendered_frontier=1, fold_version="v1", policy_digest=POLICY.digest(), as_of=NOW,
        belief_versions={"C": belief_version(b)},
    )
    verdict, reasons = freshness_of(man, res)
    assert verdict == Freshness.REVIEW
    assert "correction" not in reasons[0], reasons
    assert "intake-42" in reasons[0]


def test_a_correction_still_reaches_the_review_verdict():
    """Paired positive for the freshness branch."""
    b = _belief(corrections=["corr-1"])
    res = _result(b)
    man = ProjectionManifest(
        projection_id="p1", artifact_path="a.md", content_hash="sha256:x",
        rendered_frontier=1, fold_version="v1", policy_digest=POLICY.digest(), as_of=NOW,
        belief_versions={"C": belief_version(b)},
    )
    verdict, reasons = freshness_of(man, res)
    assert verdict == Freshness.REVIEW
    assert "unreviewed correction" in reasons[0]


def test_the_cause_reporter_covers_every_disjunct_of_review_required():
    """Structural guard: if a FOURTH cause joins `review_required`, this test goes red.

    The gate's block-reason list and the projection's omission reason must both be extended
    when the condition is; a silently-unnamed cause is exactly the defect being fixed.
    """
    from projection import _review_cause
    for kwargs in ({"corrections": ["x"]},
                   {"dependency_alerts": ["x"]},
                   {"dirty_inputs": ["x"]}):
        b = _belief(**kwargs)
        assert b.review_required
        assert _review_cause(b) != "review required for a cause this projection cannot name"
