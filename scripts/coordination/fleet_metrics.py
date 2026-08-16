#!/usr/bin/env python3
"""fleet_metrics.py — the plan's metrics, computed rather than reported.

P4-1 / D9 (Loop-Owned Fleet). Every number here is derived from an artifact
somebody else wrote — git history, the alarm ledger, the bus queue — and none of
it is a self-assessment. That is the entire design constraint, and it comes from
a measured failure: the coordinator's own recurrence counts were the least
trustworthy content in its ledger, and half of them were the role grading
itself. A metric an agent can improve by writing a nicer summary is not a metric.

WHAT IS COMPUTED, AND WHAT IS HONESTLY A PROXY
==============================================
* self-repair share      EXACT. Commit-path classification over
                         `scripts/coordination/**` + `coordination/session-bus/**`
                         against all commits in the window. This is D9's
                         definition verbatim and cannot be gamed by prose.
* alarm fidelity         EXACT. Read from the alarm ledger: how many alarms
                         fired, and how many were drill/test versus real. The
                         gate is "every drill alarm arrives; ZERO alarms on a
                         well-run night", so both halves are counted.
* queue health           EXACT. Folded from the queue: READY depth, rows in a
                         terminal-but-infra state, rows held by a dead owner.
* worker throughput      EXACT where reports exist: rows completed, tokens per
                         row, subagents_spawned (the fan-out multiplier, which
                         until now had no detector but the operator saying so).
* compute duty cycle     PROXY, and labelled as one. Derived from fleet_watch's
                         COMPUTE-IDLE observations, which sample the hardware.
                         It is only as good as fleet_watch's uptime, so the
                         report states the observed window rather than implying
                         coverage it does not have.
* operator interventions NOT COMPUTABLE from artifacts today, and the report
                         says so rather than printing a zero. A manual nudge
                         leaves no distinguishable trace. Counting it needs a
                         write-side hook; that is filed, not faked. Reporting an
                         uncounted quantity as 0 is how a gate passes for the
                         wrong reason.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from session_bus import get_bus_root  # noqa: E402

REPO = Path("/workspace")
LOOP_PLANE = ("scripts/coordination/", "coordination/session-bus/")


def _git(*args: str) -> str:
    out = subprocess.run(["git", "-C", str(REPO), *args],
                         capture_output=True, text=True, timeout=60)
    return out.stdout if out.returncode == 0 else ""


def self_repair_share(days: int) -> dict:
    """D9, exact: what fraction of commits touched the coordination layer itself?"""
    since = f"--since={days}.days.ago"
    shas = [s for s in _git("log", since, "--format=%H").split() if s]
    loop, other = 0, 0
    for sha in shas:
        files = [f for f in _git("show", "--name-only", "--format=", sha).splitlines() if f.strip()]
        if any(f.startswith(LOOP_PLANE) for f in files):
            loop += 1
        else:
            other += 1
    total = loop + other
    return {
        "window_days": days, "commits_total": total,
        "commits_touching_loop_plane": loop,
        "share_pct": round(100.0 * loop / total, 1) if total else None,
        "target_pct": "<10",
        "basis": "commit-path classification (D9) — never self-reported",
    }


def alarm_fidelity(bus_root: Path) -> dict:
    path = Path(str(bus_root / "alarms.jsonl"))
    if not path.exists():
        return {"status": "no alarm ledger yet", "records": 0}
    kinds, keys = Counter(), Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        kinds[r.get("event", "?")] += 1
        keys[r.get("key", "?")] += 1
    return {"records": sum(kinds.values()), "by_event": dict(kinds),
            "by_key": dict(keys), "target": "every drill alarm arrives; zero on a well-run night"}


def queue_health(bus_root: Path) -> dict:
    rows: dict[str, dict] = {}
    qp = bus_root / "queue.jsonl"
    if qp.exists():
        for line in qp.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("task_id"):
                rows.setdefault(r["task_id"], {}).update(
                    {k: v for k, v in r.items() if v is not None})
    by_status = Counter(r.get("status") for r in rows.values())
    return {"logical_rows": len(rows), "by_status": dict(by_status),
            "ready_depth": by_status.get("READY", 0),
            "infra_blocked": by_status.get("INFRA_BLOCKED", 0)}


def worker_throughput(runs_root: Path) -> dict:
    if not runs_root.is_dir():
        return {"status": "no runs directory yet"}
    reports, rows_pass, rows_fail, tokens, subagents = 0, 0, 0, [], []
    for d in sorted(runs_root.iterdir()):
        rp = d / "report.json"
        if not rp.exists():
            continue
        try:
            r = json.loads(rp.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        reports += 1
        tokens.append(r.get("tokens_used") or 0)
        subagents.append(r.get("subagents_spawned") or 0)
        for row in r.get("rows") or []:
            if row.get("outcome") == "pass":
                rows_pass += 1
            else:
                rows_fail += 1
    return {
        "reports": reports, "rows_pass": rows_pass, "rows_other": rows_fail,
        "tokens_per_batch_mean": round(sum(tokens) / len(tokens)) if tokens else None,
        "subagents_spawned_total": sum(subagents),
        "note": ("subagents_spawned closes RTG-49/F-15 for the pool tier: until now the "
                 "only detector of fan-out was the operator saying so"),
    }


def compute_duty_cycle(log_path: Path, days: int) -> dict:
    if not log_path.exists():
        return {"status": "no fleet_watch log", "proxy": True}
    idle = total = 0
    first = last = None
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "COMPUTE-IDLE" not in line and "COMPUTE-" not in line:
            continue
        total += 1
        if "COMPUTE-IDLE" in line:
            idle += 1
        ts = line[:19]
        first = first or ts
        last = ts
    return {
        "proxy": True,
        "observations": total, "idle_observations": idle,
        "idle_share_pct": round(100.0 * idle / total, 1) if total else None,
        "observed_from": first, "observed_to": last,
        "caveat": ("PROXY — fleet_watch samples the hardware, so this is only as good as "
                   "fleet_watch's own uptime. The window is stated rather than assumed."),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bus-root", default=str(get_bus_root()))
    ap.add_argument("--days", type=int, default=7, help="window for commit-based metrics")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    bus_root = Path(args.bus_root)
    report = {
        "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "self_repair_share": self_repair_share(args.days),
        "alarm_fidelity": alarm_fidelity(bus_root),
        "queue_health": queue_health(bus_root),
        "worker_throughput": worker_throughput(Path("/mnt/raid0/llm/worker-pool/runs")),
        "compute_duty_cycle": compute_duty_cycle(Path("/workspace/logs/fleet_watch.log"), args.days),
        "operator_delivery_interventions": {
            "value": None,
            "status": "NOT COMPUTABLE from artifacts — a manual nudge leaves no distinct trace",
            "why_not_zero": ("reporting an uncounted quantity as 0 is how a gate passes for the "
                             "wrong reason; this needs a write-side hook, which is filed, not faked"),
        },
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("=" * 74)
    print(f"FLEET METRICS — {report['generated']}  (window: {args.days}d)")
    print("=" * 74)
    s = report["self_repair_share"]
    print(f"\nSELF-REPAIR SHARE (D9, exact)   {s['share_pct']}%  target {s['target_pct']}")
    print(f"  {s['commits_touching_loop_plane']}/{s['commits_total']} commits touched the loop plane")
    q = report["queue_health"]
    print(f"\nQUEUE          {q['logical_rows']} rows · READY {q['ready_depth']} · INFRA_BLOCKED {q['infra_blocked']}")
    print(f"  {q['by_status']}")
    w = report["worker_throughput"]
    print(f"\nWORKERS        {w.get('reports', 0)} report(s) · pass {w.get('rows_pass', 0)} · "
          f"other {w.get('rows_other', 0)} · subagents {w.get('subagents_spawned_total', 0)}")
    if w.get("tokens_per_batch_mean"):
        print(f"  mean tokens/batch {w['tokens_per_batch_mean']} (D1 ceiling 250000)")
    a = report["alarm_fidelity"]
    print(f"\nALARMS         {a.get('records', 0)} record(s) {a.get('by_event', '')}")
    c = report["compute_duty_cycle"]
    print(f"\nCOMPUTE (PROXY) idle {c.get('idle_share_pct')}% of {c.get('observations')} observations")
    print(f"  {c.get('caveat', '')}")
    o = report["operator_delivery_interventions"]
    print(f"\nOPERATOR INTERVENTIONS  {o['status']}")
    print(f"  {o['why_not_zero']}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
