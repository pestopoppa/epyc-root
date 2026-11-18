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
    monkeypatch.setattr(hs, "tmux", lambda *a, **k: (1, ""))  # never reach a tmux server (INC-20260806 guard)
    monkeypatch.setattr(hs.tg, "admit", lambda conf, budget, kind="work": (True, "test"))  # no live codex meter
    monkeypatch.setattr(hs.tg, "resume_verdict", lambda e, now, conf: (True, "test"))  # G2 no-progress parking is not under test here
    real_decide = hs.decide  # fixture sessions are event-driven: with no report of their own they idle (the live
    monkeypatch.setattr(hs, "decide", lambda flags, slug, e, *a, **k:  # default "missing report -> go on" would resume them)
                        real_decide(flags, slug, e, *a, **k) if e.get("last_report") else ("pause", "test: no report"))


def _setup(tmp_path, n=3, cap=2):
    F = tmp_path / "flags"
    for d in ("ready", "grants"):
        (F / d).mkdir(parents=True)
    sessions = {f"h{i}": {"handoff": f"handoffs/active/h{i}.md", "engine": "codex", "session_id": f"sid{i}",
                          "status": "suspended", "row_patterns": [f"^h{i}-"], "last_end": hs.now_iso(),
                          "last_wrapup": f"abc123{i}"} for i in range(n)}
    (F / "handoff-sessions.json").write_text(json.dumps({"max_live": cap, "auto_start": False, "sessions": sessions}))  # no auto-start from the real repo index
    calls = []

    def runner(cmd, pf, out):
        calls.append((cmd, Path(pf).read_text()))
        Path(out).write_text('{"type":"thread.started","thread_id":"t-new"}\n')
        return 999999999, out  # a pid that is not alive: the next pass reaps it
    return F, calls, runner


def _manifest(F, rid, **kw):
    """Rows route to their owner by the manifest's handoff_task (bg.pilot_of, operator 2026-11-02), not by rid pattern."""
    (F / "ready" / f"{rid}.json").write_text(json.dumps({"id": rid, "schema": "epyc.row.v3",
                                                         "handoff_task": f"handoffs/active/{rid.split('-')[0]}.md", **kw}))


def test_run_end_resumes_owner_with_manifest_facts(tmp_path):
    F, calls, runner = _setup(tmp_path)
    (F / "grants" / "old-h0-x.ended").write_text("rc=0")
    hs.dispatch_once(str(F), runner, seed=True)
    assert not calls
    _manifest(F, "h0-row-v2", result_path="/r/x.json", decision_rule="keep if delta>=2%")
    (F / "ready" / "h0-row-v2.launcher.out").write_text("start\nEND rc=127 missing binary\n")
    (F / "grants" / "h0-row-v2.ended").write_text("rc=127 time=t reason=job-rc-127:exited")
    (F / "grants" / "other-row.ended").write_text("rc=0")
    reg, st = hs.dispatch_once(str(F), runner)
    assert len(calls) == 1
    cmd, prompt = calls[0]
    assert cmd[:4] == ["codex", "exec", "resume", "--json"] and cmd[-2:] == ["sid0", "-"]  # model pin sits between
    for frag in ("h0-row-v2", "rc=127", "END rc=127 missing binary", "result_path: /r/x.json",
                 'decision_rule: "keep if delta>=2%"', "origin/main was merged in", "BACKLOG-handoff-h0.md",
                 "verdict", "filing-done/h0-row-v2.FILED", "WRAPPED <sha>"):
        assert frag in prompt, frag
    assert reg["sessions"]["h0"]["status"] == "live"
    (F / "filing-done").mkdir(exist_ok=True)
    (F / "filing-done" / "h0-row-v2.FILED").write_text("")  # DSH-2: the receipt acks the event (else it is redelivered)
    reg, _ = hs.dispatch_once(str(F), runner)  # pid not alive, wrap-up landed -> suspended, no duplicate resume
    assert reg["sessions"]["h0"]["status"] == "suspended" and len(calls) == 1


def test_unwrapped_session_is_not_resumed_for_new_work(tmp_path, monkeypatch):
    F, calls, runner = _setup(tmp_path, n=1, cap=5)
    monkeypatch.setattr(hs, "landed", lambda sha, repo=None: False)
    hs.dispatch_once(str(F), runner, seed=True)
    _manifest(F, "h0-r")
    (F / "grants" / "h0-r.complete").write_text("complete")
    reg, st = hs.dispatch_once(str(F), runner)
    assert len(st["queue"]) == 1, "event stays queued until the wrap-up lands"
    # 01420487d: the owner is nudged at once to land its wrap-up, never handed the new run end
    assert calls and all("FIRST fix and land your wrap-up" in p and "Run end" not in p for _, p in calls)
    assert "UNWRAPPED h0" in (F / "handoff-sessions.log").read_text()
    monkeypatch.setattr(hs, "landed", lambda sha, repo=None: True)
    reg, st = hs.dispatch_once(str(F), runner)
    assert "Run end" in calls[-1][1] and "`h0-r`" in calls[-1][1] and not st["queue"]


def test_cap_queues_excess_events(tmp_path, monkeypatch):
    F, calls, runner = _setup(tmp_path, n=4, cap=2)
    hs.dispatch_once(str(F), runner, seed=True)
    monkeypatch.setattr(hs, "alive", lambda pid: bool(pid))
    for i in range(4):
        _manifest(F, f"h{i}-r")
        (F / "grants" / f"h{i}-r.complete").write_text("complete")
    reg, st = hs.dispatch_once(str(F), runner)
    assert len(calls) == 2 + hs.FILING_SLOTS and len(st["queue"]) == 1  # DSH-4: one filing slot above max_live


def test_idle_handoff_with_work_is_started_and_usage_limit_pauses(tmp_path):
    F, calls, runner = _setup(tmp_path, n=1, cap=5)
    reg = json.loads((F / "handoff-sessions.json").read_text())
    reg["sessions"]["h0"]["last_end"] = "2020-01-01T00:00:00Z"
    reg["sessions"]["h0"]["last_report"] = {"next": "h0-a"}  # the session reported open work -> go on
    (F / "handoff-sessions.json").write_text(json.dumps(reg))
    (F / "BACKLOG-handoff-h0.md").write_text("- [blocked] cpu rank=1 **h0-a**\n- [qualified-armed] gpu rank=2 **h0-b**\n")
    hs.dispatch_once(str(F), runner, seed=True)
    assert len(calls) == 1 and "go on: next=h0-a" in calls[0][1] and "WRAPPED <sha>" in calls[0][1]
    reg = json.loads((F / "handoff-sessions.json").read_text())
    Path(reg["sessions"]["h0"]["last_output"]).write_text('{"type":"error","message":"You have hit your usage limit"}\n')
    reg, _ = hs.dispatch_once(str(F), runner)
    assert reg["engine_pause"]["codex"]["until"] and reg["sessions"]["h0"]["waits_on"] == ["h0-b"]
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


def test_event_resume_honours_fresh_next(tmp_path):
    """2026-11-17: a run-end/alert resume ignored fresh_next and replayed a 115M-token thread into the G2 kill."""
    F, calls, runner = _setup(tmp_path, n=1, cap=2)
    reg = json.loads((F / "handoff-sessions.json").read_text())
    reg["sessions"]["h0"]["fresh_next"] = True
    (F / "handoff-sessions.json").write_text(json.dumps(reg))
    hs.dispatch_once(str(F), runner, seed=True)
    _manifest(F, "h0-row-v3")
    (F / "grants" / "h0-row-v3.ended").write_text("rc=0")
    reg, _ = hs.dispatch_once(str(F), runner)
    assert calls, "event did not resume the owner"
    cmd, prompt = calls[-1]
    assert "resume" not in cmd and "sid0" not in cmd, cmd
    assert "h0-row-v3" in prompt
    assert not reg["sessions"]["h0"].get("fresh_next")


def _ended_turn(tmp_path, F):
    reg = json.loads((F / "handoff-sessions.json").read_text())
    out = tmp_path / "o.jsonl"
    out.write_text('{"text":"done WRAPPED abc1230"}\n')
    reg["sessions"]["h0"].update(pid=999999999, last_output=str(out), status="live")
    (F / "handoff-sessions.json").write_text(json.dumps(reg))


def test_turn_end_closes_window_when_not_restarting(tmp_path, monkeypatch):
    """2026-11-17: no lingering pane-status window after a turn that is not followed by an immediate restart."""
    F, calls, runner = _setup(tmp_path, n=1, cap=5)
    killed = []
    monkeypatch.setattr(hs, "kill_window", lambda slug: killed.append(slug))
    _ended_turn(tmp_path, F)
    reg, _ = hs.dispatch_once(str(F), runner, seed=True)
    assert reg["sessions"]["h0"]["status"] == "suspended" and killed == ["h0"] and not calls


def test_turn_end_keeps_window_when_unpushed_restart_follows(tmp_path, monkeypatch):
    F, calls, runner = _setup(tmp_path, n=1, cap=5)
    killed = []
    monkeypatch.setattr(hs, "kill_window", lambda slug: killed.append(slug))
    monkeypatch.setattr(hs, "landed", lambda sha, repo=None: False)
    _ended_turn(tmp_path, F)
    hs.dispatch_once(str(F), runner, seed=True)
    assert killed == [] and len(calls) == 1


def test_kill_window_respects_protected_and_start_recreates(monkeypatch):
    seen = []
    monkeypatch.setattr(hs, "tmux_has_window", lambda slug: False)
    monkeypatch.setattr(hs, "tmux", lambda *a, **k: (seen.append(a), (1, ""))[1])
    hs.launch_in_tmux("h0", ["true"], "/dev/null", "/nonexistent/o.jsonl", "/")
    assert seen and seen[0][0] == "new-window"  # START after a close recreates the window by name
    seen.clear()
    monkeypatch.setattr(hs, "tmux_has_window", lambda slug: True)
    monkeypatch.setattr(hs, "window_name", lambda slug: slug)
    hs.kill_window("codex-gen")
    assert seen == []
    hs.kill_window("h0")
    assert seen and seen[0][0] == "kill-window"


# --- HS-LANE-REAP-SPAM: locked lanes skipped, failures logged once, REAPED only on success ---
class _R:
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def _reap_setup(monkeypatch, tmp_path, *, locked, remove_rc=0):
    lane = tmp_path / "h-x"
    lane.mkdir()
    calls, logs = [], []

    def fake_git(cwd, *args, timeout=300):
        calls.append(args)
        if args[:2] == ("worktree", "list"):
            out = f"worktree {tmp_path}/main\nHEAD abc\n\nworktree {lane}\nHEAD def\n"
            if locked:
                out += "locked Active session\n"
            return _R(out=out)
        if args[:2] == ("worktree", "remove"):
            assert "--force" not in args
            return _R(rc=remove_rc, err="fatal: boom" if remove_rc else "")
        return _R()

    monkeypatch.setattr(hs, "_git", fake_git)
    monkeypatch.setattr(hs, "alive", lambda pid: False)
    monkeypatch.setattr(hs, "lane_dir", lambda slug: str(lane))
    monkeypatch.setattr(hs, "lane_clean_and_landed", lambda d: True)
    monkeypatch.setattr(hs, "log", lambda flags, msg: logs.append(msg))
    reg = {"sessions": {"x": {"status": "suspended"}}}
    return reg, calls, logs


def test_reap_skips_locked_lane_and_logs_once(monkeypatch, tmp_path):
    reg, calls, logs = _reap_setup(monkeypatch, tmp_path, locked=True)
    for _ in range(5):
        hs.reap_lanes({}, reg, repo=str(tmp_path))
    assert not any(a[:2] == ("worktree", "remove") for a in calls)
    assert not any("unlock" in a for a in calls)
    assert len(logs) == 1 and logs[0].startswith("LANE-LOCKED")


def test_reap_failure_logged_once_never_as_reaped(monkeypatch, tmp_path):
    reg, calls, logs = _reap_setup(monkeypatch, tmp_path, locked=False, remove_rc=128)
    for _ in range(5):
        hs.reap_lanes({}, reg, repo=str(tmp_path))
    assert len(logs) == 1 and logs[0].startswith("LANE-REAP-FAILED")
    assert not any("LANE-REAPED" in m for m in logs)


def test_reap_success_logs_reaped(monkeypatch, tmp_path):
    reg, calls, logs = _reap_setup(monkeypatch, tmp_path, locked=False)
    hs.reap_lanes({}, reg, repo=str(tmp_path))
    assert len(logs) == 1 and logs[0].startswith("LANE-REAPED")


# HS-DUPLICATE-EVENT-TURNS: duplicate, replayed and superseded run ends are dropped before they cost a turn.
def _filed(F, rid):
    (F / "filing-done").mkdir(exist_ok=True)
    (F / "filing-done" / f"{rid}.FILED").write_text("")


def test_row_base_parses_revision_anywhere():
    assert hs.row_base("h0-x") == ("h0-x", 1)
    assert hs.row_base("h0-x-r3") == ("h0-x", 3)
    assert hs.row_base("h0-bank-r2-20261118") == ("h0-bank-20261118", 2)
    assert hs.superseded_by("h0-x", ["h0-x-r2", "h0-x-r3", "h1-x-r9"]) == "h0-x-r3"
    assert hs.superseded_by("h0-x-r3", ["h0-x-r2"]) is None


def test_twin_end_file_after_delivery_is_dropped(tmp_path):
    F, calls, runner = _setup(tmp_path, n=1, cap=5)
    hs.dispatch_once(str(F), runner, seed=True)
    _manifest(F, "h0-r")
    (F / "grants" / "h0-r.ended").write_text("rc=0")
    reg, st = hs.dispatch_once(str(F), runner)
    assert len(calls) == 1 and "h0-r" in st["delivered"]  # first delivery always goes through
    _filed(F, "h0-r")
    hs.dispatch_once(str(F), runner)  # turn ends, receipt present
    (F / "grants" / "h0-r.complete").write_text("complete")  # the .complete twin lands later
    reg, st = hs.dispatch_once(str(F), runner)
    assert len(calls) == 1 and not st["queue"]
    assert "DEDUPE-DELIVERED h0-r -> h0" in (F / "handoff-sessions.log").read_text()


def test_prefiled_row_is_still_delivered_once(tmp_path):
    F, calls, runner = _setup(tmp_path, n=1, cap=5)
    hs.dispatch_once(str(F), runner, seed=True)
    _manifest(F, "h0-r")
    _filed(F, "h0-r")
    (F / "grants" / "h0-r.complete").write_text("complete")  # filed before the owner saw it
    hs.dispatch_once(str(F), runner)
    assert len(calls) == 1  # operator 2026-11-18: first delivery kept
    (F / "grants" / "h0-r.ended").write_text("rc=0")  # the twin is still a duplicate
    hs.dispatch_once(str(F), runner)
    assert len(calls) == 1


def test_lower_revision_after_higher_delivered_is_superseded(tmp_path):
    F, calls, runner = _setup(tmp_path, n=1, cap=5)
    hs.dispatch_once(str(F), runner, seed=True)
    _manifest(F, "h0-x-r2")
    (F / "grants" / "h0-x-r2.complete").write_text("complete")
    hs.dispatch_once(str(F), runner)
    _filed(F, "h0-x-r2")
    hs.dispatch_once(str(F), runner)
    _manifest(F, "h0-x")
    (F / "grants" / "h0-x.ended").write_text("rc=1")  # a late failure of the superseded r1
    reg, st = hs.dispatch_once(str(F), runner)
    assert len(calls) == 1 and not st["queue"]
    assert "SUPERSEDED h0-x -> h0: superseded by h0-x-r2" in (F / "handoff-sessions.log").read_text()


def test_queued_lower_revision_dropped_when_higher_queued(tmp_path, monkeypatch):
    F, calls, runner = _setup(tmp_path, n=1, cap=5)
    hs.dispatch_once(str(F), runner, seed=True)
    monkeypatch.setattr(hs, "landed", lambda sha, repo=None: False)  # hold events in the queue
    _manifest(F, "h0-y")
    (F / "grants" / "h0-y.ended").write_text("rc=1")
    _, st = hs.dispatch_once(str(F), runner)
    assert [e["rid"] for e in st["queue"]] == ["h0-y"]
    _manifest(F, "h0-y-r2")
    (F / "grants" / "h0-y-r2.complete").write_text("complete")
    monkeypatch.setattr(hs, "landed", lambda sha, repo=None: True)
    n0 = len(calls)
    _, st = hs.dispatch_once(str(F), runner)
    assert not st["queue"] and len(calls) == n0 + 1 and "`h0-y-r2`" in calls[-1][1]
    assert "SUPERSEDED h0-y -> h0" in (F / "handoff-sessions.log").read_text()


# ---- R1/R2/R3/R5 autonomy rules (operator-approved 2026-11-18) ----
def _lanes(monkeypatch, tmp_path):
    monkeypatch.setattr(hs, "ensure_lane", lambda slug, repo=None: (str(tmp_path), "ok"))
    monkeypatch.setattr(hs, "_git", lambda *a, **k: type("R", (), {"returncode": 1, "stdout": ""})())


def _continue(monkeypatch):
    monkeypatch.setattr(hs, "decide", lambda flags, slug, e, *a, **k: ("continue", "test: more work"))


def _digest(F):
    p = F / hs.AUTONOMY_DIGEST_NAME
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def test_r1_refused_spawn_is_not_a_resume_and_parks_after_three(tmp_path, monkeypatch):
    F, calls, runner = _setup(tmp_path, n=1, cap=2)
    _lanes(monkeypatch, tmp_path)
    _continue(monkeypatch)

    def refuse(*a, **k):
        raise hs.tg.SpawnRefused("codex: effort 'm1' not valid")
    monkeypatch.setattr(hs, "launch", refuse)
    for i in range(3):
        reg, _ = hs.dispatch_once(str(F), runner)
        e = reg["sessions"]["h0"]
        assert not e.get("resume_ts"), "a refused spawn never counts toward max_resumes"
    assert e["parked"]["reason"] == "spawn-config-invalid: codex: effort 'm1' not valid"
    hs.dispatch_once(str(F), runner)  # parked: no fourth attempt, logged once
    log = (F / "handoff-sessions.log").read_text()
    assert log.count("REFUSED-SPAWN h0") == 3 and log.count("PARK h0: spawn-config-invalid") == 1
    assert [d["action"] for d in _digest(F) if d["slug"] == "h0"] == ["PARK"]
    e["parked"]["at"] = "2000-01-01T00:00:00Z"  # guardrail: never auto-unparked, even with a fresh event
    _manifest(F, "h0-r")
    (F / "grants" / "h0-r.ended").write_text("rc=0")
    reg, _ = hs.dispatch_once(str(F), runner)
    assert reg["sessions"]["h0"]["parked"]["reason"].startswith("spawn-config-invalid")


def test_r1_streak_resets_on_success_and_success_counts(tmp_path, monkeypatch):
    F, calls, runner = _setup(tmp_path, n=1, cap=2)
    _lanes(monkeypatch, tmp_path)
    _continue(monkeypatch)
    n = {}

    def flaky(flags, slug, e, prompt, fresh=False, runner=None):
        n[slug] = n.get(slug, 0) + 1
        if n[slug] <= 2:
            raise hs.tg.SpawnRefused("same")
        return 999999999, "out"
    monkeypatch.setattr(hs, "launch", flaky)
    for _ in range(3):
        reg, _ = hs.dispatch_once(str(F), runner)
    e = reg["sessions"]["h0"]
    assert not hs.tg.is_parked(e) and "spawn_refused_streak" not in e and len(e["resume_ts"]) == 1


def _parked_setup(tmp_path, monkeypatch, reason="no progress evidence: last 2 turn(s)", n=1, cap=2):
    F, calls, runner = _setup(tmp_path, n=n, cap=cap)
    hs.dispatch_once(str(F), runner, seed=True)
    reg = json.loads((F / "handoff-sessions.json").read_text())
    for e in reg["sessions"].values():
        e["parked"] = {"reason": reason, "at": "2020-01-01T00:00:00Z", "wrapup": e.get("last_wrapup")}
    (F / "handoff-sessions.json").write_text(json.dumps(reg))
    return F, calls, runner


def test_r2_event_after_park_auto_unparks(tmp_path, monkeypatch):
    F, calls, runner = _parked_setup(tmp_path, monkeypatch)
    _manifest(F, "h0-r")
    (F / "grants" / "h0-r.ended").write_text("rc=0")
    reg, _ = hs.dispatch_once(str(F), runner)
    assert not hs.tg.is_parked(reg["sessions"]["h0"]) and len(reg["sessions"]["h0"]["auto_unparks"]) == 1
    assert "AUTO-UNPARK h0: queued run-end event h0-r" in (F / "handoff-sessions.log").read_text()
    assert _digest(F)[0]["action"] == "AUTO-UNPARK"


def test_r2_new_landed_wrapup_auto_unparks(tmp_path, monkeypatch):
    F, calls, runner = _parked_setup(tmp_path, monkeypatch)
    reg = json.loads((F / "handoff-sessions.json").read_text())
    reg["sessions"]["h0"]["last_wrapup"] = "newsha"
    (F / "handoff-sessions.json").write_text(json.dumps(reg))
    reg, _ = hs.dispatch_once(str(F), runner)
    assert not hs.tg.is_parked(reg["sessions"]["h0"])


@pytest.mark.parametrize("reason", ["operator hold", "lease expired: 9000 s > 5400 s"])
def test_r2_never_unparks_operator_or_ineligible(tmp_path, monkeypatch, reason):
    F, calls, runner = _parked_setup(tmp_path, monkeypatch, reason=reason)
    _manifest(F, "h0-r")
    (F / "grants" / "h0-r.ended").write_text("rc=0")
    reg, _ = hs.dispatch_once(str(F), runner)
    assert hs.tg.is_parked(reg["sessions"]["h0"]) and not _digest(F)


def test_r2_guardrails_no_event_full_cap_and_daily_limit(tmp_path, monkeypatch):
    F, calls, runner = _parked_setup(tmp_path, monkeypatch)
    reg, _ = hs.dispatch_once(str(F), runner)  # same wrap-up as at park time, no event -> stays parked
    assert hs.tg.is_parked(reg["sessions"]["h0"])
    real_cap = hs.tg.width_cap
    monkeypatch.setattr(hs.tg, "width_cap", lambda *a, **k: (0, "test"))
    _manifest(F, "h0-r")
    (F / "grants" / "h0-r.ended").write_text("rc=0")
    reg, _ = hs.dispatch_once(str(F), runner)
    assert hs.tg.is_parked(reg["sessions"]["h0"]), "live >= cap: no auto-unpark"
    monkeypatch.setattr(hs.tg, "width_cap", real_cap)
    reg = json.loads((F / "handoff-sessions.json").read_text())
    reg["sessions"]["h0"]["auto_unparks"] = [hs.time.time(), hs.time.time()]
    (F / "handoff-sessions.json").write_text(json.dumps(reg))
    reg, _ = hs.dispatch_once(str(F), runner)
    assert hs.tg.is_parked(reg["sessions"]["h0"]), "2 auto-unparks in 24 h already used"


def test_r5_idle_slot_unparks_top_ranked_old_event(tmp_path, monkeypatch):
    F, calls, runner = _parked_setup(tmp_path, monkeypatch, n=2)
    st = {"seen": [], "queue": [{"slug": s, "rid": f"{s}-r", "kind": "run-end", "end": "x"} for s in ("h1", "h0")]}
    (F / "handoff-sessions.state.json").write_text(json.dumps(st))  # events queued BEFORE the park: R2 does not fire
    monkeypatch.setattr(hs, "priority_order", lambda repo, priority=None: {hs.hkey("handoffs/active/h1.md"): (0, 0),
                                                                          hs.hkey("handoffs/active/h0.md"): (1, 0)})
    reg, _ = hs.dispatch_once(str(F), runner)
    S = reg["sessions"]
    assert not hs.tg.is_parked(S["h1"]) and hs.tg.is_parked(S["h0"]), "one per pass, top-ranked first"
    assert "AUTO-UNPARK h1: idle slot" in (F / "handoff-sessions.log").read_text()


def test_r5_no_effect_when_unparked_candidate_has_work(tmp_path, monkeypatch):
    F, calls, runner = _parked_setup(tmp_path, monkeypatch, n=2)
    reg = json.loads((F / "handoff-sessions.json").read_text())
    reg["sessions"]["h1"].pop("parked")
    (F / "handoff-sessions.json").write_text(json.dumps(reg))
    (F / "handoff-sessions.state.json").write_text(json.dumps({"seen": [], "queue": [
        {"slug": "h0", "rid": "h0-r", "kind": "run-end", "end": "x"}]}))
    monkeypatch.setattr(hs, "decide", lambda flags, slug, e, *a, **k: ("continue", "work") if slug == "h1" else ("pause", "none"))
    monkeypatch.setattr(hs, "_go", lambda *a, **k: True)
    reg, _ = hs.dispatch_once(str(F), runner)
    assert hs.tg.is_parked(reg["sessions"]["h0"]) and not _digest(F)


# ---- operator gate (operator-approved 2026-11-18): operator-only work is never started by automation ----
def _gate(F, slug="h0", reason="kernel promotion v11"):
    assert hs.main(["gate", slug, "--reason", reason, "--flags", str(F)]) == 0
    return json.loads((F / "handoff-sessions.json").read_text())


def _ratify(F, name, **kw):
    d = F / "operator-ratify"
    d.mkdir(exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps({"slug": name, "by": "operator", "at": "2026-11-18T00:00:00Z", "reason": "ok", **kw}))


def test_gate_subcommand_sets_gate_and_parks(tmp_path):
    F, calls, runner = _setup(tmp_path, n=1)
    e = _gate(F)["sessions"]["h0"]
    assert e["operator_gate"]["reason"] == "kernel promotion v11" and e["operator_gate"]["since"]
    assert e["parked"]["reason"].startswith("operator-gate:")
    assert hs.tg.is_parked(e) and hs.tg.is_gated(e)
    with pytest.raises(SystemExit):
        hs.main(["gate", "h0", "--flags", str(F)])


def test_gated_session_never_spawned_nor_auto_unparked_and_events_kept(tmp_path, monkeypatch):
    F, calls, runner = _setup(tmp_path, n=1)
    _lanes(monkeypatch, tmp_path)
    _continue(monkeypatch)
    reg = _gate(F)
    e = reg["sessions"]["h0"]
    e["parked"]["reason"] = "no progress evidence: x"  # even an auto-unpark-eligible park reason stays held
    e["parked"]["at"] = "2000-01-01T00:00:00Z"
    (F / "handoff-sessions.json").write_text(json.dumps(reg))
    assert not hs.tg.auto_unpark_eligible(e, 0)
    _manifest(F, "h0-r")
    (F / "grants" / "h0-r.ended").write_text("rc=0")
    for _ in range(3):
        reg, st = hs.dispatch_once(str(F), runner)
    assert calls == [] and hs.tg.is_gated(reg["sessions"]["h0"]) and not reg["sessions"]["h0"].get("auto_unparks")
    assert any(ev["slug"] == "h0" for ev in st["queue"]), "gated events stay queued, never dropped"
    log = (F / "handoff-sessions.log").read_text()
    assert log.count("GATE-HELD h0") == 1 and "AUTO-UNPARK h0" not in log


def test_gated_session_never_auto_started(tmp_path):
    F, calls, runner = _setup(tmp_path, n=1)
    reg = _gate(F)
    assert hs.start_handoff(str(F), reg, {"handoff": "handoffs/active/h0.md", "slug": "h0"}, runner, {}, 0, 2) is None
    assert calls == []
    assert hs._go(str(F), "h0", reg["sessions"]["h0"], "p", runner, None, fresh=True) is False and calls == []


def test_unpark_refused_then_lifted_with_ratification(tmp_path):
    F, calls, runner = _setup(tmp_path, n=2)
    _gate(F)
    assert hs.main(["unpark", "h0", "--flags", str(F)]) == 3
    assert hs.tg.is_gated(json.loads((F / "handoff-sessions.json").read_text())["sessions"]["h0"])
    _ratify(F, "h0", slug="h1")  # names the wrong slug: rejected
    assert hs.main(["unpark", "h0", "--flags", str(F)]) == 3
    _ratify(F, "h0", by="")  # missing key: rejected
    assert hs.main(["unpark", "h0", "--flags", str(F)]) == 3
    _ratify(F, "h0")
    assert hs.main(["unpark", "h0", "--flags", str(F)]) == 0
    e = json.loads((F / "handoff-sessions.json").read_text())["sessions"]["h0"]
    assert not hs.tg.is_gated(e) and not hs.tg.is_parked(e)
    log = (F / "handoff-sessions.log").read_text()
    assert "GATE-LIFTED h0" in log and "UNPARK h0 (operator)" in log
    assert hs.main(["unpark", "h1", "--flags", str(F)]) == 0  # ungated unpark unchanged
