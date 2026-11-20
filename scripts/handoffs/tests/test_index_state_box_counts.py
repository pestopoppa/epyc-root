"""C1: .index-state.json / generated rows carry needs_owner + proposals_pending; --check warns on stale proposals."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import index_state as I  # noqa: E402

BDOC = {"boxes": {
    "A-1.p1": {"file": "handoffs/active/a.md", "state": "needs-owner", "proposed_by": "taskflow 2026-11-01T10:00Z"},
    "A-2": {"file": "handoffs/active/a.md", "state": "needs-owner", "proposed_by": None},
    "B-1": {"file": "handoffs/active/b.md", "state": "open"}}}


def test_annotate_counts():
    st = {"handoffs": {"a.md": {}, "b.md": {}}}
    I.annotate_box_counts(st, BDOC)
    assert st["handoffs"]["a.md"] == {"needs_owner": 2, "proposals_pending": 1} and st["handoffs"]["b.md"] == {}


def test_generated_cell_note():
    assert I._owner_note(list(BDOC["boxes"].values())) == " · needs-owner 2 (1 proposals)"
    assert I._owner_note([{"state": "open"}]) == ""


def test_stale_proposal_warning():
    w = I.stale_proposals(BDOC, today="2026-11-20")
    assert len(w) == 1 and "a.md" in w[0] and "older than 14 days" in w[0]
    assert I.stale_proposals(BDOC, today="2026-11-10") == []
