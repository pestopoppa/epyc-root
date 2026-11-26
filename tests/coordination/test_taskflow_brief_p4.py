"""Task-brief layer P4 (docs/design/task-brief-layer.md §5/§11): the two-phase run (self-brief then execute), D3
acceptance (pending holds the tick), the NEEDS-BRIEF skip, the acceptance-vs-done-when lint, and the reviewer input."""
import io
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
sys.path.insert(0, str(ROOT / "scripts" / "handoffs"))
from taskflow import brief as B, dispatch, schema, verify  # noqa: E402
import box_index  # noqa: E402
import task_lint  # noqa: E402

BOX = "- [ ] **BR-2** [non-inference] make `parse` in `scripts/x.py` strip whitespace"
TEST = "pytest -q -p no:cacheprovider tests/test_x.py"


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout.strip()


def _repo(tmp_path, done_when=TEST):
    r = tmp_path / "root"
    (r / "handoffs/active").mkdir(parents=True)
    (r / "handoffs/active/h.md").write_text(
        f"# H\n## Track: T\n### Backlog\n{BOX}\n      · done when: `{done_when}`\n      · gate: none\n")
    (r / "scripts").mkdir()
    (r / "scripts/x.py").write_text("def parse(s):\n    return s\n")
    (r / "tests").mkdir()
    (r / "tests/test_x.py").write_text("import sys; sys.path.insert(0, 'scripts')\nfrom x import parse\n\n"
                                       "def test_strip():\n    assert parse(' a ') == 'a'\n")
    (r / ".gitignore").write_text("handoffs/active/briefs/.compile-cache.json\n__pycache__/\n")
    _git(tmp_path, "init", "-q", str(r))
    _git(r, "config", "user.email", "t@t"); _git(r, "config", "user.name", "t")
    _git(r, "add", "."); _git(r, "commit", "-qm", "base")
    _git(r, "update-ref", "refs/remotes/origin/main", "HEAD")
    return r


def _fake_spawn(acceptance):
    calls = []

    def spawn(task, cwd, run_dir, base_url, family="local", timeout_s=None):
        calls.append(task.get("phase") or "exec")
        w = {"model": "fake", "rc": 0, "timed_out": False, "wall_s": 0.1, "errors": [], "tools": ["edit"],
             "tool_errors": [], "edits": 1, "nudged": False, "usage": {"input": 1, "output": 1, "cache_read": 0,
                                                                         "steps": 2}}
        if task.get("phase") == "brief":
            assert "## WRITE BRIEF FIRST" in dispatch.local_llm.task_suffix(task, {})
            return dict(w, result=None, brief={"where": ["epyc-root:scripts/x.py::parse"],
                                                "approach": "strip surrounding whitespace inside parse before returning", "acceptance": acceptance,
                                                "non_goals": ["do not rename parse"]})
        assert task["brief_state"] in ("fresh", "drift") and task["where"]            # phase 2 sees the brief
        (Path(cwd) / "scripts/x.py").write_text("def parse(s):\n    return s.strip()\n")
        return dict(w, result={"claimed_done": True, "summary": "strip", "paths": ["scripts/x.py"]})
    spawn.calls = calls
    return spawn


def _run(tmp_path, monkeypatch, root, spawn, apply=True):
    monkeypatch.setitem(schema.REPOS, "epyc-root", root)
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(tmp_path / "tf"))
    monkeypatch.setenv(B.GITNEXUS_ENV, "")
    B._GN_STATUS.clear()
    monkeypatch.setattr(dispatch.local_llm, "spawn", spawn)
    monkeypatch.setattr(dispatch, "MIN_FREE_GIB", 0)
    ticks = []
    monkeypatch.setattr(dispatch, "apply_tick", lambda *a: ticks.append(a) or "ticked")
    rec = {"file": "handoffs/active/h.md", "line": 4, "id": "BR-2", "class": "non-inference",
           "text_sha": schema.text_sha(BOX)}
    task = schema.build(rec, root=root)
    assert task["brief_state"] == "none"
    task.update(kind="code", tier="terra")
    rows = dispatch.run([task], "http://x/v1", tmp_path / "out", apply=apply, use_reviewer=False)
    return rows[0], ticks


def _lane_log(root, row):
    branch = [b for b in _git(root, "branch", "--format=%(refname:short)").split() if b.startswith("taskflow/")]
    return _git(root, "log", "--format=%s", "--name-only", f"origin/main..{branch[0]}") if branch else ""


def test_fixture_run_commits_brief_then_diff_auto_accepted(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    spawn = _fake_spawn(TEST)                                     # acceptance == the literal done-when -> auto
    row, ticks = _run(tmp_path, monkeypatch, root, spawn)
    assert spawn.calls == ["brief", "exec"]
    assert row["brief_phase"]["ok"] and row["brief_phase"]["accepted"] == "auto"
    assert row["verdict"] == "verified", row
    assert "held" not in row and ticks                            # auto -> ticked
    diff = (tmp_path / "out/t00/diff.patch").read_text()
    assert "handoffs/active/briefs/BR-2.md" in diff and "s.strip()" in diff
    log = _lane_log(root, row).split("\n")                        # newest first: worker draft, then the brief
    subjects = [ln for ln in log if ln.startswith("taskflow:")]
    assert subjects[0].startswith("taskflow: BR-2") and subjects[1].startswith("taskflow: brief BR-2 (author: self")
    brief_files = log[log.index(subjects[1]) + 1:]
    assert [f for f in brief_files if f] == ["handoffs/active/briefs/BR-2.md"]    # brief committed ALONE, first
    doc = B.parse_text(_git(root, "show", f"{_lane_branch(root)}:handoffs/active/briefs/BR-2.md") + "\n")
    assert doc["author"] == "self" and doc["review"] == "backfill" and doc["accepted"] == "auto"


def _lane_branch(root):
    return [b for b in _git(root, "branch", "--format=%(refname:short)").split() if b.startswith("taskflow/")][0]


def test_pending_acceptance_holds_the_tick(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    spawn = _fake_spawn("pytest -q -p no:cacheprovider tests/test_x.py::test_strip")   # not literal -> pending
    row, ticks = _run(tmp_path, monkeypatch, root, spawn)
    assert row["brief_phase"]["accepted"] == "pending"
    assert row["verdict"] == "verified" and row["held"] == "accepted-pending" and not ticks


def test_acceptance_passing_on_unchanged_tree_is_rejected_then_needs_brief(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    spawn = _fake_spawn("python3 scripts/x.py")                    # passes before any change: proves nothing
    row, ticks = _run(tmp_path, monkeypatch, root, spawn)
    assert spawn.calls == ["brief", "brief"] and row["verdict"] == "needs-brief"
    assert "already passes" in row["reason"] and not ticks


def test_needs_brief_tag_skips_and_missing_brief_does_not():
    rec = {"state": "open", "class": "non-inference", "lint": {"ok": True}, "file": "h.md"}
    assert box_index.skip_reason(dict(rec, brief="none")) is None              # local boxes self-brief
    assert box_index.skip_reason(dict(rec, brief="none", tier="sol")) is None  # no design rule gates cloud tiers
    assert box_index.skip_reason(dict(rec, needs_brief=True)) == "needs-brief"


def test_acceptance_vs_done_when_lint():
    assert task_lint.acceptance_rule({"acceptance_matches_done_when": True, "accepted": "auto"}) is None
    assert task_lint.acceptance_rule({"acceptance_matches_done_when": False, "accepted": "auto"}) == "k-accept-auto"
    assert task_lint.acceptance_rule({"acceptance_matches_done_when": False, "accepted": "pending"}) == "k-acceptance"
    assert task_lint.acceptance_rule({"acceptance_matches_done_when": False, "accepted": "owner"}) is None
    assert task_lint.DIFF_GATE_RULE_MODES["k-accept-auto"] == "enforce"


def test_reviewer_request_contains_acceptance_non_goals_and_full_diff(tmp_path, monkeypatch):
    lane = tmp_path / "lane"
    lane.mkdir()
    _git(tmp_path, "init", "-q", str(lane))
    _git(lane, "config", "user.email", "t@t"); _git(lane, "config", "user.name", "t")
    (lane / "a.py").write_text("x=1\n"); _git(lane, "add", "."); _git(lane, "commit", "-qm", "b")
    base = _git(lane, "rev-parse", "HEAD")
    (lane / "a.py").write_text("# " + "a" * 12000 + "\nx=2\n"); _git(lane, "commit", "-qam", "w")
    seen = {}

    def complete(req, timeout):
        seen["p"] = json.loads(req.data)["messages"][0]["content"]
        reply = {"choices": [{"message": {"content": '{"verdict":"done"}'}}]}
        return io.BytesIO(json.dumps(reply).encode())

    monkeypatch.setattr(dispatch.urllib.request, "urlopen", complete)
    reviewer = dispatch.reviewer_for("http://review.invalid/v1", "fixture")
    t = {"goal": "- [ ] **R-1** set x", "inputs": ["a.py"], "outputs": [], "forbidden": [], "test_cmds": [],
         "done_when": "x is 2 in a.py", "acceptance": "python3 a.py", "non_goals": ["do not touch b.py"],
         "brief_accepted": "pending"}
    v = verify.verify(t, lane, base, reviewer=reviewer)
    p = seen["p"]
    assert "## DONE WHEN\nx is 2 in a.py" in p and "## ACCEPTANCE\npython3 a.py" in p
    assert "## ACCEPTANCE RESULT\nrc=0" in p and "- do not touch b.py" in p
    diff = p.split("\n\n## DIFF\n", 1)[1]
    assert diff.index("+x=2\n") > 12000
    assert diff.rstrip() == _git(lane, "diff", f"{base}..HEAD")
    assert v["verdict"] == "verified" and v["hold"] == "accepted-pending" and v["evidence"]["acceptance"]["rc"] == 0
