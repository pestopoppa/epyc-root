"""taskflow Stage 1: schema (verbatim box, done-when, paths), tier selection, verify mechanical checks, opencode config."""
import json
import subprocess
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
from taskflow import dispatch, schema, verify  # noqa: E402
from taskflow.harness import local_llm  # noqa: E402

BOX = ("- [ ] **FX-1 — fix the parser.** Edit `scripts/x.py`; done when `pytest tests/test_x.py` passes.\n"
       "  continuation line kept verbatim\n")


def _fixture(tmp_path):
    (tmp_path / "handoffs/active").mkdir(parents=True)
    (tmp_path / "handoffs/active/h.md").write_text("# H\n### Backlog\n" + BOX + "\n- [ ] **FX-2** other\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/x.py").write_text("print(1)\n")
    return {"file": "handoffs/active/h.md", "line": 99, "id": "FX-1", "class": "non-inference",
            "text_sha": schema.text_sha(BOX.split("\n")[0])}


def test_build_verbatim_and_fields(tmp_path, monkeypatch):
    rec = _fixture(tmp_path)
    monkeypatch.setitem(schema.REPOS, "epyc-root", tmp_path)
    t = schema.build(rec, root=tmp_path)
    assert t["schema"] == "epyc.task.v1" and t["goal"] == BOX.rstrip("\n")     # line hint wrong -> resolved by text
    assert t["line_hint"] == 3 and t["inputs"] == ["scripts/x.py"]
    assert t["test_cmds"] == ["pytest tests/test_x.py"] and "pytest" in t["done_when"]
    assert "handoffs/**" in t["forbidden"] and t["tier"] is None


def test_tier_selection():
    base = {"goal": "", "tier": None}
    assert dispatch.pick_tier(dict(base, goal="update the README section")) == "luna"
    assert dispatch.pick_tier(dict(base, goal="fix the off-by-one in foo.py")) == "terra"
    assert dispatch.pick_tier(dict(base, goal="debug why the server hangs")) == "sol"
    assert dispatch.pick_tier(dict(base, goal="fix x", tier="haiku")) == "luna"
    assert dispatch.escalate("luna") == "terra" and dispatch.escalate("sol") is None
    assert local_llm.model_for("sol", "codex") == "gpt-6.1-sol" and local_llm.model_for("luna", "claude") == "haiku"


def _lane(tmp_path):
    lane = tmp_path / "lane"
    lane.mkdir()
    g = lambda *a: subprocess.run(["git", "-C", str(lane), *a], check=True, capture_output=True)  # noqa: E731
    g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
    (lane / "a.py").write_text("x=1\n"); g("add", "."); g("commit", "-qm", "base")
    base = subprocess.run(["git", "-C", str(lane), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    return lane, g, base


def test_verify_checks(tmp_path):
    lane, g, base = _lane(tmp_path)
    task = {"inputs": ["a.py"], "outputs": [], "forbidden": list(schema.FORBIDDEN), "test_cmds": ["true"],
            "done_when": "`true` passes"}
    assert verify.verify(task, lane, base)["reason"] == "no-change"
    (lane / "a.py").write_text("x=2\n"); g("commit", "-qam", "w")
    v = verify.verify(task, lane, base)
    assert v["verdict"] == "unchecked" or v["verdict"] == "verified"
    (lane / "handoffs").mkdir(); (lane / "handoffs/h.md").write_text("x"); g("add", "."); g("commit", "-qm", "bad")
    assert verify.verify(task, lane, base)["reason"] == "forbidden-path"


def test_verify_reviewer_and_tests(tmp_path):
    lane, g, base = _lane(tmp_path)
    (lane / "a.py").write_text("x=3\n"); g("commit", "-qam", "w")
    t = {"inputs": ["a.py"], "outputs": [], "forbidden": [], "test_cmds": [], "done_when": None}
    assert verify.verify(t, lane, base, reviewer=lambda *_: {"verdict": "done"})["verdict"] == "verified"
    assert verify.verify(t, lane, base, reviewer=lambda *_: {"verdict": "drift"})["verdict"] == "rejected"
    t["test_cmds"] = ["false"]
    assert verify.verify(t, lane, base)["reason"] == "tests-fail"


def test_opencode_config_stable_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr(local_llm, "POLICY_DIR", tmp_path / "pol")
    t = {"budget": dict(schema.DEFAULT_BUDGET), "test_cmds": ["pytest tests/a.py"]}
    p1 = local_llm.write_config(tmp_path / "r1", "http://x/v1", "m", t)
    p2 = local_llm.write_config(tmp_path / "r2", "http://x/v1", "m", dict(t, test_cmds=[]))
    c1, c2 = json.loads(p1.read_text()), json.loads(p2.read_text())
    assert c1["snapshot"] is False and c1["agent"][local_llm.AGENT]["permission"]["task"] == "deny"
    assert c1["agent"][local_llm.AGENT]["permission"]["bash"]["pytest tests/a.py"] == "allow"
    assert c1["instructions"] == c2["instructions"]                                            # cacheable prefix
    del c1["agent"], c2["agent"], c1["instructions"], c2["instructions"]
    assert c1 == c2


def test_parse_events(tmp_path):
    p = tmp_path / "e.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in [
        {"type": "text", "part": {"type": "text", "text": 'ok\nTASKFLOW-RESULT {"claimed_done": true, "summary": "s", "paths": ["a"]}'}},
        {"type": "step_finish", "part": {"tokens": {"input": 100, "output": 7, "cache": {"read": 80}}}}]))
    r = local_llm.parse_events(p)
    assert r["usage"]["input"] == 100 and r["usage"]["cache_read"] == 80 and r["result"]["claimed_done"] is True


def test_failure_class():
    w = {"usage": {"steps": 3}, "errors": [], "result": None, "timed_out": False}
    assert dispatch.failure_class(w, {"verdict": "verified"}) is None
    assert dispatch.failure_class(w, {"verdict": "rejected", "reason": "tests-fail"}) == "model-limitation"
    assert dispatch.failure_class(dict(w, result={"claimed_done": False}), {"verdict": "rejected", "reason": "no-change"}) == "task"
    assert dispatch.failure_class(dict(w, usage={"steps": 0}, errors=["x"]), {"verdict": "error"}) == "harness"


def test_prefix_cache_fixes_h1_h3(tmp_path, monkeypatch):
    monkeypatch.setattr(local_llm, "POLICY_DIR", tmp_path / "pol")
    t = {"budget": dict(schema.DEFAULT_BUDGET), "test_cmds": []}
    c = json.loads(local_llm.write_config(tmp_path / "a", "http://x/v1", "m", t).read_text())
    bash = c["agent"][local_llm.AGENT]["permission"]["bash"]
    assert bash["*"] == "deny" and bash["head *"] == "allow"            # H1: output bounded by tool_output (r8: cat allowed)
    assert c["tool_output"] == {"max_lines": local_llm.TOOL_MAX_LINES, "max_bytes": local_llm.TOOL_MAX_BYTES}
    assert c["tool_output"] == {"max_lines": local_llm.TOOL_MAX_LINES, "max_bytes": local_llm.TOOL_MAX_BYTES}
    assert c["provider"][local_llm.PROVIDER]["models"]["m"]["limit"]["context"] == 65536       # H1 ctx 64k
    assert c["agent"]["title"] == {"disable": True}                                            # H2 no title call
    c2 = json.loads(local_llm.write_config(tmp_path / "b", "http://x/v1", "m", t).read_text())
    assert c["instructions"] == c2["instructions"] and "POLICY-" in c["instructions"][0]      # H3 one shared path


def test_request_digest_h5():
    body = {"messages": [{"role": "system", "content": "S"}, {"role": "user", "content": "u"}],
            "tools": [{"function": {"name": "read"}}]}
    d = local_llm.request_digest(body)
    assert d["n_messages"] == 2 and d["tools"] == ["read"] and not d["is_title"]
    assert local_llm.request_digest({"messages": [{"role": "user", "content": "t"}]})["is_title"]
    assert d["system_sha"] == local_llm.request_digest(dict(body, messages=body["messages"] + [{"role": "user", "content": "x"}]))["system_sha"]


def test_worker_env_pwd_is_lane_h4(tmp_path, monkeypatch):
    seen = {}
    real = subprocess.Popen

    class P:
        pid, returncode = 1, 0

        def __init__(self, argv, cwd, env, **kw):
            seen.update(cwd=cwd, pwd=env["PWD"], proj=env.get("OPENCODE_DISABLE_PROJECT_CONFIG"),
                        cc=env.get("OPENCODE_DISABLE_CLAUDE_CODE"))

        def communicate(self, *a, **k):
            return b"", b""

    def fake(argv, *a, **kw):
        return P(argv, **kw) if argv[0] == local_llm.OPENCODE else real(argv, *a, **kw)
    monkeypatch.setattr(local_llm.subprocess, "Popen", fake)
    monkeypatch.setattr(local_llm, "POLICY_DIR", tmp_path / "pol")
    lane = tmp_path / "lane"
    lane.mkdir()
    subprocess.run(["git", "init", "-q", str(lane)], check=True)
    t = {"handoff": "h", "id": "X", "text_sha": "a", "goal": "g", "done_when": None, "test_cmds": [], "forbidden": [],
         "inputs": [], "tier": None, "budget": dict(schema.DEFAULT_BUDGET)}
    local_llm.spawn(t, lane, tmp_path / "run", "http://x/v1")
    assert seen["cwd"] == str(lane) == seen["pwd"]
    assert seen["proj"] == "1" and seen["cc"] == "1"         # r6: lane project plugins / CLAUDE.md isolated


def test_max_tokens_cap_and_no_side_agents(tmp_path, monkeypatch):
    b = {"messages": []}
    assert local_llm.cap_max_tokens(b) and b["max_tokens"] == local_llm.MAX_TOKENS_CAP
    b = {"max_completion_tokens": 32000}
    assert local_llm.cap_max_tokens(b) and "max_completion_tokens" not in b
    b = {"max_tokens": 200}
    assert not local_llm.cap_max_tokens(b) and b["max_tokens"] == 200
    monkeypatch.setattr(local_llm, "POLICY_DIR", tmp_path / "pol")
    c = json.loads(local_llm.write_config(tmp_path / "a", "http://x/v1", "m", {"budget": dict(schema.DEFAULT_BUDGET)}).read_text())
    assert c["agent"]["summary"] == {"disable": True} and "small_model" not in c


def test_skill_named_in_words_is_an_input_and_not_forbidden():
    # hand-check of NOFOLD-1 (canary r3): a correct change to the named skill was rejected as forbidden-path
    assert ".claude/skills/kernel-promotion/" in schema.named_paths("Done when the kernel-promotion skill's fold step cites it.")
    t = {"inputs": [".claude/skills/kernel-promotion/"], "outputs": [], "forbidden": list(schema.FORBIDDEN)}
    assert verify.forbidden_hits([".claude/skills/kernel-promotion/SKILL.md"], t) == []
    assert verify.forbidden_hits([".claude/settings.json"], t) == [".claude/settings.json"]


def test_basename_resolution_and_short_lane(tmp_path, monkeypatch):
    repo = tmp_path / "r"
    (repo / "scripts/dev").mkdir(parents=True)
    (repo / "scripts/dev/m2_guards.py").write_text("x\n")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    assert schema.resolve_basename(repo, "m2_guards.py") == "scripts/dev/m2_guards.py"
    assert schema.resolve_basename(repo, "nope.py") is None
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "b"], check=True)
    subprocess.run(["git", "-C", str(repo), "update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
    monkeypatch.setitem(schema.REPOS, "epyc-root", repo)
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(tmp_path / "tf"))
    r, lane, base = dispatch.make_lane({"repo": "epyc-root"}, tmp_path / "very/long/run-2026112099/t07", "b1")
    assert len(lane.name) == 4 and lane.parent == tmp_path / "tf" and (lane / "scripts/dev/m2_guards.py").exists()
    dispatch.drop_lane(r, lane)


def test_opencode_context_follows_server_slot_ctx(tmp_path, monkeypatch):
    monkeypatch.setattr(local_llm, "POLICY_DIR", tmp_path / "pol")
    c = json.loads(local_llm.write_config(tmp_path / "a", "http://x/v1", "m", {"budget": dict(schema.DEFAULT_BUDGET)},
                                          ctx=262144).read_text())
    assert c["provider"][local_llm.PROVIDER]["models"]["m"]["limit"]["context"] == 262144


def test_unsupported_and_refs(tmp_path, monkeypatch):
    t = {"repo": "epyc-root", "inputs": [], "goal": "SYNC-16 partial top-k in ggml CUDA path; fold into the champion"}
    assert "kernel" in schema.unsupported(t)
    assert schema.unsupported(dict(t, repo="epyc-web")).startswith("repo")
    assert schema.unsupported({"repo": "epyc-root", "inputs": ["a.py"], "goal": "fix a.py"}) is None
    other = tmp_path / "other"
    (other / "docs").mkdir(parents=True)
    (other / "docs/d.md").write_text("ref\n")
    repo = tmp_path / "r"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "a.py").write_text("x\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "b"], check=True)
    subprocess.run(["git", "-C", str(repo), "update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
    monkeypatch.setitem(schema.REPOS, "epyc-root", repo)
    monkeypatch.setitem(schema.REPOS, "epyc-orchestrator", other)
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(tmp_path / "tf"))
    task = {"repo": "epyc-root", "refs": [{"repo": "epyc-orchestrator", "path": "docs/d.md"}]}
    r, lane, base = dispatch.make_lane(task, tmp_path / "run/t0", "b2")
    assert (lane / ".taskflow-refs/epyc-orchestrator/docs/d.md").read_text() == "ref\n"
    assert dispatch.commit_lane(lane, task) is False           # refs are never committed
    dispatch.drop_lane(r, lane)
    assert not lane.exists()


def _repo(path, files):
    path.mkdir(parents=True)
    for k, v in files.items():
        (path / k).parent.mkdir(parents=True, exist_ok=True)
        (path / k).write_text(v)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "b"], check=True)
    subprocess.run(["git", "-C", str(path), "update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
    return subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def test_cross_repo_bare_name_becomes_ref(tmp_path, monkeypatch):
    _repo(tmp_path / "root", {"handoffs/active/h.md": "# H\n- [ ] **Q-1** fix `src/a.py` per `prep-doc.md`\n",
                              "progress/x/prep-doc.md": "decision\n"})
    _repo(tmp_path / "orch", {"src/a.py": "x\n"})
    for k, v in (("epyc-root", tmp_path / "root"), ("epyc-orchestrator", tmp_path / "orch"),
                 ("epyc-inference-research", tmp_path / "none"), ("epyc-web", tmp_path / "none")):
        monkeypatch.setitem(schema.REPOS, k, v)
    t = schema.build({"file": "handoffs/active/h.md", "line": 2, "id": "Q-1"}, root=tmp_path / "root")
    assert t["repo"] == "epyc-orchestrator" and {"repo": "epyc-root", "path": "progress/x/prep-doc.md"} in t["refs"]


def test_rev_path_ref_packaged_via_git_show(tmp_path, monkeypatch):
    sha = _repo(tmp_path / "orch", {"tests/test_old.py": "old\n", "src/a.py": "x\n"})
    subprocess.run(["git", "-C", str(tmp_path / "orch"), "rm", "-q", "tests/test_old.py"], check=True)
    subprocess.run(["git", "-C", str(tmp_path / "orch"), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "rm"], check=True)
    subprocess.run(["git", "-C", str(tmp_path / "orch"), "update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
    assert schema.rev_paths(f"test at `{sha[:8]}:tests/test_old.py` and `src/b.py@{sha[:8]}`") == [
        (sha[:8], "tests/test_old.py"), (sha[:8], "src/b.py")]
    monkeypatch.setitem(schema.REPOS, "epyc-orchestrator", tmp_path / "orch")
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(tmp_path / "tf"))
    task = {"repo": "epyc-orchestrator", "refs": [{"repo": "epyc-orchestrator", "path": "tests/test_old.py", "rev": sha[:8]}]}
    r, lane, base = dispatch.make_lane(task, tmp_path / "run/t0", "b3")
    assert (lane / f".taskflow-refs/epyc-orchestrator@{sha[:8]}/tests/test_old.py").read_text() == "old\n"
    dispatch.drop_lane(r, lane)


def test_degeneration_guard():
    g = local_llm.DegenerationGuard()
    assert g.feed("def f(x):\n    return x + 1\n" * 3) is None
    normal = " ".join(f"word{i}" for i in range(800))
    assert local_llm.DegenerationGuard().feed(normal) is None
    loop = local_llm.DegenerationGuard()
    assert loop.feed("the same phrase again and again " * 200).startswith("repeat-ratio")
    m = local_llm.DegenerationGuard()
    assert m.feed(timings={"predicted_n": 10, "draft_n": 10, "draft_n_accepted": 9}) is None
    assert m.feed(timings={"predicted_n": 700, "draft_n": 1400, "draft_n_accepted": 60}).startswith("mtp-acceptance")
    ok = local_llm.DegenerationGuard()
    ok.feed(timings={"predicted_n": 10, "draft_n": 10, "draft_n_accepted": 9})
    assert ok.feed(timings={"predicted_n": 700, "draft_n": 900, "draft_n_accepted": 720}) is None


def test_invalid_tool_args():
    assert local_llm.invalid_tool_args('{"path": "src/a.py"}') is None
    assert local_llm.invalid_tool_args('{"path": "<parameter=../docs/x.md"}') == "tool arguments contain <parameter="
    assert local_llm.invalid_tool_args('{"pattern": "a</function>"}')


def _lane_env(tmp_path, monkeypatch, **env):
    _repo(tmp_path / "r", {"a.py": "x\n"})
    monkeypatch.setitem(schema.REPOS, "epyc-root", tmp_path / "r")
    monkeypatch.setenv("TASKFLOW_LANE_ROOT", str(tmp_path / "tf"))
    for k, v in env.items():
        monkeypatch.setattr(dispatch, k, v)


def test_lifecycle_one_worker_per_lane_and_caps(tmp_path, monkeypatch):
    _lane_env(tmp_path, monkeypatch, MAX_LANES=1, MIN_FREE_GIB=0)
    r, lane, base = dispatch.make_lane({"repo": "epyc-root"}, tmp_path / "run/t0", "l1")
    assert (lane.parent / f"{lane.name}.lane.json").exists()
    import pytest
    with pytest.raises(dispatch.LaneRefused):              # same task dir -> same lane: one worker per worktree
        dispatch.make_lane({"repo": "epyc-root"}, tmp_path / "run/t0", "l1b")
    with pytest.raises(dispatch.LaneRefused):              # lane cap
        dispatch.make_lane({"repo": "epyc-root"}, tmp_path / "run/t1", "l2")
    monkeypatch.setattr(dispatch, "MIN_FREE_GIB", 10**9)
    monkeypatch.setattr(dispatch, "MAX_LANES", 99)
    with pytest.raises(dispatch.LaneRefused):              # disk cap
        dispatch.make_lane({"repo": "epyc-root"}, tmp_path / "run/t2", "l3")
    assert dispatch.drop_lane(r, lane) and not lane.exists()


def test_lifecycle_dirty_lane_kept_then_swept_without_force(tmp_path, monkeypatch):
    _lane_env(tmp_path, monkeypatch, MIN_FREE_GIB=0)
    r, lane, base = dispatch.make_lane({"repo": "epyc-root"}, tmp_path / "run/t0", "l4")
    (lane / "a.py").write_text("worker change\n")          # aborted worker: uncommitted change
    dispatch.keep_lane(lane, "error:test", hours=1)
    assert dispatch.sweep_lanes()["kept"] == [str(lane)] and lane.exists()
    out = dispatch.sweep_lanes(now=time.time() + 7200)
    assert out["removed"] == [str(lane)] and not lane.exists()
    log = subprocess.run(["git", "-C", str(r), "log", "--format=%s", "l4"], capture_output=True, text=True).stdout
    assert "WIP left in lane" in log                      # the change survives on the lane branch
    shown = subprocess.run(["git", "-C", str(r), "show", "l4:a.py"], capture_output=True, text=True).stdout
    assert shown == "worker change\n"


def test_sweep_deletes_expired_wip_branch_and_logs_tip(tmp_path, monkeypatch):
    _lane_env(tmp_path, monkeypatch, MIN_FREE_GIB=0)
    r, lane, base = dispatch.make_lane({"repo": "epyc-root"}, tmp_path / "run/t0", "taskflow/x/00-a")
    (lane / "a.py").write_text("wip\n")
    dispatch.keep_lane(lane, "error:test", hours=1)
    out = dispatch.sweep_lanes(now=time.time() + 7200)
    assert out["branches"] == ["taskflow/x/00-a:deleted"]
    log = (tmp_path / "tf/sweep.log").read_text()
    sha = log.split(" tip ")[1].split()[0]
    assert "deleted branch taskflow/x/00-a" in log
    assert subprocess.run(["git", "-C", str(r), "show", f"{sha}:a.py"], capture_output=True, text=True).stdout == "wip\n"


def test_sweep_keeps_pinned_and_pushed_branches(tmp_path, monkeypatch):
    _lane_env(tmp_path, monkeypatch, MIN_FREE_GIB=0)
    r, lane, base = dispatch.make_lane({"repo": "epyc-root"}, tmp_path / "run/t1", "taskflow/x/01-b")
    (lane / "a.py").write_text("keep me\n")
    dispatch.keep_lane(lane, "error:test", hours=1)
    m = lane.parent / f"{lane.name}.lane.json"
    d = json.loads(m.read_text()); d["pin"] = True; m.write_text(json.dumps(d))
    assert dispatch.sweep_lanes(now=time.time() + 7200)["branches"] == ["taskflow/x/01-b:skip:pinned"]
    r2, lane2, _ = dispatch.make_lane({"repo": "epyc-root"}, tmp_path / "run/t2", "taskflow/x/02-c")
    (lane2 / "a.py").write_text("pushed\n")
    dispatch.commit_lane(lane2, {"text_sha": "z"})
    tip = subprocess.run(["git", "-C", str(r2), "rev-parse", "taskflow/x/02-c"], capture_output=True, text=True).stdout.strip()
    subprocess.run(["git", "-C", str(r2), "update-ref", "refs/remotes/origin/taskflow-x", tip], check=True)
    assert dispatch.delete_branch_if_safe(r2, "taskflow/x/02-c", base) == "skip:pushed"
    assert dispatch.delete_branch_if_safe(r2, "main") == "skip:not-taskflow"


def test_no_change_lane_branch_deleted_at_drop(tmp_path, monkeypatch):
    _lane_env(tmp_path, monkeypatch, MIN_FREE_GIB=0)
    r, lane, base = dispatch.make_lane({"repo": "epyc-root"}, tmp_path / "run/t3", "taskflow/x/03-d")
    assert dispatch.drop_lane(r, lane)
    assert not subprocess.run(["git", "-C", str(r), "rev-parse", "-q", "--verify", "refs/heads/taskflow/x/03-d"],
                              capture_output=True, text=True).stdout.strip()


def test_brief_acceptance_cd_normalised_to_lane():
    t = {"repo": "epyc-orchestrator", "acceptance": "cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/x.py"}
    assert verify.acceptance_cmd(t) == "python3 -m pytest -q tests/unit/x.py"
    assert verify.lane_cmd("cd /workspace && python3 -m pytest -q a.py", {"repo": "epyc-root"}) == "python3 -m pytest -q a.py"
    other = {"repo": "epyc-root", "acceptance": "cd /mnt/raid0/llm/harness/opencode && node --test x.ts"}
    assert verify.acceptance_cmd(other) is None            # a foreign tree is never rewritten (and not runnable)
    assert local_llm.allowed_commands(t) == ["python3 -m pytest -q tests/unit/x.py"]


def test_brief_acceptance_keeps_quoted_whitespace_after_repo_cd(tmp_path):
    command = 'python3 -c "assert len(\'one  space\') == 10"'
    supplied = f"  `cd  /workspace  &&  {command}`  "
    task = {"repo": "epyc-root", "acceptance": supplied}
    assert verify.acceptance_cmd(task) == command
    assert local_llm.allowed_commands(task) == [command]
    assert local_llm.shell_denial_hint(task).splitlines()[-1] == command
    subprocess.run(["/bin/sh", "-c", verify.acceptance_cmd(task)], cwd=tmp_path, check=True)


def test_brief_mode_off_skips_phase1_even_cross_repo(monkeypatch):
    called = []
    monkeypatch.setattr(dispatch, "_brief_lane", lambda *a, **k: called.append("lane") or (None, None))
    t = {"id": "X-1", "repo": "epyc-orchestrator", "brief_mode": "off", "brief_state": "none"}
    assert dispatch.phase1_or_skip(t, Path("/nonexistent"), Path("/nonexistent"), "http://x/v1", "local") is None
    assert called == []


def test_lane_follows_single_brief_repo(monkeypatch, tmp_path):
    monkeypatch.setitem(schema.REPOS, "epyc-orchestrator", tmp_path)
    t = schema.follow_brief_repo({"repo": "epyc-root", "where": ["epyc-orchestrator:a.py::f", "epyc-orchestrator:b.py"]})
    assert t["repo"] == "epyc-orchestrator" and t["repo_from_box"] == "epyc-root"
    (tmp_path / "a.py").write_text("x")
    tie = schema.follow_brief_repo({"repo": "epyc-root", "where": ["epyc-orchestrator:a.py", "epyc-root:x.md"]})
    assert tie["repo"] == "epyc-root"                          # a tie keeps the box's repo
    maj = schema.follow_brief_repo({"repo": "epyc-root", "refs": [],
                                    "where": ["epyc-orchestrator:a.py", "epyc-orchestrator:b.py", "epyc-root:CLAUDE.md"]})
    assert maj["repo"] == "epyc-orchestrator" and {"repo": "epyc-root", "path": "CLAUDE.md"} in maj["refs"]


def test_brief_where_paths_are_in_pathspec():
    t = {"repo": "epyc-orchestrator", "inputs": [], "outputs": [], "forbidden": list(schema.FORBIDDEN),
         "where": ["epyc-orchestrator:src/a.py::f", "epyc-root:docs/x.md"]}
    assert verify.brief_paths(t) == {"src/a.py"}
    assert verify.outside_pathspec(["src/a.py", "src/b.py"], t) == ["src/b.py"]
