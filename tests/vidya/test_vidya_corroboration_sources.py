"""SC72 — corroboration is counted by SOURCE, and a digest-shaped string is not a digest.

Two layers of the same defect, filed together because a fix at one alone leaves the other
reachable:

* **gate/fold**: a support path whose source is unrecorded must not mint its own pseudo-source.
  The fold keyed source-less support frames by their evidence LABEL, so two paths from one
  unidentified source read as two independent witnesses; the gate's `pro_sources or [labels]`
  fallback did the same one layer down for beliefs built without source accounting. The comment
  above the gate code names this exact failure ("two index records of one paper produce two labels
  and would report as independent support") and then the fallback performed it.
* **frames**: the `subjects` digest slot validated that a digest mapping was PRESENT, never that
  it was well-formed — `{"sha256": "aa"}` passed the envelope and was silently dropped by the fold
  as unparsable, one layer below where SC69 bites.
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))

import frames  # noqa: E402
import lattice as lat  # noqa: E402
from fold import Belief, FoldResult, fold  # noqa: E402
from gate import Outcome, UsePolicy, evaluate  # noqa: E402

NOW = "2026-09-07T00:00:00Z"
G = {"Q": "Verified", "T": "Anchored"}


def _f(ftype, assertion, provenance, **kw):
    return frames.make_frame(frame_type=ftype, assertion=assertion, provenance=provenance,
                             actor="test", authority_scope="test", created_at=NOW, **kw)


def source(sid, locator):
    return _f("epyc.vidya/frame/source_observed/v1",
              {"source_id": sid, "locator": locator, "title": sid},
              {"about": sid, "method": "test"})


def claim(cid, sid=None):
    a = {"claim_id": cid, "display_text": cid}
    if sid is not None:
        a["source_id"] = sid
    return _f("epyc.vidya/frame/claim_proposed/v1", a, {"about": cid, "method": "test"})


def sup(cid, sid=None, evidence=None):
    a = {"claim_id": cid, "evidence_id": evidence or f"evd_{cid}", "grade": G}
    if sid is not None:
        a["source_id"] = sid
    return _f("epyc.vidya/frame/evidence_supports_claim/v1", a,
              {"evidence": evidence or f"evd_{cid}", "about": cid})


def _policy(**kw):
    kw.setdefault("use", "wiki-authoritative")
    kw.setdefault("floor", lat.parse_grade("Verified/Anchored"))
    return UsePolicy(**kw)


# --- the fold: source-less paths collapse to ONE unnamed source ------------------------------

def test_two_paths_that_name_no_source_are_one_source_not_two():
    """CATCHES: the fold minting a distinct pseudo-source per evidence label, so one unidentified
    source's two records read as two independent witnesses."""
    res = fold([claim("c"), sup("c", evidence="e1"), sup("c", evidence="e2")], as_of=NOW)
    b = res.beliefs["c"]
    assert len(set(b.pro_sources)) == 1, b.pro_sources
    assert len(b.pro_paths) == 2, "paths are still two; only the SOURCE count collapses"


def test_two_source_less_paths_do_not_satisfy_a_two_source_policy():
    """THE PROPERTY at the gate: min_disjoint_supports=2 must not be satisfiable by one
    unidentified source wearing two evidence labels."""
    res = fold([claim("c"), sup("c", evidence="e1"), sup("c", evidence="e2")], as_of=NOW)
    out = evaluate("c", res, _policy(min_disjoint_supports=2))
    assert out.outcome == Outcome.ABSTAIN


def test_two_genuine_sources_still_satisfy_a_two_source_policy():
    """MUTATION for the two above: real, locator-normalized sources must still count."""
    res = fold([
        source("s1", "https://arxiv.org/abs/1234.5678"),
        source("s2", "https://huggingface.co/datasets/x"),
        claim("c", "s1"), sup("c", "s1", evidence="e1"),
        claim("c", "s2"), sup("c", "s2", evidence="e2"),
    ], as_of=NOW)
    assert len(set(res.beliefs["c"].pro_sources)) == 2
    out = evaluate("c", res, _policy(min_disjoint_supports=2))
    assert out.outcome == Outcome.ALLOW


def test_a_single_source_less_path_still_counts_as_one_witness():
    """The floor is one witness, not zero: a path exists, so at least one source stands behind
    it — but no more than one can be claimed from an unrecorded identity."""
    res = fold([claim("c"), sup("c", evidence="e1")], as_of=NOW)
    out = evaluate("c", res, _policy(min_disjoint_supports=1))
    assert out.outcome == Outcome.ALLOW


# --- the gate: no label-counting fallback for source-less beliefs ----------------------------

def test_the_gate_does_not_count_labels_as_sources_on_an_unaccounted_belief():
    """CATCHES the `pro_sources or [labels]` fallback: a belief carrying paths but no source
    accounting reported each path as an independent source — the manufacture the fold-side fix
    cannot reach, because the belief was never folded."""
    paths = [("e1", lat.parse_grade("Verified/Anchored")),
             ("e2", lat.parse_grade("Verified/Anchored"))]
    res = FoldResult(beliefs={"c": Belief(claim_id="c", pro=paths[0][1], pro_paths=paths)},
                     iterations=1, frontier=2, as_of=NOW, ignored_frame_types={})
    out = evaluate("c", res, _policy(min_disjoint_supports=2))
    assert out.outcome == Outcome.ABSTAIN


def test_an_unaccounted_single_path_still_counts_as_one_witness():
    """MUTATION for the test above: the fallback must not collapse to zero -- a path that exists
    is at least one witness, only its independence from others is unclaimable."""
    g = lat.parse_grade("Verified/Anchored")
    res = FoldResult(beliefs={"c": Belief(claim_id="c", pro=g, pro_paths=[("e1", g)])},
                     iterations=1, frontier=1, as_of=NOW, ignored_frame_types={})
    out = evaluate("c", res, _policy(min_disjoint_supports=1))
    assert out.outcome == Outcome.ALLOW


# --- frames: the subjects digest must be well-formed, not merely present ----------------------

def test_a_subject_digest_of_a_two_hex_stub_is_refused():
    """CATCHES the exact hole: `{"sha256": "aa"}` satisfied the presence check and was silently
    dropped by the fold's digest parser — a digest-shaped string that is not a digest, one layer
    below where SC69 bites."""
    with pytest.raises(frames.FrameValidationError, match="sha256"):
        _f("epyc.vidya/frame/source_observed/v1",
           {"source_id": "s", "locator": "doc.md", "source_kind": "wiki"},
           {"method": "artifact-scan", "about": "doc.md"},
           subjects=[{"name": "doc.md", "digest": {"sha256": "aa"}}])


@pytest.mark.parametrize("bad", [
    {"sha256": "not-hex"},
    {"sha256": "a" * 63},
    {"sha256": ""},
    {"md5": "a" * 32},
    {"sha256": "a" * 64, "md5": "b" * 32},
])
def test_every_malformed_subject_digest_is_refused(bad):
    with pytest.raises(frames.FrameValidationError, match="sha256"):
        _f("epyc.vidya/frame/source_observed/v1",
           {"source_id": "s", "locator": "doc.md", "source_kind": "wiki"},
           {"method": "artifact-scan", "about": "doc.md"},
           subjects=[{"name": "doc.md", "digest": bad}])


def test_a_well_formed_subject_digest_is_accepted():
    """MUTATION for the refusals: the envelope must keep accepting what the fold can parse."""
    f = _f("epyc.vidya/frame/source_observed/v1",
           {"source_id": "s", "locator": "doc.md", "source_kind": "wiki"},
           {"method": "artifact-scan", "about": "doc.md"},
           subjects=[{"name": "doc.md", "digest": {"sha256": "a" * 64}}])
    assert f["subjects"][0]["digest"]["sha256"] == "a" * 64


def test_uppercase_hex_is_accepted_like_the_fold_accepts_it():
    """The fold's digest parser normalizes case on read, so the envelope refuses nothing the fold
    would have parsed -- the two layers must agree on one set."""
    _f("epyc.vidya/frame/source_observed/v1",
       {"source_id": "s", "locator": "doc.md", "source_kind": "wiki"},
       {"method": "artifact-scan", "about": "doc.md"},
       subjects=[{"name": "doc.md", "digest": {"sha256": "A" * 64}}])


def test_a_subject_without_a_name_is_refused():
    """CATCHES the presence-only twin: a digest with no name is pinned but anonymous, and a move
    in an anonymous artifact is undetectable (SC58's rule for read_set, applied to subjects)."""
    with pytest.raises(frames.FrameValidationError, match="name"):
        _f("epyc.vidya/frame/source_observed/v1",
           {"source_id": "s", "locator": "doc.md", "source_kind": "wiki"},
           {"method": "artifact-scan", "about": "doc.md"},
           subjects=[{"name": "", "digest": {"sha256": "a" * 64}}])
