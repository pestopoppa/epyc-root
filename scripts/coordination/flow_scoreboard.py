#!/usr/bin/env python3
"""flow_scoreboard.py - replaces the code-tick quota (CODE-SCOREBOARD.md) with flow metrics per bucket per day.

Zero-token, read-only except FLOW-SCOREBOARD.md and flow-scoreboard-state.json. Never nudges a pane.
Buckets = backlog_gen.build() workers: `codex-gen` plus one `handoff-<slug>` per piloted handoff.

    rows qualified today      rows whose dryrun/<id>/PASS.json `passed_at` is today (the keeper's dry run passed)
    dry-run FAILs today       keeper-log `DRYRUN-RESULT FAIL <id> ...` lines today, attributed to the row's bucket
    blocking tasks closed     blocked-row unblocking tasks (from backlog_gen) listed earlier today and no longer listed
    open fix: tasks           rows in rowflow state `failed`: a FAIL record whose launcher sha is still the current one
                              (the owner's one fix task; the keeper retries as soon as the launcher changes)
    blocked rows now / parked rows now / dry runs running now (blocked with cause=keeper)
    qualified-armed cpu/gpu/host   rows the writers may grant now (PASS present, launcher unchanged)
    idle compute-hours with a blocked row as cause
                              each keeper IDLE-ALARM today (one per ~2 min keeper tick while a bin is free) is
                              charged 2 min to every bucket that currently has a blocked/needs-launcher row
                              in that bin's lane (q0-q3 -> cpu, gpu-quiet -> gpu).

Keeper-log lines read: `DRYRUN-RESULT <PASS|FAIL|WAIT> <id> <msg>`, `ROW-ARM ARMED <id> ...`, `DRYRUN-START <id> regions=...`,
`IDLE-ALARM ...: <bin>`.

    python3 flow_scoreboard.py [--flags DIR --priority FILE --keeper-log FILE --out FILE --state FILE] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "rowflow"))
import backlog_gen as bg  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "churn"))
try:
    import tokens_per_task as tpt  # noqa: E402  (headline metric, operator 2026-11-01 22:55Z)
except ImportError:
    tpt = None
try:
    import worktree_footprint as _wtfp  # noqa: E402  (LOOP-37: GiB + tree count per owner)
except ImportError:
    _wtfp = None
try:
    import rowflow as _rf  # noqa: E402
except ImportError:
    _rf = None

TICK_H = 120 / 3600.0


def passed_today(flags: str, rid: str, day: str) -> bool:
    p = bg.load_json(os.path.join(flags, "dryrun", rid, "PASS.json"))
    return isinstance(p, dict) and str(p.get("passed_at", "")).startswith(day)


def failed_now(flags: str, rid: str) -> bool:
    """rowflow state `failed`: the latest FAIL record's launcher sha equals the row's current launcher sha."""
    if _rf is None:
        return False
    fails = _rf.fail_paths(flags, rid)
    row = bg.load_json(os.path.join(flags, "ready", rid + ".json"))
    if not fails or not isinstance(row, dict):
        return False
    lp = (row.get("launcher") or {}).get("path") or ""
    if not os.path.isfile(lp) or bg.load_json(os.path.join(flags, "dryrun", rid, "PASS.json")):
        return False
    last = bg.load_json(fails[-1]) or {}
    return last.get("launcher_sha256") == _rf.sha256(lp)


def fold_log_today(keeper_log: str, day: str) -> tuple[dict, dict, dict]:
    """(DRYRUN-RESULT verdict counts per id, ROW-ARM ARMED ids, idle alarms per lane) for today."""
    results: dict[str, dict] = {}
    armed: dict[str, int] = {}
    idle_lane = {"cpu": 0, "gpu": 0}
    try:
        lines = open(keeper_log, errors="replace").readlines()[-20000:]
    except OSError:
        lines = []
    for l in lines:
        l = l.strip()
        if not l.startswith(day):
            continue
        m = re.match(r"\S+ DRYRUN-RESULT (PASS|FAIL|WAIT) (\S+)", l)
        if m:
            results.setdefault(m.group(2), {})[m.group(1)] = results.get(m.group(2), {}).get(m.group(1), 0) + 1
            continue
        m = re.match(r"\S+ ROW-ARM ARMED (\S+)", l)
        if m:
            armed[m.group(1)] = armed.get(m.group(1), 0) + 1
            continue
        m = re.match(r"\S+ IDLE-ALARM .*: (\S+)$", l)
        if m:
            idle_lane["gpu" if "gpu" in m.group(1) else "cpu"] += 1
    return results, armed, idle_lane


def compute(flags: str, priority: str, keeper_log: str, state: dict, now: _dt.datetime) -> tuple[dict, dict]:
    day = now.strftime("%Y-%m-%d")
    if state.get("day") != day:
        state = {"day": day, "seen": {}, "closed": {}}
    data = bg.build(flags, priority, keeper_log, now)
    results, armed_log, idle_lane = fold_log_today(keeper_log, day)
    rows = {"_inventory": data.get("inventory") or {}}
    for w in data["workers"]:
        allrows = data["workers"][w]["rows"]
        # rows whose dry run is RUNNING (cause=keeper): ws58's qualification in flight, not the owner's blocking task
        awaiting = [r for r in allrows if r["state"] == "blocked" and r.get("cause") == "keeper"]
        blocked = [r for r in allrows if r["state"] in ("blocked", "needs-launcher") and r.get("cause") != "keeper"]
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
        ids = [r["id"] for r in allrows]
        rows[w] = {"armed": sum(1 for rid in ids if passed_today(flags, rid, day)),
                   "armed_log": sum(armed_log.get(rid, 0) for rid in ids),
                   "dryrun_fail": sum(results.get(rid, {}).get("FAIL", 0) for rid in ids),
                   "closed": state["closed"][w], "open_blocking": len(keys),
                   "open_fix": sum(1 for r in blocked if failed_now(flags, r["id"])),
                   "awaiting_keeper": len(awaiting), "awaiting_ids": [r["id"] for r in awaiting][:8],
                   "blocked_rows": len(blocked), "parked": sum(1 for r in allrows if r["state"] == "parked"),
                   "qual": data["workers"][w]["qual"], "idle_h": round(idle_h, 2)}
    return rows, state


def render(rows: dict, now: _dt.datetime, inventory: dict | None = None) -> str:
    metric = None
    if tpt is not None:
        try:
            metric = tpt.compute(top=3)
        except Exception as ex:  # the scoreboard must never die on the metric
            metric = {"error": repr(ex), "per": {}, "top_turns": []}

    def tok_task(w):
        r = (metric or {}).get("per", {}).get(w[8:] if w.startswith("handoff-") else w)
        if not r:
            return "-"
        return (tpt.fmt_m(r["tokens_per_task"]) if r["tokens_per_task"] else f"inf ({tpt.fmt_m(r['tokens'])} spent, 0 done)") \
            + f" [{r.get('completed', 0)} done]"
    L = [f"# FLOW scoreboard {now:%Y-%m-%dT%H:%MZ} (per bucket, today UTC; replaces the 50-tick code quota, 2026-11-01)", "",
         "**Headline: tokens per completed task** (operator 2026-11-01: process the whole backlog with the fewest tokens PER TASK, "
         "not per hour). tokens = the session's Codex rollouts + its lane sub-agents; completed = boxes ticked in landed wrap-ups + "
         "rows published + filings. Every change must make this number drop. Then the flow: unblock -> launcher -> keeper dry run "
         "(PASS) -> armed -> granted; good = rows qualified up, blocking tasks closed up, open fix: tasks and idle-hours down.", "",
         ("**Inventory (ready rows vs target = 2 x lane capacity; operator 23:30Z: compute must be the ONLY bottleneck; the target "
          "is a priority order, never a stop condition):** " + ", ".join(f"{ln} **{v['ready']}/{v['target']}**" + (" DEFICIT" if v["deficit"] else "")
                                                                          for ln, v in (inventory or {}).items()) if inventory else ""), "",
         "| bucket | **tokens / completed task (today)** | rows qualified today (dry-run PASS) | dry-run FAILs today | blocking tasks closed today | blocking tasks open now "
         "| open fix: tasks (FAIL, launcher unchanged) | blocked rows now | parked rows | dry runs running (keeper) "
         "| qualified-armed cpu/gpu/host | idle compute-hours with a blocked row as cause |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|"]
    for w, r in rows.items():
        if w.startswith("_"):
            continue
        q = r["qual"]
        L.append(f"| {w} | {tok_task(w)} | {r['armed']} | {r['dryrun_fail']} | {r['closed']} | {r['open_blocking']} | {r['open_fix']} | {r['blocked_rows']} "
                 f"| {r['parked']} | {r['awaiting_keeper']} | {q['cpu']}/{q['gpu']}/{q['host']} | {r['idle_h']} |")
    if metric and metric.get("per"):
        un = metric["per"].get("unattributed")
        L += ["", "Most expensive session turns today: " + "; ".join(
            f"{t['slug']} {t['start']:%H:%M}Z {tpt.fmt_m(t['tokens'])} — {t['subject'][:80]}" for t in metric["top_turns"]) + "."
              + (f" Unattributed (shared-/workspace-era sub-agent) spend: {tpt.fmt_m(un['tokens'])}." if un else "")]
    elif metric and metric.get("error"):
        L += ["", f"tokens-per-task metric unavailable: {metric['error']}"]
    if _wtfp is not None:
        try:
            L += ["", *_wtfp.render_lines(_wtfp.collect())]
        except Exception as ex:  # the scoreboard must never die on the footprint
            L += ["", f"worktree footprint unavailable: {ex!r}"]
    waiting = [(w, r["awaiting_ids"]) for w, r in rows.items() if not w.startswith("_") and r.get("awaiting_ids")]
    if waiting:
        L += ["", "Rows whose dry run is running now (ws58 keeper, not the owner's task): "
              + "; ".join(f"{w}: " + ", ".join(ids) for w, ids in waiting) + "."]
    L += ["", "Source: BACKLOG-<bucket>.md (scripts/coordination/backlog_gen.py), compute-flags/dryrun/<id>/ (scripts/coordination/rowflow/rowflow.py) "
          "and ws58-calendar-keeper.log. No pane nudges; the backlog file is the only instruction.", ""]
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
    text = render(rows, now, rows.get("_inventory"))
    if a.dry_run:
        print(text)
    else:
        bg.write_atomic(out, text)
        bg.write_atomic(sp, json.dumps(state))
    print(now.strftime("%FT%TZ"), json.dumps({w: {k: v for k, v in r.items() if k != "qual"} for w, r in rows.items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
