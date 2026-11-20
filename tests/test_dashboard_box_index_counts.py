"""Handoff standard C0.4/C3: the hub board carries box-index counts, holds and a staleness badge."""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))
import handoff_parser as hp  # noqa: E402


def _repo(tmp_path: Path, doc: dict | None):
    (tmp_path / "scripts").symlink_to(ROOT / "scripts")
    act = tmp_path / "handoffs" / "active"
    act.mkdir(parents=True)
    (act / "x.md").write_text("# X\n**Status**: ACTIVE — x\n\n- [ ] **X-1** t\n")
    if doc is not None:
        (act / ".box-index.json").write_text(json.dumps(doc))
    return tmp_path


DOC = {"counts": {"open": 2, "frozen": 1, "needs-owner": 1, "held": 1, "outside_backlog": 0, "blocked": 1,
                  "lint_ok": 1, "total": 4},
       "holds": [{"id": "akagg", "scope": "loop-launch"}], "holds_source": "handoffs/active/holds.yaml",
       "boxes": {"X-1": {"file": "handoffs/active/x.md", "state": "open", "holds": ["akagg"], "gate_open": True},
                 "X-2": {"file": "handoffs/active/x.md", "state": "frozen"},
                 "X-3": {"file": "handoffs/active/x.md", "state": "needs-owner", "proposed_by": "taskflow t"},
                 "X-4": {"file": "handoffs/active/x.md", "state": "done"}}}


def test_board_counts_holds_and_fresh_badge(tmp_path):
    repo = _repo(tmp_path, DOC)
    os.utime(repo / "handoffs/active/.box-index.json", (time.time() + 60, time.time() + 60))
    b = hp.build_board(repo / "handoffs")
    bi = b["box_index"]
    assert bi["available"] and not bi["stale"] and bi["counts"]["held"] == 1 and bi["counts"]["needs-owner"] == 1
    assert [h["id"] for h in bi["holds"]] == ["akagg"] and "_per_file" not in bi
    card = next(c for c in b["columns"]["active"] if c["id"] == "active/x")
    bc = card["box_counts"]
    assert (bc["open"], bc["frozen"], bc["needs-owner"], bc["held"], bc["blocked"]) == (1, 1, 1, 1, 1)
    assert bc["holds"] == ["akagg"] and bc["proposals_pending"] == 1


def test_board_stale_badge_when_sources_are_newer(tmp_path):
    repo = _repo(tmp_path, DOC)
    os.utime(repo / "handoffs/active/x.md", (time.time() + 120, time.time() + 120))
    assert hp.build_board(repo / "handoffs")["box_index"]["stale"] is True


def test_board_without_index_is_unavailable_not_zero(tmp_path):
    bi = hp.build_board(_repo(tmp_path, None) / "handoffs")["box_index"]
    assert bi["available"] is False and bi["stale"] is True and bi["counts"] == {}
