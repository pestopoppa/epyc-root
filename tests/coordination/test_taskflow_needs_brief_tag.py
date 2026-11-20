"""TASKFLOW-NEEDS-BRIEF-TAG: a `needs-brief` verdict writes the NEEDS-BRIEF tag onto the box (handoff_box.py
needs-brief) so box_index sets `needs_brief` and select.py skips it; the box's first line (its identity) is untouched."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
sys.path.insert(0, str(ROOT / "scripts" / "handoffs"))
from taskflow import dispatch, schema  # noqa: E402
import box_index  # noqa: E402
import handoff_box  # noqa: E402

BOX = "- [ ] **NB-1** [non-inference] make `parse` in `scripts/x.py` strip whitespace"
HF = f"# H\n## Track: T\n### Backlog\n{BOX}\n      · done when: `pytest -q tests/test_x.py`\n      · gate: none\n"


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout.strip()


def _repo(tmp_path):
    r = tmp_path / "root"
    (r / "handoffs/active").mkdir(parents=True)
    (r / "handoffs/active/h.md").write_text(HF)
    _git(tmp_path, "init", "-q", str(r))
    _git(r, "config", "user.email", "t@t"); _git(r, "config", "user.name", "t")
    _git(r, "add", "."); _git(r, "commit", "-qm", "base")
    _git(r, "update-ref", "refs/remotes/origin/main", "HEAD")
    return r


def _rec(root):
    doc = box_index.load(root)
    return next(r for r in doc["boxes"] if r.get("id") == "NB-1") if "boxes" in doc else None


def test_op_tags_continuation_line_keeps_first_line_and_is_idempotent(tmp_path):
    f = tmp_path / "h.md"
    f.write_text(HF)
    assert handoff_box.main(["needs-brief", "--file", str(f), "NB-1", "--reason", "missing key `where`", "--date", "2026-11-20"]) == 0
    t = f.read_text()
    assert t.split("\n")[3] == BOX                                     # identity line untouched
    assert t.count("· NEEDS-BRIEF: 2026-11-20 missing key `where`") == 1
    handoff_box.main(["needs-brief", "--file", str(f), "NB-1", "--reason", "again", "--date", "2026-11-21"])
    assert f.read_text().count("NEEDS-BRIEF:") == 1                    # replaced, not duplicated
    handoff_box.main(["needs-brief", "--file", str(f), "NB-1", "--clear"])
    assert f.read_text() == HF


def test_box_index_reads_tag_but_not_a_mention(tmp_path):
    root = _repo(tmp_path)
    f = root / "handoffs/active/h.md"
    f.write_text(HF.replace("strip whitespace", "strip whitespace (see NEEDS-BRIEF docs)"))
    own = lambda: [r for r in box_index.build(root, {"h.md": f}, {"h.md": None}, {}, {})["boxes"].values()   # noqa: E731
                   if r.get("id") == "NB-1"][0]
    assert not own().get("needs_brief")                                # a prose mention is not the tag
    handoff_box.main(["needs-brief", "--file", str(f), "NB-1", "--reason", "x"])
    rec = own()
    assert rec["needs_brief"] and box_index.skip_reason(dict(rec, state="open", lint={"ok": True}, holds=[], gate_open=False, inputs_missing=False, outside_backlog=False)) == "needs-brief"


def test_dispatch_tag_commits_on_lane_branch_in_fresh_worktree(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    monkeypatch.setitem(schema.REPOS, "epyc-root", root)
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(tmp_path / "tf"))
    monkeypatch.setattr(dispatch, "MIN_FREE_GIB", 0)
    task = {"id": "NB-1", "key": "NB-1", "handoff": "handoffs/active/h.md", "repo": "epyc-root"}
    pushed = []
    res = dispatch.tag_needs_brief(task, tmp_path / "t", "NEEDS-BRIEF:x", apply=True, push=lambda l: pushed.append(l) or "ok")
    assert res["tagged"] and res["pushed"] == "ok" and len(pushed) == 1
    assert "· NEEDS-BRIEF:" in _git(root, "show", f"{res['branch']}:handoffs/active/h.md")
    assert "NEEDS-BRIEF" not in (root / "handoffs/active/h.md").read_text()   # shared tree never touched
    assert _git(root, "diff", "--stat", "origin/main", res["branch"], "--", "handoffs/active/h.md")


def test_needs_brief_run_tags_the_box(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    monkeypatch.setitem(schema.REPOS, "epyc-root", root)
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(tmp_path / "tf"))
    monkeypatch.setattr(dispatch, "MIN_FREE_GIB", 0)
    monkeypatch.setattr(dispatch, "phase1_or_skip", lambda *a, **k: {"ok": False, "attempts": 2, "missing": ["missing key `where`"]})
    task = {"id": "NB-1", "key": "NB-1", "handoff": "handoffs/active/h.md", "repo": "epyc-root", "kind": "code",
            "tier": "terra", "goal": BOX, "text_sha": "x", "budget": {"turns": 8, "wall_s": 300}}
    row = dispatch.run([task], "http://x/v1", tmp_path / "out", apply=False, use_reviewer=False)[0]
    assert row["verdict"] == "needs-brief" and row["tag"]["tagged"] and row["tag"]["branch"].startswith("taskflow/needs-brief/NB-1")
    assert "· NEEDS-BRIEF:" in _git(root, "show", f"{row['tag']['branch']}:handoffs/active/h.md")
