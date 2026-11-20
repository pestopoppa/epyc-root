"""C7 (operator decision 1): only `[ ]` / `[x]` are boxes; `[~] [>] [!]` are LEGACY-MARKER, counted, never dispatchable."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "handoffs"))
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
import backlog_row_check as brc  # noqa: E402
import box_index as BI  # noqa: E402
import handoff_migrate as HM  # noqa: E402
import task_lint_core as L1  # noqa: E402

TXT = "# H\n\n- [ ] **A-1** open\n- [~] **A-2** partial\n- [>] **A-3** moved\n- [!] **A-4** urgent\n- [x] **A-5** done\n"


def test_only_two_states_are_boxes(tmp_path):
    f = tmp_path / "h.md"
    f.write_text(TXT)
    assert [s for _, s, _, _ in brc._boxes(f)] == ["", "x"]
    assert brc.legacy_markers(f) == [4, 5, 6]
    assert [bool(L1.CHECKBOX.match(l)) for l in TXT.split("\n")[2:7]] == [True, False, False, False, True]
    assert sum(1 for l in TXT.split("\n") if L1.LEGACY_MARKER.match(l)) == 3


def test_box_index_counts_legacy_and_never_indexes_them(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path))
    (tmp_path / "handoffs/active").mkdir(parents=True)
    f = tmp_path / "handoffs/active/h.md"
    f.write_text(TXT)
    doc = BI.build(tmp_path, {"h.md": f}, {}, {}, {})
    assert doc["counts"]["legacy_marker"] == 3 and set(doc["boxes"]) == {"A-1"}


def test_migrate_retires_markers_keeping_identity():
    new, st = HM.migrate_text(TXT, boxes=False)
    assert st["legacy_markers"] == 3 and not any(L1.LEGACY_MARKER.match(l) for l in new.split("\n"))
    lines = new.split("\n")
    i = lines.index("- [ ] **A-2** partial")
    assert "NEEDS-OWNER" in lines[i + 1] and lines[i + 1].startswith("      ")
    assert BI.text_sha("- [~] **A-2** partial".replace("[~]", "[ ]")) == BI.text_sha(lines[i])
    assert HM.migrate_text(new, boxes=False)[0] == new          # idempotent


def test_closed_findings_go_to_history_children_stay():
    txt = ("# H\n\n- [~] **E-1 — OVERSTATED, largely withdrawn 2026-07-27.** prose\n      more prose\n"
           "  - [ ] **E-1b** still open\n- [~] **E-2** half done\n\n## History\n\n- old\n")
    new, st = HM.migrate_text(txt, boxes=False)
    assert st["legacy_markers"] == 1 and "- [ ] **E-1b** still open" in new          # child dedented, kept
    hist = new.split("## History", 1)[1]
    assert "**E-1 — OVERSTATED" in hist and "[declined: C7-migration " in hist and "withdrawn 2026-07-27]" in hist
    assert "- [ ] **E-1 —" not in new and "- [ ] **E-2** half done" in new            # E-2: not closed -> NEEDS-OWNER
