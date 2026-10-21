"""Policy + liveness tests for scripts/vidya/belief_trial_reminder.py. No delivery: the
alarm channel is stubbed (send) or run with --dry-run."""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import belief_trial_reminder as btr  # noqa: E402

UP = "running"
DOWN = "not running (last 10-11 06:28Z)"


def test_monday_notifies_warning():
    key, sev, msg = btr.decide(date(2026, 10, 26), DOWN, DOWN)
    assert (key, sev) == ("belief-trial-2026-10-26", "warning")
    assert "Nov 23 (28 days)" in msg and "AutoKernel:" in msg and "Autopilot:" in msg


def test_non_monday_silent():
    assert btr.decide(date(2026, 10, 27), DOWN, DOWN) is None
    assert btr.decide(date(2026, 11, 19), DOWN, DOWN) is None  # Thursday, before start-by


def test_milestones():
    for d in (date(2026, 11, 20), date(2026, 11, 23), date(2026, 11, 30)):
        r = btr.decide(d, UP, UP)
        assert r is not None and r[0] == f"belief-trial-{d.isoformat()}"
    assert btr.decide(date(2026, 11, 20), UP, UP)[1] == "warning"
    assert "EVALUATION DAY" in btr.decide(date(2026, 11, 30), UP, UP)[2]


def test_after_start_by_loop_down_daily_critical():
    for d in (date(2026, 11, 24), date(2026, 11, 25), date(2026, 11, 29)):
        key, sev, msg = btr.decide(d, UP, DOWN)
        assert sev == "critical" and "START Autopilot NOW" in msg
    assert btr.decide(date(2026, 11, 24), UP, "unknown")[1] == "critical"  # unproven = not live


def test_after_start_by_both_running_is_quiet_midweek():
    assert btr.decide(date(2026, 11, 24), UP, UP) is None
    assert btr.decide(date(2026, 11, 23), UP, UP)[1] == "warning"  # milestone, loops fine


def test_start_by_day_loop_down_is_critical():
    assert btr.decide(date(2026, 11, 23), DOWN, UP)[1] == "critical"


def test_after_eval_final_fixed_key():
    a = btr.decide(date(2026, 12, 1), UP, UP)
    b = btr.decide(date(2027, 3, 5), DOWN, DOWN)
    assert a[0] == b[0] == "belief-trial-final"  # same key: channel dedupe keeps it single


def test_message_under_200_chars_worst_case():
    for d in (date(2026, 10, 26), date(2026, 11, 24), date(2026, 12, 1)):
        assert len(btr.decide(d, "not running (last never seen)", "not running (last never seen)")[2]) < 200


def test_main_silent_day_sends_nothing(monkeypatch):
    sent = []
    monkeypatch.setattr(btr, "send", lambda *a: sent.append(a) or 0)
    monkeypatch.setattr(btr, "_cmdlines", lambda: [["python3", "x.py"]])
    assert btr.main(["--today", "2026-10-27"]) == 0 and sent == []
    assert btr.main(["--today", "2026-10-26", "--dry-run"]) == 0
    assert sent and sent[0][3] is True


def test_autopilot_liveness(tmp_path):
    state = tmp_path / "s.json"
    state.write_text("{}")
    run = [["/venv/bin/python", "scripts/autopilot/autopilot.py", "start", "--max-trials", "3"]]
    assert btr.autopilot_state(run, state) == "running"
    # a shell that merely mentions the script, or a non-start subcommand, proves nothing
    assert btr.autopilot_state([["zsh", "-c", "autopilot.py start"]], state).startswith("not running (last ")
    assert btr.autopilot_state([["python3", "autopilot.py", "status"]], state).startswith("not running")
    assert btr.autopilot_state([["init"]], tmp_path / "missing").endswith("never seen)")


def _status(root: Path, name: str, state: str, age_s: float, stale: int = 180):
    d = root / "campaigns" / name
    d.mkdir(parents=True)
    ts = (datetime.now(timezone.utc) - timedelta(seconds=age_s)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    (d / "loop-status.json").write_text(json.dumps({"generated_at": ts, "state": state, "stale_after_s": stale}))


def test_autokernel_liveness(tmp_path):
    other = [["init"]]
    _status(tmp_path, "crashed", "running", 86400 * 30)  # left "running" by a dead loop
    assert btr.autokernel_state(other, tmp_path).startswith("not running (last ")
    _status(tmp_path, "done", "complete", 5)  # fresh but terminal
    assert btr.autokernel_state(other, tmp_path).startswith("not running")
    _status(tmp_path, "live", "running", 20)
    assert btr.autokernel_state(other, tmp_path) == "running"
    empty = tmp_path / "empty"
    empty.mkdir()
    assert btr.autokernel_state(other, empty) == "not running (last never seen)"
    proc = [["python3", "/r/scripts/kernel_rnd/autokernel/loop/serial_run.py", "--x"]]
    assert btr.autokernel_state(proc, empty) == "running"
    assert btr.autokernel_state([["bash", "-c", "autokernel/loop/run.py"]], empty).startswith("not")

