"""OP-11: a withdrawn dependency marks its dependents for review, and moves no grade.

Operator-ratified 2026-08-10. The rule mirrors the correction rule — flag, never guess a magnitude
— and the tests below pin both halves, because the tempting failure is to "helpfully" downgrade.

The last test is the one that took two attempts to get right in the engine: a claim already under
review for its OWN correction must still register a NEW dependency alert. Those are two obligations
cleared by different people, and collapsing them made the propagation test score 0 while the fold
semantics were already working.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

from fold import fold  # noqa: E402
from frames import make_frame  # noqa: E402
from impact import impact_of_retracting  # noqa: E402

AT = "2026-08-10T00:00:00Z"
G = {"Q": "Verified", "T": "Anchored"}


def _f(ftype, assertion, provenance):
    return make_frame(frame_type=ftype, assertion=assertion, provenance=provenance,
                      actor="test", authority_scope="test", created_at=AT)


def source(sid, locator):
    return _f("epyc.vidya/frame/source_observed/v1",
              {"source_id": sid, "locator": locator, "title": sid},
              {"about": sid, "method": "test"})


def claim(cid, sid):
    return _f("epyc.vidya/frame/claim_proposed/v1",
              {"claim_id": cid, "display_text": cid, "source_id": sid},
              {"about": cid, "method": "test"})


def support(cid, sid):
    return _f("epyc.vidya/frame/evidence_supports_claim/v1",
              {"claim_id": cid, "evidence_id": f"evd_{cid}", "grade": G, "source_id": sid},
              {"evidence": f"evd_{cid}", "about": cid})


def depends(cid, target_src, target_entry):
    return _f("epyc.vidya/frame/claim_depends_on/v1",
              {"claim_id": cid, "depends_on_source": target_src,
               "depends_on_entry": target_entry, "rationale": "test"},
              {"about": cid, "method": "test", "authored_by": "human"})


def correction(cid):
    return _f("epyc.vidya/frame/correction_recorded/v1",
              {"claim_ids": [cid], "correction_text": "its own source was corrected"},
              {"about": cid, "method": "test"})


def base():
    """`clm_b` depends on source `s_a`, which supports `clm_a`."""
    return [
        source("s_a", "https://example.com/a"), claim("clm_a", "s_a"), support("clm_a", "s_a"),
        source("s_b", "https://example.com/b"), claim("clm_b", "s_b"), support("clm_b", "s_b"),
        depends("clm_b", "s_a", "intake-a"),
    ]


def retraction_of(frames, source_id):
    ids = [f["frame_id"] for f in frames
           if f["frame_type"].endswith("evidence_supports_claim/v1")
           and f["assertion"]["source_id"] == source_id]
    assert ids, source_id
    return ids


def test_intact_dependency_raises_no_flag():
    b = fold(base(), as_of=AT).beliefs["clm_b"]
    assert b.dependency_alerts == []
    assert b.review_required is False


def test_withdrawn_dependency_flags_the_dependent():
    frames = base()
    targets = retraction_of(frames, "s_a")
    after = fold(frames + [
        _f("epyc.vidya/frame/retraction/v1", {"retracts": fid},
           {"method": "test", "about": fid}) for fid in targets
    ], as_of=AT)
    b = after.beliefs["clm_b"]
    assert b.dependency_alerts == ["intake-a"]
    assert b.review_required is True


def test_withdrawn_dependency_moves_no_grade():
    """The whole point of the ratified option: flag, do not guess a magnitude."""
    frames = base()
    before = fold(frames, as_of=AT).beliefs["clm_b"]
    targets = retraction_of(frames, "s_a")
    after = fold(frames + [
        _f("epyc.vidya/frame/retraction/v1", {"retracts": fid},
           {"method": "test", "about": fid}) for fid in targets
    ], as_of=AT).beliefs["clm_b"]
    assert (after.pro, after.con) == (before.pro, before.con)


def test_the_dependent_appears_in_the_impact_report():
    frames = base()
    report = impact_of_retracting(frames, retraction_of(frames, "s_a"), as_of=AT)
    affected = {i.claim_id for i in report.affected}
    assert "clm_b" in affected, "a review-only effect is still impact"


def test_a_claim_already_under_review_still_registers_a_new_alert():
    """Two reasons to review are two obligations; the second must not hide behind the first."""
    frames = base() + [correction("clm_b")]
    assert fold(frames, as_of=AT).beliefs["clm_b"].review_required is True

    report = impact_of_retracting(frames, retraction_of(frames, "s_a"), as_of=AT)
    item = next(i for i in report.affected if i.claim_id == "clm_b")
    assert item.review_changed is False, "it was already flagged, so the flag did not flip"
    assert item.dependency_alerts == ["intake-a"], "but the new alert is what makes it affected"


def test_an_undeclared_citation_propagates_nothing():
    """Only an authored `depends_on` propagates — citation alone must not."""
    frames = [f for f in base() if f["frame_type"] != "epyc.vidya/frame/claim_depends_on/v1"]
    report = impact_of_retracting(frames, retraction_of(frames, "s_a"), as_of=AT)
    assert "clm_b" not in {i.claim_id for i in report.affected}
