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


# ------------------------------------------------------------------------- fix 3: reviewer input + vacuity guard
TUGR1_THINK_DIFF = (Path(__file__).parent / "taskflow_r8e_tugr1_think_diff.patch").read_text()
TUGR1 = {"key": "TU-GR-1", "goal": "- [ ] **TU-GR-1 — Grader isolation clause.** ...",
         "done_when": "the test exists and fails on a deliberately reachable grader",
         "approach": ("Add isolation.py with probe_grader_access(sentinel, launcher). (2) test_isolated_launch_denies: "
                      "launcher=[...] must yield ENOENT/EACCES; if unshare is not permitted, pytest.skip with the errno. "
                      "Never pass vacuously (bwrap is not installed on this host)."),
         "non_goals": ["no isolation or security claim from this test"],
         "acceptance": "bash /r/orch-py.sh -m pytest -q scripts/autopilot/evals/dtap/tests/test_grader_isolation.py"}


def test_vacuity_guard_flags_the_r8e_tugr1_think_transcript():
    from taskflow import verify
    hits = verify.vacuity_hits(TUGR1_THINK_DIFF)
    assert len(hits) == 1 and hits[0].startswith("launcher_error:")
    assert "test_grader_isolation.py" in hits[0]


def test_vacuity_guard_passes_a_test_that_checks_the_errno():
    from taskflow import verify
    fixed = TUGR1_THINK_DIFF.replace(
        '+    assert result.get("ok") is False\n',
        '+    assert "launcher_error" not in result, result\n+    assert result.get("open_errno") in (errno.ENOENT, errno.EACCES)\n')
    assert fixed != TUGR1_THINK_DIFF
    assert verify.vacuity_hits(fixed) == []


def test_vacuity_guard_ignores_docstrings_and_comments():
    from taskflow import verify
    # the r8e test file mentions ENOENT only in its docstring and a comment: that is not a check
    assert "ENOENT" in TUGR1_THINK_DIFF
    assert verify.vacuity_hits(TUGR1_THINK_DIFF)
    assert verify.vacuity_hits("diff --git a/x.py b/x.py\n+++ b/x.py\n+y = 1\n") == []


def test_vacuity_guard_rejects_before_the_reviewer(tmp_path, monkeypatch):
    from taskflow import verify, dispatch
    r = tmp_path / "lane"
    r.mkdir()
    _g(r.parent, "init", "-q", "-b", "main", str(r))
    (r / "a.txt").write_text("a\n")
    _g(r, "add", "a.txt")
    _g(r, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    base = _g(r, "rev-parse", "HEAD").strip()
    _g(r, "apply", str(Path(__file__).parent / "taskflow_r8e_tugr1_think_diff.patch"))
    _g(r, "add", "-A")
    _g(r, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "w")
    called = []
    t = dict(TUGR1, acceptance=None, test_cmds=[], forbidden=[], where=[],
             outputs=["scripts/autopilot/evals/dtap/harness/isolation.py",
                      "scripts/autopilot/evals/dtap/tests/test_grader_isolation.py"], inputs=[])
    v = verify.verify(t, r, base, reviewer=lambda *a: called.append(a) or {"verdict": "done"})
    assert v["verdict"] == "rejected" and v["reason"] == "vacuous-acceptance", v
    assert not called
    w = {"usage": {"steps": 12}, "errors": [], "tools": ["edit"] * 12, "tool_errors": [], "timed_out": False}
    assert dispatch.failure_class(w, v, t) == "model-limitation"


def test_review_prompt_carries_ra_log_and_vacuity_clauses():
    from taskflow import verify
    log = ("..s\nPASSED tests/t.py::test_reachable_grader_is_flagged\n"
           "SKIPPED [1] tests/t.py:40: unshare not available\n=== 1 passed, 1 skipped ===\n")
    ra = verify.ra_lines(log)
    assert ra == ["PASSED tests/t.py::test_reachable_grader_is_flagged", "SKIPPED [1] tests/t.py:40: unshare not available"]
    p = verify.review_prompt(dict(TUGR1, acceptance_result={"rc": 0, "tail": "2 passed", "ra": ra}), "diff")
    assert "ACCEPTANCE LOG (pytest -rA" in p and "SKIPPED [1]" in p
    assert "MUST NOT PASS VACUOUSLY" in p and "Never pass vacuously" in p and "pytest.skip with the errno" in p
    assert "launcher error counted as a denial" in p
    assert "no isolation or security claim" in p          # non-goals still there


def test_acceptance_runs_with_ra():
    from taskflow import verify
    assert verify.with_ra("bash /r/orch-py.sh -m pytest -q t.py") == "bash /r/orch-py.sh -m pytest -q t.py -rA"
    assert verify.with_ra("pytest -q -rfE t.py") == "pytest -q -rfE t.py"
    assert verify.with_ra("bash scripts/validate.sh") == "bash scripts/validate.sh"


# ------------------------------------------------------------------------- fix 4: env-contention vs model on timeout
def _req(ctx, dec, n=200):
    return {"prompt_n": 100, "cache_n": ctx - 100, "decode_tok_s": dec, "predicted_n": n}


def test_timeout_slow_at_matched_context_is_env_contention():
    from taskflow import dispatch
    phase = [_req(40000 + i * 100, 12.0) for i in range(10)]
    unit = [_req(40000 + i * 100, 5.0) for i in range(6)]
    row = {"timed_out": True, "failure_class": "model-limitation"}
    assert dispatch.contention_class(row, unit, phase + unit) == "env-contention"
    assert row["contention"]["ref_decode"] == 12.0 and row["contention"]["slow"] is True


def test_r8e_ws4_think_shape_stays_model():
    """r8e WS4 think: 6.3 tok/s at 76-92k context; the phase median 15 came from 4-40k requests. No matched reference ->
    the slowdown is the unit's own KV length, not the host: class unchanged."""
    from taskflow import dispatch
    phase = [_req(c, d) for c, d in [(3700, 29), (8800, 24), (25000, 15.4), (30000, 13.9), (33000, 12.5), (12000, 23),
                                     (24500, 14.7), (28000, 15.3), (36000, 13), (38000, 11.2)]]
    unit = [_req(c, d) for c, d in [(76354, 7.1), (78561, 7.0), (82602, 6.7), (86070, 6.3), (88785, 6.3), (90637, 5.6)]]
    row = {"timed_out": True, "failure_class": "model-limitation"}
    assert dispatch.contention_class(row, unit, phase) is None
    assert row["contention"]["slow"] is None and row["contention"]["unit_decode"] < 0.5 * row["contention"]["phase_decode"]


def test_contention_only_reclasses_timed_out_model_rows():
    from taskflow import dispatch
    phase = [_req(40000, 12.0)] * 10
    unit = [_req(40000, 5.0)] * 6
    assert dispatch.contention_class({"timed_out": False, "failure_class": "model-limitation"}, unit, phase) is None
    assert dispatch.contention_class({"timed_out": True, "failure_class": "harness"}, unit, phase) is None
    assert dispatch.contention_class({"timed_out": True, "failure_class": "model-limitation"},
                                     [_req(40000, 1e6, n=1)], phase) is None        # 1-token replies ignored


# ------------------------------------------------------------------------- fix 5: WS4 packet is acceptance-only
WS4 = {"key": "WS4-WAKE-IMPERATIVE", "goal": "- [ ] **WS4-WAKE-IMPERATIVE** ...", "verify_scope": "acceptance-only",
       "done_when": ("a test shows every wake/nudge builder in handoff_sessions.py and session_bus emits an imperative "
                     "line, and a live woken session acts on one"),
       "acceptance": "python3 -m pytest -q scripts/coordination/tests/test_wake_imperative.py"}


def test_acceptance_only_scope_in_review_prompt():
    from taskflow import verify
    p = verify.review_prompt(WS4, "diff")
    assert "SCOPE: ACCEPTANCE ONLY" in p and "live session" in p
    assert "SCOPE: ACCEPTANCE ONLY" not in verify.review_prompt(dict(WS4, verify_scope=None), "diff")


def test_acceptance_only_verified_is_held_never_ticked(tmp_path):
    from taskflow import verify
    r = tmp_path / "lane"
    r.mkdir()
    _g(r.parent, "init", "-q", "-b", "main", str(r))
    (r / "a.py").write_text("a = 1\n")
    _g(r, "add", "a.py")
    _g(r, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    base = _g(r, "rev-parse", "HEAD").strip()
    (r / "a.py").write_text("a = 2\n")
    _g(r, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-am", "w")
    t = dict(WS4, acceptance=None, test_cmds=[], inputs=["a.py"], outputs=[], forbidden=[], where=[])
    v = verify.verify(t, r, base, reviewer=lambda *a: {"verdict": "done", "reason": "ok"})
    assert v["verdict"] == "verified" and v["hold"] == "acceptance-only"     # dispatch: apply only when not hold
    v = verify.verify(dict(t, brief_accepted="pending"), r, base, reviewer=lambda *a: {"verdict": "done"})
    assert v["hold"] == "accepted-pending,acceptance-only"


def test_verify_scope_is_a_brief_key():
    from taskflow import schema
    assert "verify_scope" in schema.BRIEF_KEYS
