"""Handoff standard C1: intake Stage 4 refuses an applied box that would need an LLM proposal."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validate_intake as V  # noqa: E402


def test_intake_box_lint(tmp_path):
    (tmp_path / "x.py").write_text("")
    f = tmp_path / "h.md"
    f.write_text(
        "- [ ] **IN-1** [non-inference] good box\n      · done when: verdict: PASS\n      · gate: none\n"
        "- [ ] **IN-2** missing everything\n"
        "- [ ] **IN-3** [non-inference] draft NEEDS-OWNER\n      · gate: none\n"
        "- [ ] **IN-4** [non-inference] dangling\n      · done when: verdict: PASS\n"
        "      · gate: none        · inputs: `does/not/exist.py`\n")
    assert V.intake_box_lint(f, "IN-1") == []
    e2 = " ".join(V.intake_box_lint(f, "IN-2"))
    assert "[class]" in e2 and "done when" in e2 and "gate" in e2
    assert V.intake_box_lint(f, "IN-3") == []
    assert "do not exist" in " ".join(V.intake_box_lint(f, "IN-4"))
    assert "not found" in V.intake_box_lint(f, "IN-9")[0]
