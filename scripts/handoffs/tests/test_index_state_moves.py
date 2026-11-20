"""C4 gap 3 (index side): generated rows follow .moves.jsonl after a split; --check warns on a hand row naming a file
whose track moved."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import index_state as I  # noqa: E402


def _setup(tmp_path, monkeypatch, src_exists=True, dest_owned=False):
    act = tmp_path / "handoffs" / "active"
    act.mkdir(parents=True)
    if src_exists:
        (act / "big.md").write_text("# Big\n")
    (act / "big-moved.md").write_text("# Moved\n")
    (act / ".moves.jsonl").write_text(
        json.dumps({"box_id": "M-1", "text_sha": "s1", "from": "big.md", "to": "big-moved.md", "at": "2026-11-20"}) + "\n"
        + "not json\n")
    monkeypatch.setattr(I, "ACTIVE", act)
    monkeypatch.setattr(I, "MOVES", act / ".moves.jsonl")
    idx = I.DOMAIN_INDICES[0]
    state = {"rows": {"RTG-7": {"index": idx, "line": 9, "handoff": "big.md", "deps": []}},
             "handoffs": {"big.md": {"owner_index": idx, "open": 1},
                          "big-moved.md": {"owner_index": idx if dest_owned else None, "open": 1}}}
    bdoc = {"boxes": {
        "a": {"id": "M-1", "file": "handoffs/active/big-moved.md", "state": "open", "text": "- [ ] **M-1** [non-inference] moves",
              "lint": {"ok": True}, "gate": [], "gate_open": False, "pos_in_backlog": 1, "class": "non-inference"}}}
    return idx, state, bdoc


def test_load_moves_skips_garbage(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert [m["to"] for m in I.load_moves()] == ["big-moved.md"]


def test_moved_to_follows_chains():
    moves = [{"from": "a.md", "to": "b.md"}, {"from": "b.md", "to": "c.md"}]
    assert I.moved_to("a.md", moves) == ["b.md", "c.md"]
    assert I.moved_to("z.md", moves) == []


def test_generated_row_links_destination_and_counts_its_boxes(tmp_path, monkeypatch):
    idx, state, bdoc = _setup(tmp_path, monkeypatch)
    row = next(l for l in I.render_domain_tables(state, bdoc, {})[idx].split("\n") if l.startswith("| RTG-7"))
    assert "[big.md](big.md) + [big-moved.md](big-moved.md)" in row
    assert "**M-1**" in row                         # the moved box still drives Next action


def test_generated_row_replaces_a_file_that_moved_away_entirely(tmp_path, monkeypatch):
    idx, state, bdoc = _setup(tmp_path, monkeypatch, src_exists=False)
    row = next(l for l in I.render_domain_tables(state, bdoc, {})[idx].split("\n") if l.startswith("| RTG-7"))
    assert "[big.md]" not in row and "[big-moved.md](big-moved.md)" in row


def test_destination_owned_by_its_own_row_is_not_folded_in(tmp_path, monkeypatch):
    idx, state, bdoc = _setup(tmp_path, monkeypatch, dest_owned=True)
    row = next(l for l in I.render_domain_tables(state, bdoc, {})[idx].split("\n") if l.startswith("| RTG-7"))
    assert "big-moved.md" not in row and "**M-1**" not in row


def test_check_warns_hand_row_naming_moved_track(tmp_path, monkeypatch):
    _, state, _ = _setup(tmp_path, monkeypatch)
    w = I.moved_row_warnings(state)
    assert len(w) == 1 and w[0].startswith("MOVED: row RTG-7") and "big-moved.md" in w[0]
    assert "unowned destination(s) big-moved.md" in w[0]


def test_check_warns_repoint_when_source_gone(tmp_path, monkeypatch):
    _, state, _ = _setup(tmp_path, monkeypatch, src_exists=False)
    assert "no longer exists - repoint the row" in I.moved_row_warnings(state)[0]


def test_no_moves_no_warning(tmp_path, monkeypatch):
    _, state, _ = _setup(tmp_path, monkeypatch)
    assert I.moved_row_warnings(state, moves=[]) == []
