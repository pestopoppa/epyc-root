"""PM-CODEX-LANE-VERDICT: drive.py verdicts are judged from git artifacts. Fake codex, temp repos, no real Codex."""
from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "codex_lane_drive", Path(__file__).resolve().parents[1] / "codex_lane" / "drive.py")
drive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(drive)

FAKE = r"""#!/bin/bash
# fake codex: emits a thread id, then runs $FAKE_DIR/round_<n>.sh (n = call count, 0 = initial exec)
n=$(cat "$FAKE_DIR/count" 2>/dev/null || echo 0)
echo $((n+1)) > "$FAKE_DIR/count"
cat > /dev/null
echo '{"type":"thread.started","thread_id":"tid-123"}'
[ -f "$FAKE_DIR/round_$n.sh" ] && bash "$FAKE_DIR/round_$n.sh"
exit 0
"""


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout.strip()


def commit(repo, msg):
    (Path(repo) / f"{msg}.txt").write_text(msg)
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", msg, "--no-verify")
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def env(tmp_path, monkeypatch):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    repo = tmp_path / "repo"
    subprocess.run(["git", "clone", "-q", str(origin), str(repo)], check=True, capture_output=True)
    git(repo, "checkout", "-qb", "main")
    commit(repo, "base")
    git(repo, "push", "-q", "origin", "main")
    git(repo, "checkout", "-qb", "lane-b1")
    d = tmp_path / "lanes"
    d.mkdir()
    (d / "L.prompt").write_text("do it")
    fake = tmp_path / "codex"
    fake.write_text(FAKE)
    fake.chmod(0o755)
    monkeypatch.setenv("FAKE_DIR", str(d))
    monkeypatch.setenv("CODEX_LANE_NO_NICE", "1")
    return {"repo": repo, "d": d, "codex": str(fake), "repos": {"r": str(repo)}}


def round_script(e, n, body):
    (e["d"] / f"round_{n}.sh").write_text(body)


def commit_cmd(e, msg):
    r = e["repo"]
    return (f"echo {msg} > {r}/{msg}.txt; git -C {r} add -A; "
            f"git -C {r} -c user.name=t -c user.email=t@t commit -qm {msg} --no-verify\n")


def done_report_cmd(e, box="B1", branch="lane-b1", sha_expr=None):
    r = e["repo"]
    sha = sha_expr or f"$(git -C {r} rev-parse HEAD)"
    return f'printf "LANE-STATUS: DONE\\n{box} r {branch} %s\\n" "{sha}" > {e["d"]}/L-REPORT.md\n'


def run(e, **kw):
    return drive.drive("L", e["d"], e["repos"], [("r", "lane-b1")], kw.get("max_rounds", 8),
                       kw.get("push", False), e["codex"])


def log(e):
    return (e["d"] / "L-drive.log").read_text()


def test_early_exit_then_done(env):
    round_script(env, 0, commit_cmd(env, "wip"))           # initial exec exits early, no status
    round_script(env, 1, commit_cmd(env, "b1") + done_report_cmd(env))
    assert run(env) == 0
    lg = log(env)
    assert "resume round 1" in lg and "VERDICT DONE" in lg and "wall=" in lg
    assert "resume round 2" not in lg


def test_claimed_done_without_commit_is_not_done(env):
    fake_sha = "deadbeef" * 5
    report = f"LANE-STATUS: DONE\nB1 r lane-b1 {fake_sha}\n"
    assert drive.lane_verdict(report, env["repos"]) == "CONTINUE"
    # commit exists but on another branch
    git(env["repo"], "checkout", "-qb", "other")
    sha = commit(env["repo"], "elsewhere")
    assert drive.lane_verdict(f"LANE-STATUS: DONE\nB1 r lane-b1 {sha}\n", env["repos"]) == "CONTINUE"
    # DONE with no box lines at all
    assert drive.lane_verdict("LANE-STATUS: DONE\n", env["repos"]) == "CONTINUE"
    # driver keeps resuming, then stalls (no new commits)
    round_script(env, 0, f'printf "LANE-STATUS: DONE\\nB1 r lane-b1 {fake_sha}\\n" > {env["d"]}/L-REPORT.md\n')
    assert run(env) == 4
    assert "artifacts disagree" in log(env) and "VERDICT STALLED" in log(env)


def test_blocked_needs_concrete_blocker(env):
    assert drive.lane_verdict("LANE-STATUS: BLOCKED I am unsure\n", env["repos"]) == "CONTINUE"
    v = drive.lane_verdict("LANE-STATUS: BLOCKED scripts/x.py raises ImportError\n", env["repos"])
    assert v.startswith("BLOCKED ") and "ImportError" in v
    round_script(env, 0, f'echo "LANE-STATUS: BLOCKED `rowflow.py claim` exit code 2" > {env["d"]}/L-REPORT.md\n')
    assert run(env) == 1
    assert "VERDICT BLOCKED" in log(env)


def test_stalled_after_three_rounds(env):
    assert run(env) == 4
    lg = log(env)
    assert "resume round 3" in lg and "resume round 4" not in lg and "VERDICT STALLED" in lg
    assert drive.lane_verdict("", env["repos"], stall_rounds=2) == "CONTINUE"
    assert drive.lane_verdict("", env["repos"], stall_rounds=3) == "STALLED"


def test_commit_resets_stall(env):
    for n in (1, 2, 4):
        round_script(env, n, commit_cmd(env, f"c{n}"))
    round_script(env, 6, commit_cmd(env, "fin") + done_report_cmd(env))
    assert run(env) == 0
    assert "resume round 6" in log(env)


def test_push_mode_requires_origin_main_reachability(env):
    sha = commit(env["repo"], "b1")
    report = f"LANE-STATUS: DONE\nB1 r lane-b1 {sha}\n"
    assert drive.lane_verdict(report, env["repos"]) == "DONE"
    assert drive.lane_verdict(report, env["repos"], push=True) == "CONTINUE"
    git(env["repo"], "push", "-q", "origin", "lane-b1:main")
    git(env["repo"], "fetch", "-q", "origin")
    assert drive.lane_verdict(report, env["repos"], push=True) == "DONE"


def test_multi_box_all_must_verify(env):
    s1 = commit(env["repo"], "b1")
    report = f"LANE-STATUS: DONE\nB1 r lane-b1 {s1}\nB2 r lane-b2 {s1}\n"
    assert drive.lane_verdict(report, env["repos"]) == "CONTINUE"
    git(env["repo"], "branch", "lane-b2")
    assert drive.lane_verdict(report, env["repos"]) == "DONE"


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: "
                     "python -m pytest scripts/coordination/tests/test_codex_lane_drive.py -q")
