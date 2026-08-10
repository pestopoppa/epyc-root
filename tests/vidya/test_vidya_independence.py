"""Support counted by source, not by evidence label (R4b / gate)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path("/workspace/scripts/vidya")))

from fold import fold
from frames import make_frame

AT = "2026-08-10T00:00:00Z"
G = {"Q": "Verified", "T": "Anchored"}


def src(sid, locator):
    return make_frame(
        frame_type="epyc.vidya/frame/source_observed/v1",
        assertion={"source_id": sid, "locator": locator, "title": sid},
        provenance={"about": sid, "method": "test"},
        actor="t", authority_scope="t", created_at=AT)


def claim(cid, sid):
    return make_frame(
        frame_type="epyc.vidya/frame/claim_proposed/v1",
        assertion={"claim_id": cid, "display_text": cid, "source_id": sid},
        provenance={"about": cid, "method": "test"},
        actor="t", authority_scope="t", created_at=AT)


def sup(cid, sid):
    return make_frame(
        frame_type="epyc.vidya/frame/evidence_supports_claim/v1",
        assertion={"claim_id": cid, "evidence_id": f"evd_{cid}", "grade": G, "source_id": sid},
        provenance={"evidence": f"evd_{cid}", "about": cid},
        actor="t", authority_scope="t", created_at=AT)


def alias(ids, independent):
    return make_frame(
        frame_type="epyc.vidya/frame/claim_alias/v1",
        assertion={"claim_ids": ids, "independent": independent},
        provenance={"about": ids[0], "method": "human-review/test"},
        actor="t", authority_scope="claim-identity", created_at=AT)


def base():
    """Two claims, two genuinely different sources."""
    return [
        src("s1", "https://arxiv.org/abs/1234.5678"),
        src("s2", "https://huggingface.co/datasets/x"),
        claim("clm_a", "s1"), sup("clm_a", "s1"),
        claim("clm_b", "s2"), sup("clm_b", "s2"),
    ]


def test_independent_alias_yields_two_supports():
    f = base() + [alias(["clm_a", "clm_b"], True)]
    b = fold(f, as_of=AT).beliefs["clm_a"]
    assert len(set(b.pro_sources)) == 2


def test_non_independent_alias_yields_one_support():
    f = base() + [alias(["clm_a", "clm_b"], False)]
    b = fold(f, as_of=AT).beliefs["clm_a"]
    assert len(set(b.pro_sources)) == 1, b.pro_sources


def test_same_locator_collapses_even_without_an_alias():
    """Two records of one paper are one witness, alias or no alias."""
    f = [
        src("s1", "https://arxiv.org/abs/1234.5678"),
        src("s2", "https://arxiv.org/pdf/1234.5678v2"),
        claim("clm_a", "s1"), sup("clm_a", "s1"),
        claim("clm_b", "s2"), sup("clm_b", "s2"),
        alias(["clm_a", "clm_b"], True),   # author wrongly said independent
    ]
    b = fold(f, as_of=AT).beliefs["clm_a"]
    assert len(set(b.pro_sources)) == 1, b.pro_sources
