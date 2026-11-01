"""handoff_sessions.py dispatcher: run ends resume the owning session, cap holds, usage limits pause.

2026-11-01 ruling: a session is resumed for NEW work only while its last `WRAPPED <sha>` is landed on origin/main
(`hs.wrapped()`), so every fixture session carries a `last_wrapup` sha and `hs.landed` is monkeypatched (no git)."""
import json
from pathlib import Path

import pytest

from scripts.coordination import handoff_sessions as hs


@pytest.fixture(autouse=True)
def _wrapups_landed(monkeypatch):
    monkeypatch.setattr(hs, "landed", lambda sha, repo=None: True)


def _setup(tmp_path, n=3, cap=2):
    F = tmp_path / "flags"
    for d in ("ready", "grants"):
        (F / d).mkdir(parents=True)
    sessions = {f"h{i}": {"handoff": f"handoffs/active/h{i}.md", "engine": "codex", "session_id": f"sid{i}",
                          "status": "suspended", "row_patterns": [f"^h{i}-"], "last_end": hs.now_iso(),
                          "last_wrapup": f"abc123{i}"} for i in range(n)}
    (F / "handoff-sessions.json").write_text(json.dumps({"max_live": cap, "sessions": sessions}))
    calls = []

    def runner(cmd, pf, out):
        calls.append((cmd, Path(pf).read_text()))
        Path(out).write_text('{"type":"thread.started","thread_id":"t-new"}\n')
        return 999999999, out  # a pid that is not alive: the next pass reaps it
    return F, calls, runner


def test_run_end_resumes_owner_with_manifest_facts(tmp_path):
    F, calls, runner = _setup(tmp_path)
    (F / "grants" / "old-h0-x.ended").write_text("rc=0")
    hs.dispatch_once(str(F), runner, seed=True)
    assert not calls
    (F / "ready" / "h0-row-v2.json").write_text(json.dumps({"id": "h0-row-v2", "schema": "epyc.row.v3", "result_path": "/r/x.json",
                                                            "decision_rule": "keep if delta>=2%"}))
    (F / "ready" / "h0-row-v2.launcher.out").write_text("start\nEND rc=127 missing binary\n")
    (F / "grants" / "h0-row-v2.ended").write_text("rc=127 time=t reason=job-rc-127:exited")
    (F / "grants" / "other-row.ended").write_text("rc=0")
    reg, st = hs.dispatch_once(str(F), runner)
    assert len(calls) == 1
    cmd, prompt = calls[0]
    assert cmd == ["codex", "exec", "resume", "--json", "sid0", "-"]
    for frag in ("h0-row-v2", "rc=127", "END rc=127 missing binary", "result_path: /r/x.json",
                 'decision_rule: "keep if delta>=2%"', "fetch origin", "BACKLOG-handoff-h0.md",
                 "file the verdict", "filing-done/h0-row-v2.FILED", "WRAPPED <sha>"):
        assert frag in prompt, frag
    assert reg["sessions"]["h0"]["status"] == "live"
    reg, _ = hs.dispatch_once(str(F), runner)  # pid not alive, wrap-up landed -> suspended, no duplicate resume
    assert reg["sessions"]["h0"]["status"] == "suspended" and len(calls) == 1


def test_unwrapped_session_is_not_resumed_for_new_work(tmp_path, monkeypatch):
    F, calls, runner = _setup(tmp_path, n=1, cap=5)
    monkeypatch.setattr(hs, "landed", lambda sha, repo=None: False)
    hs.dispatch_once(str(F), runner, seed=True)
    (F / "grants" / "h0-r.complete").write_text("complete")
    reg, st = hs.dispatch_once(str(F), runner)
    assert not calls and len(st["queue"]) == 1, "event stays queued until the wrap-up lands"
    assert "UNWRAPPED h0" in (F / "handoff-sessions.log").read_text()
    monkeypatch.setattr(hs, "landed", lambda sha, repo=None: True)
    reg, st = hs.dispatch_once(str(F), runner)
    assert len(calls) == 1 and not st["queue"]


def test_cap_queues_excess_events(tmp_path, monkeypatch):
    F, calls, runner = _setup(tmp_path, n=3, cap=2)
    hs.dispatch_once(str(F), runner, seed=True)
    monkeypatch.setattr(hs, "alive", lambda pid: bool(pid))
    for i in range(3):
        (F / "grants" / f"h{i}-r.complete").write_text("complete")
    reg, st = hs.dispatch_once(str(F), runner)
    assert len(calls) == 2 and len(st["queue"]) == 1


def test_idle_handoff_with_work_is_started_and_usage_limit_pauses(tmp_path):
    F, calls, runner = _setup(tmp_path, n=1, cap=5)
    reg = json.loads((F / "handoff-sessions.json").read_text())
    reg["sessions"]["h0"]["last_end"] = "2020-01-01T00:00:00Z"
    (F / "handoff-sessions.json").write_text(json.dumps(reg))
    (F / "BACKLOG-handoff-h0.md").write_text("- [blocked] cpu rank=1 **h0-a**\n- [qualified-armed] gpu rank=2 **h0-b**\n")
    hs.dispatch_once(str(F), runner, seed=True)
    assert len(calls) == 1 and "Continue your handoff" in calls[0][1] and "WRAPPED <sha>" in calls[0][1]
    reg = json.loads((F / "handoff-sessions.json").read_text())
    Path(reg["sessions"]["h0"]["last_output"]).write_text('{"type":"error","message":"You have hit your usage limit"}\n')
    reg, _ = hs.dispatch_once(str(F), runner)
    assert reg["paused_until"] and reg["sessions"]["h0"]["waits_on"] == ["h0-b"]
    assert "USAGE-LIMIT" in (F / "handoff-sessions.log").read_text()


def test_unpushed_wrapup_is_resumed_immediately(tmp_path, monkeypatch):
    F, calls, runner = _setup(tmp_path, n=1, cap=5)
    monkeypatch.setattr(hs, "landed", lambda sha, repo=None: False)
    reg = json.loads((F / "handoff-sessions.json").read_text())
    out = tmp_path / "o.jsonl"
    out.write_text('{"text":"done WRAPPED abc1234"}\n')
    reg["sessions"]["h0"].update(pid=999999999, last_output=str(out), status="live")
    (F / "handoff-sessions.json").write_text(json.dumps(reg))
    reg, _ = hs.dispatch_once(str(F), runner, seed=True)
    assert len(calls) == 1 and "serialized_push" in calls[0][1] and "abc1234" in calls[0][1]
    assert reg["sessions"]["h0"]["status"] == "live"
    reg, _ = hs.dispatch_once(str(F), runner)  # still not landed -> stays unpushed and retried, never suspended
    assert reg["sessions"]["h0"]["status"] != "suspended"
    monkeypatch.setattr(hs, "landed", lambda sha, repo=None: True)
    Path(reg["sessions"]["h0"]["last_output"]).write_text("WRAPPED abc1234\n")
    reg, _ = hs.dispatch_once(str(F), runner)
    assert reg["sessions"]["h0"]["status"] == "suspended"
