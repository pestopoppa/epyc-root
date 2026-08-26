"""PR2 — the live-ledger evaluation, and the property that makes it honest.

The thing worth testing is not the score. It is that claims the corpus *cannot* speak to are
counted as uncoverable instead of being scored as correct. A suite that scored them would report
a higher number for a worse reason, and nothing about the output would look wrong.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

from frames import make_frame  # noqa: E402
from live_eval import draw_families, run_live  # noqa: E402

AS_OF = "2026-08-10T00:00:00Z"


def _entry_frames(entry_id: str, n_claims: int, grade: dict) -> list[dict]:
    key = "clm_" + entry_id.replace("-", "_")
    src = "src_" + entry_id.replace("-", "_")
    out = []
    for i in range(n_claims):
        cid = f"{key}_{i:02d}"
        out.append(
            make_frame(
                frame_type="epyc.vidya/frame/claim_proposed/v1",
                assertion={"claim_id": cid, "display_text": f"claim {i} of {entry_id}",
                           "source_id": src},
                provenance={"method": "test", "about": cid},
                actor="test", authority_scope="test", created_at=AS_OF,
            )
        )
        out.append(
            make_frame(
                frame_type="epyc.vidya/frame/evidence_supports_claim/v1",
                assertion={"claim_id": cid, "evidence_id": f"evd_{cid}", "grade": grade,
                           "source_id": src},
                provenance={"evidence": f"evd_{cid}", "about": cid},
                actor="test", authority_scope="test", created_at=AS_OF,
            )
        )
    return out


VERIFIED = {"Q": "Verified", "T": "Anchored"}


def _corpus():
    frames = _entry_frames("intake-001", 2, VERIFIED) + _entry_frames("intake-002", 2, VERIFIED)
    index = [
        {"id": "intake-001", "verification": "dive-verified"},
        {"id": "intake-002", "verification": "dive-verified",
         "cross_references": {"intake_entries": ["intake-001"]}},
    ]
    return frames, index


def test_citing_claims_are_uncoverable_not_scored():
    """intake-002 cites intake-001, so its claims are counted and excluded from the score."""
    frames, index = _corpus()
    res = run_live(frames, index, as_of=AS_OF, count=1)
    assert res["uncoverable_claims"] == 2
    scored = {row["claim_id"] for fam in res["families"] for row in fam["rows"]}
    assert not any(c.startswith("clm_intake_002") for c in scored)


def test_source_retraction_moves_every_claim_of_that_source():
    frames, index = _corpus()
    res = run_live(frames, index, as_of=AS_OF, count=1)
    fam = res["families"][0]
    assert fam["family"] == "intake-001"
    assert fam["invalidation_recall"] == 1.0


def test_unverified_entries_must_not_clear_the_floor():
    frames = _entry_frames("intake-003", 2, {"Q": "Hinted", "T": "Located"})
    index = [{"id": "intake-003", "verification": "stage1-unverified"}]
    res = run_live(frames, index, as_of=AS_OF, count=1)
    rows = res["families"][0]["rows"]
    never = [r for r in rows if r["expected"] == "never_believed"]
    assert len(never) == 2 and all(r["correct"] for r in never)


def test_draw_is_deterministic_and_prefers_cited_entries():
    frames, index = _corpus()
    a = [f["family_id"] for f in draw_families(frames, index, count=2)]
    b = [f["family_id"] for f in draw_families(frames, index, count=2)]
    assert a == b
    assert a[0] == "intake-001", "the cited entry must be drawn first"


def _oppose_frame(entry_id: str, cid: str, grade: dict) -> dict:
    src = "src_" + entry_id.replace("-", "_")
    return make_frame(
        frame_type="epyc.vidya/frame/evidence_opposes_claim/v1",
        assertion={"claim_id": cid, "evidence_id": f"evd_{cid}", "grade": grade,
                   "source_id": src},
        provenance={"evidence": f"evd_{cid}", "about": cid},
        actor="test", authority_scope="test", created_at=AS_OF,
    )


def _depends_frame(cid: str, target_entry: str, target_src: str) -> dict:
    return make_frame(
        frame_type="epyc.vidya/frame/claim_depends_on/v1",
        assertion={"claim_id": cid, "depends_on_source": target_src,
                   "depends_on_entry": target_entry, "rationale": "test"},
        provenance={"about": cid, "method": "test", "authored_by": "human"},
        actor="test", authority_scope="test", created_at=AS_OF,
    )


def test_con_only_claims_move_when_their_oppose_evidence_is_retracted():
    """A claim whose ONLY evidence is an oppose frame must still move when its source is retracted.

    Regression for the 2026-08-26 gate run 2 harmfuls (clm_intake_1107_02, clm_intake_363_03,
    clm_intake_363_04): the source index covered support frames only, so the mutation retracted
    nothing on a con-only claim and it could never move.
    """
    frames = _entry_frames("intake-010", 1, VERIFIED)
    con_only = "clm_intake_010_01"
    frames += [
        make_frame(
            frame_type="epyc.vidya/frame/claim_proposed/v1",
            assertion={"claim_id": con_only, "display_text": "con-only claim",
                       "source_id": "src_intake_010"},
            provenance={"method": "test", "about": con_only},
            actor="test", authority_scope="test", created_at=AS_OF,
        ),
        _oppose_frame("intake-010", con_only, VERIFIED),
    ]
    index = [{"id": "intake-010", "verification": "dive-verified"}]
    res = run_live(frames, index, as_of=AS_OF, count=1)
    fam = res["families"][0]
    assert {r["claim_id"] for r in fam["rows"]} == {"clm_intake_010_00", con_only}
    assert all(r["correct"] for r in fam["rows"]), fam["rows"]
    assert fam["invalidation_recall"] == 1.0
    assert res["harmful_outcomes"] == 0


def test_dependents_on_a_never_supported_source_are_carved_out_not_failed():
    """OP-11 carve-out: an alert already active pre-mutation is not a propagation failure.

    A dive-overturned source has no support to lose, so retracting it cannot newly alert its
    dependents -- the engine behaved correctly and the "MUST move" expectation was unsatisfiable.
    Such dependents are counted as pre_alerted_dependents, never scored.
    """
    a_src = "src_intake_020"
    a_claim = "clm_intake_020_00"
    frames = [
        make_frame(
            frame_type="epyc.vidya/frame/claim_proposed/v1",
            assertion={"claim_id": a_claim, "display_text": "overturned claim", "source_id": a_src},
            provenance={"method": "test", "about": a_claim},
            actor="test", authority_scope="test", created_at=AS_OF,
        ),
        _oppose_frame("intake-020", a_claim, VERIFIED),
    ]
    b_claims = _entry_frames("intake-021", 2, VERIFIED)
    frames += b_claims
    frames += [_depends_frame(c, "intake-020", a_src) for c in
               (f["assertion"]["claim_id"] for f in b_claims
                if f["frame_type"].endswith("claim_proposed/v1"))]
    index = [
        {"id": "intake-020", "verification": "dive-overturned"},
        {"id": "intake-021", "verification": "dive-verified",
         "cross_references": {"intake_entries": ["intake-020"]}},
    ]
    res = run_live(frames, index, as_of=AS_OF, count=1)
    fam = res["families"][0]
    assert fam["family"] == "intake-020", "the overturned source must be drawn"
    assert fam["pre_alerted_dependents"] == 2
    assert not any(r["expected"] == "propagated" for r in fam["rows"])
    assert {r["claim_id"] for r in fam["rows"]} == {a_claim}, "dependents are counted, not scored"
    assert res["harmful_outcomes"] == 0
    assert fam["invalidation_recall"] == 1.0, "the source's own claims must still move"


def test_dependents_on_a_supported_source_still_must_move():
    """The carve-out is narrow: a genuinely supported source's dependents are still required to move."""
    frames, index = _corpus()
    dependent = "clm_intake_002_00"
    frames.append(_depends_frame(dependent, "intake-001", "src_intake_001"))
    res = run_live(frames, index, as_of=AS_OF, count=1)
    fam = res["families"][0]
    assert fam["pre_alerted_dependents"] == 0
    prop = [r for r in fam["rows"] if r["expected"] == "propagated"]
    assert [r["claim_id"] for r in prop] == [dependent]
    assert prop[0]["correct"] is True, "a supported source's retraction must propagate"
    assert res["harmful_outcomes"] == 0
