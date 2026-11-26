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
def test_shell_requires_checked_remove_command(tmp_path, monkeypatch):
    b = _bash(tmp_path, monkeypatch)
    assert _ok(b, "taskflow-scratch rm tests/test_unshare_debug.py")
    assert _ok(b, "taskflow-scratch rm tests/unit/_debug_alias.py")
    for bad in ("rm tests/test_unshare_debug.py", "rm README.md", "/bin/rm README.md", "rm -rf tests",
                "taskflow-scratch rm a.py>README.md", "taskflow-scratch rm $(cat list)", "taskflow-scratch rm `ls`"):
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
    # r8g fix 3: harness / no-change timeouts are evaluated too (the class is not fixed before the contention check)
    assert dispatch.contention_class({"timed_out": True, "failure_class": "harness"}, unit, phase) == "env-contention"
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


# ------------------------------------------------------------------------- r8g fix 1: empty stdout is an error, not a denial
TUGR1_NOTHINK_DIFF = (Path(__file__).parent / "taskflow_r8f_tugr1_nothink_diff.patch").read_text()


def test_vacuity_guard_flags_the_r8f_tugr1_nothink_empty_stdout_denial():
    from taskflow import verify
    hits = verify.vacuity_hits(TUGR1_NOTHINK_DIFF)
    assert hits and "launcher_error" in hits[0], hits


def test_vacuity_guard_empty_stdout_ok_when_test_pins_errno():
    from taskflow import verify
    d = TUGR1_NOTHINK_DIFF.replace(
        "+    assert_grader_unreachable(result)  # should NOT raise",
        "+    assert result[\"errno\"] in (\"2\", \"13\")\n+    assert_grader_unreachable(result)")
    assert d != TUGR1_NOTHINK_DIFF and verify.vacuity_hits(d) == []


def test_vacuity_guard_empty_stdout_branch_shape_without_token():
    from taskflow import verify
    src = ("+def probe(c):\n+    out = run(c).stdout.strip()\n+    if not out:\n+        return {\"ok\": False, \"why\": 1}\n+    return load(out)\n")
    diff = ("diff --git a/x/p.py b/x/p.py\nnew file mode 100644\n--- /dev/null\n+++ b/x/p.py\n@@ -0,0 +1,5 @@\n" + src +
            "diff --git a/x/test_p.py b/x/test_p.py\nnew file mode 100644\n--- /dev/null\n+++ b/x/test_p.py\n@@ -0,0 +1,2 @@\n"
            "+def test_a():\n+    assert not probe(1)['ok']\n")
    assert verify.vacuity_hits(diff)


# ------------------------------------------------------------------------- r8g fix 2: worktree tools cut, lane destroyed reported
def test_proxy_strips_worktree_tools_from_the_request():
    body = {"tools": [{"function": {"name": n}} for n in
                      ("read", "edit", "opencode_worktree_remove", "opencode_worktree_create", "opencode_worktree_list")]}
    gone = L.strip_worker_tools(body)
    assert gone == ["opencode_worktree_remove", "opencode_worktree_create", "opencode_worktree_list"]
    assert [t["function"]["name"] for t in body["tools"]] == ["read", "edit"]
    assert L.strip_worker_tools({"messages": []}) == []


def test_edit_permission_denies_the_lane_directory_itself(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "POLICY_DIR", tmp_path / "pol")
    t = {"repo": "epyc-orchestrator", "budget": dict(schema.DEFAULT_BUDGET), "acceptance": None}
    perm = json.loads(L.write_config(tmp_path, "http://x/v1", "m", t, lane=LANE).read_text())["agent"][L.AGENT]["permission"]
    assert perm["edit"]["*"] == "allow" and perm["edit"][LANE] == "deny" and perm["edit"][LANE + "/"] == "deny"
    for k in ("opencode_worktree_remove", "opencode_worktree_list", "opencode_*", "opencode.*"):
        assert perm[k] == "deny"
    perm2 = json.loads(L.write_config(tmp_path, "http://x/v1", "m", t).read_text())["agent"][L.AGENT]["permission"]
    assert perm2["edit"] == "allow"                               # no lane given: unchanged


def test_lane_destroyed_by_worker_is_a_harness_row_not_calledprocesserror(tmp_path, monkeypatch):
    import subprocess
    from taskflow import dispatch
    repo = tmp_path / "repo"
    repo.mkdir()
    g = lambda *a: subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *a],
                                  check=True, capture_output=True, text=True)
    g("init", "-q")
    (repo / "a.txt").write_text("x")
    g("add", "a.txt")
    g("commit", "-q", "-m", "i")
    lane = tmp_path / "lane1"
    g("worktree", "add", "-q", "--detach", str(lane))
    assert not dispatch.lane_destroyed(lane)
    import shutil
    shutil.rmtree(lane)                                           # what opencode_worktree_remove(force) did
    assert dispatch.lane_destroyed(lane)

    task = {"key": "MM-5", "handoff": "h.md", "repo": "epyc-orchestrator", "budget": dict(schema.DEFAULT_BUDGET),
            "text_sha": "ab", "id": "MM-5"}
    lane2 = tmp_path / "lane2"
    monkeypatch.setattr(dispatch, "make_lane", lambda *a, **k: (repo, lane2, "base"))
    monkeypatch.setattr(dispatch, "gitnexus_trigger", lambda *a, **k: "")
    monkeypatch.setattr(dispatch, "phase1_or_skip", lambda *a, **k: None)
    monkeypatch.setattr(dispatch, "sweep_lanes", lambda *a, **k: {})
    g("worktree", "add", "-q", "--detach", str(lane2))

    def fake_spawn(*a, **k):
        shutil.rmtree(lane2)
        return {"usage": {"steps": 3, "input": 0, "output": 0, "cache_read": 0}, "errors": [], "tools": ["opencode_worktree_remove"],
                "model": "m", "rc": 0, "timed_out": False, "result": None, "wall_s": 1, "tool_errors": []}
    monkeypatch.setattr(dispatch.local_llm, "spawn", fake_spawn)
    rows = dispatch.run([task], "http://x", tmp_path / "out", apply=False, use_reviewer=False, check_fresh=False)
    assert rows[0]["reason"] == "lane-destroyed-by-worker" and rows[0]["failure_class"] == "harness", rows[0]
    assert "opencode_worktree_remove" in rows[0]["detail"]


def test_lane_destroyed_is_not_a_finished_unit():
    from taskflow import stage1_result
    assert stage1_result.no_model_work({"reason": "lane-destroyed-by-worker"})
    assert not stage1_result.no_model_work({"reason": "reviewer-done"})
# ------------------------------------------------------------------------- r8g fix 3: contention classifier
# Fixture: the real r8f request log (all arms, both stints). think WS4 decoded 2.5-3.5 tok/s at 3.7k context on its
# first requests against 20-27 tok/s for every other unit's first request; nothink WS4 was NOT contention (decode fell
# smoothly with a 36-79k context).
R8F_REQS = json.loads((Path(__file__).parent / "taskflow_r8f_requests.json").read_text())["requests"]


def _unit(arm, task):
    return [r for r in R8F_REQS if r["arm"] == arm and r["task"] == task]


def test_contention_think_ws4_nochange_timeout_is_env_with_job_fallback_and_early_check():
    from taskflow import dispatch
    row = {"timed_out": True, "failure_class": "harness", "reason": "no-change", "rc": 130}
    unit = _unit("canary-think", "WS4-WAKE-IMPERATIVE")
    phase = [r for r in R8F_REQS if r["arm"] == "canary-think"]
    assert dispatch.contention_class(row, unit, phase, job_reqs=R8F_REQS) == "env-contention"
    c = row["contention"]
    assert c["slow"] and "early-context-first-request" in c["slow_by"], c
    assert c["first_decode"] < 0.5 * c["first_ref"] and c["first_ctx"] < 6000, c


def test_contention_not_evaluated_before_r8g_no_job_reqs_means_no_early_check():
    from taskflow import dispatch
    row = {"timed_out": True, "failure_class": "harness", "reason": "no-change", "rc": 130}
    unit = _unit("canary-think", "WS4-WAKE-IMPERATIVE")
    assert dispatch.contention_class(row, unit, unit + [r for r in R8F_REQS if r["arm"] == "canary-think"]) is None


def test_contention_nothink_ws4_is_not_flagged():
    from taskflow import dispatch
    row = {"timed_out": True, "failure_class": "model-limitation", "reason": "tests-fail", "rc": 130}
    unit = _unit("canary-nothink", "WS4-WAKE-IMPERATIVE")
    phase = [r for r in R8F_REQS if r["arm"] == "canary-nothink"]
    assert dispatch.contention_class(row, unit, phase, job_reqs=R8F_REQS) is None
    assert row["contention"]["slow"] is False, row["contention"]


def test_contention_job_wide_fallback_when_phase_has_few_matched():
    from taskflow import dispatch
    unit = [{"arm": "a", "task": "T", "t0": i, "prompt_n": 20000, "cache_n": 0, "predicted_n": 100, "decode_tok_s": 4.0}
            for i in range(6)]
    phase = [dict(r, arm="a", task="X", prompt_n=3000) for r in unit]            # phase has nothing near 20k
    job = [{"arm": "b", "task": "Y", "t0": i, "prompt_n": 21000, "cache_n": 0, "predicted_n": 100, "decode_tok_s": 12.0}
           for i in range(8)]
    c = dispatch.contention_check(unit, phase, job_reqs=job)
    assert c["ref_scope"] == "job" and c["slow"] is True and "job-context-matched" in c["slow_by"], c


def test_contention_runs_on_model_class_rows_and_skips_task_and_verified():
    from taskflow import dispatch
    unit = _unit("canary-think", "WS4-WAKE-IMPERATIVE")
    for cls in ("task", None, "env-contention"):
        assert dispatch.contention_class({"timed_out": True, "failure_class": cls}, unit, unit, job_reqs=R8F_REQS) is None
    assert dispatch.contention_class({"timed_out": False, "failure_class": "harness"}, unit, unit, job_reqs=R8F_REQS) is None
    assert dispatch.contention_class({"timed_out": True, "failure_class": "model-limitation"}, unit, unit,
                                     job_reqs=R8F_REQS) == "env-contention"


def test_no_change_timeout_rc130_does_not_default_to_harness():
    from taskflow import dispatch
    w = {"usage": {"steps": 20}, "errors": [], "tools": ["read"] * 20, "tool_errors": [], "timed_out": True, "rc": 130,
         "result": None}
    v = {"verdict": "rejected", "reason": "no-change", "checks": []}
    assert dispatch.failure_class(w, v, {}) == "model-limitation"


# ------------------------------------------------------------------------- r8g fix 4: mv + refusal message names allowed forms
def test_shell_requires_checked_move_command(tmp_path, monkeypatch):
    b = _bash(tmp_path, monkeypatch)
    assert _ok(b, "taskflow-scratch mv tests/unit/_debug.py tests/unit/test_x.py")
    assert _ok(b, "taskflow-scratch mv _debug_result.json old.json")
    for bad in ("mv a b", "/bin/mv a b", "mv -f a b", "taskflow-scratch mv a b | sh",
                "taskflow-scratch mv a $HOME/b", "taskflow-scratch mv a b `id`"):
        assert not _ok(b, bad), bad


def test_policy_names_mv_and_the_allowed_forms():
    assert "`taskflow-scratch mv <relative src> <relative dst>`" in L.POLICY and "orch-py.sh -c" in L.POLICY


def test_denied_shell_result_gets_the_allowed_forms_idempotently():
    body = {"messages": [{"role": "user", "content": "x"},
                         {"role": "tool", "tool_call_id": "1", "content": "Permission denied: shell"},
                         {"role": "tool", "tool_call_id": "2", "content": "ok output"}]}
    assert L.annotate_denials(body) == 1
    c = body["messages"][1]["content"]
    assert c.startswith("Permission denied: shell") and "orch-py.sh -c" in c and "`taskflow-scratch rm <relative path>`" in c
    assert body["messages"][2]["content"] == "ok output"
    assert L.annotate_denials(body) == 0 and body["messages"][1]["content"] == c          # idempotent: stable prefix


# ------------------------------------------------------------------------- r8g fix 5: think-arm per-request cap
def test_request_cap_defaults_and_configurable():
    assert schema.request_token_cap({"thinking": False}) == 2048
    assert schema.request_token_cap({"thinking": True}) == 6144
    assert schema.request_token_cap({"thinking": True, "request_cap": {"think_cap_tokens": 3000}}) == 3000
    assert schema.request_token_cap({"thinking": True, "request_cap": {"think_cap_tokens": 500}}) == 1024   # floor


def test_two_capped_thinking_requests_never_consume_the_wall():
    # r8f think: decode 10.7 tok/s; the old wall rate (17.4) and a 1739 s budget let two 4096-token outputs take ~1160 s
    arm = {"thinking": True, "wall_budget": {"prefill_tok_s": 79.0, "decode_tok_s": 10.7, "expected_output_tokens": 10000,
                                             "expected_prompt_tokens": 80000}}
    for wall in (600, 1000, 1739, 2554, 3600):
        cap = schema.request_token_cap(arm, wall_s=wall)
        assert 2 * cap / 10.7 <= 0.5 * wall + 1, (wall, cap)       # two capped outputs <= half the wall
    assert schema.request_token_cap(arm) == 6144                   # wall scaled from measured rates (2554 s): cap binds
    assert schema.request_token_cap(dict(arm, request_cap={"max_request_wall_frac": None}), wall_s=600) == 6144   # disabled


# ------------------------------------------------------------------------- r8g fix 6: where line ranges (WS4)
def test_where_accepts_line_ranges_and_checks_them(tmp_path):
    from taskflow import brief
    pw = brief.parse_where("epyc-root:scripts/coordination/handoff_sessions.py#L530-613")
    assert pw["path"] == "scripts/coordination/handoff_sessions.py" and pw["lines"] == (530, 613) and pw["sym"] is None
    assert brief.parse_where("epyc-root:a/b.py::f#L3")["lines"] == (3, 3)
    assert brief.parse_where("epyc-root:a/b.py::f")["lines"] is None
    (tmp_path / "x.py").write_text("a\nb\nc\n")
    ok = brief.parse_where("epyc-root:x.py#L1-3")
    assert brief._lines_in_file(tmp_path, ok)
    assert not brief._lines_in_file(tmp_path, brief.parse_where("epyc-root:x.py#L2-9"))     # beyond the file
    assert not brief._lines_in_file(tmp_path, brief.parse_where("epyc-root:x.py#L3-1"))     # reversed


def test_where_ranges_reach_the_worker_prompt():
    t = {"where": ["epyc-root:scripts/coordination/handoff_sessions.py#L530-613", "epyc-root:a.py::f"]}
    sec = L.brief_sections(t)[0]
    assert "#L530-613" in sec and "read ONLY those lines" in sec
    assert "read ONLY" not in L.brief_sections({"where": ["epyc-root:a.py::f"]})[0]


def test_ws4_brief_points_at_line_ranges_not_the_whole_file():
    from taskflow import brief
    root = Path(__file__).resolve().parents[2]
    doc = brief.parse_text((root / "handoffs/active/briefs/WS4-WAKE-IMPERATIVE.md").read_text())
    hs = [w for w in doc["where"] if "handoff_sessions.py" in w]
    assert hs and all("#L" in w for w in hs), hs
    for w in hs:
        assert brief._lines_in_file(root, brief.parse_where(w)), w


