"""P5b: executable compliance suite — the fold checked against its own claimed properties.

Spec: docs/design/vidya-pilot-spec.md §18 (governance invariants); pattern adopted from Kumiho's
49-scenario postulate suite (intake-1033) and TOKI's Claim-vs-Wire method (intake-1035).

**Why this file exists separately from the unit tests.** The unit tests check that each piece does
what its author intended. This one checks that the SYSTEM has the properties the spec promises a
reader — and it is written from the spec's claims, not from the code. Two verdicts per property:

    CLAIM — what the design documents assert
    WIRE  — what the running code actually does

They are supposed to agree. The value is entirely in the cases where they would not, which is why
each test names the invariant it is checking rather than the function it is calling.

**Deliberately rejected postulates are tested too.** A property the design chose NOT to have is
still a property; leaving it untested means a future change could quietly introduce it. The
AGM Recovery postulate is the worked example: re-asserting a retracted claim must produce a fresh
belief, never resurrect the retracted evidence.
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
from gate import Outcome, Standard, UsePolicy, evaluate  # noqa: E402
from impact import impact_of_retracting  # noqa: E402

NOW = "2026-08-09T12:00:00Z"
FLOOR = lat.parse_grade("Verified/Anchored")


def _sup(claim, evidence, q="Verified", t="Anchored", kind="evidence_supports_claim"):
    return frames.make_frame(
        frame_type=f"epyc.vidya/frame/{kind}/v1",
        assertion={"claim_id": claim, "evidence_id": evidence, "grade": {"Q": q, "T": t}},
        provenance={"method": "compliance", "anchor": f"anchor:{evidence}"},
        actor="compliance", authority_scope="research-verification", created_at=NOW)


def _retract(target, claim):
    return frames.make_frame(
        frame_type="epyc.vidya/frame/retraction/v1",
        assertion={"retracts": target["frame_id"], "claim_id": claim},
        provenance={"method": "compliance", "about": target["frame_id"]},
        actor="operator", authority_scope="research-verification", created_at=NOW)


class TestGovernanceInvariants:
    """Spec §18, one test per numbered invariant that is mechanically checkable."""

    def test_inv2_frames_are_immutable_after_acceptance(self):
        # CLAIM: frames are immutable after acceptance.
        # WIRE:  content addressing makes any edit a different frame, detectable by validation.
        f = _sup("c", "e")
        original = f["frame_id"]
        f["assertion"]["claim_id"] = "tampered"
        with pytest.raises(frames.FrameValidationError):
            frames.validate_frame(f)
        assert original != frames.envelope_hash(f) if hasattr(frames, "envelope_hash") else True

    def test_inv3_derived_state_is_reproducible_from_frames_alone(self):
        # CLAIM: derived state is disposable and reproducible.
        # WIRE:  two independent folds of the same frames produce the same state hash.
        corpus = [_sup("a", "e1"), _sup("b", "e2", "Judged", "Located")]
        assert fold(corpus, as_of=NOW).state_hash() == fold(corpus, as_of=NOW).state_hash()

    def test_inv4_a_hash_proves_identity_not_truth(self):
        # CLAIM: a hash proves content identity, not truth or authority.
        # WIRE:  a well-formed frame asserting nonsense is still accepted and folded; nothing in
        #        the pipeline confuses "hashes correctly" with "is correct".
        nonsense = _sup("the-moon-is-cheese", "e", "Witnessed", "Attested")
        frames.validate_frame(nonsense)
        b = fold([nonsense], as_of=NOW).beliefs["the-moon-is-cheese"]
        assert b.pro == lat.TOP, "the fold reports what the evidence says, not what is true"

    def test_inv6_evidence_status_and_intent_stay_separate(self):
        # CLAIM: human intent authorizes work but cannot manufacture evidence.
        # WIRE:  an intent frame contributes no support to any claim.
        intent = frames.make_frame(
            frame_type="epyc.vidya/frame/human_intent_recorded/v1",
            assertion={"decision": "approve-integration-plan", "claim_ids": ["c"]},
            provenance={"method": "operator-approval", "about": "plan-1"},
            actor="operator", authority_scope="stage3-approval", created_at=NOW)
        result = fold([intent], as_of=NOW)
        assert result.beliefs == {}, "an approval must not create or support a belief"

    def test_inv9_a_stale_projection_is_never_served_as_current(self):
        # CLAIM: stale state is never served as current under an authoritative policy.
        # WIRE:  only ALLOW is usable_as_current, across every reachable outcome.
        weak = fold([_sup("c", "e", "Judged", "Located")], as_of=NOW)
        for pol in (
            UsePolicy(use="auth", floor=FLOOR),
            UsePolicy(use="explore", floor=FLOOR, allow_labelled_stale=True),
            UsePolicy(use="auth", floor=FLOOR, standard=Standard.BRD),
        ):
            res = evaluate("c", weak, pol)
            assert res.usable_as_current == (res.outcome == Outcome.ALLOW)

    def test_inv10_an_unresolved_change_yields_a_named_state_not_continuity(self):
        # CLAIM: an unresolved change yields dirty/unknown/downgraded/blocked -- never fabricated
        #        continuity.
        # WIRE:  retracting the only support drops the belief to bottom rather than holding the
        #        previous grade.
        s = _sup("c", "e")
        b = fold([s, _retract(s, "c")], as_of=NOW).beliefs["c"]
        assert b.pro == lat.BOTTOM

    def test_inv11_exact_impact_claims_are_qualified_by_coverage(self):
        # CLAIM: exact impact claims are always qualified by graph coverage.
        # WIRE:  the report refuses to call an unanchored belief 'verified unaffected'.
        target, vague = _sup("c1", "e1"), _sup("c2", "e2", "Verified", "Located")
        rep = impact_of_retracting([target, vague], [target["frame_id"]], as_of=NOW).as_dict()
        assert "c2" in rep["unaffected_but_unmapped"]
        assert rep["verified_unaffected"] == []

    def test_inv12_incremental_matches_full_refold(self):
        # CLAIM: full refold is the correctness oracle for incremental derivation.
        # WIRE:  the predicted impact equals a committed retraction's actual result.
        s1, s2 = _sup("c", "e1", "Witnessed", "Attested"), _sup("c", "e2", "Judged", "Located")
        predicted = impact_of_retracting([s1, s2], [s1["frame_id"]], as_of=NOW)
        actual = fold([s1, s2, _retract(s1, "c")], as_of=NOW).beliefs["c"]
        item = next(i for i in predicted.affected if i.claim_id == "c")
        assert (item.after_pro, item.after_con) == (actual.pro, actual.con)

    def test_inv13_history_survives_a_retraction(self):
        # CLAIM: historical decisions remain historical facts.
        # WIRE:  the retracted frame is still named in the belief, not erased from the record.
        s = _sup("c", "e")
        b = fold([s, _retract(s, "c")], as_of=NOW).beliefs["c"]
        assert s["frame_id"] in b.retracted_support


class TestRejectedPostulates:
    """Properties the design deliberately does NOT have.

    Untested rejections rot: a later change can quietly introduce the behaviour and nothing fails.
    """

    def test_recovery_is_rejected_re_assertion_is_fresh_not_resurrection(self):
        # AGM's Recovery postulate says contracting then re-expanding restores the original. This
        # design rejects it (intake-1033 §7.3): re-assertion is a NEW frame with its own
        # provenance, never a revival of the retracted one.
        original = _sup("c", "e-original", "Witnessed", "Attested")
        retract = _retract(original, "c")
        re_asserted = _sup("c", "e-fresh", "Judged", "Located")
        b = fold([original, retract, re_asserted], as_of=NOW).beliefs["c"]
        assert b.pro == lat.parse_grade("Judged/Located"), "must not resurrect the retracted grade"
        assert [label for label, _ in b.pro_paths] == ["e-fresh"]

    def test_the_fold_cannot_derive_accrual(self):
        # Two independent Judged paths must NOT combine into something stronger. Accrual is
        # non-idempotence, and adopting it would forfeit the deletion and convergence theorems.
        two = fold([_sup("c", "e1", "Judged", "Located"),
                    _sup("c", "e2", "Judged", "Located")], as_of=NOW).beliefs["c"]
        one = fold([_sup("c", "e1", "Judged", "Located")], as_of=NOW).beliefs["c"]
        assert two.pro == one.pro

    def test_a_correction_is_not_counter_evidence(self):
        # A correction marks review; it must never behave as opposition, or every corrected claim
        # would read as contested.
        s = _sup("c", "e")
        corr = frames.make_frame(
            frame_type="epyc.vidya/frame/correction_recorded/v1",
            assertion={"entry_id": "x", "claim_ids": ["c"], "correction_text": "t",
                       "classification": None},
            provenance={"method": "adapter", "about": "x", "parsed": False},
            actor="adapter", authority_scope="research-verification", created_at=NOW)
        b = fold([s, corr], as_of=NOW).beliefs["c"]
        assert b.con == lat.BOTTOM and b.review_required

    def test_no_model_is_reachable_from_the_fold(self):
        # Structural, not behavioural: the rule "no model invocation during fold" is enforced by
        # the module importing no client at all, so it cannot be violated by a code path nobody
        # exercised in a test.
        import fold as fold_module

        source = Path(fold_module.__file__).read_text()
        for forbidden in ("import requests", "import httpx", "openai", "anthropic", "urllib.request"):
            assert forbidden not in source, f"fold.py must not reach a model: found {forbidden!r}"


class TestClaimVsWire:
    """Spec claims restated as assertions, checked against the running code."""

    @pytest.mark.parametrize(
        "claim,check",
        [
            ("the carrier is 20 elements",
             lambda: len(lat.Q_LEVELS) * len(lat.T_LEVELS) == 20),
            ("Corroborated is not in the carrier",
             lambda: "Corroborated" not in lat.Q_LEVELS and "Corroborated" not in lat.T_LEVELS),
            ("bottom is (Q0,T0) and top is (Witnessed,Attested)",
             lambda: str(lat.BOTTOM) == "Q0/T0" and str(lat.TOP) == "Witnessed/Attested"),
            ("SE and DV are certifiable; PE/CCE/BRD are not",
             lambda: Standard.CERTIFIABLE == {"SE", "DV"}
             and Standard.ADVISORY_ONLY == {"PE", "CCE", "BRD"}),
        ],
    )
    def test_spec_claim_holds_in_code(self, claim, check):
        assert check(), f"spec claims {claim!r}, and the code disagrees"
