#!/usr/bin/env python3
"""belief_trial_reminder.py -- durable, host-side reminders for the belief-kernel refocus trial.

WHY: the refocus is evaluated on 2026-11-30 (moved from 2026-11-11 by the operator,
2026-10-21) and AutoKernel and autopilot each need >= 7 days live on the belief-reader code,
so each must be started by 2026-11-23. Claude-session timers die with sessions; this is a
cron-run script that talks to the operator through the project's alarm channel
(`scripts/coordination/alarm_channel.py`, live via ntfy). Owning task:
handoffs/active/vidya-belief-substrate-program.md (VB-REFOCUS-TRIAL-REMINDER, "Trial clock").

MESSAGE POLICY (run once per day; every other day exits 0 silently)
  * every MONDAY                         status line (days to start-by / evaluation, loop state)
  * milestones 2026-11-20, 11-23, 11-30  always
  * from 2026-11-23 through 11-30        EVERY day a loop is not running (severity critical)
  * after 2026-11-30                     one final message, then silent forever
Severity is `warning`, except `critical` for "past start-by and a loop is not running".

LIVENESS (never claims a loop is live from a signal that cannot prove it)
  * autopilot : a process whose argv holds `autopilot.py` followed by `start` (read from
                /proc/*/cmdline, read-only; the loop's own singleton flock is NOT probed, a
                probe could win the lock and block the real start). Last activity = mtime of
                orchestration/autopilot_state.json (any autopilot command may touch it, so it
                is reported only as "last activity", never as proof of running).
  * AutoKernel: a process running autokernel/loop/run.py or serial_run.py, OR a
                `loop-status.json` (heartbeat every 30 s, `status.py`) under
                /mnt/raid0/llm/autokernel whose state is non-terminal AND whose generated_at
                is inside its own stale_after_s. A crashed loop leaves state "running" in the
                file, so freshness is mandatory (the 2026-09-08 loop-memory file still says
                "running"; it is correctly reported as not running).
  * states: "running" | "not running (last <ts>)" | "unknown" (the /proc scan itself failed).
    `unknown` counts as not-running for the risk rule: an unproven loop is not a live loop.

CLEAR POLICY: yesterday's key is NOT cleared. `alarm_channel.py clear` notifies too, so
clearing would double every reminder. Keys are unique per notification date
(`belief-trial-YYYY-MM-DD`, final one `belief-trial-final`), so each notifies exactly once; a
second cron run the same day is deduped by the channel (suppressed, no notification). The
consequence is that old keys stay "active" in alarm_state.json (about 20 by the end); the
fleet_watch clear sweep only touches keys it owns and ignores these. After the trial the
operator may `alarm_channel.py clear --key belief-trial-final` etc. (this pings once each),
or ignore them.

CRON (install once, then remove after the trial; points at the hub view that tracks
origin/main, /workspace is a diverged shared clone; cron has no PATH to speak of, so the
interpreter is absolute and the script resolves every path itself):

    17 8 * * * cd /mnt/raid0/llm/views/epyc-root-main && /usr/bin/python3 scripts/vidya/belief_trial_reminder.py >> /mnt/raid0/llm/logs/belief_trial_reminder.log 2>&1

Options: --dry-run (passed to alarm_channel, delivers nothing, writes no state),
         --today YYYY-MM-DD (testing).  Exit 0 = ok/silent; non-zero = alarm_channel's code.
Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

EVAL_DATE = date(2026, 11, 30)
START_BY = date(2026, 11, 23)
MIN_LIVE_DAYS = 7
MILESTONES = (date(2026, 11, 20), START_BY, EVAL_DATE)

REPO_ROOT = Path(__file__).resolve().parents[2]
ALARM_CHANNEL = REPO_ROOT / "scripts" / "coordination" / "alarm_channel.py"
ORCH_ROOT = Path(os.environ.get("EPYC_ORCH_ROOT", "/mnt/raid0/llm/epyc-orchestrator"))
AUTOPILOT_STATE = ORCH_ROOT / "orchestration" / "autopilot_state.json"
AK_ROOT = Path(os.environ.get("EPYC_AK_ROOT", "/mnt/raid0/llm/autokernel"))
AK_STATUS_NAME = "loop-status.json"  # research scripts/kernel_rnd/autokernel/loop/status.py
AK_TERMINAL = frozenset({"complete", "failed"})
AK_DEFAULT_STALE_S = 180.0  # run.py: HEARTBEAT_S (30) * 6
MAX_MSG = 199


# -- liveness ---------------------------------------------------------------
def _cmdlines(proc: Path = Path("/proc")) -> list[list[str]] | None:
    """argv of every readable process, or None if /proc cannot be scanned at all."""
    try:
        pids = [p for p in proc.iterdir() if p.name.isdigit()]
    except OSError:
        return None
    out: list[list[str]] = []
    for p in pids:
        try:
            raw = (p / "cmdline").read_bytes()
        except OSError:
            continue  # exited, or not ours to read
        argv = [a for a in raw.decode("utf-8", "replace").split("\0") if a]
        if argv:
            out.append(argv)
    return out if out else None


def _is_python(argv: list[str]) -> bool:
    return os.path.basename(argv[0]).startswith("python")


def _fmt_ts(ts: datetime | None) -> str:
    return ts.astimezone(timezone.utc).strftime("%m-%d %H:%MZ") if ts else "never seen"


def autopilot_state(cmdlines=None, state_file: Path = AUTOPILOT_STATE) -> str:
    cmds = _cmdlines() if cmdlines is None else cmdlines
    if cmds is None:
        return "unknown"
    for argv in cmds:
        if not _is_python(argv):  # a shell whose text merely mentions the script is not the loop
            continue
        for i, a in enumerate(argv[1:], 1):
            if os.path.basename(a) == "autopilot.py" and "start" in argv[i + 1:]:
                return "running"
    try:
        last = datetime.fromtimestamp(state_file.stat().st_mtime, timezone.utc)
    except OSError:
        last = None
    return f"not running (last {_fmt_ts(last)})"


def _parse_ts(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _ak_status_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for pattern in (AK_STATUS_NAME, f"*/{AK_STATUS_NAME}", f"*/*/{AK_STATUS_NAME}",
                    f"campaigns/*/*/{AK_STATUS_NAME}"):
        try:
            found.extend(root.glob(pattern))
        except OSError:
            pass
    return found


def autokernel_state(cmdlines=None, root: Path = AK_ROOT, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    cmds = _cmdlines() if cmdlines is None else cmdlines
    if cmds is None:
        return "unknown"
    for argv in cmds:
        if not _is_python(argv):
            continue
        for i, a in enumerate(argv[1:], 1):
            if a.endswith(("autokernel/loop/run.py", "autokernel/loop/serial_run.py")):
                return "running"
            if argv[i - 1] == "-m" and a in ("autokernel.loop.run", "autokernel.loop.serial_run"):
                return "running"
    newest: datetime | None = None
    for f in _ak_status_files(root):
        try:
            body = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(body, dict):
            continue
        ts = _parse_ts(body.get("generated_at"))
        if ts is None:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if newest is None or ts > newest:
            newest = ts
        try:
            limit = float(body.get("stale_after_s") or AK_DEFAULT_STALE_S)
        except (TypeError, ValueError):
            limit = AK_DEFAULT_STALE_S
        if str(body.get("state")) not in AK_TERMINAL and (now - ts).total_seconds() <= limit:
            return "running"
    return f"not running (last {_fmt_ts(newest)})"


def is_running(state: str) -> bool:
    return state == "running"


# -- policy -----------------------------------------------------------------
def _d(d: date) -> str:
    return d.strftime("%b ") + str(d.day)


def decide(today: date, ak: str, ap: str):
    """Return (key, severity, message) or None for a silent day."""
    if today > EVAL_DATE:
        return ("belief-trial-final", "warning",
                f"Belief trial: evaluation date {_d(EVAL_DATE)} has passed; this is the last reminder. "
                f"AutoKernel: {ak}. Autopilot: {ap}.")
    down = [n for n, s in (("AutoKernel", ak), ("Autopilot", ap)) if not is_running(s)]
    past_start = today >= START_BY
    milestone = today in MILESTONES
    monday = today.weekday() == 0
    if not (milestone or monday or (past_start and down)):
        return None
    to_start, to_eval = (START_BY - today).days, (EVAL_DATE - today).days
    states = f"AutoKernel: {ak}. Autopilot: {ap}."
    if today == EVAL_DATE:
        msg = f"Belief trial: EVALUATION DAY. {states}"
    elif past_start and down:
        msg = (f"Belief trial: START {' and '.join(down)} NOW, past the {_d(START_BY)} start-by; "
               f"under {MIN_LIVE_DAYS} live days will not count. {states} Eval {_d(EVAL_DATE)} ({to_eval}d).")
    elif past_start:
        msg = f"Belief trial: both loops running. {states} Eval {_d(EVAL_DATE)} ({to_eval}d)."
    else:
        msg = (f"Belief trial: start both loops by {_d(START_BY)} ({to_start} days). "
               f"{states} Eval {_d(EVAL_DATE)}.")
    severity = "critical" if (past_start and down) else "warning"
    if len(msg) > MAX_MSG:  # shorten the long "last ts" detail rather than cut mid-word
        msg = msg.replace("not running (last ", "down (").replace("never seen", "never")
    return (f"belief-trial-{today.isoformat()}", severity, msg[:MAX_MSG])


def send(key: str, severity: str, message: str, dry_run: bool) -> int:
    cmd = [sys.executable, str(ALARM_CHANNEL)]
    if dry_run:
        cmd.append("--dry-run")
    cmd += ["raise", "--severity", severity, "--key", key, "--message", message]
    return subprocess.run(cmd, check=False).returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--today", type=date.fromisoformat, default=None, help="YYYY-MM-DD (testing)")
    args = ap.parse_args(argv)
    today = args.today or datetime.now(timezone.utc).date()
    # Liveness is only read when a message could be sent, keeping silent days free.
    cmds = _cmdlines()
    decision = decide(today, autokernel_state(cmds), autopilot_state(cmds))
    if decision is None:
        return 0
    key, severity, message = decision
    print(f"belief_trial_reminder {today} {severity} {key}: {message}")
    return send(key, severity, message, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
