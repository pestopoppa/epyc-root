#!/usr/bin/env python3
"""Hand-back sweep (AK audit C2, 2026-11-20): when a subagent hands back, name the background
tasks it started and never stopped or saw finish.

Evidence (audit section 2.8; 11-18 22:58Z, 11-19 14:47Z, 11-17 11:39Z): subagents returned while
background Bash tasks they launched kept running (watchers, builds, pollers) and nobody stopped
them; they held cores and wrote into files the next owner then misread.

Registered on PostToolUse(Agent|Task) and SubagentStop. Reads the subagent's own transcript
(`agent_transcript_path`, falling back to `transcript_path` on SubagentStop), collects every Bash
call made with run_in_background and the task id the harness reported for it, and drops the ones
later stopped (TaskStop/KillShell naming the id) or reported finished (a task-notification with
status completed/failed/killed). Survivors are listed with a `TaskStop` prompt:
  * PostToolUse -> additionalContext (reaches the dispatching model);
  * SubagentStop -> systemMessage (shown to the operator).

LOW RISK by construction: never blocks (exit 0 on every path, including its own errors), never
stops anything itself, silent when nothing survives or no transcript is readable. Not covered:
age-based staleness of ListAgents rows (the hook cannot see the agent list; that stays a skill
step).
"""
import json
import re
import sys

TASK_ID = re.compile(r"\(ID:\s*([A-Za-z0-9_-]+)\)|\bshell[_ ]id[\"':\s]+([A-Za-z0-9_-]+)|\btask[_ ]id[\"':\s]+([A-Za-z0-9_-]+)", re.I)
NOTIFY = re.compile(r"<task-id>([^<]+)</task-id>.*?<status>(completed|failed|killed|stopped)</status>", re.S)
STOP_TOOLS = ("TaskStop", "KillShell", "KillBash")


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(_text(c.get("text") if c.get("type") == "text" else c.get("content")) for c in content if isinstance(c, dict))
    return ""


def survivors(path):
    """[(task_id, command)] of background tasks started and never stopped/finished, in launch order."""
    pending = {}      # tool_use_id -> command
    started = {}      # task_id -> command
    ended = set()
    try:
        fh = open(path, errors="replace")
    except (OSError, TypeError):
        return []
    with fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            content = (rec.get("message") or {}).get("content")
            if isinstance(content, str):
                ended.update(t.strip() for t, _ in NOTIFY.findall(content))
                continue
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "tool_use":
                    inp = c.get("input") or {}
                    if c.get("name") == "Bash" and inp.get("run_in_background"):
                        pending[c.get("id")] = str(inp.get("command", ""))[:120]
                    elif c.get("name") in STOP_TOOLS:
                        for v in inp.values():
                            if isinstance(v, str):
                                ended.add(v.strip())
                elif c.get("type") == "tool_result" and c.get("tool_use_id") in pending:
                    m = TASK_ID.search(_text(c.get("content")))
                    if m:
                        started[next(g for g in m.groups() if g)] = pending.pop(c.get("tool_use_id"))
                elif c.get("type") == "text":
                    ended.update(t.strip() for t, _ in NOTIFY.findall(c.get("text") or ""))
    return [(t, cmd) for t, cmd in started.items() if t not in ended]


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0
    event = payload.get("hook_event_name")
    if event == "PostToolUse" and payload.get("tool_name") not in ("Agent", "Task"):
        return 0
    path = payload.get("agent_transcript_path") or (payload.get("transcript_path") if event == "SubagentStop" else None)
    alive = survivors(path) if path else []
    if not alive:
        return 0
    # P5-1: only harness-issued task ids go into context, never subagent-authored command text
    # (a relayed statement must not reach the dispatching model through a hook channel).
    lines = ", ".join(re.sub(r"[^A-Za-z0-9_-]", "", t)[:32] for t, _ in alive[:8])
    msg = (f"HAND-BACK SWEEP: the subagent left {len(alive)} background task(s) not stopped and not reported "
           f"finished: {lines}. Check each and TaskStop it unless it is meant to outlive the hand-back.")
    if event == "SubagentStop":
        out = {"systemMessage": msg}
    else:
        out = {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}
    json.dump(out, sys.stdout)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
