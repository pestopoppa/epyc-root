"""`depends_on` — the explicit evidential edge (schema 2026-08-10).

A citation is not a dependency: 18% of citation edges from dived entries were evidential when
measured over 60 of them, so only the hand-authored edge reaches the ledger. These tests pin that
separation — a cross_reference must produce no dependency frame, and a depends_on must.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

from adapters.research_intake import _depends_frames  # noqa: E402

AT = "2026-08-10T00:00:00Z"
FT = "epyc.vidya/frame/claim_depends_on/v1"


def test_cross_reference_alone_creates_no_dependency():
    entry = {
        "id": "intake-100",
        "key_claims": ["a", "b"],
        "cross_references": {"intake_entries": ["intake-200"]},
    }
    assert _depends_frames(entry, AT) == []


def test_claim_index_scopes_the_dependency_to_one_claim():
    entry = {
        "id": "intake-100",
        "key_claims": ["a", "b", "c"],
        "depends_on": [{"entry": "intake-200", "claim_index": 1, "why": "rests on their Thm 4"}],
    }
    frames = _depends_frames(entry, AT)
    assert len(frames) == 1
    a = frames[0]["assertion"]
    assert frames[0]["frame_type"] == FT
    assert a["claim_id"] == "clm_intake_100_01"
    assert a["depends_on_entry"] == "intake-200"
    assert a["rationale"] == "rests on their Thm 4"


def test_omitting_claim_index_applies_to_every_claim():
    entry = {
        "id": "intake-100",
        "key_claims": ["a", "b"],
        "depends_on": [{"entry": "intake-200", "why": "the whole entry restates their result"}],
    }
    assert len(_depends_frames(entry, AT)) == 2


def test_a_dependency_without_a_reason_is_dropped():
    """An unexplained dependency cannot be reviewed, so it does not reach the ledger."""
    entry = {
        "id": "intake-100",
        "key_claims": ["a"],
        "depends_on": [{"entry": "intake-200"}, {"entry": "intake-300", "why": "  "}],
    }
    assert _depends_frames(entry, AT) == []


def test_dependency_frames_are_human_authored_in_provenance():
    entry = {
        "id": "intake-100",
        "key_claims": ["a"],
        "depends_on": [{"entry": "intake-200", "why": "x"}],
    }
    assert _depends_frames(entry, AT)[0]["provenance"]["authored_by"] == "human"
