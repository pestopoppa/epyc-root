"""r8c harness fixes from the r8b CPU canary (FIX-HARNESS, 2026-11-22; docs/design/taskflow-stage1-canary-findings.md r8b)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
from taskflow import dispatch, schema, verify  # noqa: E402
from taskflow.harness import local_llm as L  # noqa: E402


# ------------------------------------------------------------------------------------- fix 1: wall budget
def test_wall_budget_scales_with_cpu_rate():
    # r8b medians: prefill 111 tok/s, decode 17.4 tok/s; 80k prompt + 6k output -> 1.25*(720.7+344.8)+120
    assert schema.wall_budget_s({"prefill_tok_s": 111, "decode_tok_s": 17.4}) == 1452
    assert schema.wall_budget_s({"prefill_tok_s": 2000, "decode_tok_s": 60}) == 600           # GPU: floor holds
    assert schema.wall_budget_s({"prefill_tok_s": 10, "decode_tok_s": 1}) == 3600             # cap
    assert schema.wall_budget_s(None) is None and schema.wall_budget_s({"prefill_tok_s": 100}) is None


def test_apply_wall_budget_overrides_only_wall():
    t = {"budget": dict(schema.DEFAULT_BUDGET, ctx=65536)}
    out = schema.apply_wall_budget(t, {"prefill_tok_s": 111, "decode_tok_s": 17.4, "expected_output_tokens": 10000})
    assert out["budget"]["wall_s"] == 1739 and out["budget"]["ctx"] == 65536 and t["budget"]["wall_s"] == 600
    assert schema.apply_wall_budget(t, None) is t


# ------------------------------------------------------------------------- fix 2: verifier runs acceptance
ORCH = "bash /mnt/raid0/llm/tmp/taskflow-stage1-cpu-r8-20261120/orch-py.sh -m pytest -q tests/unit/test_vl_describe_resize.py"


def test_packet_acceptance_survives_brief_remerge(monkeypatch, tmp_path):
    """r8b MM-5: the cross-repo brief re-merge from origin/main replaced the packet's orch-py.sh acceptance with the
    committed brief's bare `python3 -m pytest` (rc=4, no fastapi). The verifier must see the packet's command."""
    seen = {}
    task = {"key": "MM-5", "id": "MM-5", "handoff": "h.md", "repo": "epyc-orchestrator", "brief_state": "fresh",
            "acceptance": ORCH, "budget": dict(schema.DEFAULT_BUDGET), "goal": "g", "text_sha": "x"}
    monkeypatch.setattr(dispatch, "make_lane", lambda t, d, b: (tmp_path, tmp_path, "base"))
    monkeypatch.setattr(dispatch, "drop_lane", lambda r, l: True)
    monkeypatch.setattr(dispatch, "sweep_lanes", lambda: {})
    monkeypatch.setattr(dispatch, "phase1_or_skip", lambda t, *a, **k: t.update(acceptance="python3 -m pytest -q x.py"))
    monkeypatch.setattr(dispatch.local_llm, "spawn", lambda *a, **k: {"model": "m", "rc": 0, "timed_out": False, "wall_s": 1,
                        "usage": {"steps": 1, "input": 0, "cache_read": 0, "output": 0}, "tools": [], "errors": []})
    monkeypatch.setattr(dispatch, "commit_lane", lambda l, t: False)
    monkeypatch.setattr(dispatch.verify, "verify", lambda t, *a, **k: seen.update(acc=t["acceptance"]) or
                        {"verdict": "rejected", "reason": "no-change", "checks": []})
    row = dispatch.run([task], "http://x/v1", tmp_path / "out", apply=False, use_reviewer=False, gnx_trigger=False)[0]
    assert seen["acc"] == ORCH and row["acceptance_restored"]["packet"] == ORCH


def test_grep_acceptance_is_runnable():
    a = "grep -q '^## NO-FOLD list' docs/reference/kernel-manifests/README.md && grep -q x .claude/skills/kernel-promotion/SKILL.md"
    assert verify.acceptance_cmd({"acceptance": a, "repo": "epyc-root"}) == a


# ------------------------------------------------------------------------- fix 3: acceptance in the shell
def test_worker_shell_allows_acceptance_shapes_seen_in_r8b(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "POLICY_DIR", tmp_path / "pol")
    import fnmatch
    import json
    lane = "/mnt/raid0/llm/tf/9785"
    t = {"repo": "epyc-orchestrator", "budget": dict(schema.DEFAULT_BUDGET),
         "acceptance": "bash /mnt/raid0/llm/tmp/r/orch-py.sh -m pytest -q tests/unit/test_a.py tests/unit/test_b.py"}
    bash = json.loads(L.write_config(tmp_path, "http://x/v1", "m", t, lane=lane).read_text())["agent"][L.AGENT]["permission"]["bash"]

    def ok(cmd):   # opencode: last matching pattern wins; approximate with "any allow and no deny matches"
        return (any(fnmatch.fnmatchcase(cmd, p) for p, v in bash.items() if v == "allow" and p != "*")
                and not any(fnmatch.fnmatchcase(cmd, p) for p, v in bash.items() if v == "deny" and p != "*"))
    assert ok(t["acceptance"])
    assert ok(f"cd {lane} && {t['acceptance']}")
    assert ok("bash /mnt/raid0/llm/tmp/r/orch-py.sh -m pytest -q tests/unit/test_a.py")          # another selection
    assert ok(t["acceptance"] + ' 2>&1; echo "EXIT: $?"')
    assert not ok(t["acceptance"] + " > out.txt")
    assert not ok("git commit -m x")
    v = {"repo": "epyc-root", "budget": dict(schema.DEFAULT_BUDGET), "acceptance": "bash scripts/validate/validate_intake.sh"}
    bash = json.loads(L.write_config(tmp_path / "v", "http://x/v1", "m", v, lane="/mnt/raid0/llm/tf/4dab").read_text())["agent"][L.AGENT]["permission"]["bash"]
    assert ok('cd /mnt/raid0/llm/tf/4dab && bash scripts/validate/validate_intake.sh 2>&1; echo "EXIT: $?"')


# ------------------------------------------------------------------------- fix 4: approach-named new files
TUGR = {"repo": "epyc-orchestrator", "inputs": [], "outputs": [],
        "where": ["epyc-orchestrator:scripts/autopilot/evals/dtap/harness/runner.py::JudgeApplication",
                  "epyc-root:docs/design/tu-grader-isolation-boundary.md"],
        "approach": "Add epyc-orchestrator scripts/autopilot/evals/dtap/harness/isolation.py with probe_grader_access(sentinel: Path, ...)",
        "acceptance": "bash /mnt/raid0/llm/tmp/r/orch-py.sh -m pytest -q scripts/autopilot/evals/dtap/tests/test_grader_isolation.py"}


def test_approach_named_new_files_are_in_the_pathspec():
    new = ["scripts/autopilot/evals/dtap/harness/isolation.py", "scripts/autopilot/evals/dtap/tests/test_grader_isolation.py"]
    assert verify.outside_pathspec(new, TUGR) == new                     # r8b behaviour without the added set
    assert verify.outside_pathspec(new, TUGR, set(new)) == []
    assert "/mnt/raid0/llm/tmp/r/orch-py.sh" not in verify.approach_new_paths(TUGR)


def test_approach_names_do_not_admit_modified_existing_files():
    t = dict(TUGR, approach="Recreate tests/unit/test_c.py; do NOT touch src/concurrency.py")
    assert verify.outside_pathspec(["src/concurrency.py"], t, {"tests/unit/test_c.py"}) == ["src/concurrency.py"]


# ------------------------------------------------------------------------- fix 5: skip self-brief
def test_fresh_hand_brief_skips_phase1_and_remerge(tmp_path, monkeypatch):
    t = {"key": "NUMA-DECOUPLE-1", "id": "NUMA-DECOUPLE-1", "repo": "epyc-inference-research", "brief_state": "fresh",
         "brief_author": "owner", "where": ["epyc-inference-research:scripts/benchmark/server_numa_np_sweep.py::summarize_cell"],
         "approach": "In summarize_cell ...", "acceptance": "python3 -m pytest -q scripts/benchmark/tests/test_x.py",
         "budget": dict(schema.DEFAULT_BUDGET)}
    monkeypatch.setattr(dispatch, "_brief_lane", lambda *a: (_ for _ in ()).throw(AssertionError("no brief lane")))
    monkeypatch.setattr(dispatch, "self_brief", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no self-brief")))
    assert dispatch.phase1_or_skip(t, tmp_path, tmp_path, "http://x/v1", "local") == {"ok": True, "skipped": "fresh-hand-brief"}
    assert dispatch.phase1_or_skip(dict(t, repo="epyc-root"), tmp_path, tmp_path, "http://x/v1", "local")["skipped"]


def test_self_or_stale_brief_still_runs_phase1():
    base = {"brief_state": "fresh", "where": ["x"], "approach": "a", "acceptance": "pytest -q t.py", "brief_author": "owner"}
    assert dispatch.fresh_hand_brief(base)
    assert not dispatch.fresh_hand_brief(dict(base, brief_author="self"))
    assert not dispatch.fresh_hand_brief(dict(base, brief_state="stale"))
    assert not dispatch.fresh_hand_brief(dict(base, acceptance=None))


# ------------------------------------------------------------------------- fix 6: reviewer under thinking
def test_review_parsed_from_reasoning_when_content_empty():
    r = dispatch.parse_review({"content": "", "reasoning_content": 'All 4 greps pass. {"verdict":"done","reason":"meets done-when"}'})
    assert r["verdict"] == "done"
    assert dispatch.parse_review({"content": '{"verdict":"not_done","reason":"x"}'})["verdict"] == "not_done"
    e = dispatch.parse_review({"content": "", "reasoning_content": "thinking about it"})
    assert e["verdict"] == "unparseable" and e["empty"]


def test_reviewer_cap_raised():
    assert dispatch.REVIEW_MAX_TOKENS >= 1024


# ------------------------------------------------------------------------- fix 8: failure classifier
def test_classifier_matches_the_r8b_hand_audit():
    """16 real r8b runs (results.jsonl + TASKS.json, tf1-cpu-r8b-canary-35b-q0q2-20261122). The old classifier said
    model-limitation 11; the hand audit (findings doc r8b table) says harness 11, task (packet) 3, model 1, verified 1."""
    import json
    cases = json.loads((Path(__file__).parent / "taskflow_r8b_canary_cases.json").read_text())
    got = {}
    for c in cases:
        if c["verify"]["verdict"] == "needs-brief":
            got[c["unit_id"]] = dispatch.needs_brief_class(c["task"])
        else:
            got[c["unit_id"]] = dispatch.failure_class(c["worker"], c["verify"], c["task"])
    assert got == {c["unit_id"]: c["audited"] for c in cases}
    vals = list(got.values())
    assert (vals.count("harness"), vals.count("task"), vals.count("model-limitation"), vals.count(None)) == (11, 3, 1, 1)
    assert sum(c["r8b_classifier"] == "model-limitation" for c in cases) == 11       # the defect being fixed


def test_classifier_env_test_failure_and_empty_reviewer():
    w = {"timed_out": False, "usage": {"steps": 9}, "tool_errors": [], "tools": ["edit"] * 9, "errors": []}
    env = {"verdict": "rejected", "reason": "tests-fail", "test_tail": "ModuleNotFoundError: No module named 'fastapi'",
           "checks": [{"check": "tests", "ok": False, "why": "x rc=1"}]}
    assert dispatch.failure_class(w, env) == "harness"
    real = {"verdict": "rejected", "reason": "tests-fail", "test_tail": "AssertionError: 3 != 4",
            "checks": [{"check": "tests", "ok": False, "why": "pytest -q t.py rc=1"}]}
    assert dispatch.failure_class(w, real) == "model-limitation"
    assert dispatch.failure_class(w, {"verdict": "rejected", "reason": "reviewer-not_done", "review": {"empty": True}}) == "harness"
    assert dispatch.failure_class(w, {"verdict": "rejected", "reason": "reviewer-not_done", "review": {}}) == "model-limitation"
