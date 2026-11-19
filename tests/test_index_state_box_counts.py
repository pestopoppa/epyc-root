"""Graph `open` must equal the file's unticked task boxes, guarded checklists included."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "handoffs"))
import index_state as s  # noqa: E402

RTG18 = """# Audit
## Update Checklist For Any Model-Stack Change
> **THESE BOXES ARE UNCHECKED BY DESIGN — DO NOT DISPATCH OR FLIP THEM.**
> This is a **reusable per-change runbook**, not a task list. Every `- [ ]` below is a step.

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
    """RTG-18 regression through build_graph itself (the old test only did arithmetic on a literal)."""
    p = tmp_path / "h.md"
    p.write_text(RTG18)
    st = s.scan_handoff(p)
    st.update(last_advanced="2026-11-10", state="active")
    row = {"id": "RTG-18", "index": "routing-and-orchestration-index.md", "track": "t", "handoff": "h.md",
           "next_action": "n", "deps": "", "deps_raw": ""}
    g = s.build_graph({"rows": {"RTG-18": row}, "handoffs": {"h.md": st}})
    node = next(n for n in g["nodes"] if n["id"] == "RTG-18")
    assert node["open"] == 3, node            # every unticked box, guarded included
    assert node["dispatchable"] == st["open"]
    assert node["dispatchable"] == 0 and node["guarded"] == 3  # the exact RTG-18 shape: open must not read 0


def test_unified_tick_counts_closed_and_frozen_bucket(tmp_path):
    """Unified tick suffix is a closed box; a frozen box is its own bucket (handoff standard Stage B)."""
    p = tmp_path / "h.md"
    p.write_text("# H\n\n- [x] **A-1** measure ✅ 2026-11-19 [belief: clm_u1] KEEP +3.1% decode\n- [ ] **A-2** next thing to do\n"
                 "- [ ] **A-3** later thing\n      · ❄ frozen until: OP-1\n"
                 "- [ ] **A-4** parent\n      · roll-up: children carry the work\n")
    b = s.scan_handoff(p)
    assert b["closed"] == 1 and b.get("frozen") == 1 and b["open"] + b["blocked"] + b["guarded"] == 1
    assert s.prune_signal(p, dict(b, open=0, blocked=0, guarded=0))["blocker"] == "frozen-tasks"
