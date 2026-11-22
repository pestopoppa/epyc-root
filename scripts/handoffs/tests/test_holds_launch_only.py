"""Scoped holds (operator ruling 2026-11-22): a `launch_only: true` hold gates launching/relaunching the loop only --
its sessions and explicitly named launch boxes -- and never propagates to the boxes of its handoffs."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "coordination"))
import box_index  # noqa: E402
import holds as H  # noqa: E402

YAML = """holds:
- id: ak-loop
  launch_only: true
  scope: loop-launch
  sessions: [h-ak-loop]
  handoffs: [ak.md]
  boxes: [AK-LAUNCH-1]
- id: blanket
  scope: loop-launch
  sessions: [other]
  handoffs: [other.md]
"""


def _holds(tmp_path):
    (tmp_path / "handoffs/active").mkdir(parents=True)
    (tmp_path / "handoffs/active/holds.yaml").write_text(YAML)
    return box_index.load_holds(tmp_path)


def test_launch_only_does_not_hold_handoff_boxes(tmp_path):
    hs = _holds(tmp_path)
    assert box_index.holds_on(hs, "ak.md", None, "AK-7", "sha7") == []


def test_launch_only_holds_named_launch_box(tmp_path):
    hs = _holds(tmp_path)
    assert box_index.holds_on(hs, "ak.md", None, "AK-LAUNCH-1", "sha1") == ["ak-loop"]


def test_launch_only_still_gates_session_launch(tmp_path):
    hs = _holds(tmp_path)
    assert box_index.holds_on(hs, "ak-loop.md", None, None, "s") == ["ak-loop"]   # session's own handoff stem
    doc = H.load(str(tmp_path))
    assert "ak-loop" in H.held_sessions(doc)


def test_blanket_hold_unchanged(tmp_path):
    hs = _holds(tmp_path)
    assert box_index.holds_on(hs, "other.md", None, "O-1", "s") == ["blanket"]


def test_operator_decision_gate_kept():
    rec = {"state": "open", "holds": [], "decision_kind": "operator-decision", "class": "operator-decision"}
    # an [operator] box is never dispatchable regardless of holds
    assert not box_index.dispatchable(rec)


def test_validate_launch_only():
    assert H.validate([{"id": "a", "launch_only": True, "scope": "all-rows", "sessions": ["x"]}])
    assert H.validate([{"id": "a", "launch_only": "yes", "sessions": ["x"]}])
    assert H.validate([{"id": "a", "launch_only": True, "handoffs": ["x.md"]}])
    assert H.validate([{"id": "a", "launch_only": True, "sessions": ["x"], "handoffs": ["x.md"]}]) == []
