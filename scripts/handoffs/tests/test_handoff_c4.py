"""C4 (handoff standard Stage C): split-file + .moves.jsonl repointing, compaction, new_handoff."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
import box_index as BI  # noqa: E402
import handoff_box as HB  # noqa: E402
import handoff_compact as HC  # noqa: E402
import handoff_ref as HR  # noqa: E402
import new_handoff as NH  # noqa: E402
import task_lint_core as L1  # noqa: E402

SRC = ("# Big\n**Status**: ACTIVE — x\n**Row**: RTG-7\n**Domain**: routing\n\n"
       "## Track: keep\n\n### Backlog\n\n- [ ] **K-1** [non-inference] stays\n      · done when: verdict: PASS\n\n"
       "## Track: move-me\n\n### Backlog\n\n- [ ] **M-1** [non-inference] moves\n      · done when: verdict: PASS\n"
       "- [x] **M-0** old ✅ 2026-01-01 [no-belief: x] done\n\n## History\n\n- h\n")


def _root(tmp_path):
    (tmp_path / "handoffs/active").mkdir(parents=True)
    p = tmp_path / "handoffs/active/big.md"
    p.write_text(SRC)
    return p


def test_split_file_moves_track_writes_moves_and_keeps_first_lines(tmp_path):
    p = _root(tmp_path)
    before = sorted(l for l in SRC.split("\n") if L1.CHECKBOX.match(l))
    r = HB.split_file(p, "move-me", "big-moved", tmp_path, today="2026-11-20")
    assert r["moved_boxes"] == 2
    dest = tmp_path / "handoffs/active/big-moved.md"
    src_after, dest_txt = p.read_text(), dest.read_text()
    after = sorted(l for l in (src_after + "\n" + dest_txt).split("\n") if L1.CHECKBOX.match(l))
    assert before == after                                             # zero first-line changes
    assert "**M-1**" in dest_txt and "**M-1**" not in src_after and "Moved to [big-moved.md]" in src_after
    assert "**Row**: RTG-7" in dest_txt and "**Parent**: [big.md](big.md)" in dest_txt
    moves = [json.loads(l) for l in (tmp_path / "handoffs/active/.moves.jsonl").read_text().splitlines()]
    assert {m["box_id"] for m in moves} == {"M-1", "M-0"} and all(m["to"] == "big-moved.md" for m in moves)


def test_row_published_before_a_move_still_resolves(tmp_path):
    p = _root(tmp_path)
    sha = BI.text_sha("- [ ] **M-1** [non-inference] moves")
    HB.split_file(p, "move-me", "big-moved", tmp_path, today="2026-11-20")
    assert HR.resolve("big.md:M-1", tmp_path) == "big-moved.md:M-1"              # by id
    assert HR.resolve("big.md:X-9", tmp_path, sha) == "big-moved.md:X-9"         # by text_sha first
    assert HR.resolve("big.md:K-1", tmp_path) == "big.md:K-1"                    # unmoved box: unchanged


def test_publish_row_task_box_follows_moves(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts" / "coordination" / "rowflow"))
    import publish_row as pr
    p = _root(tmp_path)
    HB.split_file(p, "move-me", "big-moved", tmp_path, today="2026-11-20")
    spec = {"handoff_task": "big.md:M-1"}
    path, line, txt, _ = pr.task_box(spec, str(tmp_path))
    assert path.endswith("big-moved.md") and spec["handoff_task"] == "big-moved.md:M-1" and "**M-1**" in txt


def test_compaction_folds_old_ticks_and_respects_the_audit():
    new, arch, st = HC.compact(SRC, "big.md", 30, {}, today="2026-11-20")
    assert st["folded"] == 1 and "- [x] **M-0** ✅ 2026-01-01 done" in new and "### Done" in new
    assert "- [x] **M-0** old ✅" in arch and "- [x] **M-0** old ✅" not in new
    assert sorted(l for l in new.split("\n") if L1.CHECKBOX.match(l) and l.startswith("- [ ]")) == \
        sorted(l for l in SRC.split("\n") if L1.CHECKBOX.match(l) and l.startswith("- [ ]"))   # open boxes untouched
    audit = {"flagged": [{"handoff": "handoffs/active/big.md", "text": "- [x] **M-0** old ✅ 2026-01-01 [no-belief: x] done"}]}
    new2, _, st2 = HC.compact(SRC, "big.md", 30, audit, today="2026-11-20")
    assert st2["folded"] == 0 and st2["refused_audit"] == 1 and new2 == SRC
    assert HC.compact(SRC, "big.md", 400, {}, today="2026-11-20")[2]["folded"] == 0       # too recent


def test_new_handoff_renders_the_anatomy(tmp_path):
    t = NH.render("my-thing", "RTG-99", "routing", today="2026-11-20")
    for k in ("**Status**:", "**Row**: RTG-99", "**Domain**: routing", "**Created**: 2026-11-20", "**Holds**: none",
              "## Dispatch contract", "## Track: my-thing", "### Backlog", "### Done", "## Findings", "## History"):
        assert k in t
    (tmp_path / "handoffs/active").mkdir(parents=True)
    assert NH.main(["my-thing", "--row", "RTG-99", "--domain", "routing", "--root", str(tmp_path)]) == 0
    assert NH.main(["my-thing", "--row", "RTG-99", "--domain", "routing", "--root", str(tmp_path)]) == 1
