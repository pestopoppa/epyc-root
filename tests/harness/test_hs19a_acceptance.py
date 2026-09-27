"""HS-19a "Linked" acceptance runner: offline tests (no OpenCode run, no inference).

Synthetic `opencode export` sessions, inference-tap events and progress-log rows stand in for
a live run. The tap shape follows the orchestrator contract for the `v1_subagent_link` flag.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/harness/hs19a_acceptance.py"


def _load():
    spec = importlib.util.spec_from_file_location("hs19a_acceptance", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = _load()
PID = "ses_parent01"
CID = "ses_child01"
USER = "u1"
IDENTITY = [
    "--harness-card-version", "hs4-p0-draft",
    "--model-role", "frontdoor",
    "--build-info", "10303 (ffc1bac8)",
    "--enable-thinking", "false",
]


def _by(checks, name):
    return next(c for c in checks if c["check"] == name)


def _step(inp, read=0, out=5):
    return {"type": "step-finish", "tokens": {"input": inp, "output": out, "reasoning": 0,
                                              "cache": {"read": read, "write": 0}}}


def _assistant(agent, *parts, provider="epyc-orchestrator", model="orchestrator"):
    return {"info": {"role": "assistant", "providerID": provider, "modelID": model,
                     "agent": agent}, "parts": list(parts)}


def _task_part(child=CID, status="completed"):
    return {"type": "tool", "tool": "task", "state": {
        "status": status,
        "input": {"subagent_type": "general", "description": "find codename", "prompt": "..."},
        "metadata": {"parentSessionId": PID, "sessionId": child,
                     "model": {"providerID": "epyc-orchestrator", "modelID": "orchestrator"}},
    }}


def _parent(answer=f"CODENAME={m.CODENAME}"):
    return {"info": {"id": PID, "agent": "build"}, "messages": [
        {"info": {"role": "user"}, "parts": [{"type": "text", "text": m.TASK_PROMPT}]},
        _assistant("build", _task_part(), _step(100, 0)),
        _assistant("build", {"type": "text", "text": answer}, _step(40, 100)),
    ]}


def _child():
    return {"info": {"id": CID, "parentID": PID, "agent": "general"}, "messages": [
        {"info": {"role": "user"}, "parts": [{"type": "text", "text": "find RELEASE_CODENAME"}]},
        _assistant("general", {"type": "tool", "tool": "grep", "state": {"status": "completed"}},
                   _step(80, 0)),
        _assistant("general", {"type": "text", "text": m.CODENAME}, _step(20, 80)),
    ]}


PARENT_KEYS = {"x_session_id": PID, "x_user_id": USER, "x_tool_mode": "client",
               "x_show_routing": True, "x_agent_name": "build"}
CHILD_KEYS = {"x_session_id": CID, "x_user_id": USER, "x_tool_mode": "client",
              "x_show_routing": True, "x_agent_name": "general", "parent_session_id": PID,
              "parent_session_id_source": "header:x-parent-session-id", "subagent_depth": 1,
              "subagent_depth_basis": "observed"}
# (request_id, keys, role, server prompt tokens) per model call; matches the step-finish parts.
CALLS = [
    ("p1", PARENT_KEYS, "frontdoor", 100),
    ("c1", CHILD_KEYS, "frontdoor", 80),
    ("c2", CHILD_KEYS, "frontdoor", 20 + 80),
    ("p2", PARENT_KEYS, "frontdoor", 40 + 100),
]


def _tap_rows(now, calls=CALLS):
    rows = []
    for i, (rid, keys, role, prompt) in enumerate(calls):
        ts = now - 40 + i
        rows.append({"event": "metadata", "ts_epoch": ts, "request_id": rid, "role": role,
                     "request_keys": keys})
        rows.append({"event": "timings", "ts_epoch": ts + 0.5, "request_id": rid, "role": role,
                     "request_keys": keys, "tokens": 5, "prompt_tokens": prompt,
                     "prompt_tokens_source": "server_terminal"})
    return rows


def _progress_row(now, child=CID, parent=PID, ts_offset=-38.0):
    ts = datetime.fromtimestamp(now + ts_offset, timezone.utc)
    return {"event_type": "session_created", "task_id": "chatcmpl-1", "timestamp": ts.isoformat(),
            "data": {"kind": "harness_subagent_link", "session_id": child,
                     "parent_session_id": parent,
                     "parent_session_id_source": "header:x-parent-session-id",
                     "subagent_depth": 1, "subagent_depth_basis": "observed",
                     "name": "general", "user_id": USER}}


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def _simulate(tmp_path, *, parent=None, child=None, child_ids=(CID,), tap=None,
              progress=None, exit_rc="0"):
    """Prepare a real fixture, then drop in the evidence a successful run.sh would leave."""
    out = tmp_path / "hs19a"
    assert m.main(["prepare", "--out", str(out)]) == 0
    evid = out / "evidence"
    now = time.time()
    (evid / "window-start.txt").write_text(f"{now - 60}\n")
    (evid / "window-end.txt").write_text(f"{now - 1}\n")
    (evid / "opencode-version.txt").write_text(m.PINNED_VERSION + "\n")
    (evid / "opencode-exit.txt").write_text(exit_rc + "\n")
    (evid / "events.jsonl").write_text(json.dumps({"type": "step_start", "sessionID": PID}) + "\n")
    (evid / "parent-session-id.txt").write_text(PID + "\n")
    (evid / "parent-session.json").write_text(json.dumps(parent or _parent()))
    (evid / "child-session-ids.txt").write_text("".join(f"{c}\n" for c in child_ids))
    for cid in child_ids:
        (evid / f"child-{cid}.json").write_text(json.dumps(child or _child()))
    tap_path = tmp_path / "tap.jsonl"
    _write_jsonl(tap_path, tap(now) if callable(tap) else _tap_rows(now))
    prog_dir = tmp_path / "progress"
    rows = progress(now) if callable(progress) else [_progress_row(now)]
    day = datetime.fromtimestamp(now - 30, timezone.utc).date().isoformat()
    _write_jsonl(prog_dir / f"{day}.jsonl", rows)
    return out, evid, tap_path, prog_dir


def _verify(evid, tap, prog_dir, *extra):
    rc = m.main(["verify", "--evidence", str(evid), "--user-id", USER, "--tap-events", str(tap),
                 "--progress-log-dir", str(prog_dir), *extra])
    return rc, json.loads((evid / "verdict.json").read_text())


# ── prepare / plan ────────────────────────────────────────────────────────────


def test_prepare_writes_a_runnable_script(tmp_path):
    out = tmp_path / "hs19a"
    assert m.main(["prepare", "--out", str(out)]) == 0
    evid = out / "evidence"
    run_sh = (evid / "run.sh").read_text()
    run_lines = [ln for ln in run_sh.splitlines() if "opencode run" in ln and not ln.startswith("#")]
    assert len(run_lines) == 1
    assert "--format json" in run_lines[0] and "--auto" not in run_lines[0]
    assert '< "$EVID/prompt.txt"' in run_sh, "the prompt goes on stdin (audit pitfall 1)"
    for var in ("EPYC_USER_ID", "EPYC_HARNESS_CARD_VERSION", "EPYC_MODEL_ROLE", "EPYC_BUILD_INFO",
                "EPYC_ENABLE_THINKING"):
        assert f"${{{var}:?" in run_sh
    assert "ORCHESTRATOR_FEATURE_V1_SUBAGENT_LINK=1" in run_sh
    assert "v1_subagent_link: true" in run_sh
    assert "--profile subagents" in run_sh
    assert "opencode export \"$PARENT\"" in run_sh and "opencode export \"$CID\"" in run_sh
    assert subprocess.run(["bash", "-n", str(evid / "run.sh")]).returncode == 0
    assert (evid / "prompt.txt").read_text().strip() == m.TASK_PROMPT
    assert "@" not in m.TASK_PROMPT, "no user-typed @agent subtask path (E8)"
    assert (evid / "opencode.jsonc").read_text() == m.TEMPLATE.read_text()
    assert m.lint_config(evid / "opencode.jsonc")["ok"]
    # The fixture starts clean, and the codename is in exactly one file.
    assert m.check_repo_unmodified(out / "repo")["ok"]
    hits = [n for n, t in m.FIXTURE_FILES.items() if m.CODENAME in t]
    assert hits == ["config/release.toml"]


def test_prepare_refuses_a_non_empty_directory(tmp_path):
    (tmp_path / "x").write_text("keep")
    assert m.main(["prepare", "--out", str(tmp_path)]) == 2
    assert (tmp_path / "x").read_text() == "keep"


def test_live_template_fails_the_subagents_lint(tmp_path):
    cfg = tmp_path / "live.jsonc"
    cfg.write_text(m.p04.TEMPLATE.read_text())
    check = m.lint_config(cfg)
    assert not check["ok"] and "stampAgentName" in check["detail"]


def test_run_helpers_extract_parent_and_child_ids(tmp_path, capsys):
    events = tmp_path / "events.jsonl"
    events.write_text("\n" + json.dumps({"type": "text", "sessionID": PID}) + "\n"
                      + json.dumps({"type": "text", "sessionID": "ses_other"}) + "\n")
    assert m.main(["parent-id", "--events", str(events)]) == 0
    assert capsys.readouterr().out.strip() == PID
    session = tmp_path / "parent.json"
    doubled = _parent()
    doubled["messages"][1]["parts"].insert(0, _task_part("ses_child02"))
    doubled["messages"][1]["parts"].append(_task_part(CID))  # a repeat id is listed once
    session.write_text(json.dumps(doubled))
    assert m.main(["child-ids", "--session", str(session)]) == 0
    assert capsys.readouterr().out.split() == ["ses_child02", CID]
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    assert m.main(["parent-id", "--events", str(empty)]) == 1


# ── the full offline verify ───────────────────────────────────────────────────


def test_verify_passes_and_writes_sc86_beliefs(tmp_path):
    _, evid, tap, prog = _simulate(tmp_path)
    rc, verdict = _verify(evid, tap, prog, *IDENTITY)
    failed = [c for c in verdict["checks"] if not c["ok"]]
    assert rc == 0 and not failed, failed
    assert verdict["parent_session_id"] == PID and verdict["child_session_ids"] == [CID]
    assert verdict["belief_capture"]["status"] == "written"

    sys.path.insert(0, str(ROOT / "scripts" / "vidya" / "adapters"))
    import opencode_shell_run_capture as cap

    run = json.loads((evid / cap.RUN_SIDECAR_NAME).read_text())
    assert cap.validate_run_sidecar(run) == []
    assert run["run_id"] == f"hs19a-{PID}"
    assert run["task_suite"] == {"name": "hs19a-linked-subagent-fixture",
                                 "fingerprint": m.task_suite_fingerprint()}
    assert run["counts"]["input_tokens"] == sum(c[3] for c in CALLS)
    assert run["counts"]["cached_prompt_tokens"] == 100 + 80
    assert run["counts"]["passed_attempts"] == 1
    assert verdict["token_counts"]["input_tokens_source"] == "tap_server_terminal"
    record = json.loads((evid / "attempts.jsonl").read_text())
    assert record["task"] == "hs19a-linked-subagent-lookup"
    assert record["session_id"] == PID and record["child_session_id"] == CID
    assert record["per_session_input_tokens"] == {"parent": 240, "child": 180}
    rows = [json.loads(x) for x in (evid / cap.SIDECAR_NAME).read_text().splitlines()]
    assert {r["metric"] for r in rows} == set(cap.METRICS)
    assert all(cap.validate_row(r) == [] for r in rows)
    assert all(r["producer"] == "scripts/harness/hs19a_acceptance.py" for r in rows)
    link = _by(verdict["checks"], "S3-parent-link-recorded")
    assert "2 child call(s) checked, 2 carrying x_agent_name" in link["detail"]


def test_missing_serving_identity_fails_the_verdict(tmp_path):
    _, evid, tap, prog = _simulate(tmp_path)
    rc, verdict = _verify(evid, tap, prog)
    assert rc == 1
    assert verdict["belief_capture"]["status"] == "refused"
    assert not _by(verdict["checks"], "sc86-belief-capture")["ok"]


def test_capture_can_be_skipped_explicitly(tmp_path):
    _, evid, tap, prog = _simulate(tmp_path)
    rc, verdict = _verify(evid, tap, prog, "--no-belief-capture")
    assert rc == 0, [c for c in verdict["checks"] if not c["ok"]]
    assert verdict["belief_capture"]["status"] == "skipped"


def test_wrong_answer_is_recorded_as_a_failed_attempt(tmp_path):
    _, evid, tap, prog = _simulate(tmp_path, parent=_parent(answer="CODENAME=unknown"))
    rc, verdict = _verify(evid, tap, prog, *IDENTITY)
    assert rc == 1
    assert not _by(verdict["checks"], "T1-answer-correct")["ok"]
    assert verdict["belief_capture"]["status"] == "written"
    run = json.loads((evid / "opencode_shell_run.json").read_text())
    assert run["counts"]["passed_attempts"] == 0


def test_a_modified_repo_fails_t2(tmp_path):
    out, evid, tap, prog = _simulate(tmp_path)
    (out / "repo" / "config" / "release.toml").write_text("changed\n")
    rc, verdict = _verify(evid, tap, prog, "--no-belief-capture")
    assert rc == 1 and not _by(verdict["checks"], "T2-repo-unmodified")["ok"]


def test_verify_without_tap_file_fails_s2_to_s5(tmp_path):
    _, evid, _, prog = _simulate(tmp_path)
    rc, verdict = _verify(evid, tmp_path / "missing.jsonl", prog, "--no-belief-capture")
    assert rc == 1
    for name in ("S2-tap-keyed-parent-and-child", "S3-parent-link-recorded",
                 "S5-parent-tokens-match-tap", "S5-child-tokens-match-tap"):
        assert not _by(verdict["checks"], name)["ok"], name
    assert _by(verdict["checks"], "S4-one-logical-model")["ok"]


# ── S1: exactly one linked child ──────────────────────────────────────────────


def _s1(parent, children, child_ids):
    return _by(m.check_sessions(parent, PID, children, child_ids), "S1-one-linked-child")


def test_s1_passes_for_one_linked_child():
    assert _s1(_parent(), {CID: _child()}, [CID])["ok"]


def _no_task():
    p = _parent()
    p["messages"][1]["parts"] = [_step(100)]
    return p


def _two_tasks():
    p = _parent()
    p["messages"][1]["parts"].append(_task_part("ses_child02"))
    return p


def _task_error():
    p = _parent()
    p["messages"][1]["parts"][0] = _task_part(status="error")
    return p


def _child_with(mutate):
    c = _child()
    mutate(c)
    return c


@pytest.mark.parametrize("parent,children,ids", [
    (_no_task(), {}, []),
    (_two_tasks(), {CID: _child(), "ses_child02": _child()}, [CID, "ses_child02"]),
    (_task_error(), {CID: _child()}, [CID]),
    (_parent(), {}, [CID]),  # child export missing
    (_parent(), {CID: _child_with(lambda c: c["info"].update(parentID="ses_x"))}, [CID]),
    (_parent(), {CID: _child_with(lambda c: c["messages"][1]["parts"].append(
        {"type": "compaction"}))}, [CID]),
    (_parent(), {CID: _child_with(lambda c: c["messages"][1]["parts"].append(
        _task_part("ses_grandchild")))}, [CID]),
])
def test_s1_failures(parent, children, ids):
    assert not _s1(parent, children, ids)["ok"]


def test_s1_compaction_in_parent_fails():
    p = _parent()
    p["messages"][2]["parts"].append({"type": "compaction"})
    assert not _s1(p, {CID: _child()}, [CID])["ok"]


# ── S2 / S3 / S4 on tap calls ─────────────────────────────────────────────────


def _calls(calls=CALLS, now=1000.0):
    return m.tap_calls(_tap_rows(now, calls), 0, 2000)


def _with(keys, **changes):
    k = copy.deepcopy(keys)
    for key, value in changes.items():
        if value is None:
            k.pop(key, None)
        else:
            k[key] = value
    return k


def test_s2_s3_s4_pass_on_contract_shaped_calls():
    calls = _calls()
    checks = (m.check_tap(calls, PID, CID, USER, strict_window=True)
              + m.check_link(calls, PID, CID, "build", "general")
              + m.check_selection(calls, PID, CID, [_parent(), _child()], _parent()))
    assert all(c["ok"] for c in checks), checks


def test_s2_needs_a_child_keyed_call():
    calls = _calls([c for c in CALLS if c[1] is PARENT_KEYS])
    assert not m.check_tap(calls, PID, CID, USER, False)[0]["ok"]


def test_s2_a_foreign_session_fails_and_unkeyed_is_advisory():
    foreign = CALLS + [("f1", _with(PARENT_KEYS, x_session_id="ses_other"), "frontdoor", 1)]
    assert not m.check_tap(_calls(foreign), PID, CID, USER, False)[0]["ok"]
    rows = _tap_rows(1000.0) + [{"event": "end", "ts_epoch": 1000.0, "request_id": "side"}]
    calls = m.tap_calls(rows, 0, 2000)
    assert m.check_tap(calls, PID, CID, USER, strict_window=False)[0]["ok"]
    assert not m.check_tap(calls, PID, CID, USER, strict_window=True)[0]["ok"]


def test_s2_wrong_user_fails():
    bad = [(r, _with(k, x_user_id="other") if k is CHILD_KEYS else k, role, p)
           for r, k, role, p in CALLS]
    assert not m.check_tap(_calls(bad), PID, CID, USER, False)[0]["ok"]


def _link(child_keys=CHILD_KEYS, parent_keys=PARENT_KEYS, child_agent="general"):
    calls = [(r, child_keys if k is CHILD_KEYS else parent_keys, role, p) for r, k, role, p in CALLS]
    return m.check_link(_calls(calls), PID, CID, "build", child_agent)[0]


@pytest.mark.parametrize("source", ["body", "header:x-parent-session-id",
                                    "header:x-dynamo-parent-session-id"])
def test_s3_accepts_every_contract_source(source):
    assert _link(_with(CHILD_KEYS, parent_session_id_source=source))["ok"]


def test_s3_accepts_parent_unseen_basis_and_a_missing_agent_name():
    assert _link(_with(CHILD_KEYS, subagent_depth_basis="parent_unseen", x_agent_name=None))["ok"]


@pytest.mark.parametrize("changes", [
    {"parent_session_id": None},
    {"parent_session_id": "ses_other"},
    {"parent_session_id_source": None},
    {"parent_session_id_source": "query"},
    {"subagent_depth": 2},
    {"subagent_depth": True},
    {"subagent_depth": None},
    {"subagent_depth_basis": "guessed"},
    {"parent_session_id_mismatch": True},
    {"session_id_mismatch": True},
    {"x_agent_name": "explore"},
])
def test_s3_child_link_defects_fail(changes):
    assert not _link(_with(CHILD_KEYS, **changes))["ok"], changes


def test_s3_parent_calls_must_carry_no_link_keys():
    assert not _link(parent_keys=_with(PARENT_KEYS, parent_session_id="ses_x"))["ok"]
    assert not _link(parent_keys=_with(PARENT_KEYS, subagent_depth=0))["ok"]
    assert not _link(parent_keys=_with(PARENT_KEYS, x_agent_name="general"))["ok"]


def test_s3_without_child_calls_fails():
    calls = _calls([c for c in CALLS if c[1] is PARENT_KEYS])
    assert not m.check_link(calls, PID, CID, "build", "general")[0]["ok"]


def _selection(calls, sessions=None):
    sessions = sessions or [_parent(), _child()]
    return {c["check"]: c for c in m.check_selection(_calls(calls), PID, CID, sessions, sessions[0])}


def test_s4_child_served_by_selection_records_but_does_not_gate_the_role():
    mixed = [("p1", PARENT_KEYS, "frontdoor", 1), ("p2", PARENT_KEYS, "coder", 1),
             ("c1", CHILD_KEYS, "coder", 1)]
    check = _selection(mixed)["S4-child-served-by-selection"]
    assert check["ok"] and "child within parent's roles: True" in check["detail"]
    outside = [("p1", PARENT_KEYS, "frontdoor", 1), ("c1", CHILD_KEYS, "architect", 1)]
    check = _selection(outside)["S4-child-served-by-selection"]
    assert check["ok"]
    assert "parent roles ['frontdoor']; child roles ['architect']" in check["detail"]
    assert "child within parent's roles: False" in check["detail"]
    unserved = [("p1", PARENT_KEYS, "frontdoor", 1)]
    assert not _selection(unserved)["S4-child-served-by-selection"]["ok"]


@pytest.mark.parametrize("key", ["x_force_model", "x_force_role"])
def test_s4_any_force_pin_fails(key):
    forced = CALLS + [("x1", _with(PARENT_KEYS, **{key: "coder"}), "coder", 1)]
    assert not _selection(forced)["S4-no-force-pin"]["ok"]


def test_s4_a_second_model_in_either_export_fails():
    child = _child()
    child["messages"][1]["info"]["modelID"] = "coder-32b"
    assert not _selection(CALLS, [_parent(), child])["S4-one-logical-model"]["ok"]
    parent = _parent()
    parent["messages"][1]["parts"][0]["state"]["metadata"]["model"]["modelID"] = "other"
    assert not _selection(CALLS, [parent, _child()])["S4-one-logical-model"]["ok"]


# ── S5: token parity per session ──────────────────────────────────────────────


def test_s5_is_checked_per_session(tmp_path):
    child = _child()
    for msg in child["messages"][1:]:
        for part in msg["parts"]:
            if part["type"] == "step-finish":
                part["tokens"]["input"] = 0
                part["tokens"]["cache"]["read"] = 0
    _, evid, tap, prog = _simulate(tmp_path, child=child)
    rc, verdict = _verify(evid, tap, prog, *IDENTITY)
    assert rc == 1
    assert _by(verdict["checks"], "S5-parent-tokens-match-tap")["ok"]
    assert not _by(verdict["checks"], "S5-child-tokens-match-tap")["ok"]
    # The tap measured every call, so its count survives the client's accounting failure.
    run = json.loads((evid / "opencode_shell_run.json").read_text())
    assert run["counts"]["input_tokens"] == sum(c[3] for c in CALLS)


def test_combine_tokens_falls_back_to_sessions_unless_the_tap_measured_both():
    tap_both = {"input_tokens": 10, "session_prompt_tokens": 9, "cached_prompt_tokens": 2,
                "input_tokens_source": "tap_server_terminal"}
    sess = {"input_tokens": 7, "session_prompt_tokens": 7, "cached_prompt_tokens": 1,
            "input_tokens_source": "opencode_session"}
    both = m.combine_tokens({"parent": tap_both, "child": tap_both})
    assert (both["input_tokens"], both["input_tokens_source"]) == (20, "tap_server_terminal")
    mixed = m.combine_tokens({"parent": tap_both, "child": sess})
    assert (mixed["input_tokens"], mixed["input_tokens_source"]) == (16, "opencode_session")
    assert mixed["cached_prompt_tokens"] == 3


# ── S6: the orchestrator session log ──────────────────────────────────────────


def _s6(tmp_path, rows, strict=False, window=(100.0, 200.0), make_dir=True):
    d = tmp_path / "prog"
    if make_dir:
        day = datetime.fromtimestamp(window[0], timezone.utc).date().isoformat()
        _write_jsonl(d / f"{day}.jsonl", rows)
    return m.check_session_log(d, PID, CID, window[0], window[1], strict)


def test_s6_row_in_window_passes(tmp_path):
    assert _s6(tmp_path, [_progress_row(150.0, ts_offset=0)])["ok"]


@pytest.mark.parametrize("row", [
    _progress_row(150.0, parent="ses_other", ts_offset=0),
    _progress_row(150.0, child="ses_other", ts_offset=0),
    _progress_row(500.0, ts_offset=0),  # outside the window
    {**_progress_row(150.0, ts_offset=0), "event_type": "session_resumed"},
    {**_progress_row(150.0, ts_offset=0), "data": {**_progress_row(150.0)["data"], "kind": "repl"}},
])
def test_s6_wrong_or_late_rows_fail(tmp_path, row):
    assert not _s6(tmp_path, [row])["ok"]


def test_s6_missing_log_dir_is_advisory_unless_strict(tmp_path):
    assert _s6(tmp_path, [], make_dir=False)["ok"]
    assert not _s6(tmp_path, [], strict=True, make_dir=False)["ok"]


def test_s6_strict_verify_fails_without_the_row(tmp_path):
    _, evid, tap, prog = _simulate(tmp_path, progress=lambda now: [])
    rc, verdict = _verify(evid, tap, prog, "--no-belief-capture", "--strict-session-log")
    assert rc == 1 and not _by(verdict["checks"], "S6-session-log-link")["ok"]


def test_task_suite_fingerprint_is_stable_hex():
    value = m.task_suite_fingerprint()
    assert len(value) == 64 and int(value, 16) >= 0
    assert value == m.task_suite_fingerprint()
    assert value != m.p04.task_suite_fingerprint()
