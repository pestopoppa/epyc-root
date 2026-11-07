"""VB-CC-2: cc-extract/v1 proposer (deterministic, draft-only)."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import cc_extract as cx  # noqa: E402

RESULT = ("- [x] **K99 — f16 vs bf16 KV bench ✅ 2026-07-17**: adds runner + tests. "
          "Result: f16 41.3 t/s vs bf16 38.0 t/s, KEEP f16 (+8.7%).")
PLUMB = "- [x] **W1 — adds runner, wires the CLI and fixture** ✅ 2026-07-17"
UNTICKED = "- [ ] **K100 — bench shows REGRESSED -12% t/s** pending"


def test_unticked_item_is_gated_out():
    r = cx.score_item(UNTICKED)
    assert r["gate"] == "unticked" and r["proposed"] is False


def test_sentence_scoring_finds_result_inside_plumbing_item():
    r = cx.score_item(RESULT)
    assert r["proposed"] and "KEEP" in r["best_sentence"]


def test_plumbing_only_item_not_proposed():
    assert cx.score_item(PLUMB)["proposed"] is False


def test_draft_row_fields_and_determinism():
    a = cx.draft_row("handoffs/active/x.md", 3, 3, RESULT)
    b = cx.draft_row("handoffs/completed/x.md", 9, 9, RESULT)
    assert a["draft"] is True and "confirmed_by" not in a
    assert a["cc_id"] == b["cc_id"]          # active -> completed keeps identity
    assert a["task_id"] == "K99" and a["dedup_key"] == "task:K99"
    assert a["stated"]["verdict_native"] == "KEEP"
    assert {m["unit"] for m in a["stated"]["metrics"]} >= {"t/s", "%"}
    assert a["stated"]["date"] == "2026-07-17"


def test_scope_proposal_line_then_heading():
    sc, ev = cx.scope_of("Qwen3.6-35B-A3B Q8_0 on MI210 41 t/s")
    assert ev == "line" and sc["quant"] == "Q8_0" and sc["backend"] == "gpu"
    sc, ev = cx.scope_of("41 t/s", heading="## Qwen3.6-27B Q4_K_M cpu")
    assert ev == "heading"
    assert cx.scope_of("nothing here")[1] == "none"


def test_progress_restatement_merges_into_handoff_anchor():
    h = cx.draft_row("handoffs/active/x.md", 3, 3, RESULT)
    p = cx.draft_row("progress/2026-07/2026-07-17.md", 5, 5,
                     "- **K99** KEEP f16: 41.3 t/s vs 38.0 t/s")
    out = cx.merge_restatements([p, h])
    assert len(out) == 1 and out[0]["anchor_hint"]["path"].startswith("handoffs/")
    assert out[0]["also_anchored"][0]["path"].startswith("progress/")


def test_ac0_math():
    items = [{"text": RESULT}, {"text": PLUMB}, {"text": UNTICKED}]
    r = cx.ac0(items, {0, 2})
    assert r["true_positives"] == 1 and r["n_proposed"] == 1
    assert r["recall"] == 0.5 and r["precision"] == 1.0 and r["pass"] is False


def test_scan_reads_git_ref_not_worktree(tmp_path):
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / "handoffs/active").mkdir(parents=True)
    (tmp_path / "progress/2026-07").mkdir(parents=True)
    (tmp_path / "handoffs/active/x.md").write_text("# x\n" + RESULT + "\n" + PLUMB + "\n")
    (tmp_path / "progress/2026-07/2026-07-17.md").write_text(
        "# day\n### Results\n- **K99** KEEP f16: 41.3 t/s vs 38.0 t/s\n")
    git("add", "-A")
    git("commit", "-qm", "c")
    (tmp_path / "handoffs/active/x.md").write_text("# x\n")   # uncommitted: must be ignored
    rows = cx.scan(tmp_path, "HEAD", [])
    assert len(rows) == 1 and rows[0]["task_id"] == "K99"
    assert rows[0]["anchor_hint"]["line_start"] == 2 and len(rows[0]["also_anchored"]) == 1
