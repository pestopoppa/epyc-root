#!/usr/bin/env python3
"""PostToolUse hook (matcher ``Bash``): FM-8 serial-collapse detector. WARN ONLY, always exit 0.

A task boundary is a main-thread Bash call that appends a heartbeat with a task_id
(``session_bus.py append ... --target heartbeat --json '{..."task_id":"X"...}'``),
the boundary the project contract already requires. On each boundary this hook counts
main-thread dispatches logged by check_agent_dispatch.py for the same session_id since
the previous boundary (fan-out width), appends a ``boundary`` line to the same audit
log, and warns when the last N (default 3) completed tasks all had width 0.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path

HOOK = "check_serial_collapse"
THRESHOLD = int(os.environ.get("SERIAL_COLLAPSE_THRESHOLD", "3"))
HOOK_PATH = Path(__file__).resolve()
TASK_RE = re.compile(r'"task_id"\s*:\s*"([^"]*)"')


def audit_log_path() -> Path:
    env = os.environ.get("AGENT_DISPATCH_AUDIT_LOG")
    if env:
        return Path(env)
    root = os.environ.get("CLAUDE_PROJECT_DIR") or str(HOOK_PATH.parents[2])
    return Path(root) / "logs" / "agent_dispatch_audit.jsonl"


def boundary_task(command: str):
    if "session_bus.py" not in command or " append" not in command or "heartbeat" not in command:
        return None
    m = TASK_RE.search(command)
    return m.group(1) if m else None


def session_rows(path: Path, session_id: str) -> list:
    rows = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if isinstance(d, dict) and d.get("session_id") == session_id:
                    rows.append(d)
    except OSError:
        pass
    return rows


def width_since_last_boundary(rows: list) -> int:
    width = 0
    for d in rows:
        if d.get("hook") == HOOK:
            width = 0
        elif d.get("hook") == "check_agent_dispatch":
            width += 1
    return width


def handle(raw: str) -> None:
    payload = json.loads(raw)
    if not isinstance(payload, dict) or payload.get("agent_id"):
        return
    if payload.get("tool_name") not in (None, "Bash"):
        return
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    task = boundary_task(cmd)
    session_id = payload.get("session_id")
    if task is None or not session_id:
        return
    path = audit_log_path()
    rows = session_rows(path, session_id)
    width = width_since_last_boundary(rows)
    prior = [d.get("width") for d in rows if d.get("hook") == HOOK]
    streak = 0
    for w in reversed(prior + [width]):
        if w != 0:
            break
        streak += 1
    flagged = streak >= THRESHOLD
    rec = {
        "ts": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hook": HOOK, "mode": "warn", "event": "boundary", "session_id": session_id,
        "task_id": task, "width": width, "zero_streak": streak,
        "findings": ["serial_collapse"] if flagged else [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    if flagged:
        sys.stderr.write(f"[{HOOK}] WARN serial_collapse: {streak} consecutive tasks with zero "
                         "subagent dispatches; fan out genuinely parallel work.\n")


def main() -> int:
    try:
        handle(sys.stdin.read())
    except Exception as exc:  # warn mode never blocks
        try:
            sys.stderr.write(f"[{HOOK}] internal error allowed: {exc!r}\n")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
