"""SC58 — a judgment frame is pinned to the DIGEST of the artifact it judged, and the belief goes
dirty when that digest moves.

Spec: docs/design/vidya-pilot-spec.md §6 (judge discipline), §7.2 (`dirty` is the belief state for
"a registered input changed and recomputation has not completed"), §8.1 (`dirty` maps to `aging`
in THE ONE CLASSIFIER, never to `stale`).

THE DEFECT THIS PINS, verified absent on 2026-09-07 before it was fixed. `_check_judgment` asked
only whether `read_set` and `tool_output_hash` were PRESENT. `read_set: ["a"]` folded cleanly and
so did `tool_output_hash: "sha256:aa"` — and the shipped fixtures in `test_vidya_p1.py` were
written that way, so the suite actively demonstrated that non-digest replay keys were accepted.
That is a contract on the NAME of a field, not on its content. `intake-1308#03`: "a read-back of
an older version of the code is worse than none, because it testifies about the wrong artifact" —
and the platform that finding came from enforces the rule only as prose and stores no hash of the
audited text, which is exactly why it cannot detect its own violation. We were in the identical
position: `dirty` appeared nowhere in the implementation, and the fold discarded a judgment's
`assertion.claim_id`, so even a correctly pinned judgment had no surface to be reported on.

Every refusal test below is paired with a MUTATION that makes the same fold succeed, and every
dirty test is paired with the clean case, because a checker that dirtied everything would satisfy
a one-sided suite just as well as a correct one.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))

import frames  # noqa: E402
import lattice as lat  # noqa: E402
from fold import FoldError, fold  # noqa: E402
from gate import Outcome, UsePolicy, evaluate  # noqa: E402

NOW = "2026-09-07T00:00:00Z"
D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64
TOOL = "sha256:" + "f" * 64
ARTIFACT = "wiki/kernel-lineage.md"


def _support(claim="c", evidence="e"):
    return frames.make_frame(
        frame_type="epyc.vidya/frame/evidence_supports_claim/v1",
        assertion={"claim_id": claim, "evidence_id": evidence,
                   "grade": {"Q": "Verified", "T": "Anchored"}},
        provenance={"method": "test", "anchor": f"anchor:{evidence}"},
        actor="test", authority_scope="research-verification", created_at=NOW)


def _judgment(*, claim="c", read_set=None, tool=TOOL, seed=1, assertion_extra=None):
    assertion = {"verdict": "equivalent"}
    if claim is not None:
        assertion["claim_id"] = claim
    if assertion_extra:
        assertion.update(assertion_extra)
    if read_set is None:
        read_set = [{"name": ARTIFACT, "digest": {"sha256": "1" * 64}}]
    return frames.make_frame(
        frame_type="epyc.vidya/frame/judgment_recorded/v1",
        assertion=assertion,
        provenance={"method": "llm-equivalence-check", "replay_key": {
            "read_set": read_set, "prompt": "p", "seed": seed,
            "model_version": "m", "temperature": 0, "tool_output_hash": tool}},
        actor="model:x", authority_scope="research-verification", created_at=NOW)


def _observe(name=ARTIFACT, hexdigest="2" * 64, at=NOW):
    """A frame that merely OBSERVES an artifact at a digest, via the in-toto `subjects` slot.

    That slot was already validated by `frames.validate_frame` and had no producer and no test in
    the entire tree — a digest-shaped hole in the envelope. It is the natural carrier for "this is
    what the artifact hashes to now", so SC58 reads it rather than inventing a parallel one.
    """
    return frames.make_frame(
        frame_type="epyc.vidya/frame/source_observed/v1",
        assertion={"source_id": "src-1", "locator": name, "source_kind": "wiki"},
        provenance={"method": "artifact-scan", "about": name},
        actor="scanner", authority_scope="research-verification", created_at=at,
        subjects=[{"name": name, "digest": {"sha256": hexdigest}}])


# --- (a) the pin: a digest, of a named artifact ----------------------------------------------

def test_a_bare_label_read_set_is_refused():
    """CATCHES the exact shipped defect: `read_set: ["a"]` used to fold."""
    with pytest.raises(FoldError, match="not a named artifact"):
        fold([_judgment(read_set=["a"])], as_of=NOW)


def test_a_named_digest_read_set_folds():
    """MUTATION for the test above — without it, the refusal test would also pass against a fold
    that rejected every judgment."""
    res = fold([_support(), _judgment()], as_of=NOW)
    assert len(res.counted_judgments) == 1


def test_a_named_artifact_without_a_digest_is_refused():
    """CATCHES: naming the artifact but pinning nothing — the half-fix that reads as a fix."""
    with pytest.raises(FoldError, match="no sha256 content digest"):
        fold([_judgment(read_set=[{"name": ARTIFACT}])], as_of=NOW)


def test_a_digest_without_a_name_is_refused():
    """CATCHES: an anonymous digest. It is pinned, but a move in an unnamed artifact is
    undetectable, so accepting it would leave half the property unimplementable."""
    with pytest.raises(FoldError, match="not a named artifact"):
        fold([_judgment(read_set=[D1])], as_of=NOW)


def test_an_empty_read_set_is_refused():
    with pytest.raises(FoldError, match="non-empty list"):
        fold([_judgment(read_set=[])], as_of=NOW)


@pytest.mark.parametrize("bad", ["sha256:aa", "aa", "not-a-hash", "sha256:" + "z" * 64, 7])
def test_a_tool_output_hash_that_is_not_a_digest_is_refused(bad):
    """CATCHES the second half of the shipped defect: the fixture's `"sha256:aa"` stub, which no
    real digest could be, satisfied a field literally named `tool_output_hash`."""
    with pytest.raises(FoldError, match="tool_output_hash"):
        fold([_judgment(tool=bad)], as_of=NOW)


def test_a_full_digest_tool_output_hash_is_accepted():
    """MUTATION for the parametrized refusal above."""
    assert len(fold([_judgment(tool=TOOL)], as_of=NOW).counted_judgments) == 1


def test_a_judgment_that_names_no_claim_is_refused():
    """CATCHES: a judgment nothing can attribute to a belief. The fold used to discard
    `assertion.claim_id` entirely, so a stale judgment had no surface to be reported on."""
    with pytest.raises(FoldError, match="no assertion.claim_id"):
        fold([_judgment(claim=None)], as_of=NOW)


# --- (b) the transition: dirty when the digest MOVES -----------------------------------------

def test_a_judgment_is_clean_while_its_artifact_has_not_moved():
    """The anti-vacuity anchor for every dirty test below."""
    b = fold([_support(), _judgment()], as_of=NOW).beliefs["c"]
    assert b.dirty_inputs == [] and b.dirty is False


def test_the_belief_goes_dirty_when_the_judged_digest_moves():
    """THE PROPERTY. CATCHES: a judgment testifying about a version of an artifact that no longer
    exists — indefinitely and undetectably, which is where this substrate was."""
    b = fold([_support(), _judgment(), _observe()], as_of=NOW).beliefs["c"]
    assert b.dirty is True
    assert len(b.dirty_inputs) == 1
    assert ARTIFACT in b.dirty_inputs[0]
    assert D1 in b.dirty_inputs[0] and D2 in b.dirty_inputs[0], \
        "a dirty report that names neither the digest judged nor the current one sends the reader " \
        "back to the ledger to re-derive what the fold already knew"


def test_an_unrelated_artifact_moving_leaves_the_belief_clean():
    """MUTATION: the check must be per-artifact. A fold that dirtied on ANY observation would pass
    the test above and be useless."""
    b = fold([_support(), _judgment(), _observe(name="other/file.md")], as_of=NOW).beliefs["c"]
    assert b.dirty is False


def test_a_re_judgement_at_the_current_digest_clears_dirty():
    """CATCHES the one-way ratchet — the failure the correction rule already had to be rescued
    from (spec risk §19.7), where a single flag blocks a claim forever and the gate deadlocks the
    work it was meant to protect."""
    corpus = [_support(), _judgment(), _observe(),
              _judgment(seed=2, read_set=[{"name": ARTIFACT, "digest": {"sha256": "2" * 64}}])]
    assert fold(corpus, as_of=NOW).beliefs["c"].dirty is False


def test_without_the_re_judgement_it_stays_dirty():
    """MUTATION for the test above: same corpus minus the re-judgement."""
    corpus = [_support(), _judgment(), _observe()]
    assert fold(corpus, as_of=NOW).beliefs["c"].dirty is True


def test_the_latest_observation_in_ledger_order_is_the_current_one():
    """CATCHES an order-blind implementation. A judgment written AFTER the artifact moved read the
    current artifact and is clean; the same two frames in the other order are not."""
    moved_then_judged = [_support(), _observe(), _judgment()]
    judged_then_moved = [_support(), _judgment(), _observe()]
    assert fold(moved_then_judged, as_of=NOW).beliefs["c"].dirty is False
    assert fold(judged_then_moved, as_of=NOW).beliefs["c"].dirty is True


def test_a_dirty_judgment_never_creates_a_belief():
    """CATCHES: the dirty stratum inventing claims. It annotates beliefs; it does not mint them."""
    res = fold([_judgment(claim="ghost"), _observe()], as_of=NOW)
    assert "ghost" not in res.beliefs


# --- (c) no grade moves, and the report names the right cause --------------------------------

def test_going_dirty_moves_no_lattice_value():
    """CATCHES: dirty being implemented as counter-evidence. It is a freshness state — same rule
    as corrections, for the same reason: we know the ground shifted, not by how much."""
    clean = fold([_support(), _judgment()], as_of=NOW).beliefs["c"]
    dirty = fold([_support(), _judgment(), _observe()], as_of=NOW).beliefs["c"]
    assert dirty.dirty is True and clean.dirty is False
    assert (dirty.pro, dirty.con) == (clean.pro, clean.con)
    assert dirty.pro_paths == clean.pro_paths and dirty.con_paths == clean.con_paths
    assert dirty.verdict(lat.parse_grade("Verified/Anchored")) == \
        clean.verdict(lat.parse_grade("Verified/Anchored"))


def test_dirty_is_on_the_review_path():
    assert fold([_support(), _judgment(), _observe()], as_of=NOW).beliefs["c"].review_required


def test_the_gate_blocks_a_dirty_belief_and_names_the_artifact_not_a_correction():
    """CATCHES the `test_gate_review_reasons` failure mode repeating for the new cause: a belief
    blocked purely by a moved digest must not be refused with a correction count it does not have.
    """
    res = fold([_support(), _judgment(), _observe()], as_of=NOW)
    r = evaluate("c", res, UsePolicy(use="wiki-authoritative",
                                     floor=lat.parse_grade("Verified/Anchored")))
    text = " ".join(r.reasons + r.required_next_actions)
    assert r.outcome == Outcome.BLOCK
    assert "dirty" in text and ARTIFACT in text
    assert "correction" not in text and "depends_on" not in text
    assert "re-judge" in text


def test_the_clean_belief_is_allowed_through_the_same_policy():
    """MUTATION for the test above: the BLOCK must be caused by the moved digest, not by the
    fixture failing the floor for some unrelated reason."""
    res = fold([_support(), _judgment()], as_of=NOW)
    r = evaluate("c", res, UsePolicy(use="wiki-authoritative",
                                     floor=lat.parse_grade("Verified/Anchored")))
    assert r.outcome == Outcome.ALLOW


def test_each_block_reason_still_has_a_matching_next_action():
    """The invariant `test_gate_review_reasons.py` pins, extended to the third cause."""
    res = fold([_support(), _judgment(), _observe()], as_of=NOW)
    r = evaluate("c", res, UsePolicy(use="wiki-authoritative",
                                     floor=lat.parse_grade("Verified/Anchored")))
    assert len(r.reasons) == len(r.required_next_actions) == 1


def test_a_policy_may_still_opt_in_to_review_required_beliefs():
    res = fold([_support(), _judgment(), _observe()], as_of=NOW)
    r = evaluate("c", res, UsePolicy(use="exploration",
                                     floor=lat.parse_grade("Verified/Anchored"),
                                     allow_review_required=True))
    assert r.outcome == Outcome.ALLOW


def test_dirty_inputs_appear_in_derived_state_only_when_present():
    """CATCHES: an always-present empty key moving the pinned golden state hash to record the
    absence of something nobody wrote."""
    clean = fold([_support(), _judgment()], as_of=NOW).beliefs["c"]
    dirty = fold([_support(), _judgment(), _observe()], as_of=NOW).beliefs["c"]
    assert "dirty_inputs" not in clean.as_dict()
    assert dirty.as_dict()["dirty_inputs"] == dirty.dirty_inputs
