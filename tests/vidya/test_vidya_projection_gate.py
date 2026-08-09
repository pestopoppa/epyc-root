"""P4 + P5: projections with dependency manifests, and the query-time freshness gate.

Spec: docs/design/vidya-pilot-spec.md §8, §9, §11.2, §12.

The load-bearing tests here are about refusal. A gate that only gets tested on the allow path is a
gate nobody has checked, and the pilot's entire promise is about what happens when the answer is
NOT available.
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
from projection import (  # noqa: E402
    Freshness,
    SelectionPolicy,
    build_manifest,
    freshness_of,
    select_beliefs,
)

NOW = "2026-08-09T12:00:00Z"
FLOOR = lat.parse_grade("Verified/Anchored")


def _sup(claim, evidence, q, t, kind="evidence_supports_claim"):
    return frames.make_frame(
        frame_type=f"epyc.vidya/frame/{kind}/v1",
        assertion={"claim_id": claim, "evidence_id": evidence, "grade": {"Q": q, "T": t}},
        provenance={"method": "test", "anchor": f"anchor:{evidence}"},
        actor="test", authority_scope="research-verification", created_at=NOW)


def _correction(claim_ids):
    return frames.make_frame(
        frame_type="epyc.vidya/frame/correction_recorded/v1",
        assertion={"entry_id": "e", "claim_ids": claim_ids, "correction_text": "x",
                   "classification": None},
        provenance={"method": "adapter", "about": "e", "parsed": False},
        actor="adapter", authority_scope="research-verification", created_at=NOW)


POLICY = SelectionPolicy(policy_id="wiki-authoritative-v1", floor=FLOOR)


class TestSelection:
    def test_eligible_belief_is_included(self):
        r = fold([_sup("c", "e", "Verified", "Anchored")], as_of=NOW)
        sel = select_beliefs(r, POLICY)
        assert [b.claim_id for b in sel.included] == ["c"] and sel.omitted == []

    def test_every_exclusion_is_named_with_a_reason(self):
        # The omissions lane: a manifest that lists only assertions is silent about what the page
        # should have said and did not, which is the failure a reader cannot see.
        r = fold([_sup("weak", "e", "Judged", "Located")], as_of=NOW)
        sel = select_beliefs(r, POLICY)
        assert sel.included == []
        assert sel.omitted[0][0] == "weak" and "conjunctive" in sel.omitted[0][1]

    def test_conflicted_belief_is_omitted_by_default(self):
        r = fold([_sup("c", "e1", "Verified", "Anchored"),
                  _sup("c", "e2", "Verified", "Anchored", "evidence_opposes_claim")], as_of=NOW)
        assert select_beliefs(r, POLICY).omitted[0][1].startswith("conflicted")

    def test_review_required_belief_is_omitted_by_default(self):
        r = fold([_sup("c", "e", "Verified", "Anchored"), _correction(["c"])], as_of=NOW)
        sel = select_beliefs(r, POLICY)
        assert sel.included == [] and "correction" in sel.omitted[0][1]

    def test_selection_is_deterministic(self):
        r = fold([_sup("a", "e1", "Verified", "Anchored"),
                  _sup("b", "e2", "Verified", "Anchored")], as_of=NOW)
        assert [b.claim_id for b in select_beliefs(r, POLICY).included] == ["a", "b"]


class TestManifest:
    def _built(self, frames_in, claim_ids=None):
        r = fold(frames_in, as_of=NOW)
        sel = select_beliefs(r, POLICY, claim_ids=claim_ids)
        text, man = build_manifest(
            projection_id="prj-1", artifact_path="wiki/x.md", selection=sel,
            fold_result=r, policy=POLICY, fold_version="test-0")
        return r, sel, text, man

    def test_manifest_records_every_rendered_belief(self):
        _, _, _, man = self._built([_sup("c", "e", "Verified", "Anchored")])
        assert set(man.belief_versions) == {"c"}
        assert man.assertions[0].belief_ids == ["c"]

    def test_manifest_carries_the_omissions_lane(self):
        _, _, _, man = self._built([_sup("c", "e", "Verified", "Anchored"),
                                    _sup("weak", "e2", "Hinted", "Located")])
        assert [o["claim_id"] for o in man.omissions] == ["weak"]
        assert man.omissions[0]["reason"]

    def test_manifest_pins_the_policy_digest(self):
        _, _, _, man = self._built([_sup("c", "e", "Verified", "Anchored")])
        assert man.policy_digest == POLICY.digest()
        other = SelectionPolicy(policy_id="other", floor=lat.parse_grade("Hinted/Located"))
        assert other.digest() != POLICY.digest()

    def test_an_assertion_citing_an_unselected_belief_is_refused(self):
        # Verification is part of publication, not a later step.
        from projection import Assertion

        r = fold([_sup("c", "e", "Verified", "Anchored")], as_of=NOW)
        sel = select_beliefs(r, POLICY)
        bad = lambda _: ("text\n", [Assertion("ast_0", "text", ["not-selected"])])  # noqa: E731
        with pytest.raises(ValueError, match="cites beliefs the policy did not select"):
            build_manifest(projection_id="p", artifact_path="x", selection=sel,
                           fold_result=r, policy=POLICY, fold_version="t", renderer=bad)

    def test_a_factual_assertion_with_no_belief_is_refused(self):
        from projection import Assertion

        r = fold([_sup("c", "e", "Verified", "Anchored")], as_of=NOW)
        sel = select_beliefs(r, POLICY)
        bad = lambda _: ("t\n", [Assertion("ast_0", "t", [])])  # noqa: E731
        with pytest.raises(ValueError, match="cites no belief"):
            build_manifest(projection_id="p", artifact_path="x", selection=sel,
                           fold_result=r, policy=POLICY, fold_version="t", renderer=bad)


class TestFreshness:
    def _setup(self):
        base = [_sup("c", "e1", "Verified", "Anchored")]
        r = fold(base, as_of=NOW)
        sel = select_beliefs(r, POLICY)
        text, man = build_manifest(projection_id="p", artifact_path="x", selection=sel,
                                   fold_result=r, policy=POLICY, fold_version="t")
        return base, text, man

    def test_unchanged_state_is_current(self):
        base, text, man = self._setup()
        assert freshness_of(man, fold(base, as_of=NOW), artifact_text=text)[0] == Freshness.CURRENT

    def test_added_support_makes_it_stale(self):
        base, text, man = self._setup()
        later = fold(base + [_sup("c", "e2", "Witnessed", "Attested")], as_of=NOW)
        state, reasons = freshness_of(man, later, artifact_text=text)
        assert state == Freshness.STALE and "version changed" in reasons[0]

    def test_a_correction_alone_makes_it_stale(self):
        # The grade does not move, but a reader would not know a review is outstanding -- which is
        # exactly the kind of silent drift a projection manifest exists to catch.
        base, text, man = self._setup()
        later = fold(base + [_correction(["c"])], as_of=NOW)
        assert freshness_of(man, later, artifact_text=text)[0] == Freshness.STALE

    def test_prose_edited_outside_the_compiler_is_invalid_not_stale(self):
        base, _, man = self._setup()
        state, reasons = freshness_of(man, fold(base, as_of=NOW),
                                      artifact_text="somebody hand-edited this\n")
        assert state == Freshness.INVALID and "edited outside the compiler" in reasons[0]

    def test_retracted_support_makes_it_stale(self):
        base, text, man = self._setup()
        retract = frames.make_frame(
            frame_type="epyc.vidya/frame/retraction/v1",
            assertion={"retracts": base[0]["frame_id"], "claim_id": "c"},
            provenance={"method": "op", "about": base[0]["frame_id"]},
            actor="op", authority_scope="research-verification", created_at=NOW)
        assert freshness_of(man, fold(base + [retract], as_of=NOW),
                            artifact_text=text)[0] == Freshness.STALE


class TestGate:
    def _policy(self, **kw):
        base = dict(use="wiki-authoritative", floor=FLOOR, standard=Standard.DV)
        base.update(kw)
        return UsePolicy(**base)

    def test_allow_carries_a_certificate(self):
        r = fold([_sup("c", "e", "Verified", "Anchored")], as_of=NOW)
        res = evaluate("c", r, self._policy())
        assert res.outcome == Outcome.ALLOW and res.usable_as_current
        cert = res.certificate
        assert cert["input_attestations"] == ["e"]
        assert cert["policy"]["digest"] == self._policy().digest()
        assert "NOT that the underlying proposition is true" in cert["proves"]
        assert cert["certificate_hash"].startswith("sha256:")

    def test_insufficient_support_abstains_and_names_the_missing_axis(self):
        # A refusal that does not say what is missing is a shrug.
        r = fold([_sup("c", "e", "Judged", "Located")], as_of=NOW)
        res = evaluate("c", r, self._policy())
        assert res.outcome == Outcome.ABSTAIN and not res.usable_as_current
        actions = " ".join(res.required_next_actions)
        assert "warrant quality" in actions and "traceability" in actions
        assert "claim_anchors" in actions

    def test_missing_claim_abstains(self):
        assert evaluate("nope", fold([], as_of=NOW), self._policy()).outcome == Outcome.ABSTAIN

    def test_conflict_blocks_by_default(self):
        r = fold([_sup("c", "e1", "Verified", "Anchored"),
                  _sup("c", "e2", "Verified", "Anchored", "evidence_opposes_claim")], as_of=NOW)
        res = evaluate("c", r, self._policy())
        assert res.outcome == Outcome.BLOCK and "conflicted" in res.reasons[0]

    def test_unreviewed_correction_blocks(self):
        r = fold([_sup("c", "e", "Verified", "Anchored"), _correction(["c"])], as_of=NOW)
        res = evaluate("c", r, self._policy())
        assert res.outcome == Outcome.BLOCK
        assert "review the recorded correction" in " ".join(res.required_next_actions)

    def test_stale_frontier_recomputes_rather_than_refusing(self):
        r = fold([_sup("c", "e", "Verified", "Anchored")], as_of=NOW)
        res = evaluate("c", r, self._policy(), requested_frontier=99)
        assert res.outcome == Outcome.RECOMPUTE

    def test_exploratory_policy_may_opt_into_a_labelled_answer(self):
        r = fold([_sup("c", "e", "Judged", "Located")], as_of=NOW)
        res = evaluate("c", r, self._policy(use="exploration", allow_labelled_stale=True))
        assert res.outcome == Outcome.ALLOW_WITH_WARNING
        assert not res.usable_as_current, "labelled != authoritative"
        assert res.certificate is None

    def test_advisory_standard_is_refused_not_downgraded(self):
        # A policy that thinks it got BRD and got SE is worse off than one that got an error.
        r = fold([_sup("c", "e", "Witnessed", "Attested")], as_of=NOW)
        res = evaluate("c", r, self._policy(standard=Standard.BRD))
        assert res.outcome == Outcome.BLOCK
        assert "advisory degrees" in res.reasons[0]

    def test_independence_requirement_abstains_when_unmet(self):
        r = fold([_sup("c", "e", "Verified", "Anchored")], as_of=NOW)
        res = evaluate("c", r, self._policy(min_disjoint_supports=2))
        assert res.outcome == Outcome.ABSTAIN and "independent support" in res.reasons[0]

    def test_independence_requirement_met_by_two_paths(self):
        r = fold([_sup("c", "e1", "Verified", "Anchored"),
                  _sup("c", "e2", "Verified", "Anchored")], as_of=NOW)
        assert evaluate("c", r, self._policy(min_disjoint_supports=2)).outcome == Outcome.ALLOW

    def test_the_gate_never_serves_stale_as_current(self):
        """The pilot's one promise, stated as a test.

        Across every reachable outcome, `usable_as_current` is true only for ALLOW.
        """
        r = fold([_sup("c", "e", "Judged", "Located"), _correction(["c"])], as_of=NOW)
        for pol in (self._policy(), self._policy(allow_labelled_stale=True),
                    self._policy(standard=Standard.PE)):
            res = evaluate("c", r, pol)
            assert res.usable_as_current == (res.outcome == Outcome.ALLOW)
            if res.outcome != Outcome.ALLOW:
                assert res.certificate is None, "only an ALLOW may carry a certificate"


class TestR5bTelemetry:
    """The two write-time records that cannot be reconstructed later."""

    def test_query_served_records_the_outcome_not_just_the_hit(self):
        from gate import query_served_frame

        r = fold([_sup("c", "e", "Judged", "Located")], as_of=NOW)
        res = evaluate("c", r, UsePolicy(use="wiki-authoritative", floor=FLOOR))
        f = query_served_frame(res, UsePolicy(use="wiki-authoritative", floor=FLOOR),
                               frontier=r.frontier, at=NOW)
        frames.validate_frame(f)
        # An abstention is the datum that says the gate refuses too much; a success-only log hides it.
        assert f["assertion"]["outcome"] == Outcome.ABSTAIN
        assert f["assertion"]["usable_as_current"] is False

    def test_query_served_carries_the_policy_digest(self):
        from gate import query_served_frame

        pol = UsePolicy(use="explore", floor=FLOOR)
        r = fold([_sup("c", "e", "Verified", "Anchored")], as_of=NOW)
        f = query_served_frame(evaluate("c", r, pol), pol, frontier=r.frontier, at=NOW)
        assert f["provenance"]["policy_digest"] == pol.digest()

    def test_obligation_disposition_rejects_an_unknown_value(self):
        from gate import obligation_disposition_frame

        with pytest.raises(ValueError, match="disposition must be one of"):
            obligation_disposition_frame("obl-1", "sort-of-did-it", actor="op", at=NOW)

    def test_obligation_disposition_frame_is_valid(self):
        from gate import obligation_disposition_frame

        f = obligation_disposition_frame("obl-1", "dismissed", actor="operator", at=NOW,
                                         note="not relevant to this projection")
        frames.validate_frame(f)
        assert f["assertion"]["disposition"] == "dismissed"
