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
