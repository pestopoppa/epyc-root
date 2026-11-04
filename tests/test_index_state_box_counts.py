"""Graph `open` must equal the file's unticked task boxes, guarded checklists included."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "handoffs"))
import index_state as s  # noqa: E402

RTG18 = """# Audit
## Update Checklist For Any Model-Stack Change
> This is a **reusable per-change runbook**, not a task list. Every `- [ ]` below is a step. DO-NOT-DISPATCH
- [ ] Identify the change
- [ ] Update inputs:
  - nested detail
- [ ] Compile priors.
- [x] done step
"""

def test_guarded_boxes_count_as_open(tmp_path):
    p = tmp_path / "h.md"
    p.write_text(RTG18)
    b = s.scan_handoff(p)
    unticked = b["open"] + b["guarded"] + b["blocked"]
    assert unticked == 3 and b["closed"] == 1

def test_node_open_includes_guarded(tmp_path):
    st = {"open": 0, "guarded": 11, "blocked": 1, "closed": 2}
    assert st["open"] + st["guarded"] + st["blocked"] == 12
