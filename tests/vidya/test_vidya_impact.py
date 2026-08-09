"""P3: reverse impact, coverage classes, and obligation state.

Spec: docs/design/vidya-pilot-spec.md §5.5, §10, §14.

The tests that matter most here are the ones about what the report REFUSES to say. An impact
report's dangerous failure is not missing a change -- it is confidently reporting "these are
untouched" about items whose dependencies were never registered. Several tests below exist purely
to pin that distinction.
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
from impact import (  # noqa: E402
    Coverage,
    Obligation,
    ObligationState,
    coverage_of,
    derive_obligations,
    impact_of_retracting,
)

NOW = "2026-08-09T12:00:00Z"
FLOOR = lat.parse_grade("Verified/Anchored")


def _sup(claim, evidence, q, t, kind="evidence_supports_claim"):
    return frames.make_frame(
        frame_type=f"epyc.vidya/frame/{kind}/v1",
        assertion={"claim_id": claim, "evidence_id": evidence, "grade": {"Q": q, "T": t}},
        provenance={"method": "test", "anchor": f"anchor:{evidence}"},
        actor="test", authority_scope="research-verification", created_at=NOW)


class TestCoverage:
    def test_fully_anchored_support_is_claim_complete(self):
        b = fold([_sup("c", "e", "Verified", "Anchored")], as_of=NOW).beliefs["c"]
        assert coverage_of(b) == Coverage.CLAIM_COMPLETE

    def test_document_level_support_is_only_source_complete(self):
        b = fold([_sup("c", "e", "Verified", "Located")], as_of=NOW).beliefs["c"]
        assert coverage_of(b) == Coverage.SOURCE_COMPLETE

    def test_mixed_anchoring_is_partial(self):
        b = fold([_sup("c", "e1", "Verified", "Anchored"),
                  _sup("c", "e2", "Judged", "Located")], as_of=NOW).beliefs["c"]
        assert coverage_of(b) == Coverage.PARTIAL

    def test_no_support_is_unmapped(self):
        from fold import Belief
        assert coverage_of(Belief(claim_id="c")) == Coverage.UNMAPPED


class TestImpact:
    def test_retracting_one_of_two_paths_downgrades_without_unsupporting(self):
        strong = _sup("c", "e-strong", "Witnessed", "Attested")
        weak = _sup("c", "e-weak", "Judged", "Located")
        rep = impact_of_retracting([strong, weak], [strong["frame_id"]], as_of=NOW)
        item = next(i for i in rep.affected if i.claim_id == "c")
        assert item.before_pro == lat.parse_grade("Witnessed/Attested")
        assert item.after_pro == lat.parse_grade("Judged/Located")
        assert item.surviving_paths == ["e-weak"] and not item.fragile

    def test_retracting_the_only_path_is_flagged_fragile(self):
        only = _sup("c", "e", "Verified", "Anchored")
        rep = impact_of_retracting([only], [only["frame_id"]], as_of=NOW)
        item = next(i for i in rep.affected if i.claim_id == "c")
        assert item.after_pro == lat.BOTTOM and item.fragile

    def test_unrelated_anchored_claim_is_verified_unaffected(self):
        target = _sup("c1", "e1", "Verified", "Anchored")
        other = _sup("c2", "e2", "Verified", "Anchored")
        rep = impact_of_retracting([target, other], [target["frame_id"]], as_of=NOW)
        assert "c2" in rep.verified_unaffected
        assert "c2" not in rep.unaffected_but_unmapped

    def test_unanchored_claim_is_NOT_claimed_as_verified_unaffected(self):
        """The exactness contract, enforced.

        A document-level claim may well be unaffected, but we cannot verify that from the edges we
        have. Reporting it as 'untouched' would be the confidently-precise-and-quietly-wrong output
        this whole contract exists to prevent.
        """
        target = _sup("c1", "e1", "Verified", "Anchored")
        vague = _sup("c2", "e2", "Verified", "Located")   # document-level only
        rep = impact_of_retracting([target, vague], [target["frame_id"]], as_of=NOW)
        assert "c2" in rep.unaffected_but_unmapped
        assert "c2" not in rep.verified_unaffected

    def test_report_separates_the_two_unaffected_counts(self):
        d = impact_of_retracting(
            [_sup("c1", "e1", "Verified", "Anchored"), _sup("c2", "e2", "Judged", "Located")],
            [], as_of=NOW).as_dict()
        assert "verified_unaffected_count" in d and "unaffected_but_unmapped_count" in d
        assert "exactness_note" in d

    def test_impact_is_hypothetical_and_commits_nothing(self):
        s = _sup("c", "e", "Verified", "Anchored")
        corpus = [s]
        before = fold(corpus, as_of=NOW).state_hash()
        impact_of_retracting(corpus, [s["frame_id"]], as_of=NOW)
        assert fold(corpus, as_of=NOW).state_hash() == before, "impact must not mutate anything"

    def test_impact_matches_a_real_retraction(self):
        """The predicted state must equal the state a committed retraction actually produces.

        This is the property that makes the report trustworthy, and it holds by construction only
        because impact runs the same fold rather than a parallel traversal.
        """
        s1 = _sup("c", "e1", "Witnessed", "Attested")
        s2 = _sup("c", "e2", "Judged", "Located")
        real = frames.make_frame(
            frame_type="epyc.vidya/frame/retraction/v1",
            assertion={"retracts": s1["frame_id"], "claim_id": "c"},
            provenance={"method": "operator", "about": s1["frame_id"]},
            actor="operator", authority_scope="research-verification", created_at=NOW)
        predicted = impact_of_retracting([s1, s2], [s1["frame_id"]], as_of=NOW)
        actual = fold([s1, s2, real], as_of=NOW).beliefs["c"]
        item = next(i for i in predicted.affected if i.claim_id == "c")
        assert item.after_pro == actual.pro and item.after_con == actual.con


class TestObligations:
    def _ob(self, **kw):
        base = dict(
            obligation_id="obl-1", title="Revise the section",
            activation={"belief_state_in": {"claim_id": "c", "states": ["Opposed", "Unknown"]}},
            satisfaction={"review_status": "accepted"},
            authority_frame="frm-approval",
        )
        base.update(kw)
        return Obligation(**base)

    def test_no_authority_frame_means_proposed_not_open(self):
        # An obligation that opens itself would be the fold granting work -- that is the intent
        # plane's job, and conflating them is how a system starts authorising itself.
        res = fold([_sup("c", "e", "Judged", "Located")], as_of=NOW)
        out = derive_obligations([self._ob(authority_frame=None)], res, floor=FLOOR)
        assert out[0].state == ObligationState.PROPOSED

    def test_activation_opens_an_authorized_obligation(self):
        res = fold([_sup("c", "e", "Judged", "Located")], as_of=NOW)   # Unknown at this floor
        out = derive_obligations([self._ob()], res, floor=FLOOR)
        assert out[0].state == ObligationState.OPEN
        assert "Unknown" in out[0].reasons[0]

    def test_satisfaction_beats_activation(self):
        res = fold([_sup("c", "e", "Judged", "Located")], as_of=NOW)
        out = derive_obligations([self._ob()], res, floor=FLOOR,
                                 context={"review_status": "accepted"})
        assert out[0].state == ObligationState.SATISFIED

    def test_a_satisfied_obligation_reopens_when_activation_fires_again(self):
        res = fold([_sup("c", "e", "Judged", "Located")], as_of=NOW)
        prior = self._ob(state=ObligationState.SATISFIED)
        out = derive_obligations([prior], res, floor=FLOOR)
        assert out[0].state == ObligationState.REOPENED

    def test_unmet_activation_leaves_state_untouched(self):
        res = fold([_sup("c", "e", "Verified", "Anchored")], as_of=NOW)   # Supported
        out = derive_obligations([self._ob()], res, floor=FLOOR)
        assert out[0].state == ObligationState.PROPOSED   # unchanged from input

    def test_unknown_predicate_is_refused(self):
        res = fold([], as_of=NOW)
        with pytest.raises(ValueError, match="unknown predicate"):
            derive_obligations([self._ob(activation={"belief_is_pretty": {"x": 1}})],
                               res, floor=FLOOR)

    def test_nesting_beyond_one_level_is_refused(self):
        # The cap is the feature: an obligation DSL grows until it needs its own semantics.
        res = fold([], as_of=NOW)
        nested = {"any": [{"all": [{"review_status": "accepted"}]}]}
        with pytest.raises(ValueError, match="nesting is capped"):
            derive_obligations([self._ob(activation=nested)], res, floor=FLOOR)

    def test_any_and_all_combinators_work_at_one_level(self):
        res = fold([_sup("c", "e", "Judged", "Located")], as_of=NOW)
        ob = self._ob(activation={"any": [
            {"belief_state_in": {"claim_id": "c", "states": ["Supported"]}},
            {"belief_state_in": {"claim_id": "c", "states": ["Unknown"]}},
        ]})
        assert derive_obligations([ob], res, floor=FLOOR)[0].state == ObligationState.OPEN

    def test_derivation_is_pure(self):
        res = fold([_sup("c", "e", "Judged", "Located")], as_of=NOW)
        original = self._ob()
        derive_obligations([original], res, floor=FLOOR)
        assert original.state == ObligationState.PROPOSED, "input must not be mutated"
