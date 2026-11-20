"""C0.1 (handoff standard Stage C): generated `Next action` and taskflow.select share ONE dispatchable predicate."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "handoffs"))
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
import box_index  # noqa: E402
import index_state as I  # noqa: E402
from taskflow import select as S  # noqa: E402


def rec(i, **kw):
    r = {"file": "handoffs/active/x.md", "line": i, "id": f"X-{i}", "text": f"- [ ] **X-{i}** task {i}",
         "state": "open", "class": "non-inference", "gate": [], "gate_open": False, "inputs_missing": [],
         "holds": [], "outside_backlog": False, "lint": {"ok": True, "fails": []}, "pos_in_backlog": i}
    r.update(kw)
    return r


def test_first_box_failing_lint_is_skipped():
    boxes = [rec(1, lint={"ok": False, "fails": ["a"]}), rec(2)]
    assert I.generated_next_action(boxes, exclude=set()).startswith("**X-2**")


def test_zero_admissible_renders_needs_owner():
    boxes = [rec(1, lint={"ok": False, "fails": ["a"]}), rec(2, inputs_missing=["p"]), rec(3, class_="x", **{"class": "operator-decision"})]
    assert I.generated_next_action(boxes, exclude=set()) == "NEEDS-OWNER: 3"


def test_gated_renders_blocked_and_frozen_renders_frozen():
    assert I.generated_next_action([rec(1, gate=["Y-1"], gate_open=True)], exclude=set()) == "BLOCKED: Y-1"
    assert I.generated_next_action([rec(1, state="frozen", frozen_until="v11")], exclude=set()) == "FROZEN until v11"


def test_held_box_or_file_renders_hold():
    assert I.generated_next_action([rec(1, holds=["ak"])], exclude=set()).startswith("FROZEN (operator hold: ak")
    assert I.generated_next_action([rec(1)], exclude={"x.md"}).startswith("FROZEN (operator hold")


def test_select_and_generated_rows_agree():
    boxes = [rec(1, outside_backlog=True), rec(2, proposed_by="taskflow"), rec(3, holds=["h"]), rec(4)]
    doc = {"boxes": {b["id"]: b for b in boxes}, "holds_source": "handoffs/active/holds.yaml"}
    cands, hist = S.candidates(doc, set())
    assert [k for k, _ in cands] == ["X-4"]
    assert I.generated_next_action(boxes, exclude=set()).startswith("**X-4**")
    assert hist["proposal-pending"] == 1 and hist["held"] == 1 and hist["outside-backlog"] == 1
    assert all(box_index.skip_reason(b, set()) == S.skip_reason(b, set()) for b in boxes)
