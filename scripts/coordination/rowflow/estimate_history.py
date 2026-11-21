#!/usr/bin/env python3
"""estimate_history.py — estimate_s from what rows of the same family actually ran (AK parallel loop P0).

Deterministic and read-only. Sources, all under the compute-flags root:
  grants/<id>.ended        rc, end `time`, `started`, `estimated_wall_s`, `reason`
  grants/<id>.grant        fallback start (`start=`) when .ended carries no `started`
  ready/<id>.json          `estimate_s`, `unit_key` (the progress field in the native results file)
  filing-done/<id>.verdict.json   filed verdict, `compute_burned`, `dry_run`, `result_path`

A sample is one row run that ended `reason=complete` with rc 0 and was not a dry run (a filed
verdict, when present, must say compute_burned and not dry_run). Its family is the row id with the
`-YYYYMMDD…` tail removed (`ak-dtree-build-gpu-20261120-r2` -> `ak-dtree-build-gpu`), or the
manifest's `family` field. Per family: wall-time percentiles; when the native results file carries
the manifest's `unit_key`, also seconds per distinct unit.

  suggested estimate_s = p75(wall) x 1.25       (needs >= MIN_SAMPLES runs)
  overrun flag         = wall > 1.5 x the row's own estimate

CLI:
  estimate_history.py --row <row-id> [--units N]   one suggestion as JSON (exit 3 when no history)
  estimate_history.py --table [--json]             the per-family table
  estimate_history.py --overruns                   rows that ran > 1.5x their estimate
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime
from typing import Any, Iterable

FLAGS = "/mnt/raid0/llm/tmp/compute-flags"
MARGIN = 1.25
OVERRUN = 1.5
MIN_SAMPLES = 3
SCHEMA = "epyc.rowflow.estimate_history.v1"
_DATE_TAIL = re.compile(r"-20\d{6}(?:[T-].*)?$")


def family_of(row_id: str, manifest: dict | None = None) -> str:
    fam = (manifest or {}).get("family")
    if isinstance(fam, str) and fam.strip():
        return fam.strip()
    return _DATE_TAIL.sub("", str(row_id))


def parse_kv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for tok in re.split(r"\s+", text or ""):
        if "=" in tok:
            k, v = tok.split("=", 1)
            out.setdefault(k, v)
    return out


def _ts(value: str | None) -> float | None:
    if not value:
        return None
    v = value.strip().replace("Z", "+00:00")
    if re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d\+00:00", v):
        v = v.replace("+00:00", ":00+00:00")
    try:
        return datetime.fromisoformat(v).timestamp()
    except ValueError:
        return None


def percentile(values: list[float], q: float) -> float | None:
    """Nearest-rank on the sorted list (deterministic, no interpolation)."""
    if not values:
        return None
    v = sorted(values)
    return v[min(len(v) - 1, max(0, math.ceil(q * len(v)) - 1))]


def _load_json(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def count_units(result_path: str | None, unit_key: str | None) -> int | None:
    """Distinct values of `unit_key` in a jsonl results file (None if not countable)."""
    if not result_path or not unit_key or not result_path.endswith(".jsonl"):
        return None
    seen = set()
    try:
        with open(result_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if isinstance(rec, dict) and rec.get(unit_key) is not None and rec.get("mode") != "smoke":
                    seen.add(json.dumps(rec[unit_key], sort_keys=True))
    except OSError:
        return None
    return len(seen) or None


def samples(flags: str = FLAGS) -> list[dict[str, Any]]:
    """One record per ended row run (all of them; `usable` marks the estimate population)."""
    gdir = os.path.join(flags, "grants")
    out = []
    try:
        names = sorted(n for n in os.listdir(gdir) if n.endswith(".ended"))
    except OSError:
        return out
    for name in names:
        rid = name[: -len(".ended")]
        try:
            with open(os.path.join(gdir, name), encoding="utf-8", errors="replace") as fh:
                ended = parse_kv(fh.read())
        except OSError:
            continue
        start = _ts(ended.get("started"))
        if start is None:
            try:
                with open(os.path.join(gdir, rid + ".grant"), encoding="utf-8") as fh:
                    start = _ts(parse_kv(fh.read()).get("start"))
            except OSError:
                start = None
        end = _ts(ended.get("time"))
        wall = round(end - start, 1) if start is not None and end is not None and end >= start else None
        manifest = _load_json(os.path.join(flags, "ready", rid + ".json")) or {}
        filed = _load_json(os.path.join(flags, "filing-done", rid + ".verdict.json")) or {}
        est = manifest.get("estimate_s") or ended.get("estimated_wall_s")
        try:
            est = float(est) if est is not None else None
        except (TypeError, ValueError):
            est = None
        burned = filed.get("compute_burned", True) is not False and not filed.get("dry_run")
        usable = (wall is not None and wall > 0 and ended.get("rc") == "0"
                  and ended.get("reason") == "complete" and burned)
        units = count_units(filed.get("result_path") or manifest.get("result_path"),
                            manifest.get("unit_key")) if usable else None
        out.append({"row": rid, "family": family_of(rid, manifest), "wall_s": wall,
                    "estimate_s": est, "rc": ended.get("rc"), "reason": ended.get("reason"),
                    "filed": filed.get("row_verdict"), "usable": usable, "units": units,
                    "overrun": bool(wall and est and wall > OVERRUN * est)})
    return out


def table(recs: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    fams: dict[str, list[dict[str, Any]]] = {}
    for r in recs:
        if r["usable"]:
            fams.setdefault(r["family"], []).append(r)
    out = {}
    for fam, rs in sorted(fams.items()):
        walls = [r["wall_s"] for r in rs]
        per_unit = [r["wall_s"] / r["units"] for r in rs if r.get("units")]
        p75 = percentile(walls, 0.75)
        out[fam] = {"n": len(rs), "p50_s": percentile(walls, 0.5), "p75_s": p75,
                    "p90_s": percentile(walls, 0.9), "max_s": max(walls),
                    "suggested_estimate_s": math.ceil(p75 * MARGIN) if len(rs) >= MIN_SAMPLES else None,
                    "per_unit_n": len(per_unit),
                    "per_unit_p75_s": round(percentile(per_unit, 0.75), 2) if per_unit else None,
                    "overruns": sum(1 for r in rs if r["overrun"]),
                    "rows": [r["row"] for r in rs][-5:]}
    return out


def suggest(row_id: str, *, units: int | None = None, flags: str = FLAGS,
            recs: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """Suggested estimate for a new row from its family's history, or None (< MIN_SAMPLES).
    With `units` and a per-unit history of >= MIN_SAMPLES, scales units x per-unit p75 x 1.25."""
    fam = family_of(row_id)
    t = table(samples(flags) if recs is None else recs).get(fam)
    if not t or t["n"] < MIN_SAMPLES:
        return None
    if units and t["per_unit_n"] >= MIN_SAMPLES and t["per_unit_p75_s"]:
        est = math.ceil(units * t["per_unit_p75_s"] * MARGIN)
        just = (f"history {fam} n={t['per_unit_n']}: {units} units x {t['per_unit_p75_s']} s/unit p75 "
                f"x {MARGIN} margin = {est} s")
    else:
        est = t["suggested_estimate_s"]
        just = f"history {fam} n={t['n']}: p75 wall {t['p75_s']} s x {MARGIN} margin = {est} s"
    return {"schema": SCHEMA, "family": fam, "estimate_s": est, "estimate_justification": just,
            "overrun_threshold_s": math.ceil(est * OVERRUN), **{k: t[k] for k in
            ("n", "p50_s", "p75_s", "p90_s", "per_unit_p75_s", "overruns")}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--flags", default=FLAGS)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--row")
    g.add_argument("--table", action="store_true")
    g.add_argument("--overruns", action="store_true")
    ap.add_argument("--units", type=int)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    recs = samples(a.flags)
    if a.row:
        s = suggest(a.row, units=a.units, recs=recs)
        print(json.dumps(s, indent=1) if s else f"NO-HISTORY {family_of(a.row)} (< {MIN_SAMPLES} usable runs)")
        return 0 if s else 3
    if a.overruns:
        for r in recs:
            if r["overrun"]:
                print(f"OVERRUN {r['row']} wall={r['wall_s']} est={r['estimate_s']} "
                      f"x{r['wall_s'] / r['estimate_s']:.2f}")
        return 0
    t = table(recs)
    if a.json:
        print(json.dumps({"schema": SCHEMA, "families": t}, indent=1, sort_keys=True))
        return 0
    print(f"{'family':48s} {'n':>4s} {'p50':>8s} {'p75':>8s} {'p90':>8s} {'suggest':>8s} {'s/unit':>8s} over")
    for fam, r in t.items():
        print(f"{fam[:48]:48s} {r['n']:4d} {r['p50_s']:8.0f} {r['p75_s']:8.0f} {r['p90_s']:8.0f} "
              f"{r['suggested_estimate_s'] or '-':>8} {r['per_unit_p75_s'] or '-':>8} {r['overruns']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
