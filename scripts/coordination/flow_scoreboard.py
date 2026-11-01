#!/usr/bin/env python3
"""flow_scoreboard.py - replaces the code-tick quota (CODE-SCOREBOARD.md) with flow metrics per worker per day.

Zero-token, read-only except FLOW-SCOREBOARD.md and flow-scoreboard-state.json. Never nudges a pane.

    rows armed (qualified)   READY-QUAL lines in the keeper log today, attributed to the manifest's owner.
    blocking tasks closed    blocked-row unblocking tasks (from backlog_gen) that were listed earlier today
                             and are no longer listed (the row moved on or the task disappeared).
    idle compute-hours with a blocked row as cause
                             each keeper IDLE-ALARM today (one per ~2 min keeper tick while a bin is free) is
                             charged 2 min to every worker that currently has a blocked/needs-launcher row
                             in that bin's lane (q0-q3 -> cpu, gpu-quiet -> gpu).

    python3 flow_scoreboard.py [--flags DIR --priority FILE --keeper-log FILE --out FILE --state FILE] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backlog_gen as bg  # noqa: E402

TICK_H = 120 / 3600.0


def owner_of(flags: str, rid: str) -> str | None:
    for p in (f"{flags}/ready/{rid}.json", f"{flags}/ready/armed/{rid}.json", f"{flags}/withdrawn/{rid}.json"):
        d = bg.load_json(p)
        if isinstance(d, dict):
            return bg.worker_of(str(d.get("owner", "")))
    return bg.worker_of(rid)


def compute(flags: str, priority: str, keeper_log: str, state: dict, now: _dt.datetime) -> tuple[dict, dict]:
    day = now.strftime("%Y-%m-%d")
    if state.get("day") != day:
        state = {"day": day, "seen": {w: {} for w in bg.WORKERS}, "closed": {w: 0 for w in bg.WORKERS}}
    data = bg.build(flags, priority, keeper_log, now)
    armed = {w: 0 for w in bg.WORKERS}
    idle_lane = {"cpu": 0, "gpu": 0}
    try:
        lines = open(keeper_log, errors="replace").readlines()[-20000:]
    except OSError:
        lines = []
    for l in lines:
        if not l.startswith(day):
            continue
        m = re.match(r"\S+ READY-QUAL (?:\S*/)?([A-Za-z0-9_.-]+?)\.json:", l)
        if m:
            w = owner_of(flags, m.group(1))
            if w in armed:
                armed[w] += 1
            continue
        m = re.match(r"\S+ IDLE-ALARM .*: (\S+)$", l.strip())
        if m:
            idle_lane["gpu" if "gpu" in m.group(1) else "cpu"] += 1
    rows = {}
    for w in bg.WORKERS:
        blocked = [r for r in data["workers"][w]["rows"] if r["state"] in ("blocked", "needs-launcher")]
        keys = {f"{r['id']}|{t}" for r in blocked for t in r["tasks"]}
        seen = state["seen"].setdefault(w, {})
        gone = [k for k in seen if k not in keys]
        for k in gone:
            del seen[k]
        state["closed"][w] = state["closed"].get(w, 0) + len(gone)
        for k in keys:
            seen.setdefault(k, now.strftime("%H:%MZ"))
        lanes_blocked = {r["lane"] for r in blocked}
        idle_h = sum(idle_lane[l] * TICK_H for l in ("cpu", "gpu") if l in lanes_blocked)
        rows[w] = {"armed": armed[w], "closed": state["closed"][w], "open_blocking": len(keys),
                   "blocked_rows": len(blocked), "qual": data["workers"][w]["qual"], "idle_h": round(idle_h, 2)}
    return rows, state


def render(rows: dict, now: _dt.datetime) -> str:
    L = [f"# FLOW scoreboard {now:%Y-%m-%dT%H:%MZ} (per worker, today UTC; replaces the 50-tick code quota, 2026-11-01)", "",
         "Flow: unblock -> launcher -> keeper qualification (dry run) -> armed. Good = rows armed up, blocking tasks closed up, idle-hours down.", "",
         "| worker | rows armed (qualified) today | blocking tasks closed today | blocking tasks open now | blocked rows now | qualified-armed cpu/gpu/host | idle compute-hours with a blocked row as cause |",
         "|---|---:|---:|---:|---:|---|---:|"]
    for w, r in rows.items():
        q = r["qual"]
        L.append(f"| {w} | {r['armed']} | {r['closed']} | {r['open_blocking']} | {r['blocked_rows']} | {q['cpu']}/{q['gpu']}/{q['host']} | {r['idle_h']} |")
    L += ["", "Source: BACKLOG-<worker>.md (scripts/coordination/backlog_gen.py) and ws58-calendar-keeper.log. No pane nudges; the backlog file is the only instruction.", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--flags", default=bg.FLAGS_DEFAULT)
    ap.add_argument("--priority", default=bg.PRIORITY_DEFAULT)
    ap.add_argument("--keeper-log", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--state", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    klog = a.keeper_log or os.path.join(a.flags, "ws58-calendar-keeper.log")
    out = a.out or os.path.join(a.flags, "FLOW-SCOREBOARD.md")
    sp = a.state or os.path.join(a.flags, "flow-scoreboard-state.json")
    now = _dt.datetime.now(_dt.timezone.utc)
    state = bg.load_json(sp) or {}
    rows, state = compute(a.flags, a.priority, klog, state, now)
    text = render(rows, now)
    if a.dry_run:
        print(text)
    else:
        bg.write_atomic(out, text)
        bg.write_atomic(sp, json.dumps(state))
    print(now.strftime("%FT%TZ"), json.dumps({w: {k: v for k, v in r.items() if k != "qual"} for w, r in rows.items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
