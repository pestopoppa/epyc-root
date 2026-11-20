"""Cross-repo lanes run the brief phase too: the worker reads the code in the other repo's lane, the dispatcher writes
and commits `handoffs/active/briefs/<ID>.md` in a separate epyc-root worktree before phase 2, and an existing brief
reaches the packet fresh (read from epyc-root origin/main, not from the possibly stale plan)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
sys.path.insert(0, str(ROOT / "scripts" / "handoffs"))
from taskflow import brief as B, dispatch, schema  # noqa: E402

BOX = "- [ ] **XR-1** [non-inference] make `parse` in `scripts/x.py` of epyc-orchestrator strip whitespace"
TEST = "pytest -q -p no:cacheprovider tests/test_x.py"


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout.strip()


def _init(tmp_path, name):
    r = tmp_path / name
    r.mkdir()
    _git(tmp_path, "init", "-q", str(r))
    _git(r, "config", "user.email", "t@t"); _git(r, "config", "user.name", "t")
    return r


def _commit(r, msg="base"):
    _git(r, "add", "."); _git(r, "commit", "-qm", msg)
    _git(r, "update-ref", "refs/remotes/origin/main", "HEAD")


def _repos(tmp_path):
    root, orch = _init(tmp_path, "root"), _init(tmp_path, "orch")
    (root / "handoffs/active").mkdir(parents=True)
    (root / "handoffs/active/h.md").write_text(
        f"# H\n## Track: T\n### Backlog\n{BOX}\n      · done when: `{TEST}`\n      · gate: none\n")
    (root / ".gitignore").write_text("handoffs/active/briefs/.compile-cache.json\n__pycache__/\n")
    _commit(root)
    (orch / "scripts").mkdir(); (orch / "tests").mkdir()
    (orch / "scripts/x.py").write_text("def parse(s):\n    return s\n")
    (orch / "tests/test_x.py").write_text("import sys; sys.path.insert(0, 'scripts')\nfrom x import parse\n\n"
                                          "def test_strip():\n    assert parse(' a ') == 'a'\n")
    (orch / ".gitignore").write_text("__pycache__/\n")
    _commit(orch)
    return root, orch


def _w(**kw):
    return {"model": "fake", "rc": 0, "timed_out": False, "wall_s": 0.1, "errors": [], "tools": ["edit"],
            "tool_errors": [], "edits": 1, "nudged": False,
            "usage": {"input": 1, "output": 1, "cache_read": 0, "steps": 2}, **kw}


def _setup(tmp_path, monkeypatch, root, orch, spawn):
    monkeypatch.setitem(schema.REPOS, "epyc-root", root)
    monkeypatch.setitem(schema.REPOS, "epyc-orchestrator", orch)
    monkeypatch.setitem(B.REPOS, "epyc-orchestrator", orch)
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(tmp_path / "tf"))
    monkeypatch.setenv(B.GITNEXUS_ENV, "")
    B._GN_STATUS.clear()
    monkeypatch.setattr(dispatch.local_llm, "spawn", spawn)
    monkeypatch.setattr(dispatch, "MIN_FREE_GIB", 0)
    monkeypatch.setattr(dispatch, "apply_tick", lambda *a: "ticked")
    rec = {"file": "handoffs/active/h.md", "line": 4, "id": "XR-1", "class": "non-inference",
           "text_sha": schema.text_sha(BOX)}
    task = schema.build(rec, root=root)
    task.update(repo="epyc-orchestrator", kind="code", tier="terra")
    return task


def _exec(cwd):
    (Path(cwd) / "scripts/x.py").write_text("def parse(s):\n    return s.strip()\n")
    return _w(result={"claimed_done": True, "summary": "strip", "paths": ["scripts/x.py"]})


def test_cross_repo_lane_self_briefs_and_commits_brief_in_root_worktree(tmp_path, monkeypatch):
    root, orch = _repos(tmp_path)
    calls = []

    def spawn(task, cwd, run_dir, base_url, family="local", timeout_s=None):
        calls.append((task.get("phase") or "exec", Path(cwd).resolve()))
        if task.get("phase") == "brief":
            return _w(result=None, brief={"where": ["epyc-orchestrator:scripts/x.py::parse"], "approach": "strip",
                                          "acceptance": TEST, "non_goals": ["do not rename parse"]})
        assert task["brief_state"] in ("fresh", "drift") and task["where"] == ["epyc-orchestrator:scripts/x.py::parse"]
        return _exec(cwd)
    task = _setup(tmp_path, monkeypatch, root, orch, spawn)
    assert task["brief_state"] == "none"
    row = dispatch.run([task], "http://x/v1", tmp_path / "out", apply=False, use_reviewer=False)[0]
    assert [c[0] for c in calls] == ["brief", "exec"]
    assert row["brief_phase"]["ok"] and not row["brief_phase"].get("skipped") and row["brief_phase"]["accepted"] == "auto"
    assert row["verdict"] == "verified", row
    # the brief is committed ALONE in an epyc-root branch; the orchestrator lane carries only the code change
    bb = [b for b in _git(root, "branch", "--format=%(refname:short)").split() if b.startswith("taskflow/brief/XR-1")]
    assert len(bb) == 1
    assert _git(root, "diff", "--name-only", f"origin/main..{bb[0]}") == "handoffs/active/briefs/XR-1.md"
    doc = B.parse_text(_git(root, "show", f"{bb[0]}:handoffs/active/briefs/XR-1.md") + "\n")
    assert doc["author"] == "self" and doc["review"] == "backfill" and doc["accepted"] == "auto"
    ob = [b for b in _git(orch, "branch", "--format=%(refname:short)").split() if b.startswith("taskflow/")][0]
    assert _git(orch, "diff", "--name-only", f"origin/main..{ob}") == "scripts/x.py"
    assert list((tmp_path / "tf").glob("*.lane.json")) == [] or all(
        '"state": "live"' not in m.read_text() for m in (tmp_path / "tf").glob("*.lane.json"))   # brief lane removed
    assert "handoffs/active/briefs" not in _git(root, "status", "--porcelain")                  # shared clone untouched


def test_cross_repo_failed_self_brief_ends_needs_brief(tmp_path, monkeypatch):
    root, orch = _repos(tmp_path)
    calls = []

    def spawn(task, cwd, run_dir, base_url, family="local", timeout_s=None):
        calls.append(task.get("phase") or "exec")
        return _w(result=None, brief={"approach": "x"})                       # no where / acceptance, twice
    task = _setup(tmp_path, monkeypatch, root, orch, spawn)
    row = dispatch.run([task], "http://x/v1", tmp_path / "out", apply=False, use_reviewer=False)[0]
    assert calls == ["brief", "brief"] and row["verdict"] == "needs-brief"
    assert row["tag"]["tagged"]
    assert "· NEEDS-BRIEF:" in _git(root, "show", f"{row['tag']['branch']}:handoffs/active/h.md")


def test_existing_brief_reaches_cross_repo_worker_even_with_a_stale_plan(tmp_path, monkeypatch):
    root, orch = _repos(tmp_path)
    calls = []

    def spawn(task, cwd, run_dir, base_url, family="local", timeout_s=None):
        calls.append(task.get("phase") or "exec")
        assert task.get("phase") != "brief"
        assert task["brief_state"] == "fresh" and task["approach"] == "strip in parse"
        assert task["where"] == ["epyc-orchestrator:scripts/x.py::parse"] and task["non_goals"] == ["keep the name"]
        return _exec(cwd)
    task = _setup(tmp_path, monkeypatch, root, orch, spawn)       # packet planned BEFORE the brief existed
    monkeypatch.setitem(B.REPOS, "epyc-orchestrator", orch)
    B.write_brief("XR-1", ["epyc-orchestrator:scripts/x.py::parse"], "strip in parse", TEST, ["keep the name"],
                  author="owner", accepted="owner", root=root)
    _commit(root, "brief")
    assert task["brief_state"] == "none"
    row = dispatch.run([task], "http://x/v1", tmp_path / "out", apply=False, use_reviewer=False)[0]
    assert calls == ["exec"] and row["verdict"] == "verified", row
    assert "brief_phase" not in row                                 # nothing to self-brief
