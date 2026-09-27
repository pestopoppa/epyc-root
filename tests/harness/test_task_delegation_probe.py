"""Task-delegation probe (measurement package B): offline tests (no OpenCode run, no inference).

Synthetic `opencode export` sessions and inference-tap events stand in for a live run. The tap
shape follows the orchestrator contract: `role`/`port` per event, `request_keys` with the typed
keys, the HS-19a link keys on child calls, and (orchestrator 83b18f03) the role override a call
carried.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/harness/task_delegation_probe.py"


def _load():
    spec = importlib.util.spec_from_file_location("task_delegation_probe", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = _load()
PID, CID, CID2 = "ses_parent01", "ses_child01", "ses_child02"
USER = "u1"
IDENTITY = ["--harness-card-version", "hs4-p0-draft", "--build-info", "10303 (ffc1bac8)"]


def _by(checks, name):
    return next(c for c in checks if c["check"] == name)


def _step(inp, read=0, out=5):
    return {"type": "step-finish", "tokens": {"input": inp, "output": out, "reasoning": 0,
                                              "cache": {"read": read, "write": 0}}}


def _assistant(agent, *parts, provider="epyc-orchestrator", model="orchestrator"):
    return {"info": {"role": "assistant", "providerID": provider, "modelID": model,
                     "agent": agent}, "parts": list(parts)}


def _task_part(child=CID, status="completed", subagent="general"):
    return {"type": "tool", "tool": "task", "state": {
        "status": status,
        "input": {"subagent_type": subagent, "description": "lookup", "prompt": "..."},
        "metadata": {"parentSessionId": PID, "sessionId": child,
                     "model": {"providerID": "epyc-orchestrator", "modelID": "orchestrator"}},
    }}


def _parent(agent="build", first=None, answer=f"CODENAME={m.CODENAME}"):
    first = first if first is not None else [_task_part()]
    return {"info": {"id": PID, "agent": agent}, "messages": [
        {"info": {"role": "user"}, "parts": [{"type": "text", "text": "prompt"}]},
        _assistant(agent, *first, _step(100, 0)),
        _assistant(agent, {"type": "text", "text": answer}, _step(40, 100)),
    ]}


def _child(cid=CID, agent="general"):
    return {"info": {"id": cid, "parentID": PID, "agent": agent}, "messages": [
        {"info": {"role": "user"}, "parts": [{"type": "text", "text": "find it"}]},
        _assistant(agent, {"type": "tool", "tool": "grep", "state": {"status": "completed"}},
                   _step(80, 0)),
        _assistant(agent, {"type": "text", "text": m.CODENAME}, _step(20, 80)),
    ]}


def _keys(sid, agent, extra=None, child=False):
    k = {"x_session_id": sid, "x_user_id": USER, "x_tool_mode": "client",
         "x_show_routing": True, "x_agent_name": agent}
    if child:
        k.update({"parent_session_id": PID, "parent_session_id_source": "header:x-parent-session-id",
                  "subagent_depth": 1, "subagent_depth_basis": "observed"})
    k.update(extra or {})
    return k


def _calls(parent_role="architect_general", parent_port=8083, parent_extra=None,
           child_role="frontdoor", child_port=8070, child_extra=None, parent_agent="build",
           child_agent="general", with_child=True):
    rows = [("p1", _keys(PID, parent_agent, parent_extra), parent_role, parent_port, 100, ["task"])]
    if with_child:
        rows += [("c1", _keys(CID, child_agent, child_extra, True), child_role, child_port, 80, ["grep"]),
                 ("c2", _keys(CID, child_agent, child_extra, True), child_role, child_port, 100, [])]
    rows.append(("p2", _keys(PID, parent_agent, parent_extra), parent_role, parent_port, 140, []))
    return rows


def _tap_rows(now, calls):
    rows = []
    for i, (rid, keys, role, port, prompt, tools) in enumerate(calls):
        ts = now - 40 + i
        base = {"request_id": rid, "role": role, "port": port, "request_keys": keys}
        rows.append({"event": "metadata", "ts_epoch": ts, **base, "client_tool_calls": tools})
        rows.append({"event": "timings", "ts_epoch": ts + 0.5, **base, "tokens": 5,
                     "prompt_tokens": prompt, "prompt_tokens_source": "server_terminal"})
    return rows


def _simulate(tmp_path, *, variant="hs19a", arm="27b-think", seed=101, parent=None,
              children=None, calls=None, exit_rc="0"):
    out = tmp_path / "run"
    assert m.main(["prepare", "--out", str(out), "--variant", variant, "--arm", arm,
                   "--seed", str(seed)]) == 0
    evid = out / "evidence"
    now = time.time()
    (evid / "window-start.txt").write_text(f"{now - 60}\n")
    (evid / "window-end.txt").write_text(f"{now - 1}\n")
    (evid / "opencode-version.txt").write_text(m.PINNED_VERSION + "\n")
    (evid / "opencode-exit.txt").write_text(exit_rc + "\n")
    (evid / "events.jsonl").write_text(json.dumps({"type": "step_start", "sessionID": PID}) + "\n")
    (evid / "parent-session-id.txt").write_text(PID + "\n")
    parent = parent if parent is not None else _parent()
    (evid / "parent-session.json").write_text(json.dumps(parent))
    children = children if children is not None else {CID: _child()}
    (evid / "child-session-ids.txt").write_text("".join(f"{c}\n" for c in children))
    for cid, sess in children.items():
        (evid / f"child-{cid}.json").write_text(json.dumps(sess))
    pin = m.ARMS[arm]["force_role"]
    if calls is None:
        calls = (_calls(parent_extra={"x_force_role": pin}) if pin else
                 _calls(parent_role="frontdoor", parent_port=8070))
    tap = tmp_path / "tap.jsonl"
    tap.write_text("".join(json.dumps(r) + "\n" for r in _tap_rows(now, calls)))
    return out, evid, tap


def _verify(evid, tap, *extra):
    rc = m.main(["verify", "--evidence", str(evid), "--user-id", USER, "--tap-events", str(tap),
                 *extra])
    return rc, json.loads((evid / "verdict.json").read_text())


# ── JSONC ─────────────────────────────────────────────────────────────────────


def test_strip_jsonc_keeps_strings_and_drops_comments_and_trailing_commas():
    text = ('// head\n{ "url": "https://x.y/z", /* c */ "s": "a // b /* c */ \\" q",\n'
            '  "l": [1, 2,], "o": {"k": 1,}, // tail\n}')
    assert m.json.loads(m.strip_jsonc(text)) == {
        "url": "https://x.y/z", "s": 'a // b /* c */ " q', "l": [1, 2], "o": {"k": 1}}


def test_the_subagents_template_parses():
    cfg = m.load_jsonc(m.TEMPLATE)
    assert cfg["model"] == "epyc-orchestrator/orchestrator"
    assert cfg["permission"]["task"] == {"*": "deny", "general": "allow"}
    assert cfg["agent"]["general"] == {"permission": {"task": "deny"}}


# ── config: the pin sits on the parent only ──────────────────────────────────


@pytest.mark.parametrize("variant", sorted(m.VARIANTS))
@pytest.mark.parametrize("arm", sorted(m.ARMS))
def test_build_config_pins_only_the_primary_agent(tmp_path, variant, arm):
    v = m.VARIANTS[variant]
    cfg = m.build_config(variant, arm, 7, tmp_path / "instructions.md")
    probe = {"primary": v["primary"], "subagents": v["subagents"],
             "force_role": m.ARMS[arm]["force_role"]}
    assert m.check_config_pin(cfg, probe)["ok"]
    agents = cfg["agent"]
    assert agents[v["primary"]]["options"].get("x_force_role") == m.ARMS[arm]["force_role"]
    for sub in v["subagents"]:
        assert agents[sub]["options"] == {"seed": 7}
        assert agents[sub]["permission"]["task"] == "deny"
    assert agents[v["primary"]]["options"]["seed"] == 7
    assert all("model" not in a for a in agents.values())


def test_check_config_pin_refuses_a_misplaced_or_extra_pin(tmp_path):
    probe = {"primary": "build", "subagents": ["general"], "force_role": "architect_general"}
    cfg = m.build_config("hs19a", "27b-think", 1, None)
    child_pin = m.copy.deepcopy(cfg)
    child_pin["agent"]["general"]["options"]["x_force_role"] = "architect_general"
    assert not m.check_config_pin(child_pin, probe)["ok"]
    static = m.copy.deepcopy(cfg)
    static["plugin"][0][1]["staticKeys"]["x_force_role"] = "architect_general"
    assert not m.check_config_pin(static, probe)["ok"]
    wrong = m.copy.deepcopy(cfg)
    wrong["agent"]["build"]["options"]["x_force_role"] = "frontdoor"
    assert not m.check_config_pin(wrong, probe)["ok"]
    unpinned = m.build_config("hs19a", "fd", 1, None)
    assert not m.check_config_pin(unpinned, probe)["ok"], "a declared pin that is missing fails"
    modelled = m.copy.deepcopy(unpinned)
    modelled["agent"]["build"]["model"] = "epyc-orchestrator/orchestrator"
    assert not m.check_config_pin(modelled, {**probe, "force_role": None})["ok"]


@pytest.mark.parametrize("variant", sorted(m.VARIANTS))
def test_lint_passes_on_the_stripped_copy_and_refuses_the_pinned_config(tmp_path, variant):
    out = tmp_path / "r"
    assert m.main(["prepare", "--out", str(out), "--variant", variant, "--arm", "27b-think",
                   "--seed", "101"]) == 0
    evid = out / "evidence"
    probe = json.loads((evid / "probe.json").read_text())
    assert m.lint_stripped(evid, probe)["ok"]
    pinned = m.h.lint_config(evid / "opencode.jsonc")
    assert not pinned["ok"] and "x_force" in pinned["detail"], "the harness lint still refuses pins"


# ── prepare / schedule ───────────────────────────────────────────────────────


@pytest.mark.parametrize(("variant", "arm"), [("hs19a", "fd"), ("ds41", "27b-nothink")])
def test_prepare_writes_a_runnable_script(tmp_path, variant, arm):
    out = tmp_path / "r"
    assert m.main(["prepare", "--out", str(out), "--variant", variant, "--arm", arm,
                   "--seed", "202", "--run-id", "07-x"]) == 0
    evid = out / "evidence"
    run_sh = (evid / "run.sh").read_text()
    assert subprocess.run(["bash", "-n", str(evid / "run.sh")]).returncode == 0
    run_lines = [ln for ln in run_sh.splitlines() if "opencode run" in ln and not ln.startswith("#")]
    assert len(run_lines) == 1 and "--auto" not in run_lines[0]
    assert '< "$EVID/prompt.txt"' in run_sh and "timeout --kill-after=30 900" in run_lines[0]
    assert ("--agent planner" in run_lines[0]) == (variant == "ds41")
    assert "opencode.lint.jsonc" in run_sh and "check-config" in run_sh
    assert "workspace-76" in run_sh and "ORCHESTRATOR_FEATURE_V1_SUBAGENT_LINK=1" in run_sh
    assert "/props" in run_sh and "opencode debug agent" in run_sh
    assert (evid / "prompt.txt").read_text().strip() == m.VARIANTS[variant]["prompt"]
    assert "@" not in m.VARIANTS[variant]["prompt"], "no user-typed @agent subtask path (E8)"
    probe = json.loads((evid / "probe.json").read_text())
    assert (probe["variant"], probe["arm"], probe["seed"], probe["run_id"]) == (variant, arm, 202, "07-x")
    assert m.main(["check-config", "--evidence", str(evid)]) == 0
    assert m.h.check_repo_unmodified(out / "repo")["ok"]
    if variant == "ds41":
        assert (evid / "instructions.md").read_text() == m.DS41_INSTRUCTIONS
        cfg = m.load_jsonc(evid / "opencode.jsonc")
        assert cfg["instructions"] == [str(evid / "instructions.md")]
        assert cfg["agent"]["scout"]["description"] == m.SCOUT_DESCRIPTION
        assert "task" not in m.DS41_PROMPT, "the ds41 prompt never names the task tool"


def test_prepare_refuses_a_non_empty_directory(tmp_path):
    (tmp_path / "x").write_text("keep")
    assert m.main(["prepare", "--out", str(tmp_path), "--variant", "hs19a", "--arm", "fd",
                   "--seed", "1"]) == 2
    assert (tmp_path / "x").read_text() == "keep"


def test_check_config_fails_after_tampering(tmp_path):
    out = tmp_path / "r"
    m.main(["prepare", "--out", str(out), "--variant", "hs19a", "--arm", "27b-think", "--seed", "1"])
    evid = out / "evidence"
    cfg = m.load_jsonc(evid / "opencode.jsonc")
    cfg["agent"]["general"]["options"]["x_force_role"] = "architect_general"
    (evid / "opencode.jsonc").write_text(json.dumps(cfg))
    assert m.main(["check-config", "--evidence", str(evid)]) == 1


def test_schedule_is_aba_and_paired_by_seed():
    rows = m.schedule()
    assert len(rows) == 18 and len({r[0] for r in rows}) == 18
    v1 = [(a, s) for _, v, a, s in rows if v == "hs19a"]
    assert [a for a, _ in v1] == ["fd", "27b-nothink", "27b-think", "27b-think", "27b-nothink", "fd",
                                  "fd", "27b-nothink", "27b-think"]
    assert [s for _, s in v1] == [101] * 3 + [202] * 3 + [303] * 3
    v2 = [a for _, v, a, _ in rows[9:15]]
    assert v2 == ["fd", "27b-think", "27b-think", "fd", "fd", "27b-think"]
    assert [(v, a) for _, v, a, _ in rows[15:]] == [("ds41", "27b-nothink")] * 3
    assert len(m.schedule(include_conditional=False)) == 15


def test_prepare_all_writes_every_run_and_one_conditional_header(tmp_path):
    root = tmp_path / "probe"
    assert m.main(["prepare-all", "--out-root", str(root)]) == 0
    text = (root / "SCHEDULE.txt").read_text()
    runs = [ln for ln in text.splitlines() if ln.startswith("bash ")]
    assert len(runs) == 18 and text.count("# CONDITIONAL") == 1
    assert text.index("# CONDITIONAL") > text.index("15-ds41-27b-think-s303")
    assert all(Path(ln.split(" ", 1)[1]).is_file() for ln in runs)
    assert m.main(["prepare-all", "--out-root", str(root)]) == 2


# ── verify ───────────────────────────────────────────────────────────────────


def test_verify_pinned_parent_and_unpinned_child_is_valid_and_delegated(tmp_path):
    _, evid, tap = _simulate(tmp_path)
    rc, v = _verify(evid, tap, "--no-belief-capture")
    failed = [c for c in v["checks"] if not c["ok"]]
    assert rc == 0 and v["valid"] and not failed, failed
    assert v["outcome"] == "delegated" and v["delegated"] and v["answer_correct"]
    assert v["pin"] == {"field": "x_force_role", "role": "architect_general", "agent": "build",
                        "child_agents_unpinned": ["general"]}
    c2 = _by(v["checks"], "C2-parent-pinned")
    assert "basis: tap request_keys" in c2["detail"] and "[8083]" in c2["detail"]
    assert "ports [8070]" in _by(v["checks"], "C3-child-unpinned")["detail"]
    assert v["observations"]["tap"]["parent_override_keys"] == [{"x_force_role": "architect_general"}] * 2
    assert v["observations"]["tap"]["parent_tool_calls_parsed"] == ["task"]


def test_verify_falls_back_to_the_served_port_when_the_tap_has_no_override_keys(tmp_path):
    _, evid, tap = _simulate(tmp_path, calls=_calls())
    rc, v = _verify(evid, tap, "--no-belief-capture")
    assert rc == 0 and v["valid"]
    assert "basis: served port" in _by(v["checks"], "C2-parent-pinned")["detail"]
    rc, v = _verify(evid, tap, "--no-belief-capture", "--require-tap-pin")
    assert rc == 1 and not v["valid"]


@pytest.mark.parametrize("calls", [
    _calls(parent_port=8070, parent_role="frontdoor", parent_extra={"x_force_role": "architect_general"}),
    _calls(parent_extra={"x_force_role": "coder_escalation"}),
    _calls(parent_extra={"x_force_role": "architect_general"}, child_extra={"x_force_role": "architect_general"}),
    _calls(parent_extra={"x_force_role": "architect_general"}, child_port=8083, child_role="architect_general"),
    _calls(parent_extra={"x_force_role": "architect_general"}, child_extra={"x_orchestrator_role": "frontdoor"}),
])
def test_verify_invalidates_a_wrong_pin_or_a_pinned_child(tmp_path, calls):
    _, evid, tap = _simulate(tmp_path, calls=calls)
    rc, v = _verify(evid, tap, "--no-belief-capture")
    assert rc == 1 and not v["valid"]
    assert not (_by(v["checks"], "C2-parent-pinned")["ok"] and _by(v["checks"], "C3-child-unpinned")["ok"])


def test_verify_unpinned_arm(tmp_path):
    _, evid, tap = _simulate(tmp_path, arm="fd")
    rc, v = _verify(evid, tap, "--no-belief-capture")
    assert rc == 0 and v["valid"] and v["outcome"] == "delegated"
    assert _by(v["checks"], "C2-parent-unpinned")["ok"]
    pinned_fd = _calls(parent_role="frontdoor", parent_port=8070, parent_extra={"x_force_role": "frontdoor"})
    _, evid2, tap2 = _simulate(tmp_path / "b", arm="fd", calls=pinned_fd)
    rc, v = _verify(evid2, tap2, "--no-belief-capture")
    assert rc == 1 and not _by(v["checks"], "C2-parent-unpinned")["ok"]


@pytest.mark.parametrize(("first", "answer", "outcome"), [
    ([{"type": "text", "text": '<tool_call>\n{"name": "task", "arguments": {}}\n</tool_call>'}],
     "no idea", "unparsed_attempt"),
    ([{"type": "tool", "tool": "grep", "state": {"status": "completed"}}],
     f"CODENAME={m.CODENAME}", "self_served"),
    ([], f"CODENAME={m.CODENAME}", "no_tool"),
    ([_task_part(status="error")], "failed", "delegated_failed"),
])
def test_non_delegating_outcomes_are_valid_runs(tmp_path, first, answer, outcome):
    calls = _calls(parent_extra={"x_force_role": "architect_general"}, with_child=False)
    children = {} if outcome != "delegated_failed" else {}
    _, evid, tap = _simulate(tmp_path, parent=_parent(first=first, answer=answer),
                             children=children, calls=calls)
    rc, v = _verify(evid, tap, "--no-belief-capture")
    assert v["outcome"] == outcome and not v["delegated"]
    assert rc == 0 and v["valid"], [c for c in v["checks"] if not c["ok"]]
    assert "n/a: no child session" in _by(v["checks"], "C3-child-unpinned")["detail"]


def test_verify_ds41_two_scouts(tmp_path):
    parent = _parent(agent="planner", first=[_task_part(CID, subagent="scout"),
                                             _task_part(CID2, subagent="scout")],
                     answer=f"CODENAME={m.CODENAME}\nMAX_RETRIES=13")
    children = {CID: _child(CID, "scout"), CID2: _child(CID2, "scout")}
    calls = _calls(parent_extra={"x_force_role": "architect_general"}, parent_agent="planner",
                   child_agent="scout")
    _, evid, tap = _simulate(tmp_path, variant="ds41", parent=parent, children=children, calls=calls)
    rc, v = _verify(evid, tap, "--no-belief-capture")
    assert rc == 0 and v["valid"] and v["outcome"] == "delegated" and v["answer_correct"]
    assert v["classification"]["subagent_types"] == ["scout", "scout"]
    assert sorted(v["classification"]["linked_children"]) == [CID, CID2]


def test_verify_writes_sc86_beliefs_for_a_valid_run(tmp_path):
    _, evid, tap = _simulate(tmp_path)
    rc, v = _verify(evid, tap, *IDENTITY)
    assert rc == 0 and v["belief_capture"]["status"] == "written", v["belief_capture"]
    sys.path.insert(0, str(ROOT / "scripts" / "vidya" / "adapters"))
    import opencode_shell_run_capture as cap

    run = json.loads((evid / cap.RUN_SIDECAR_NAME).read_text())
    assert cap.validate_run_sidecar(run) == []
    assert run["serving"]["model_role"] == "architect_general"
    assert run["serving"]["enable_thinking"] is True
    assert run["task_suite"]["name"] == "task-delegation-probe-hs19a"
    record = json.loads((evid / "attempts.jsonl").read_text())
    assert record["passed"] and record["arm"] == "27b-think" and record["outcome"] == "delegated"


def test_invalid_run_writes_no_beliefs(tmp_path):
    _, evid, tap = _simulate(tmp_path, calls=_calls(parent_port=8070, parent_role="frontdoor"))
    rc, v = _verify(evid, tap, *IDENTITY)
    assert rc == 1 and v["belief_capture"]["status"] == "skipped"
    assert "not valid" in v["belief_capture"]["reason"]


# ── the decision rule ────────────────────────────────────────────────────────


def _cells(**states):
    """states: key 'v1_fd' etc. -> (delegated, valid[, outcomes])."""
    names = {"v1_fd": ("hs19a", "fd"), "v1_nt": ("hs19a", "27b-nothink"),
             "v1_th": ("hs19a", "27b-think"), "v2_fd": ("ds41", "fd"),
             "v2_th": ("ds41", "27b-think"), "v2_nt": ("ds41", "27b-nothink")}
    out = {}
    for key, spec in states.items():
        d, n, *rest = spec
        outcome = rest[0] if rest else "self_served"
        verdicts = ([{"valid": True, "delegated": True, "outcome": "delegated"}] * d
                    + [{"valid": True, "delegated": False, "outcome": outcome}] * (n - d))
        out[names[key]] = m.cell_state(verdicts)
    return out


@pytest.mark.parametrize(("states", "verdict"), [
    (dict(v1_fd=(3, 3), v1_nt=(3, 3)), "INCOMPLETE"),
    (dict(v1_fd=(1, 3), v1_nt=(0, 3), v1_th=(0, 3)), "CONTROL_FAILED"),
    (dict(v1_fd=(3, 3), v1_nt=(1, 3), v1_th=(0, 3)), "INCONCLUSIVE"),
    (dict(v1_fd=(3, 3), v1_nt=(0, 3), v1_th=(0, 3)), "MODEL"),
    (dict(v1_fd=(3, 3), v1_nt=(3, 3), v1_th=(0, 3)), "SETUP"),
    (dict(v1_fd=(3, 3), v1_nt=(3, 3), v1_th=(3, 3)), "SETUP (V1)"),
    (dict(v1_fd=(3, 3), v1_nt=(3, 3), v1_th=(2, 3), v2_fd=(3, 3), v2_th=(0, 3)), "PENDING_CONDITIONAL"),
    (dict(v1_fd=(3, 3), v1_nt=(3, 3), v1_th=(3, 3), v2_fd=(3, 3), v2_th=(0, 3), v2_nt=(3, 3)), "SETUP"),
    (dict(v1_fd=(3, 3), v1_nt=(3, 3), v1_th=(3, 3), v2_fd=(3, 3), v2_th=(0, 3), v2_nt=(0, 3)),
     "MODEL (propensity)"),
    (dict(v1_fd=(3, 3), v1_nt=(3, 3), v1_th=(3, 3), v2_fd=(0, 3), v2_th=(0, 3)), "SETUP"),
    (dict(v1_fd=(3, 3), v1_nt=(3, 3), v1_th=(3, 3), v2_fd=(3, 3), v2_th=(3, 3)), "SETUP"),
    (dict(v1_fd=(3, 3), v1_nt=(3, 3), v1_th=(3, 3), v2_fd=(0, 3), v2_th=(3, 3)), "SETUP"),
    (dict(v1_fd=(3, 3), v1_nt=(3, 3), v1_th=(3, 3), v2_fd=(3, 3), v2_th=(1, 3)),
     "SETUP (V1); ds41 INCONCLUSIVE"),
])
def test_decision_rule(states, verdict):
    d = m.decide(_cells(**states))
    assert d["verdict"] == verdict, d
    assert d["run_conditional_block"] == (verdict == "PENDING_CONDITIONAL")


def test_model_verdict_names_the_parser_when_attempts_are_unparsed():
    d = m.decide(_cells(v1_fd=(3, 3), v1_nt=(0, 3, "unparsed_attempt"), v1_th=(0, 3)))
    assert d["verdict"] == "MODEL" and "parser" in d["qualifier"]
    d = m.decide(_cells(v1_fd=(3, 3), v1_nt=(0, 3, "self_served"), v1_th=(0, 3)))
    assert "behavioural" in d["qualifier"]


def test_invalid_runs_do_not_count():
    verdicts = [{"valid": True, "delegated": True, "outcome": "delegated"}] * 2 + [
        {"valid": False, "delegated": True, "outcome": "delegated"}]
    c = m.cell_state(verdicts)
    assert c == {"state": "incomplete", "valid": 2, "delegated": 2, "invalid": 1,
                 "outcomes": {"delegated": 2}}


def test_summarize_reads_every_verdict(tmp_path):
    root = tmp_path / "probe"
    for i, (variant, arm, deleg) in enumerate([("hs19a", "fd", True)] * 3 + [("hs19a", "27b-nothink", False)] * 3
                                              + [("hs19a", "27b-think", False)] * 3):
        evid = root / f"{i:02d}" / "evidence"
        evid.mkdir(parents=True)
        (evid / "verdict.json").write_text(json.dumps({
            "variant": variant, "arm": arm, "valid": True, "delegated": deleg,
            "outcome": "delegated" if deleg else "self_served"}))
    assert m.main(["summarize", "--root", str(root)]) == 0
    s = json.loads((root / "summary.json").read_text())
    assert s["runs"] == 9 and s["decision"]["verdict"] == "MODEL"
    assert s["cells"]["hs19a/fd"]["state"] == "yes"
