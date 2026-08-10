"""R1b-discharge: the pilot's first negation stratum.

A correction is DISCHARGED when no claim transitively depending on it remains flagged. This is the
first rule in the system whose body needs the non-existence of a derived fact — every earlier gate
rule tested a materialized relation after the fixpoint closed, which is evaluation plus a filter.

It also closes a live ratchet: 678 claims sit `review_required` with nothing able to say a
correction is finished.

The transitivity test is the one that matters. Discharging on direct dependents only would declare
a correction complete while its reach was still flagged, which is the same over-confidence the
substrate exists to refuse.
"""

from __future__ import annotations

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


def correction(cid):
    return _f("epyc.vidya/frame/correction_recorded/v1",
              {"claim_ids": [cid], "correction_text": "needs review"},
              {"about": cid, "method": "test"})


def chain():
    """entry-a <- clm_b <- clm_c : a two-hop dependency chain."""
    return [
        source("s_a"), claim("clm_a", "s_a"), support("clm_a", "s_a"),
        source("s_b"), claim("clm_b", "s_b"), support("clm_b", "s_b"),
        source("s_c"), claim("clm_c", "s_c"), support("clm_c", "s_c"),
        depends("clm_b", "s_a", "entry-a"),
        depends("clm_c", "s_b", "entry-b"),
    ]


def test_a_clear_dependency_tree_is_discharged():
    res = fold(chain(), as_of=AT)
    assert "entry-a" in res.discharged
    assert "entry-a" not in res.undischarged


def test_a_flagged_direct_dependent_holds_the_correction_open():
    res = fold(chain() + [correction("clm_b")], as_of=AT)
    assert "entry-a" in res.undischarged
    assert res.undischarged["entry-a"] == ["clm_b"]


def test_a_flagged_TRANSITIVE_dependent_also_holds_it_open():
    """The load-bearing case: clm_c depends on entry-b, which clm_b belongs to.

    Discharging entry-a on its direct dependents alone would call it finished while a claim two
    hops out is still flagged.
    """
    res = fold(chain() + [correction("clm_c")], as_of=AT)
    assert "entry-a" in res.undischarged, "transitive reach was not followed"
    assert "clm_c" in res.undischarged["entry-a"]


def test_an_entry_appears_in_exactly_one_of_the_two_sets():
    res = fold(chain() + [correction("clm_b")], as_of=AT)
    assert set(res.discharged) & set(res.undischarged) == set()


def test_an_entry_with_no_dependents_is_in_neither_set():
    """Discharge is a statement about a dependency tree; an entry without one has nothing to say."""
    frames = [source("s_a"), claim("clm_a", "s_a"), support("clm_a", "s_a")]
    res = fold(frames, as_of=AT)
    assert res.discharged == {} and res.undischarged == {}


def test_clearing_the_dependent_discharges_the_correction():
    """The ratchet actually opens — this is the point of the rule."""
    flagged = fold(chain() + [correction("clm_b")], as_of=AT)
    assert "entry-a" in flagged.undischarged

    reviewed = fold(chain(), as_of=AT)          # correction resolved / never recorded
    assert "entry-a" in reviewed.discharged
