"""r8d harness fixes from the r8c CPU canary (FIX-HARNESS, 2026-11-22; docs/design/taskflow-stage1-canary-findings.md r8c)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
from taskflow import dispatch  # noqa: E402


def _g(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True).stdout


def _repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    _g(r, "init", "-q", "-b", "main")
    (r / "a.txt").write_text("a\n")
    _g(r, "add", "a.txt")
    _g(r, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    return r


# ------------------------------------------------------------------------------- fix 1: lanes on resume
def test_resumed_unit_reclaims_its_leftover_worktree(tmp_path, monkeypatch):
    """r8c TU-GR-1 think / MM-5 think: the rc=75 kill left the lane; the resumed unit must reclaim it."""
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(tmp_path / "tf"))
    repo = _repo(tmp_path)
    base_dir = tmp_path / "out" / "t00" / "t00"
    lane = dispatch.lane_root() / __import__("hashlib").sha1(str(base_dir).encode()).hexdigest()[:4]
    lane.parent.mkdir(parents=True)
    base_dir.mkdir(parents=True)
    (base_dir / "lane.path").write_text(str(lane))
    _g(repo, "worktree", "add", "-q", "-b", "taskflow/old/00", str(lane), "HEAD")
    (lane / "wip.txt").write_text("half done\n")                 # killed mid-edit
    dispatch._meta(lane).write_text(json.dumps({"lane": str(lane), "repo": str(repo), "branch": "taskflow/old/00",
                                                "task": "TU-GR-1", "state": "live"}))
    how = dispatch.reclaim_resumed_lane(lane, base_dir, {"key": "TU-GR-1"}, repo)
    assert how == "worktree-remove" and not lane.exists() and not dispatch._meta(lane).exists()
    assert "wip.txt" in _g(repo, "show", "--name-only", "taskflow/old/00")      # WIP kept on its branch


def test_unregistered_leftover_goes_through_guarded_rm(tmp_path, monkeypatch):
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(tmp_path / "tf"))
    repo = _repo(tmp_path)
    fake = tmp_path / "grm.sh"
    trash = tmp_path / "trash"
    trash.mkdir()
    fake.write_text(f'#!/bin/bash\nset -euo pipefail\nmv "$1" {trash}/\n')
    monkeypatch.setenv("GUARDED_RM", str(fake))
    base_dir = tmp_path / "bd"
    base_dir.mkdir()
    lane = tmp_path / "tf" / "abcd"
    lane.mkdir(parents=True)
    (lane / "x").write_text("x")
    dispatch._meta(lane).write_text(json.dumps({"lane": str(lane), "repo": str(repo), "task": "MM-5"}))
    assert dispatch.reclaim_resumed_lane(lane, base_dir, {"key": "MM-5"}, repo) == "guarded_rm"
    assert not lane.exists() and (trash / "abcd" / "x").exists() and not dispatch._meta(lane).exists()


def test_foreign_lane_is_still_refused(tmp_path):
    repo = _repo(tmp_path)
    lane = tmp_path / "tf" / "beef"
    lane.mkdir(parents=True)
    dispatch._meta(lane).write_text(json.dumps({"lane": str(lane), "repo": str(repo), "task": "OTHER"}))
    with pytest.raises(dispatch.LaneRefused):
        dispatch.reclaim_resumed_lane(lane, tmp_path / "bd", {"key": "MM-5"}, repo)
    assert lane.exists()


def test_live_dispatcher_lane_is_not_reclaimed(tmp_path):
    repo = _repo(tmp_path)
    bd = tmp_path / "bd"
    bd.mkdir()
    lane = tmp_path / "tf" / "cafe"
    lane.mkdir(parents=True)
    (bd / "lane.path").write_text(str(lane))
    import os
    dispatch._meta(lane).write_text(json.dumps({"lane": str(lane), "repo": str(repo), "task": "MM-5",
                                                "owner": dispatch._proc_id(os.getpid())}))
    with pytest.raises(dispatch.LaneRefused, match="alive"):
        dispatch.reclaim_resumed_lane(lane, bd, {"key": "MM-5"}, repo)
    assert lane.exists()


# ------------------------------------------------------------------------------- fix 2: reviewer under thinking
TEMPLATE = '{"verdict":"done|not_done|drift","reason":"<=150 chars"}'


def test_template_echo_is_not_a_verdict():
    """r8c NOFOLD-1 / WS4 think: reasoning echoed the prompt template and the parser returned it."""
    r = dispatch.parse_review({"content": "", "reasoning_content": "The format is " + TEMPLATE + " so let me think..."})
    assert r["verdict"] == "unparseable" and r["template_echo"]
    ok = dispatch.parse_review({"content": "", "reasoning_content": "Format " + TEMPLATE + ' ok. {"verdict":"done","reason":"greps pass"}'})
    assert ok["verdict"] == "done"
    assert dispatch.template_echo({"verdict": "done|not_done|drift"}) and not dispatch.template_echo({"verdict": "done", "reason": "x"})


def test_reviewer_disables_thinking_and_retries_once(monkeypatch):
    sent = []

    class R:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(self.body).encode()

    replies = [{"content": "", "reasoning_content": "think " + TEMPLATE}, {"content": '{"verdict":"done","reason":"ok"}'}]

    def fake_open(req, timeout=0):
        sent.append((json.loads(req.data), dict(req.header_items())))
        return R({"choices": [{"message": replies[len(sent) - 1], "finish_reason": "stop"}], "usage": {}})

    monkeypatch.setattr(dispatch.urllib.request, "urlopen", fake_open)
    v = dispatch.reviewer_for("http://x/v1", dispatch.local_llm.model_for("terra"), max_tokens=1024)({"goal": "g"}, "diff")
    assert v["verdict"] == "done" and v["retried"]["template_echo"]
    assert [b["max_tokens"] for b, _ in sent] == [1024, 2048]
    assert all(b["chat_template_kwargs"] == {"enable_thinking": False, "preserve_thinking": True}
               for b, _ in sent)
    assert all(h.get("X-taskflow-role") == "reviewer" for _, h in sent)


# ------------------------------------------------------------------------------- fix 3: packet freshness
def _root_with_box(tmp_path, ticked: bool):
    from taskflow import schema
    up = tmp_path / "up"
    up.mkdir()
    _g(up, "init", "-q", "-b", "main")
    (up / "h.md").write_text(f"- [{'x' if ticked else ' '}] **NV-1** do the thing\n")
    (up / "ok.sh").write_text("exit 0\n")
    _g(up, "add", ".")
    _g(up, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(up), str(clone)], check=True)
    return clone, schema.text_sha("- [ ] **NV-1** do the thing")


def test_stale_packet_box_ticked_or_gone(tmp_path, monkeypatch):
    from taskflow import schema
    clone, sha = _root_with_box(tmp_path, ticked=True)
    monkeypatch.setitem(schema.REPOS, "epyc-root", clone)
    t = {"handoff": "h.md", "text_sha": sha, "repo": "epyc-root"}
    assert dispatch.box_state_at_base(t) == "ticked"
    assert dispatch.stale_packet(t, clone) == "box ticked at origin/main"
    assert dispatch.box_state_at_base(dict(t, text_sha="0" * 16)) == "gone"
    assert dispatch.box_state_at_base(dict(t, handoff="missing.md")) is None        # unknown never skips


def test_stale_packet_acceptance_already_passes(tmp_path, monkeypatch):
    """r8c INTAKE-VALIDATE-86 (validator already exits 0) / NUMA-DECOUPLE-1 (landed as a56df365b)."""
    from taskflow import schema
    clone, sha = _root_with_box(tmp_path, ticked=False)
    monkeypatch.setitem(schema.REPOS, "epyc-root", clone)
    t = {"handoff": "h.md", "text_sha": sha, "repo": "epyc-root"}
    assert dispatch.box_state_at_base(t) == "open"
    assert dispatch.stale_packet(dict(t, acceptance="bash ok.sh"), clone).startswith("acceptance already passes")
    assert dispatch.stale_packet(dict(t, acceptance="bash missing_test.sh"), clone) is None
    assert dispatch.stale_packet(t, clone) is None


def test_run_skips_stale_packet_before_the_model(tmp_path, monkeypatch):
    monkeypatch.setattr(dispatch, "make_lane", lambda t, d, b: (tmp_path, tmp_path, "base"))
    dropped = []
    monkeypatch.setattr(dispatch, "drop_lane", lambda r, l: dropped.append(l) or True)
    monkeypatch.setattr(dispatch, "sweep_lanes", lambda: {})
    monkeypatch.setattr(dispatch, "stale_packet", lambda t, l: "acceptance already passes on base: `x`")
    monkeypatch.setattr(dispatch.local_llm, "spawn", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no model")))
    task = {"key": "NUMA-DECOUPLE-1", "handoff": "h.md", "repo": "epyc-root", "budget": {"wall_s": 600}}
    row = dispatch.run([task], "http://x/v1", tmp_path / "out", apply=False, use_reviewer=False, gnx_trigger=False)[0]
    assert (row["verdict"], row["reason"], row["failure_class"]) == ("skipped", "stale-packet", "task") and dropped


# ------------------------------------------------------------------------------- fix 4: pathspec
NUMA = {"repo": "epyc-inference-research",
        "where": ["epyc-inference-research:scripts/benchmark/server_numa_np_sweep.py::summarize_cell",
                  "epyc-inference-research:scripts/benchmark/tests/test_server_numa_np_sweep.py"],
        "approach": "Update the two existing asserts in test_server_numa_np_sweep.py.\nNew test_decision_grade_decouple.py: "
                    "copy the fixture pattern. Also edit scripts/benchmark/sweep_report.py to print it.\n"
                    "Do NOT touch scripts/benchmark/trim.py.",
        "acceptance": "python3 -m pytest -q scripts/benchmark/tests/test_decision_grade_decouple.py",
        "non_goals": ["do not change scripts/benchmark/cache_reset.py"],
        "inputs": ["scripts/benchmark/server_numa_np_sweep.py"], "outputs": []}


def test_pathspec_admits_approach_named_existing_files():
    """r8c NUMA-DECOUPLE-1: the decouple test existed in base; fix 4 only admitted ADDED approach files."""
    from taskflow import verify
    t = "scripts/benchmark/tests/test_decision_grade_decouple.py"
    assert verify.outside_pathspec([t], NUMA, modified={t}) == []                      # acceptance-named, existing
    rep = "scripts/benchmark/sweep_report.py"
    assert verify.outside_pathspec([rep], NUMA) == [rep]
    assert verify.outside_pathspec([rep], NUMA, modified={rep}) == []                 # approach-named, existing


def test_pathspec_named_sibling_by_basename():
    from taskflow import verify
    t = dict(NUMA, acceptance="python3 -m pytest -q x")
    p = "scripts/benchmark/tests/test_decision_grade_decouple.py"
    assert verify.outside_pathspec([p], t, added={p}) == []
    assert verify.outside_pathspec(["other/test_decision_grade_decouple.py"], t, added={"other/test_decision_grade_decouple.py"})


def test_pathspec_still_rejects_junk_and_negated_paths():
    """r8c INTAKE-VALIDATE-86: `tmp_extract_refs.py` was a correct reject."""
    from taskflow import verify
    assert verify.outside_pathspec(["tmp_extract_refs.py"], NUMA, added={"tmp_extract_refs.py"}) == ["tmp_extract_refs.py"]
    for p in ("scripts/benchmark/trim.py", "scripts/benchmark/cache_reset.py"):
        assert verify.outside_pathspec([p], NUMA, modified={p}) == [p]


# ------------------------------------------------------------------------------- fix 5: classifier
def test_classifier_matches_the_r8c_hand_audit():
    """14 real r8c runs (results.jsonl + TASKS.json + diff.patch paths, tf1-cpu-r8c-canary-35b-q0q2-20261122). Hand
    audit (findings doc r8c table): harness 4, task (packet) 4, model 3, verified 3. The stale packets carry the
    `stale_packet` reason fix 3 now finds at selection time; lane errors are harness in dispatch.run itself."""
    cases = json.loads((Path(__file__).parent / "taskflow_r8c_canary_cases.json").read_text())
    got = {}
    for c in cases:
        if c["verify"]["verdict"] == "error":
            got[c["unit_id"]] = "harness"
        else:
            got[c["unit_id"]] = dispatch.failure_class(c["worker"], c["verify"], c["task"])
    assert got == {c["unit_id"]: c["audited"] for c in cases}
    vals = list(got.values())
    assert (vals.count("harness"), vals.count("task"), vals.count("model-limitation"), vals.count(None)) == (4, 4, 3, 3)


def test_rc4_without_the_test_file_is_model():
    w = {"timed_out": False, "usage": {"steps": 30}, "tool_errors": [], "tools": ["edit"] * 30, "errors": []}
    v = {"verdict": "rejected", "reason": "tests-fail", "evidence": {"paths": ["scripts/coordination/tmux_adapter.py"]},
         "checks": [{"check": "tests", "ok": False, "why": "python3 -m pytest -q scripts/coordination/tests/test_wake_imperative.py rc=4"}]}
    assert dispatch.failure_class(w, v, {"inputs": []}) == "model-limitation"
    wrote = dict(v, evidence={"paths": ["scripts/coordination/tests/test_wake_imperative.py"]})
    assert dispatch.failure_class(w, wrote, {"inputs": []}) == "harness"            # wrote it: rc=4 is env
    env = dict(v, test_tail="ModuleNotFoundError: No module named 'fastapi'", evidence={"paths": ["a.py"]})
    env["checks"] = [{"check": "tests", "ok": False, "why": "pytest -q tests/unit/test_vl.py rc=4"}]
    assert dispatch.failure_class(w, env, {"inputs": ["tests/unit/test_vl.py"]}) == "harness"


def test_no_change_on_stale_packet_is_task():
    w = {"timed_out": False, "usage": {"steps": 30}, "tool_errors": [], "tools": ["read"] * 30, "errors": []}
    v = {"verdict": "rejected", "reason": "no-change", "checks": []}
    assert dispatch.failure_class(w, v, {"stale_packet": "acceptance already passes on base"}) == "task"
    assert dispatch.failure_class(w, v, {}) == "model-limitation"


# ------------------------------------------------------------------------------- fix 6: shell pipe filters
def test_shell_allows_sed_sort_awk_cut_in_pipes_deny_still_wins(tmp_path, monkeypatch):
    """r8c INTAKE-VALIDATE-86: every `grep … | sed … | sort -u` / `| awk` / `| cut` was denied."""
    import fnmatch
    from taskflow import schema
    from taskflow.harness import local_llm as L
    monkeypatch.setattr(L, "POLICY_DIR", tmp_path / "pol")
    t = {"repo": "epyc-root", "budget": dict(schema.DEFAULT_BUDGET), "acceptance": "bash scripts/validate/validate_intake.sh"}
    bash = json.loads(L.write_config(tmp_path, "http://x/v1", "m", t, lane="/mnt/raid0/llm/tf/76db").read_text())["agent"][L.AGENT]["permission"]["bash"]

    def ok(cmd):    # whole-command approximation (any allow, no deny), as in the r8c shell test
        return (any(fnmatch.fnmatchcase(cmd, p) for p, v in bash.items() if v == "allow" and p != "*")
                and not any(fnmatch.fnmatchcase(cmd, p) for p, v in bash.items() if v == "deny" and p != "*"))

    def stage_ok(cmd):   # per-stage approximation: every pipe stage allowed, the whole command not denied
        return all(ok(seg.strip()) for seg in cmd.split(" | ")) and ok(cmd)
    for c in ["grep -A1 'handoffs:' research/intake_index.yaml | grep '^\\s*-' | sed 's/^\\s*-\\s*//' | sort -u",
              "grep -A1 handoffs: research/intake_index.yaml | grep -- '- ' | awk '{print $2}' | sort -u",
              "grep -A1 handoffs: research/intake_index.yaml | grep -- '- ' | cut -d'-' -f2- | sort",
              "cat research/intake_index.yaml 2>&1 | sed -n '1,20p'"]:
        assert ok(c) and stage_ok(c), c
    for c in ["cat f | sed -i 's/a/b/' g", "cat f | sort -o out.txt", "cat f | awk '{system(\"rm x\")}'",
              "cat f | awk '{print > \"o\"}'", "grep x f | sed 's/a/b/' > out", "sed -i 's/a/b/' f",
              "cat f | sort --output=o", "grep x f | sed 's/a/b/w out.txt'"]:
        assert not ok(c), c
    assert "sed, sort, awk or cut" in L.POLICY
