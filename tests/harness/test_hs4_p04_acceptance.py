"""HS-4 P0.4 acceptance runner: offline tests (no OpenCode run, no inference)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/harness/hs4_p04_acceptance.py"


def _load():
    spec = importlib.util.spec_from_file_location("hs4_p04_acceptance", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = _load()
SID = "ses_abc"
USER = "u1"


def _tool(name, status="completed"):
    return {"type": "tool", "tool": name, "state": {"status": status}}


def _session(*parts):
    return {"info": {"id": SID}, "messages": [{"info": {}, "parts": list(parts)}]}


def _by(checks, name):
    return next(c for c in checks if c["check"] == name)


def _tap(rid, ts, keys=None, event="end"):
    e = {"event": event, "ts_epoch": ts, "request_id": rid}
    if keys is not None:
        e["request_keys"] = keys
    return e


OURS = {"x_session_id": SID, "x_user_id": USER, "x_tool_mode": "client"}


def test_loop_in_order_passes():
    checks = m.check_session(_session(_tool("read"), _tool("edit"), _tool("bash")))
    assert all(c["ok"] for c in checks)


def test_write_counts_as_the_edit_step():
    checks = m.check_session(_session(_tool("read"), _tool("write"), _tool("bash")))
    assert _by(checks, "A1-read-edit-bash-loop")["ok"]


@pytest.mark.parametrize(
    "parts",
    [
        [_tool("read"), _tool("bash")],
        [_tool("bash"), _tool("edit"), _tool("read")],
        [_tool("read"), _tool("edit", status="error"), _tool("bash")],
        [],
    ],
)
def test_incomplete_or_misordered_loop_fails(parts):
    assert not _by(m.check_session(_session(*parts)), "A1-read-edit-bash-loop")["ok"]


@pytest.mark.parametrize("extra", [{"type": "compaction"}, {"type": "subtask"}, _tool("task")])
def test_compaction_or_subtask_fails(extra):
    checks = m.check_session(_session(_tool("read"), _tool("edit"), _tool("bash"), extra))
    assert not _by(checks, "A3-no-compaction-or-subtask")["ok"]


def test_tap_keys_for_this_session_pass():
    events = [_tap("r1", 10, event="metadata"), _tap("r1", 11, OURS), _tap("r2", 12, OURS)]
    checks = m.check_tap(events, SID, USER, 0, 100, strict_window=True)
    assert all(c["ok"] for c in checks), checks


def test_no_keyed_call_fails_a2():
    checks = m.check_tap([_tap("r1", 10)], SID, USER, 0, 100, strict_window=False)
    assert not _by(checks, "A2-keys-at-top-level")["ok"]


@pytest.mark.parametrize("field,value", [("x_user_id", "other"), ("x_tool_mode", "repl")])
def test_wrong_key_value_fails_a2(field, value):
    keys = {**OURS, field: value}
    checks = m.check_tap([_tap("r1", 10, keys)], SID, USER, 0, 100, strict_window=False)
    assert not _by(checks, "A2-keys-at-top-level")["ok"]


def test_unkeyed_call_is_advisory_unless_strict():
    events = [_tap("r1", 10, OURS), _tap("side", 11)]
    loose = m.check_tap(events, SID, USER, 0, 100, strict_window=False)
    strict = m.check_tap(events, SID, USER, 0, 100, strict_window=True)
    assert _by(loose, "A4-no-unkeyed-side-calls")["ok"]
    assert not _by(strict, "A4-no-unkeyed-side-calls")["ok"]


def test_events_outside_the_window_are_ignored():
    events = [_tap("r1", 10, OURS), _tap("old", 1), _tap("late", 500, {**OURS, "x_user_id": "x"})]
    checks = m.check_tap(events, SID, USER, 5, 100, strict_window=True)
    assert all(c["ok"] for c in checks), checks


def test_another_session_in_window_fails_a4():
    events = [_tap("r1", 10, OURS), _tap("r2", 11, {**OURS, "x_session_id": "ses_other"})]
    checks = m.check_tap(events, SID, USER, 0, 100, strict_window=False)
    assert not _by(checks, "A4-no-unkeyed-side-calls")["ok"]


def test_render_config_enables_mcp_only_on_request():
    text = m.TEMPLATE.read_text()
    assert m.render_config(text, False) == text
    rendered = m.render_config(text, True)
    assert '"enabled": true' in rendered and '"enabled": false' not in rendered


IDENTITY = [
    "--harness-card-version", "hs4-p0-draft",
    "--model-role", "frontdoor",
    "--build-info", "10125 (0db32c06)",
    "--enable-thinking", "false",
]


def _step(inp, read, write=0):
    return {"type": "step-finish", "tokens": {"input": inp, "output": 5, "reasoning": 0,
                                              "cache": {"read": read, "write": write}}}


def _simulate_run(tmp_path, fixed=True):
    out = tmp_path / "p04"
    assert m.main(["prepare", "--out", str(out)]) == 0
    repo, evid = out / "repo", out / "evidence"
    if fixed:
        calc = repo / "calc.py"
        calc.write_text(calc.read_text().replace("a - b", "a + b"))
    now = time.time()
    (evid / "session-id.txt").write_text(SID + "\n")
    (evid / "window-start.txt").write_text(f"{now - 60}\n")
    (evid / "window-end.txt").write_text(f"{now - 1}\n")
    (evid / "opencode-version.txt").write_text(m.PINNED_VERSION + "\n")
    (evid / "opencode-exit.txt").write_text("0\n")
    (evid / "events.jsonl").write_text(json.dumps({"type": "tool_use", "sessionID": SID}) + "\n")
    (evid / "session.json").write_text(json.dumps(_session(
        _tool("read"), _step(100, 0, 20), _tool("edit"), _step(30, 120), _tool("bash"),
        _step(10, 150),
    )))
    tap = tmp_path / "tap.jsonl"
    tap.write_text(json.dumps(_tap("r1", now - 30, OURS)) + "\n")
    return out, evid, tap


def _verify(evid, tap, *extra):
    rc = m.main(["verify", "--evidence", str(evid), "--user-id", USER,
                 "--tap-events", str(tap), *extra])
    return rc, json.loads((evid / "verdict.json").read_text())


def test_prepare_writes_a_runnable_script(tmp_path):
    out = tmp_path / "p04"
    assert m.main(["prepare", "--out", str(out)]) == 0
    run_sh = (out / "evidence" / "run.sh").read_text()
    run_lines = [ln for ln in run_sh.splitlines() if "opencode run" in ln and not ln.startswith("#")]
    assert len(run_lines) == 1
    assert "--format json" in run_lines[0] and "--auto" not in run_lines[0]
    for var in ("EPYC_HARNESS_CARD_VERSION", "EPYC_MODEL_ROLE", "EPYC_BUILD_INFO",
                "EPYC_ENABLE_THINKING"):
        assert f"${{{var}:?" in run_sh
    assert subprocess.run(["bash", "-n", str(out / "evidence" / "run.sh")]).returncode == 0
    # Before the fix the fixture test fails.
    assert not m.check_fixture(out / "repo")["ok"]


def test_verify_passes_and_writes_sc86_beliefs(tmp_path):
    _, evid, tap = _simulate_run(tmp_path)
    rc, verdict = _verify(evid, tap, *IDENTITY)
    assert rc == 0, verdict
    assert verdict["belief_capture"]["status"] == "written"

    sys.path.insert(0, str(ROOT / "scripts" / "vidya" / "adapters"))
    import opencode_shell_run_capture as cap

    run = json.loads((evid / cap.RUN_SIDECAR_NAME).read_text())
    assert cap.validate_run_sidecar(run) == []
    assert run["counts"]["input_tokens"] == 100 + 20 + 30 + 120 + 10 + 150
    assert run["counts"]["cached_prompt_tokens"] == 270
    assert run["counts"]["passed_attempts"] == 1
    assert run["harness"]["pin"] == m.AUDITED_TIP
    assert run["config_sha256"] == cap.file_sha256(evid / "opencode.jsonc")
    rows = [json.loads(x) for x in (evid / cap.SIDECAR_NAME).read_text().splitlines()]
    assert {r["metric"] for r in rows} == set(cap.METRICS)
    assert all(cap.validate_row(r) == [] for r in rows)


def test_failed_attempt_is_recorded_not_dropped(tmp_path):
    _, evid, tap = _simulate_run(tmp_path, fixed=False)
    rc, verdict = _verify(evid, tap, *IDENTITY)
    assert rc == 1
    assert verdict["belief_capture"]["status"] == "written"
    run = json.loads((evid / "opencode_shell_run.json").read_text())
    assert run["counts"]["passed_attempts"] == 0


def test_missing_serving_identity_fails_the_verdict(tmp_path):
    _, evid, tap = _simulate_run(tmp_path)
    rc, verdict = _verify(evid, tap)
    assert rc == 1
    assert verdict["belief_capture"]["status"] == "refused"
    assert not (evid / "opencode_shell_run.beliefs.jsonl").exists()


def test_capture_can_be_skipped_explicitly(tmp_path):
    _, evid, tap = _simulate_run(tmp_path)
    rc, verdict = _verify(evid, tap, "--no-belief-capture")
    assert rc == 0, verdict
    assert verdict["belief_capture"]["status"] == "skipped"


def test_plugin_and_suite_digests_are_stable_hex():
    for value in (m.plugin_sha256(), m.task_suite_fingerprint()):
        assert len(value) == 64 and int(value, 16) >= 0
    assert m.plugin_sha256() == m.plugin_sha256()


def test_prepare_refuses_a_non_empty_directory(tmp_path):
    (tmp_path / "x").write_text("keep")
    assert m.main(["prepare", "--out", str(tmp_path)]) == 2
    assert (tmp_path / "x").read_text() == "keep"


def test_preflight_flags_an_unpinned_opencode(tmp_path):
    fake = tmp_path / "opencode"
    fake.write_text("#!/bin/bash\necho 0.0.1\n")
    fake.chmod(0o755)
    check = _by(m.preflight(str(fake)), "opencode-version-pinned")
    assert not check["ok"]
    assert f"opencode-ai@{m.PINNED_VERSION}" in check["detail"]
