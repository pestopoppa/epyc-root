"""SC70 — a `claim_depends_on` edge REGISTERS its dependent claim.

The fold's `FT_DEPENDS` branch appended to `depends_edges` and never called `claims.add`, so a
claim the ledger has never otherwise seen — no claim frame, no support frame — silently had no
belief to alert on. The dependency-alert stratum computed its alerts keyed by that claim id, the
derivation loop only materialized beliefs for ids in `claims`, and the gate answered "no such
claim at this frontier" for exactly the claim the alert was about: a dangling edge that registers
nothing.

The two directions are pinned separately: a healthy dependency produces a belief too (the claim
now EXISTS, so a later withdrawal has somewhere to surface), and a broken one must land its alert
on that belief.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

from fold import fold  # noqa: E402
from frames import make_frame  # noqa: E402

AT = "2026-08-11T00:00:00Z"
G = {"Q": "Verified", "T": "Anchored"}


def _f(ftype, assertion, provenance):
    return make_frame(frame_type=ftype, assertion=assertion, provenance=provenance,
                      actor="test", authority_scope="test", created_at=AT)


def source(sid):
    return _f("epyc.vidya/frame/source_observed/v1",
              {"source_id": sid, "locator": f"https://example.com/{sid}", "title": sid},
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


def retract(frame):
    return _f("epyc.vidya/frame/retraction/v1",
              {"retracts": frame["frame_id"], "claim_id": frame["assertion"]["claim_id"]},
              {"about": frame["frame_id"], "method": "operator-retraction"})


def test_a_dependent_claim_seen_only_in_a_depends_on_edge_gets_a_belief():
    """CATCHES: the edge registering no claim. With the source healthy the dependent must still
    EXIST as a belief — a later withdrawal of the source needs somewhere to surface, and the
    discharge stratum keys its closures off these edges."""
    frames = [
        source("s_a"), claim("clm_a", "s_a"), support("clm_a", "s_a"),
        depends("clm_dep", "s_a", "entry-a"),
    ]
    res = fold(frames, as_of=AT)
    assert "clm_dep" in res.beliefs, "a depends_on edge must register its dependent claim"
    b = res.beliefs["clm_dep"]
    assert b.dependency_alerts == [] and not b.review_required


def test_a_withdrawn_source_alerts_through_the_registered_dependent():
    """THE PROPERTY. When the source a claim depends on loses all support, the alert must land on
    a belief — previously the dependent had no belief, so the alert was computed and invisible."""
    sup = support("clm_a", "s_a")
    frames = [
        source("s_a"), claim("clm_a", "s_a"), sup,
        depends("clm_dep", "s_a", "entry-a"),
        retract(sup),
    ]
    res = fold(frames, as_of=AT)
    assert "clm_dep" in res.beliefs
    b = res.beliefs["clm_dep"]
    assert b.dependency_alerts == ["entry-a"]
    assert b.review_required and not b.corrections


def test_a_withdrawn_source_holds_its_discharge_open_through_the_dependent():
    """The discharge stratum classified a never-registered dependent as discharged — the entry
    read as clear while the only claim it could have flagged did not exist."""
    sup = support("clm_a", "s_a")
    frames = [
        source("s_a"), claim("clm_a", "s_a"), sup,
        depends("clm_dep", "s_a", "entry-a"),
        retract(sup),
    ]
    res = fold(frames, as_of=AT)
    assert "entry-a" in res.undischarged
    assert "clm_dep" in res.undischarged["entry-a"]
    assert "entry-a" not in res.discharged
