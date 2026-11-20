"""Stage B of the handoff standard: fixes from the Fable review of Stage A (S1-S4) and the consumer wiring."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import box_index as BI  # noqa: E402
import handoff_box as HB  # noqa: E402
import task_lint as TL  # noqa: E402
import task_lint_core as L1  # noqa: E402

ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t"}

LEGACY = """# x

- [ ] **KPF-18.3 — legacy parent with no explicit condition**
  - [ ] **KPF-18.3a — child one** do the first part
  - [ ] **KPF-18.3b — child two** do the second part
- [ ] **AKX-ALL-5 (C1): legacy box two** with prose
      evidence line one
"""


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True, env=ENV).stdout


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "handoffs" / "active").mkdir(parents=True)
    (tmp_path / "handoffs" / "active" / "fx.md").write_text(LEGACY)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "init")
    return tmp_path


def _edit(repo, old, new):
    f = repo / "handoffs" / "active" / "fx.md"
    f.write_text(f.read_text().replace(old, new))
    _git(repo, "add", ".")


# ---- S1 / S1b: a parent is not "touched" by its children or a plain evidence line ----------------------------------
def test_nested_tick_does_not_touch_parent(repo):
    _edit(repo, "- [ ] **KPF-18.3a — child one** do the first part",
          "- [x] **KPF-18.3a — child one** do the first part ✅ 2026-11-19 [belief: cc] PASS")
    assert TL.diff_gate(repo, None, "enforce")[1] == 0


def test_child_add_does_not_touch_parent(repo):
    _edit(repo, "  - [ ] **KPF-18.3b — child two** do the second part",
          "  - [ ] **KPF-18.3b — child two** do the second part\n  - [ ] **KPF-18.3c** draft NEEDS-OWNER")
    lines, n = TL.diff_gate(repo, None, "enforce")
    assert n == 0, lines


def test_evidence_append_does_not_touch_legacy_box(repo):
    _edit(repo, "      evidence line one", "      evidence line one\n      evidence line two")
    lines, n = TL.diff_gate(repo, None, "enforce")
    assert n == 0 and "0 touched" in lines[-1]


def test_field_line_change_touches_box_but_legacy_literal_not_demanded(repo):
    # an edited legacy box (first line NOT new) is judged by rubric field a, never by the literal `done when`
    _edit(repo, "      evidence line one", "      evidence line one\n      · gate: none")
    finds = TL.touched_box_findings(repo, None)
    assert len(finds) == 1 and finds[0][1] == 6


def test_new_box_still_needs_literal_done_when(repo):
    _edit(repo, "      evidence line one", "      evidence line one\n- [ ] **N-1** [non-inference] fix the scorer tests pass")
    assert TL.diff_gate(repo, None, "default")[1] == 1


def test_pathspec_temp_index_is_judged(repo):
    # S3: GIT_INDEX_FILE is honoured, so a hook running on a temporary index sees that index
    f = repo / "handoffs" / "active" / "fx.md"
    f.write_text(f.read_text() + "- [ ] **N-2** [non-inference] new box without condition\n")
    tmp_index = repo / ".git" / "tmp-index"
    env = {**ENV, "GIT_INDEX_FILE": str(tmp_index)}
    subprocess.run(["git", "-C", str(repo), "read-tree", "HEAD"], env=env, check=True)
    subprocess.run(["git", "-C", str(repo), "add", "handoffs/active/fx.md"], env=env, check=True)
    old = os.environ.get("GIT_INDEX_FILE")
    os.environ["GIT_INDEX_FILE"] = str(tmp_index)
    try:
        assert TL.diff_gate(repo, None, "default")[1] == 1        # the temp index carries the new box
    finally:
        os.environ.pop("GIT_INDEX_FILE") if old is None else os.environ.__setitem__("GIT_INDEX_FILE", old)
    assert TL.diff_gate(repo, None, "default")[1] == 0            # the real index does not


def test_check_mode_diffs_working_tree_against_head(repo):
    f = repo / "handoffs" / "active" / "fx.md"
    f.write_text(f.read_text() + "- [ ] **N-3** [non-inference] unstaged new box\n")
    assert TL.diff_gate(repo, "HEAD", "default")[1] == 1


# ---- S2: one id rule ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("line,want", [
    ("- [ ] **KPF-18.3 — text**", "KPF-18.3"),
    ("- [ ] **AKX-ALL-5 (C1): x**", "AKX-ALL-5"),
    ("- [ ] **KPF-17: tests.** body", "KPF-17"),
    ("- [ ] **B5** body", "B5"),
    ("- [x] **❄ HS-4** frozen", "HS-4"),
    ("- [ ] **Note** an English word", None),
    ("- [ ] plain box", None),
])
def test_shared_id_rule(line, want):
    assert L1.head_id(line) == want
    assert TL.box_id(line) == want


def test_backlog_row_check_and_index_state_share_the_rule():
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root / "scripts" / "coordination"))
    import backlog_row_check as brc
    assert brc._lead_id("**AKX-ALL-5 (C1): x**") == "AKX-ALL-5"
    assert brc._lead_id("HG-1 unbolded legacy") == "HG-1"


# ---- S2: fences, History/Done, outside-backlog, track/file freeze ---------------------------------------------------
MULTI = """# Multi
**Status**: ACTIVE — fixture

## Track: alpha

### Backlog

- [ ] **A-1** [non-inference] do a
      · done when: pytest a passes
      · gate: B-1

## Track: beta
❄ frozen until: OP-9 decided

### Backlog

- [ ] **B-1** [non-inference] do b
      · done when: pytest b passes
- [ ] **B-2** parent box
      · roll-up: children carry the work
  - [ ] **B-2a** child
  - [ ] **B-2b** child

## History

```
- [ ] **F-1** fenced example
```
- [ ] **H-1** stray open box under History
"""


def _bi(tmp_path, text, track_open=None):
    (tmp_path / "handoffs" / "active").mkdir(parents=True, exist_ok=True)
    f = tmp_path / "handoffs" / "active" / "m.md"
    f.write_bytes(text.encode())
    return BI.build(tmp_path, {"m.md": f}, {"m.md": "TST-1"}, {"TST-1": True}, {}, track_open)


def test_fenced_box_not_indexed_and_history_box_flagged(tmp_path):
    d = _bi(tmp_path, MULTI)
    assert "F-1" not in d["boxes"]
    assert d["boxes"]["H-1"]["outside_backlog"] is True
    assert d["boxes"]["A-1"]["outside_backlog"] is False
    assert d["counts"]["outside_backlog"] == 1


def test_two_backlogs_positions(tmp_path):
    b = _bi(tmp_path, MULTI)["boxes"]
    assert b["A-1"]["pos_in_backlog"] == 1 and b["B-1"]["pos_in_backlog"] == 1 and b["B-2"]["pos_in_backlog"] == 2


def test_track_freeze_inherited(tmp_path):
    b = _bi(tmp_path, MULTI)["boxes"]
    assert b["B-1"]["state"] == "frozen" and b["B-1"]["frozen_until"] == "OP-9 decided"
    assert b["A-1"]["state"] == "open"


def test_whole_file_freeze_inherited(tmp_path):
    b = _bi(tmp_path, MULTI.replace("**Status**: ACTIVE — fixture",
                                    "**Status**: FROZEN — ❄ frozen until: v11 (was: ACTIVE)"))["boxes"]
    assert b["A-1"]["state"] == "frozen" and b["A-1"]["frozen_until"] == "v11"


def test_freeze_track_written_by_handoff_box_is_read(tmp_path):
    text = MULTI.replace("❄ frozen until: OP-9 decided\n", "")
    (tmp_path / "handoffs" / "active").mkdir(parents=True, exist_ok=True)
    f = tmp_path / "handoffs" / "active" / "m.md"
    f.write_text(text)
    a = HB.parser().parse_args(["freeze", "--track", "alpha", "--until", "EV-1", "--file", str(f)])
    HB.apply(f, "freeze", a, root=tmp_path)
    d = BI.build(tmp_path, {"m.md": f}, {}, {}, {})
    assert d["boxes"]["A-1"]["state"] == "frozen" and d["boxes"]["A-1"]["frozen_until"] == "EV-1"


def test_rollup_continuation_and_cont_lines_own_block(tmp_path):
    b = _bi(tmp_path, MULTI)["boxes"]
    assert b["B-2"]["state"] == "rollup"
    assert b["B-2"]["cont_lines"] == 1           # its own `· roll-up:` line; the two children are not counted


# ---- S3: gate refs -------------------------------------------------------------------------------------------------
def test_row_track_ref_and_unknown_ref(tmp_path):
    text = MULTI.replace("      · gate: B-1", "      · gate: TST-1#beta, ZZZ-404")
    b = _bi(tmp_path, text, {"TST-1#beta": False})["boxes"]["A-1"]
    assert b["gate_open"] is False                    # resolved track closed; the unknown ref does NOT open the gate
    assert b["gate_unknown"] == ["ZZZ-404"] and "g-gate-unknown" in b["lint"]["fails"]
    b2 = _bi(tmp_path, text, {"TST-1#beta": True})["boxes"]["A-1"]
    assert b2["gate_open"] is True


def test_two_builds_byte_identical(tmp_path):
    assert BI.dumps(_bi(tmp_path, MULTI)) == BI.dumps(_bi(tmp_path, MULTI))


# ---- S3/S4: handoff_box ---------------------------------------------------------------------------------------------
def test_add_on_untracked_file_creates_backlog_after_header(tmp_path):
    (tmp_path / "handoffs" / "active").mkdir(parents=True)
    f = tmp_path / "handoffs" / "active" / "u.md"
    f.write_text("# U\n**Status**: ACTIVE — x\n\n## Notes\n\nprose\n")
    a = HB.parser().parse_args(["add", "--track", "any", "--id", "U-1", "--class", "non-inference", "--text", "do u",
                                "--done-when", "pytest u passes", "--file", str(f)])
    HB.apply(f, "add", a, root=tmp_path)
    lines = f.read_text().split("\n")
    assert lines.index("### Backlog") < lines.index("## Notes")
    assert BI.build(tmp_path, {"u.md": f}, {}, {}, {})["boxes"]["U-1"]["outside_backlog"] is False


def test_add_after_nested_child_goes_after_parent_block(tmp_path):
    (tmp_path / "handoffs" / "active").mkdir(parents=True)
    f = tmp_path / "handoffs" / "active" / "m.md"
    f.write_text(MULTI)
    a = HB.parser().parse_args(["add", "--track", "beta", "--id", "B-9", "--class", "non-inference", "--text", "do b9",
                                "--done-when", "ok", "--after", "B-2a", "--file", str(f)])
    HB.apply(f, "add", a, root=tmp_path)
    lines = f.read_text().split("\n")
    i = next(i for i, l in enumerate(lines) if "**B-9**" in l)
    assert lines[i].startswith("- [ ]") and "**B-2b**" in lines[i - 1]


def test_apply_preserves_crlf_and_stray_bytes(tmp_path):
    (tmp_path / "handoffs" / "active").mkdir(parents=True)
    f = tmp_path / "handoffs" / "active" / "c.md"
    f.write_bytes(MULTI.replace("\n", "\r\n").encode() + b"stray \xff byte\r\n")
    a = HB.parser().parse_args(["gate", "A-1", "--none", "--file", str(f)])
    HB.apply(f, "gate", a, root=tmp_path)
    raw = f.read_bytes()
    assert b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b"") and b"\xff" in raw


def test_parse_fields_case_insensitive():
    assert TL.parse_fields("- [ ] **X-1** t\n      · Done when: ok")["done when"] == "ok"


# ---- mechanical migration (handoff_migrate.py) ----------------------------------------------------------------------
import handoff_migrate as HM  # noqa: E402

MIG = """# M
**Status**: ACTIVE — x

## Track: t
<!-- gate: none -->

### Phase 1 notes

- [ ] **M-1 — implement the parser** wire it into run.py
  - [ ] **M-1a** child
- [x] **M-0** done ✅ 2026-11-01 [belief: cc] ok
  - [ ] **M-0b** open child of a ticked parent
- [ ] **M-2 ❄ FROZEN — resume only once OP-7 is decided** later

## History

- [ ] **H-9** stray
"""


def test_migration_moves_marks_and_keeps_first_lines():
    new, st = HM.migrate_text(MIG)
    lines = new.split("\n")
    bl = lines.index("### Backlog")
    i1 = next(i for i, l in enumerate(lines) if l.startswith("- [ ] **M-1 "))
    i2 = next(i for i, l in enumerate(lines) if l.startswith("- [ ] **M-2 "))
    assert bl < i1 < i2 < lines.index("### Phase 1 notes")
    blk = "\n".join(lines[i1:i2])
    assert "· roll-up: children carry the work" in blk and "· section: Phase 1 notes" in blk
    assert "· ❄ frozen until: OP-7 is decided" in "\n".join(lines[i2:i2 + 4])
    assert st["moved"] == 2 and st["left_nested"] == 1 and st["left_section"] == 1
    assert HM.open_shas(MIG.split("\n")) == HM.open_shas(lines)
    assert HM.first_lines(MIG.split("\n")) == HM.first_lines(lines)
    assert HM.migrate_text(new)[0] == new                 # idempotent


def test_annotations_never_change_the_rubric():
    box = "- [ ] **Z-1 — fix the scorer** tests pass"
    ann = box + "\n      · section: Deferred until after the parked thing lands\n      · class: non-inference"
    assert TL.dispatch_result(box)["fails"] == TL.dispatch_result(ann)["fails"]


def test_headers_added_once_after_status():
    new, st = HM.migrate_text(MIG, "RTG-1", "routing-and-optimization", boxes=False)
    lines = new.split("\n")
    assert lines[2:4] == ["**Row**: RTG-1", "**Domain**: routing-and-optimization"] and st["headers"] == 2
    assert HM.migrate_text(new, "RTG-9", "x", boxes=False)[0] == new      # an existing key is never rewritten


def test_generated_domain_table_is_not_a_hand_row(tmp_path, monkeypatch):
    import index_state as IS
    p = tmp_path / "x-index.md"
    p.write_text("| ID | Track | Handoff | Next action | Deps |\n|---|---|---|---|---|\n"
                 "| RTG-1 | t | [a.md](a.md) | do it | — |\n\n"
                 + IS.GEN_START + "\n" + IS.GEN_HEAD + "\n| RTG-1 | [a.md](a.md) | x | — | 1 | 1/0/0 | — |\n" + IS.GEN_END + "\n")
    rows = IS.parse_index_rows(p)
    assert len(rows) == 1 and not rows[0].get("malformed")
    nxt = IS.generated_next_action([{"state": "open", "class": "non-inference", "id": "A-1", "pos_in_backlog": 1,
                                     "text": "- [ ] **A-1 — do the thing** now", "gate_open": False,
                                     "lint": {"ok": True}}], exclude=set())
    assert nxt == "**A-1** do the thing now"
    assert IS.generated_next_action([{"state": "frozen", "frozen_until": "OP-1", "text": "x"}]) == "FROZEN until OP-1"


def test_moved_box_with_annotations_is_not_touched(repo):
    f = repo / "handoffs" / "active" / "fx.md"
    new, _ = HM.migrate_text(f.read_text())
    f.write_text(new)
    _git(repo, "add", ".")
    lines, n = TL.diff_gate(repo, None, "enforce")
    assert n == 0, lines
