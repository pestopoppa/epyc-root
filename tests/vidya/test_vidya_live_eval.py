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
