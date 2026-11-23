"""r8f harness fixes from the r8e CPU canary (2026-11-23, FIX-HARNESS, audited 6/10;
docs/design/taskflow-stage1-canary-findings.md r8e)."""
import fnmatch
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
from taskflow import schema  # noqa: E402
from taskflow.harness import local_llm as L  # noqa: E402

ROW = "/mnt/raid0/llm/tmp/taskflow-stage1-cpu-r8f-20261123"
LANE = "/mnt/raid0/llm/tf/ab12"


def _bash(tmp_path, monkeypatch, acceptance=f"bash {ROW}/orch-py.sh -m pytest -q tests/unit/test_a.py"):
    monkeypatch.setattr(L, "POLICY_DIR", tmp_path / "pol")
    t = {"repo": "epyc-orchestrator", "budget": dict(schema.DEFAULT_BUDGET), "acceptance": acceptance}
    return json.loads(L.write_config(tmp_path, "http://x/v1", "m", t, lane=LANE).read_text())["agent"][L.AGENT]["permission"]["bash"]


def _ok(bash, cmd):   # opencode: last matching pattern wins; deny entries are written last, so any deny wins
    return (any(fnmatch.fnmatchcase(cmd, p) for p, v in bash.items() if v == "allow" and p != "*")
            and not any(fnmatch.fnmatchcase(cmd, p) for p, v in bash.items() if v == "deny" and p != "*"))


# ------------------------------------------------------------------------- fix 1: orch-py.sh -c / lane .py
def test_orch_py_c_and_lane_script_allowed(tmp_path, monkeypatch):
    b = _bash(tmp_path, monkeypatch)
    assert _ok(b, f'bash {ROW}/orch-py.sh -c "import x; print(x.__file__)"')            # r8e LOOP-62 one-line probe
    assert _ok(b, f"{ROW}/orch-py.sh -c 'print(1)'")
    assert _ok(b, f"bash {ROW}/orch-py.sh tests/unit/_debug_alias.py")                   # lane-relative script
    assert _ok(b, f"bash {ROW}/orch-py.sh scripts/x.py --flag 2>&1 | tail -20")
    assert _ok(b, f"cd {LANE} && bash {ROW}/orch-py.sh -c 'print(1)'")
    assert _ok(b, f"bash {ROW}/orch-py.sh -m pytest -q tests/unit/test_b.py")            # unchanged


def test_orch_py_deny_list_still_wins(tmp_path, monkeypatch):
    b = _bash(tmp_path, monkeypatch)
    assert not _ok(b, f"bash {ROW}/orch-py.sh /etc/evil.py")                             # absolute script
    assert not _ok(b, f"bash {ROW}/orch-py.sh ../other/x.py")                            # outside the lane
    assert not _ok(b, f"bash {ROW}/orch-py.sh sub/../../x.py")
    assert not _ok(b, f"bash {ROW}/orch-py.sh -c 'print(1)' > out.txt")                  # redirect
    assert not _ok(b, f"bash {ROW}/orch-py.sh -c 'x' | bash")
    assert not _ok(b, "bash /tmp/other/orch-py.sh -c 'print(1)'")                         # another row's runner
    assert not _ok(b, "python3 -c 'print(1)'")                                            # not the row runner


def test_no_orch_runner_no_scratch_patterns(tmp_path, monkeypatch):
    b = _bash(tmp_path, monkeypatch, acceptance="bash scripts/validate/validate_intake.sh")
    assert not any("-c *" in p for p, v in b.items() if v == "allow")


# ------------------------------------------------------------------------- fix 2: rm untracked, drop empty new files
def test_rm_of_lane_relative_path_allowed_flags_and_escapes_denied(tmp_path, monkeypatch):
    b = _bash(tmp_path, monkeypatch)
    assert _ok(b, "rm tests/test_unshare_debug.py")                                       # r8e TU-GR-1 nothink
    assert _ok(b, "rm tests/unit/_debug_alias.py")                                        # r8e LOOP-62 nothink
    for bad in ("rm -rf tests", "rm -f x.py", "rm x.py -r", "rm /etc/passwd", "rm a.py /etc/x", "rm ../x.py",
                "rm sub/../../x", "rm ~/x", "rm .git/index", "rm x; git push", "rm x && git commit -m y",
                "rm $(cat list)", "rm `ls`"):
        assert not _ok(b, bad), bad


def _g(repo, *a):
    import subprocess
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True).stdout


def test_commit_tidy_restores_tracked_deletes_and_drops_empty_scratch(tmp_path):
    from taskflow import dispatch
    r = tmp_path / "lane"
    (r / "tests" / "unit").mkdir(parents=True)
    (r / "keep.py").write_text("x = 1\n")
    _g(r.parent, "init", "-q", "-b", "main", str(r))
    _g(r, "add", "keep.py")
    _g(r, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    (r / "keep.py").unlink()                                       # worker `rm` of a tracked file
    (r / "tests" / "test_unshare_debug.py").write_text("")         # emptied scratch file (r8e TU-GR-1 nothink)
    (r / "tests" / "unit" / "__init__.py").write_text("")          # conventionally empty: kept
    (r / "named.py").write_text("")                                # empty but the packet names it: kept
    (r / "real.py").write_text("y = 2\n")
    task = {"id": "T", "text_sha": "x", "outputs": ["named.py"], "inputs": []}
    assert dispatch.commit_lane(r, task) is True
    rep = dispatch.COMMIT_REPORTS.pop(str(r))
    assert rep == {"restored": ["keep.py"], "dropped_empty": ["tests/test_unshare_debug.py"]}
    files = set(_g(r, "show", "--name-only", "--format=", "HEAD").split())
    assert files == {"real.py", "named.py", "tests/unit/__init__.py"}
    assert (r / "keep.py").read_text() == "x = 1\n"


def test_commit_tidy_only_empty_scratch_means_no_commit(tmp_path):
    from taskflow import dispatch
    r = tmp_path / "lane"
    r.mkdir()
    (r / "a.py").write_text("a = 1\n")
    _g(r.parent, "init", "-q", "-b", "main", str(r))
    _g(r, "add", "a.py")
    _g(r, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    (r / "scratch.py").write_text("")
    assert dispatch.commit_lane(r, {"id": "T", "text_sha": "x"}) is False
    assert dispatch.COMMIT_REPORTS.pop(str(r))["dropped_empty"] == ["scratch.py"]
