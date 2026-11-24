#!/usr/bin/env python3
"""AK row-robustness RCA 2026-11-24, pipeline-owned items 1, 2, 4, 6 (no compute; tmp flags dirs only)."""
import json
import os
import subprocess
import sys
import time

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
_ROWFLOW = os.path.join(os.path.dirname(_TESTS), "rowflow")
sys.path.insert(0, _ROWFLOW)
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "akloop"))
_REPO = os.path.abspath(os.path.join(_TESTS, "..", "..", ".."))
sys.path.insert(0, os.path.join(_REPO, ".claude", "skills", "inference-backlog-scheduling", "scripts"))

import failclass  # noqa: E402
import owner_watch  # noqa: E402
import publish_row as PR  # noqa: E402
import queue_status as QS  # noqa: E402
import rowflow as rf  # noqa: E402
import smoke_verdict as SV  # noqa: E402
import supersedes_check as SC  # noqa: E402


def wj(p, d):
    os.makedirs(os.path.dirname(str(p)), exist_ok=True)
    with open(p, "w") as f:
        json.dump(d, f)


# ---------------------------------------------------------------- item 2: smoke verdict semantics
def q4kv_row(tmp_path):
    """Regression fixture: ak-gvfattn-q4kv-gpu-20261124 (ON arm q4_0_ok 10 vs OFF 12, complete:true, 37 s)."""
    d = tmp_path / "ak-gvfattn-q4kv-gpu-20261124"
    wj(d / "out-smoke" / "RESULT.json", {"complete": True, "verdict": "FUTILITY_CORRECTNESS", "smoke": True,
                                         "correct": {"ON": {"q4_0_ok": 10}, "OFF": {"q4_0_ok": 12}}})
    wj(d / "out-smoke" / "TERMINAL-smoke.json", {"verdict": "FAIL", "rc": 3, "ok": False,
                                                 "reason": "FUTILITY_CORRECTNESS: see out-smoke/RESULT.json"})
    return d, {"id": d.name, "owner": "autokernel", "scratch_root": str(d), "workdir": str(d),
               "result_path": str(d / "out" / "RESULT.json")}


def test_terminal_smoke_result_q4kv(tmp_path):
    d, row = q4kv_row(tmp_path)
    t0 = time.time() - 37
    tr = SV.terminal_smoke_result(row, t0)
    assert tr and tr["verdict"] == "FUTILITY_CORRECTNESS" and tr["path"].endswith("out-smoke/RESULT.json")
    assert SV.terminal_smoke_result(row, time.time() + 60) is None      # older than this smoke: not its verdict


@pytest.mark.parametrize("v,ok", [("FUTILITY_CORRECTNESS", True), ("FAIL_CORRECTNESS", True), ("PASS", True),
                                  ("PASS_CORRECTNESS", True), ("FAIL", False), ("SMOKE_OK", False), ("", False)])
def test_terminal_tokens(v, ok):
    assert SV.is_terminal(v) is ok


def test_incomplete_result_is_not_terminal(tmp_path):
    d, row = q4kv_row(tmp_path)
    wj(d / "out-smoke" / "RESULT.json", {"complete": False, "verdict": "FUTILITY_CORRECTNESS"})
    assert SV.terminal_smoke_result(row, 0) is None


def test_record_smoke_result_files_result_not_fail(tmp_path, monkeypatch):
    flags = tmp_path / "flags"
    d, row = q4kv_row(tmp_path)
    launcher = d / "launch.sh"
    launcher.write_text("true\n")
    row["launcher"] = {"path": str(launcher)}
    os.makedirs(rf.dry_dir(str(flags), row["id"]))
    sent = []
    monkeypatch.setattr(rf.notify, "emit", lambda *a, **k: sent.append(a[1]))
    tr = SV.terminal_smoke_result(row, 0)
    v, msg = rf.record_smoke_result(str(flags), row["id"], row, tr, "job ended rc=3", {"elapsed_s": 37}, rf.sha256(str(launcher)))
    assert v == "RESULT" and "FUTILITY_CORRECTNESS" in msg
    assert not rf.fail_paths(str(flags), row["id"])                    # no FAIL-N, no "fix and republish"
    sr = rf.load_json(rf.smoke_result_path(str(flags), row["id"]))
    assert sr["verdict"] == "FUTILITY_CORRECTNESS" and "do not republish" in sr["file_task"]
    assert sent == ["smoke-result"]
    st = rf._status_raw(str(flags), row["id"], {row["id"]: dict(row, lane="gpu")})
    assert st["state"] == "done" and "FUTILITY_CORRECTNESS" in st["reason"]


def test_smoke_result_is_no_strike(tmp_path):
    flags = str(tmp_path)
    PR.record_smoke_outcome(flags, "x-r1", "RESULT", "terminal")
    assert int(PR.smoke_strikes(flags, "x-r1").get("count") or 0) == 0


def test_failclass_terminal_smoke_is_a_verdict():
    rec = {"id": "ak-gvfattn-q4kv-gpu-20261124", "reason": "job ended rc=3 reason=job-rc-3:exited",
           "launcher_out_tail": ["FUTILITY_CORRECTNESS"],
           "smoke_result": {"verdict": "FUTILITY_CORRECTNESS", "result_path": "/x/out-smoke/RESULT.json"}}
    c = failclass.classify_fail(rec)
    assert c.side == "candidate" and c.klass == "correctness_gate" and c.rule == "result:smoke-terminal-verdict"
    rec.pop("smoke_result")   # without the terminal record the old rules still apply
    assert failclass.classify_fail(rec).rule != "result:smoke-terminal-verdict"


# ---------------------------------------------------------------- item 4: computed supersedes
def test_supersedes_gvfattn_served_r3_omits_r1(tmp_path):
    flags = str(tmp_path)
    fam = "ak-gvfattn-served-gpu-20261124"
    wj(os.path.join(flags, "dryrun", fam, "PASS.json"), {"id": fam})              # r1: GRANTABLE with a PASS
    wj(os.path.join(flags, "ready", fam + ".json"), {"id": fam, "owner": "autokernel"})
    wj(os.path.join(flags, "ready", ".superseded", fam + ".json"), {"by": fam + "-r2"})
    wj(os.path.join(flags, "dryrun", fam + "-r2", "unpublished.json"), {"id": fam + "-r2"})
    wj(os.path.join(flags, "ready", "other-row-r1.json"), {"id": "other-row-r1"})
    missing, msg = SC.check({"id": fam + "-r3", "supersedes": fam + "-r2"}, flags)
    assert list(missing) == [fam] and "SUPERSEDES-INCOMPLETE" in msg and fam in msg
    assert SC.check({"id": fam + "-r3", "supersedes": [fam, fam + "-r2"]}, flags) == ({}, None)
    assert SC.check({"id": fam + "-r2", "supersedes": [fam]}, flags) == ({}, None)   # r3 is not a predecessor of r2


def test_supersedes_warn_first(tmp_path, capsys):
    flags = str(tmp_path)
    wj(os.path.join(flags, "ready", "fam-x.json"), {"id": "fam-x"})
    spec = {"id": "fam-x-r2"}
    assert SC.SUPERSEDES_ENFORCE is False
    assert "fam-x" in PR.check_supersedes(spec, flags)                # warns, never raises
    assert any("SUPERSEDES-INCOMPLETE" in w for w in spec["publish_warnings"])


def test_supersedes_done_rows_not_live(tmp_path):
    flags = str(tmp_path)
    wj(os.path.join(flags, "dryrun", "fam-y", "PASS.json"), {})
    os.makedirs(os.path.join(flags, "grants"))
    open(os.path.join(flags, "grants", "fam-y.ended"), "w").close()
    assert SC.check({"id": "fam-y-r2"}, flags) == ({}, None)


# ---------------------------------------------------------------- item 6a: busy_fraction false positive
def test_busy_flag_suppressed_before_first_progress():
    # ak-c21-census-refresh-cpu: 10 s crash, declared 1, measured 0
    assert rf.busy_flag(1.0, 0.0, elapsed_s=10, first_progress_s=600, progressed=False) is None
    assert rf.busy_flag(1.0, 0.0, elapsed_s=10, first_progress_s=600, progressed=True)   # a progressed smoke is judged
    assert rf.busy_flag(1.0, 0.0, elapsed_s=700, first_progress_s=600, progressed=False)
    assert rf.busy_flag(1.0, 0.0)                                      # old callers unchanged


# ---------------------------------------------------------------- item 6b: owner-watcher liveness
def test_owner_watcher_dead_once_per_change(tmp_path):
    flags = str(tmp_path)
    rows = {"a": {"owner": "autokernel"}, "b": {"owner": "never-watched"}}
    hb = os.path.join(owner_watch.hb_dir(flags), "autokernel.hb")
    os.makedirs(os.path.dirname(hb))
    open(hb, "w").close()
    now = time.time()
    os.utime(hb, (now - 900, now - 900))
    sent, logs = [], []

    class N:
        @staticmethod
        def emit(*a, **k):
            sent.append(a[1])
    assert owner_watch.check(flags, rows, N, logs.append, now=now) == ["autokernel"]
    assert sent == ["owner-watcher-dead"]
    assert sum("OWNER-WATCHER-NONE never-watched" in x for x in logs) == 1
    assert owner_watch.check(flags, rows, N, logs.append, now=now + 60) == []   # once per change
    assert sum("OWNER-WATCHER-NONE" in x for x in logs) == 1                    # INFO logged once
    os.utime(hb, (now + 100, now + 100))
    assert owner_watch.check(flags, rows, N, logs.append, now=now + 120) == []  # fresh: re-armed
    assert owner_watch.check(flags, rows, N, logs.append, now=now + 100 + 700) == ["autokernel"]
    assert owner_watch.check(flags, {}, N, logs.append, now=now + 2000) == []   # no live rows: no alert


def test_watch_rows_touches_heartbeat():
    src = open(os.path.join(_REPO, ".claude", "skills", "row-owner-loop", "scripts", "watch_rows.sh")).read()
    loop = src[src.index("while true; do\n  touch"):]
    assert 'touch "$HB_DIR/$OWNER.hb"' in loop and "state/owner-watch" in src


# ---------------------------------------------------------------- item 1: KEEPER-STALE
def _git(repo, *a):
    subprocess.run(["git", "-C", repo, *a], check=True, capture_output=True,
                   env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                            GIT_COMMITTER_EMAIL="t@t"))
    return subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def test_keeper_stale(tmp_path):
    repo = str(tmp_path / "repo")
    os.makedirs(os.path.join(repo, "scripts/coordination/rowflow"))
    subprocess.run(["git", "init", "-q", repo], check=True)
    f = os.path.join(repo, QS.ROWFLOW_REL)
    open(f, "w").write("a\nb\n")
    _git(repo, "add", "-A")
    dep = _git(repo, "commit", "-qm", "one", "--no-verify")
    flags = str(tmp_path / "flags")
    wj(os.path.join(flags, "bin", "rowflow", "DEPLOYED.json"), {"sha": dep})
    open(os.path.join(flags, "bin", "rowflow", "rowflow.py"), "w").write("a\nb\n")
    _git(repo, "update-ref", "refs/remotes/origin/main", dep)
    assert QS.keeper_stale(flags, repo) is None
    open(f, "w").write("a\nB\nc\n")
    _git(repo, "add", "-A")
    head = _git(repo, "commit", "-qm", "two", "--no-verify")
    _git(repo, "update-ref", "refs/remotes/origin/main", head)
    assert QS.keeper_stale(flags, repo) == f"KEEPER-STALE deployed={dep[:9]} head={head[:9]} (3 lines differ)"
    os.remove(os.path.join(flags, "bin", "rowflow", "DEPLOYED.json"))
    assert QS.keeper_stale(flags, repo) is None                        # unknown: never guesses
