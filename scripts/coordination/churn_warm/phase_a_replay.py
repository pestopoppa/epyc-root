#!/usr/bin/env python3
"""CHURN-WARM-1 phase A: zero-GPU replay of the per-row dry-run launch over closed rows.

A row pays publish -> smoke (a full launch + model load) -> grant -> startup -> measurement.
A warm worker holding one grant would delete the smoke launch for every row after the first.
This replay reads the CLOSED rows' own records only (read-only):
    ready/<id>.json      published_at, lane
    dryrun/<id>/PASS.json  elapsed_s (the smoke launch wall), first_unit_at, passed_at
    grants/<id>.ended      the REAL run: "rc=<n> time=<iso> ..." + "started=<iso>" (dryrun/<id>/ended is
                           the smoke's own end and must not be used as the run end)
and estimates saved seconds per row = smoke elapsed_s (a LOWER bound: the model load inside
the real run is not counted). Stop rule (from the handoff): median saved fraction per unit
< 10% of the row's total wall -> STOP (phase B not worth a live window).

`--limit N` takes the N most recently ended rows with rc=0, a smoke elapsed_s > 0 and a
grant. Phase B (a live warm window) waits for rowflow2 and is NOT done here.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path

FLAGS = "/mnt/raid0/llm/tmp/compute-flags"
STOP_FRACTION = 0.10
_ENDED = re.compile(r"rc=(-?\d+)\s+time=(\S+)")
_STARTED = re.compile(r"^started=(\S+)", re.M)


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def _json(p):
    try:
        return json.loads(Path(p).read_text("utf-8"))
    except (OSError, ValueError):
        return None


def load_rows(flags=FLAGS):
    rows = []
    dry = Path(flags) / "dryrun"
    for d in sorted(dry.iterdir()) if dry.is_dir() else []:
        rid = d.name
        try:
            passj = _json(d / "PASS.json")
            gp = Path(flags) / "grants" / f"{rid}.ended"
            ended = gp.read_text("utf-8") if gp.is_file() else None
            ready = _json(Path(flags) / "ready" / f"{rid}.json") or {}
            m, st = _ENDED.search(ended or ""), _STARTED.search(ended or "")
            if not (passj and m and st and passj.get("elapsed_s")):
                continue
            end_t, start_t = ts(m.group(2)), ts(st.group(1))
            rows.append({"id": rid, "rc": int(m.group(1)), "end": end_t, "smoke_s": float(passj["elapsed_s"]),
                         "run_wall_s": end_t - start_t,
                         "publish_to_first_unit_s": (ts(passj["first_unit_at"]) - ts(ready["published_at"]))
                         if passj.get("first_unit_at") and ready.get("published_at") else None,
                         "lane": ready.get("lane")})
        except (KeyError, ValueError, OSError):
            continue
    return rows


def replay(rows, limit=20):
    closed = sorted((r for r in rows if r["rc"] == 0 and r["run_wall_s"] > 0), key=lambda r: r["end"])[-limit:]
    fr = [r["smoke_s"] / (r["smoke_s"] + r["run_wall_s"]) for r in closed]
    med = statistics.median(fr) if fr else None
    return {"schema": "epyc.churn_warm.phase_a.v1", "n_rows": len(closed),
            "saved_seconds_total": round(sum(r["smoke_s"] for r in closed), 1),
            "saved_seconds_median_per_row": statistics.median([r["smoke_s"] for r in closed]) if closed else None,
            "median_saved_fraction_of_row_wall": med,
            "stop_rule": f"median saved per unit < {STOP_FRACTION:.0%}",
            "verdict": ("NO DATA" if med is None else
                        "STOP: median saved fraction below 10% (smoke launch is not the dominant per-row cost)" if med < STOP_FRACTION
                        else "PROCEED to phase B after rowflow2 cut-over"),
            "estimate_is_lower_bound": True, "rows": closed}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--flags", default=FLAGS)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = replay(load_rows(a.flags), a.limit)
    text = json.dumps(res, indent=1, sort_keys=True) + "\n"
    if a.out:
        Path(a.out).write_text(text)
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
