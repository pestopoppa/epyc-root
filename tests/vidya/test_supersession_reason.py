"""SC59 — an optional free-text `reason` on supersession and retraction, surfaced and never weighed.

Spec: docs/design/vidya-pilot-spec.md §3.5 (supersession / retraction / dispute).

THE CONSUMER. A citer who is told that a frame was superseded currently learns THAT and nothing
more, and so re-walks the rejected reasoning at full price — while the person who superseded it
already knew why and had nowhere to write it down. Precedent: Prove2Me makes `reason` mandatory on
every milestone re-link specifically so solvers do not re-walk rejected paths
(`intake-1299#record`).

THE PROHIBITION, which is the harder half. The reason has NO GRADE EFFECT, deliberately and for
exactly the reason a correction has none: we know the ground shifted, not by how much, and a system
that inferred the magnitude from prose would manufacture the confidence this substrate exists to
refuse. So this file is mostly negative tests — the reason must move no lattice value, no verdict,
no `review_required`, and no gate OUTCOME. It may only change what a refusal SAYS.

Each of those negatives is paired with the positive that the text really did arrive, because a
no-op implementation would satisfy every "changes nothing" assertion here perfectly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))

import frames  # noqa: E402
import lattice as lat  # noqa: E402
from fold import fold  # noqa: E402
from gate import UsePolicy, evaluate  # noqa: E402

NOW = "2026-09-07T00:00:00Z"
FLOOR = lat.parse_grade("Verified/Anchored")
WHY = "the sweep used the pre-freeze binary; re-run under v9 before re-deriving this"


def _support(claim="c", evidence="e", q="Verified", t="Anchored", **kw):
    return frames.make_frame(
        frame_type="epyc.vidya/frame/evidence_supports_claim/v1",
        assertion={"claim_id": claim, "evidence_id": evidence, "grade": {"Q": q, "T": t}},
        provenance={"method": "test", "anchor": f"anchor:{evidence}"},
        actor="test", authority_scope="research-verification", created_at=NOW, **kw)


def _retraction(target, *, claim="c", reason=None):
    assertion = {"retracts": target["frame_id"], "claim_id": claim}
    if reason is not None:
        assertion["reason"] = reason
    return frames.make_frame(
        frame_type="epyc.vidya/frame/retraction/v1",
        assertion=assertion,
        provenance={"method": "operator-retraction", "about": target["frame_id"]},
        actor="operator", authority_scope="research-verification", created_at=NOW)


# --- the text arrives -------------------------------------------------------------------------

def test_a_retraction_reason_reaches_the_belief():
    """CATCHES: a reason recorded in the ledger and dropped by the fold — written down where
    nobody reads it is the same as never written."""
    s = _support()
    b = fold([s, _retraction(s, reason=WHY)], as_of=NOW).beliefs["c"]
    assert len(b.supersession_reasons) == 1 and WHY in b.supersession_reasons[0]
    assert s["frame_id"] in b.supersession_reasons[0], "a reason must name what it is about"


def test_the_same_retraction_without_a_reason_records_nothing():
    """MUTATION for the test above. `reason` is OPTIONAL, and absence is recorded as absence — a
    reason is never invented on read."""
    s = _support()
    assert fold([s, _retraction(s)], as_of=NOW).beliefs["c"].supersession_reasons == []


def test_a_supersession_reason_reaches_the_belief():
    """The other carrier: `pubinfo.supersedes_reason` on the frame that did the superseding."""
    first = _support(evidence="e1")
    second = _support(evidence="e2", supersedes=first["frame_id"], supersedes_reason=WHY)
    b = fold([first, second], as_of=NOW).beliefs["c"]
    assert len(b.supersession_reasons) == 1 and WHY in b.supersession_reasons[0]
    assert first["frame_id"] in b.supersession_reasons[0]


def test_a_retraction_reason_finds_the_claim_through_the_frame_it_retracted():
    """CATCHES: requiring the retraction to repeat the claim id. A retraction names a FRAME; the
    fold must resolve that to a belief, or every reason written the natural way is lost."""
    s = _support()
    bare = frames.make_frame(
        frame_type="epyc.vidya/frame/retraction/v1",
        assertion={"retracts": s["frame_id"], "reason": WHY},   # no claim_id
        provenance={"method": "operator-retraction", "about": s["frame_id"]},
        actor="operator", authority_scope="research-verification", created_at=NOW)
    assert WHY in fold([s, bare], as_of=NOW).beliefs["c"].supersession_reasons[0]


def test_a_reason_never_creates_a_belief():
    """CATCHES: an annotation minting a claim out of a dangling reference."""
    s = _support(claim="c")
    orphan = _retraction(s, claim="nobody", reason=WHY)
    assert "nobody" not in fold([s, orphan], as_of=NOW).beliefs


def test_an_empty_or_whitespace_reason_is_not_recorded():
    s = _support()
    for blank in ("", "   ", None):
        assert fold([s, _retraction(s, reason=blank)], as_of=NOW) \
            .beliefs["c"].supersession_reasons == []


# --- and moves nothing ------------------------------------------------------------------------

def test_the_reason_moves_no_lattice_value_and_no_verdict():
    """THE PROHIBITION. Identical corpora but for the prose; every graded quantity must be equal.

    Paired deliberately with `test_a_retraction_reason_reaches_the_belief` above: without that
    positive, this test would pass against an implementation that ignored `reason` entirely.
    """
    s = _support()
    without = fold([s, _retraction(s)], as_of=NOW).beliefs["c"]
    with_ = fold([s, _retraction(s, reason=WHY)], as_of=NOW).beliefs["c"]
    assert with_.supersession_reasons and not without.supersession_reasons
    assert (with_.pro, with_.con) == (without.pro, without.con)
    assert with_.pro_paths == without.pro_paths and with_.con_paths == without.con_paths
    assert with_.pro_sources == without.pro_sources
    assert with_.verdict(FLOOR) == without.verdict(FLOOR)


def test_the_reason_does_not_put_a_belief_on_the_review_path():
    """CATCHES: prose acquiring the force of a correction. `review_required` is for conditions a
    person must clear; a reason is an explanation of one that already happened."""
    first = _support(evidence="e1")
    second = _support(evidence="e2", supersedes=first["frame_id"], supersedes_reason=WHY)
    b = fold([first, second], as_of=NOW).beliefs["c"]
    assert b.supersession_reasons and b.review_required is False


def test_the_reason_does_not_change_the_gate_outcome():
    """The outcome is bit-identical; only the text differs. This is why `gate.evaluate` appends
    the notes strictly OUTSIDE `_decide`."""
    s = _support()
    policy = UsePolicy(use="wiki-authoritative", floor=FLOOR)
    without = evaluate("c", fold([s, _retraction(s)], as_of=NOW), policy)
    with_ = evaluate("c", fold([s, _retraction(s, reason=WHY)], as_of=NOW), policy)
    assert with_.outcome == without.outcome
    assert with_.required_next_actions == without.required_next_actions
    assert with_.certificate == without.certificate


def test_the_reason_is_surfaced_to_the_citer():
    """MUTATION for the test above: without this, a gate that silently discarded every note would
    satisfy `test_the_reason_does_not_change_the_gate_outcome` perfectly."""
    s = _support()
    r = evaluate("c", fold([s, _retraction(s, reason=WHY)], as_of=NOW),
                 UsePolicy(use="wiki-authoritative", floor=FLOOR))
    text = " ".join(r.reasons)
    assert WHY in text
    assert "carries no grade" in text, "surfacing prose without labelling it invites it being read " \
                                       "as evidence, which is precisely what it is not"


def test_the_reason_is_surfaced_on_an_allowed_answer_too():
    """A superseded-but-still-supported claim is the case the citer most needs the note on: the
    gate says yes, and the note says which path was already rejected and why."""
    first = _support(evidence="e1")
    second = _support(evidence="e2", supersedes=first["frame_id"], supersedes_reason=WHY)
    r = evaluate("c", fold([first, second], as_of=NOW),
                 UsePolicy(use="wiki-authoritative", floor=FLOOR))
    assert r.usable_as_current and WHY in " ".join(r.reasons)


def test_derived_state_carries_the_reason_only_when_there_is_one():
    """CATCHES: an always-present empty key moving the pinned golden state hash (test_vidya_golden)
    to record the absence of a field nobody wrote."""
    s = _support()
    assert "supersession_reasons" not in fold([s], as_of=NOW).beliefs["c"].as_dict()
    assert "supersession_reasons" in \
        fold([s, _retraction(s, reason=WHY)], as_of=NOW).beliefs["c"].as_dict()


# --- envelope discipline ----------------------------------------------------------------------

def test_a_reason_with_nothing_to_be_the_reason_for_is_refused():
    """CATCHES: a dangling explanation, which reads as an explanation of the whole frame."""
    with pytest.raises(frames.FrameValidationError, match="must say what"):
        frames.make_frame(
            frame_type="epyc.vidya/frame/evidence_supports_claim/v1",
            assertion={"claim_id": "c", "evidence_id": "e", "grade": {"Q": "Judged", "T": "T0"}},
            provenance={"method": "test", "anchor": "anchor:e"},
            actor="test", authority_scope="research-verification", created_at=NOW,
            supersedes_reason=WHY)


def test_the_same_frame_validates_once_it_says_what_it_superseded():
    """MUTATION for the test above."""
    assert _support(supersedes="sha256:" + "0" * 64, supersedes_reason=WHY)["pubinfo"][
        "supersedes_reason"] == WHY


def test_an_empty_supersedes_reason_is_refused_by_the_envelope():
    with pytest.raises(frames.FrameValidationError, match="non-empty string"):
        _support(supersedes="sha256:" + "0" * 64, supersedes_reason="   ")


def test_the_reason_is_still_forbidden_from_carrying_grade():
    """CATCHES: SC59 being used as a doorway past lint rule 2 — pubinfo speaks only of the frame,
    and a frame inherits nothing from the one it replaced."""
    with pytest.raises(frames.FrameValidationError, match="pubinfo must not carry"):
        _support(supersedes="sha256:" + "0" * 64, supersedes_reason=WHY,
                 extra_pubinfo={"grade": {"Q": "Witnessed", "T": "Attested"}})
