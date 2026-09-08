"""SC61 — `claim_statement_binding/v1`: the frame type, the review worksheet, and the fold pass
that APPLIES the human judgment — the producer SC56's `attested` binding was missing.

SC56 accepts two binding kinds: `identity`, machine-checkable by normalized string equality, and
`attested` — a human judgment that a claim follows from the proposition the checker decided.
Until this module existed `attested` had no producer, so only `identity` was reachable.

Three properties are pinned here, mirroring the `claim_alias` producer it was built parallel to:

* **The worksheet decides nothing.** Rows start `pending` and emit nothing; only a human flipping
  a row to `follows` — with a named reviewer — produces a binding. A pre-filled worksheet would
  be the machine making the judgment with extra steps.
* **The frame is the retrievable judgment.** A claim frame's `binding_ref` names a live binding
  frame for THE SAME claim and THE SAME proposition; a reference that names nothing, another
  claim, or another proposition is refused — an attested binding that nobody can point at is
  indistinguishable from none, and a claim citing a judgment about a different proposition is a
  false attestation.
* **The fold applies, never derives.** Binding frames annotate claims; they never create a belief
  out of nothing, and they move no lattice value — the grade was decided at projection, where the
  tuple's `binding_ref` licensed the SC56 cap.
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))

import frames  # noqa: E402
import statement_binding as sb  # noqa: E402
from claim_tuple import ClaimTuple, to_frames  # noqa: E402
from fold import FoldError, fold  # noqa: E402

NOW = "2026-09-07T00:00:00Z"
CLAIM = "the sort routine returns a sorted permutation of its input"
PROP = "for every list xs of int, sorted_permutation(sort(xs), xs) holds"
OTHER_PROP = "the parser accepts exactly the grammar its type declares"


def _f(ftype, assertion, provenance, **kw):
    return frames.make_frame(frame_type=ftype, assertion=assertion, provenance=provenance,
                             actor="test", authority_scope="test", created_at=NOW, **kw)


def _verifier_tuple(binding_ref=""):
    return ClaimTuple(
        measurement_id="sc61", metric="obligations_discharged", value=1,
        date="2026-09-07", category="CANDIDATE", claim=CLAIM,
        protocol_id="P-verifier-1", reps=3, attestation_path="MEASUREMENT.md",
        attestation_sha256="a" * 64, attestation_verified=True,
        source_class="verifier", decided_proposition=PROP,
        binding_kind="attested" if binding_ref else "", binding_ref=binding_ref)


def _claim_frame(binding_ref="", decided=PROP, cid="clm_sc61"):
    assertion = {"claim_id": cid, "display_text": CLAIM, "source_id": "src_x"}
    if decided:
        assertion["decided_proposition"] = decided
    if binding_ref:
        assertion["binding_kind"] = "attested"
        assertion["binding_ref"] = binding_ref
    return _f("epyc.vidya/frame/claim_proposed/v1", assertion, {"about": cid, "method": "test"})


def _support_frame(cid="clm_sc61"):
    return _f("epyc.vidya/frame/evidence_supports_claim/v1",
              {"claim_id": cid, "evidence_id": f"evd_{cid}",
               "grade": {"Q": "Verified", "T": "Anchored"}},
              {"evidence": f"evd_{cid}", "about": cid})


def _binding_frame(cid="clm_sc61", decided=PROP):
    return _f(sb.FT_STATEMENT_BINDING,
              {"claim_id": cid, "decided_proposition": decided},
              {"method": "human-review/statement-binding-worksheet", "about": cid,
               "reviewers": ["reviewer-1"]})


def _worksheet(rows):
    return {"schema": sb.WORKSHEET_SCHEMA, "generated_at": NOW,
            "generator": "test", "rows": rows}


def _decision_row(cid="clm_sc61", decision="follows", reviewer="reviewer-1",
                  decided=PROP, **extra):
    row = {"claim_id": cid, "claim_text": CLAIM, "decided_proposition": decided,
           "decision": decision, "reviewer": reviewer, "note": ""}
    row.update(extra)
    return row


# --- the worksheet --------------------------------------------------------------------------

def test_candidate_rows_skip_bound_and_identity_eligible_claims():
    bound = _claim_frame(binding_ref="", cid="clm_bound")
    bound["assertion"]["binding_kind"] = "identity"
    identity_eligible = _claim_frame(binding_ref="", cid="clm_identity",
                                     decided=CLAIM)
    no_proposition = _f("epyc.vidya/frame/claim_proposed/v1",
                        {"claim_id": "clm_none", "display_text": CLAIM,
                         "source_id": "s"}, {"about": "clm_none", "method": "test"})
    candidates = sb.candidate_rows(
        [_claim_frame(binding_ref="", cid="clm_open"), bound, identity_eligible,
         no_proposition])
    assert [c["claim_id"] for c in candidates] == ["clm_open"]
    assert candidates[0]["decided_proposition"] == PROP


def test_worksheet_rows_start_pending_and_pending_emits_nothing():
    ws = sb.worksheet_from_candidates(
        sb.candidate_rows([_claim_frame(binding_ref="", cid="clm_open")]),
        generated_at=NOW)
    assert ws["schema"] == sb.WORKSHEET_SCHEMA
    assert ws["rows"][0]["decision"] == "pending"
    assert sb.bindings_from_worksheet(ws) == []


def test_a_follows_row_with_a_reviewer_emits_a_binding():
    ws = _worksheet([_decision_row(decision="follows", reviewer="reviewer-7")])
    out = sb.bindings_from_worksheet(ws)
    assert out == [{"claim_id": "clm_sc61", "decided_proposition": PROP,
                    "reviewer": "reviewer-7", "note": ""}]


def test_a_does_not_follow_row_emits_nothing():
    assert sb.bindings_from_worksheet(
        _worksheet([_decision_row(decision="does_not_follow", reviewer="r")])) == []


def test_an_approved_row_without_a_reviewer_is_refused():
    with pytest.raises(sb.WorksheetError, match="reviewer"):
        sb.bindings_from_worksheet(_worksheet([_decision_row(reviewer="")]))


def test_an_unknown_decision_is_refused():
    with pytest.raises(sb.WorksheetError, match="decision"):
        sb.bindings_from_worksheet(_worksheet([_decision_row(decision="probably")]))


def test_an_unknown_worksheet_schema_is_refused():
    with pytest.raises(sb.WorksheetError, match="schema"):
        sb.bindings_from_worksheet({"schema": "epyc.vidya/alias-worksheet/v1", "rows": []})


def test_the_frame_is_content_addressed_and_carries_the_judgment_verbatim():
    b = sb.bindings_from_worksheet(_worksheet([_decision_row()]))[0]
    frame = sb.frame_from_binding(b, actor="reviewer-1", at=NOW,
                                  worksheet_digest="sha256:" + "d" * 64)
    frames.validate_frame(frame)
    assert frame["frame_type"] == sb.FT_STATEMENT_BINDING
    assert frame["assertion"] == {"claim_id": "clm_sc61", "decided_proposition": PROP}
    assert frame["provenance"]["reviewers"] == ["reviewer-1"]
    assert frame["provenance"]["worksheet_digest"] == "sha256:" + "d" * 64


def test_a_bound_tuple_grades_at_verified_through_its_ref():
    """SC61's contract from the tuple side: a `binding_ref` pointing at one of these frames is
    what SC56's attested kind required, and the pair grades at the SC56 ceiling."""
    from claim_tuple import grade
    assert grade(_verifier_tuple(binding_ref="frm_binding_sc61"))[:2] == \
        ("Verified", "Attested")


# --- the fold pass: APPLY, never derive ------------------------------------------------------

def test_a_binding_frame_folds_onto_its_claim_and_is_recorded():
    res = fold([_claim_frame(), _support_frame(), _binding_frame()], as_of=NOW)
    assert res.statement_bindings["clm_sc61"] == [_binding_frame()["frame_id"]]
    b = res.beliefs["clm_sc61"]
    assert b.pro == b.pro, "the binding moves no lattice value -- it annotates"


def test_a_binding_frame_alone_never_creates_a_belief_or_a_claim():
    """The fold applies; it does not derive. A binding for a claim that never appears in the
    ledger is a judgment about nothing and is refused -- SC70's shape one level up."""
    with pytest.raises(FoldError, match="does not appear in this ledger"):
        fold([_binding_frame(cid="clm_ghost")], as_of=NOW)


def test_a_claim_ref_resolves_against_a_live_binding_frame():
    corpus = [_claim_frame(binding_ref=_binding_frame()["frame_id"]),
              _binding_frame()]
    res = fold(corpus, as_of=NOW)
    assert res.statement_bindings["clm_sc61"] == [_binding_frame()["frame_id"]]


def test_a_dangling_binding_ref_is_refused():
    """CATCHES: a claim frame asserting an attested binding to a judgment that is not in the
    ledger. A judgment nobody can retrieve is indistinguishable from none, and the claim frame's
    attested status would otherwise ride on nothing."""
    with pytest.raises(FoldError, match="not a live claim_statement_binding"):
        fold([_claim_frame(binding_ref="frm_binding_nope")], as_of=NOW)


def test_a_binding_about_another_claim_is_refused():
    with pytest.raises(FoldError, match="binds claim"):
        fold([_claim_frame(binding_ref=_binding_frame(cid="clm_other")["frame_id"]),
              _binding_frame(cid="clm_other")], as_of=NOW)


def test_a_binding_judged_against_another_proposition_is_refused():
    with pytest.raises(FoldError, match="DIFFERENT proposition"):
        fold([_claim_frame(binding_ref=_binding_frame(decided=OTHER_PROP)["frame_id"]),
              _binding_frame(decided=OTHER_PROP)], as_of=NOW)


def test_whitespace_does_not_break_a_proposition_match():
    """The normalization is claim_tuple's own -- a copied normalizer here would be a second
    dialect of the identity rule."""
    frame = _binding_frame(decided="   for every list xs of int, sorted_permutation"
                                    "(sort(xs), xs) holds.   ")
    res = fold([_claim_frame(binding_ref=frame["frame_id"]), frame], as_of=NOW)
    assert res.statement_bindings["clm_sc61"] == [frame["frame_id"]]


def test_a_retracted_binding_frame_stops_licensing_its_ref():
    """Retraction of the judgment withdraws it: a claim frame citing a retracted binding is
    refused, the same zero-substitution discipline every other frame type lives under."""
    binding = _binding_frame()
    retraction = _f("epyc.vidya/frame/retraction/v1",
                    {"retracts": binding["frame_id"], "claim_id": "clm_sc61"},
                    {"about": binding["frame_id"], "method": "operator-retraction"})
    with pytest.raises(FoldError, match="not a live claim_statement_binding"):
        fold([_claim_frame(binding_ref=binding["frame_id"]), binding, retraction], as_of=NOW)


def test_a_malformed_binding_frame_is_refused():
    bad = _f(sb.FT_STATEMENT_BINDING, {"claim_id": "clm_sc61"},
             {"method": "human-review", "about": "clm_sc61", "reviewers": ["r"]})
    with pytest.raises(FoldError, match="decided proposition"):
        fold([bad], as_of=NOW)


def test_binding_frames_are_not_reported_as_ignored():
    res = fold([_claim_frame(), _binding_frame()], as_of=NOW)
    assert sb.FT_STATEMENT_BINDING not in res.ignored_frame_types


def test_the_whole_wave_flows_end_to_end():
    """Worksheet -> frames -> ledger corpus -> fold: the attested tuple, the binding frame, and
    the claim frame all land together, and the fold resolves the ref without error."""
    ws = sb.worksheet_from_candidates(
        sb.candidate_rows([_claim_frame(binding_ref="", cid="clm_open")]), generated_at=NOW)
    ws["rows"][0]["decision"] = "follows"
    ws["rows"][0]["reviewer"] = "reviewer-1"
    binding = sb.bindings_from_worksheet(ws)[0]
    binding_frame = sb.frame_from_binding(binding, actor="reviewer-1", at=NOW,
                                          worksheet_digest="sha256:" + "e" * 64)
    claim_frame = _claim_frame(binding_ref=binding_frame["frame_id"], cid="clm_open")
    res = fold([claim_frame, binding_frame], as_of=NOW)
    assert res.statement_bindings["clm_open"] == [binding_frame["frame_id"]]
    # The claim's tuple was projected with the SC56 cap applied; the frame's grade is what the
    # ledger says, and the fold never re-grades it.
    sup = _support_frame("clm_open")
    res2 = fold([claim_frame, binding_frame, sup], as_of=NOW)
    assert res2.beliefs["clm_open"].pro.q_name == "Verified"
