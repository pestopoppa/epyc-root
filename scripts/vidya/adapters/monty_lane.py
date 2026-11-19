"""Orchestrator Monty REPL lane telemetry -> strict reader -> shared grade (VB-MONTY-LANE-WIRE).

Source: ``logs/monty_lane.jsonl`` (``ORCHESTRATOR_MONTY_LANE_LOG``) written by orchestrator
``src/repl_environment/monty_adapter.py`` (flag ``monty_repl``, default off, so the file does not exist until the
flag runs). One JSON row per REPL cell, plus ``{"event": "lane_unavailable", "reason": ...}`` rows when the lane
could not be built. Only an explicitly named file is read.

What is projected (DIAGNOSTIC shares of the lane, never task success):

* ``monty_lane_route_share`` -- cells whose route is ``monty`` over all cells, per (role, lane build).
* ``monty_lane_fallback_share`` -- cells that were screened in (``screen == "in_subset"``) and then fell back to
  CPython (``fallback`` set) over all screened-in cells, per (role, lane build). Cells the screen sent to CPython
  up front are not fallbacks; they are in the route share and in ``extra.screen_reasons``.
* ``monty_lane_total_ms_p95`` -- nearest-rank p95 of ``total_ms`` over all cells, per (role, lane build); the
  per-route p95 is in ``extra.route_p95``. At most 3 tuples per role: the planning context admits only 3
  harness-tier claims, so a finer split would crowd the shares out of the answer.

The screen-reason histogram (reasons truncated to their first two ``:`` segments so a per-name reason such as
``name:undefined:<n>`` cannot explode cardinality) rides in ``extra`` of the share tuples.

Not inferred: the log carries no lane build. An optional ``lane_build`` field on a row is read into the stratum;
absent it reads ``unknown`` (era = pydantic-monty 1.6.0 is a write-side addition, never invented here). A row
with an unknown ``event`` is counted and ignored; ``lane_unavailable`` rows are tallied in ``extra`` only. The log
is unsealed producer output: category CANDIDATE, protocol_id empty, ``ClaimTuple.grade()`` is the only grader --
this module writes no grading rule.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from claim_tuple import ClaimTuple, ProjectionError, register

SOURCE_KIND = "monty-lane"
ADAPTER_ID = "vidya.adapters.monty_lane/v1"
AUTHORITY = "measurement"
PLANNER_CONSUMER = "orchestrator.monty_lane"
ROUTE_SHARE = "monty_lane_route_share"
FALLBACK_SHARE = "monty_lane_fallback_share"
LATENCY = "monty_lane_total_ms_p95"
MAX_BYTES = 64 * 1024 * 1024
_ROUTES = {"monty", "cpython"}
_INT = ("cell", "pid", "refusals", "callbacks", "sessions")
_BOOL = ("ok", "final", "timed_out")
_OPT_MS = ("monty_ms", "cpython_ms")
_OPT_INT = ("replayed", "journal")


def _bad(msg: str) -> None:
    raise ProjectionError("monty-lane: " + msg)


def _num(v: Any) -> bool:
    return type(v) in (int, float) and math.isfinite(v)


def _nonneg_int(v: Any) -> bool:
    return type(v) is int and v >= 0


def _pairs(items):
    out: dict = {}
    for k, v in items:
        if k in out:
            _bad("duplicate JSON key " + k)
        out[k] = v
    return out


def _read(path: Path) -> tuple[bytes, list[dict]]:
    if not path.is_file():
        _bad("not a file")
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        _bad("file exceeds bounded envelope")
    lines = raw.split(b"\n")
    lines.pop()                           # '' after a terminated final line, else a torn concurrent append: never a row
    rows = []
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_pairs, parse_constant=lambda x: _bad("nonfinite constant"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ProjectionError(f"monty-lane: line {i} is not JSON") from exc
        if not isinstance(row, dict) or not _num(row.get("ts")):
            _bad(f"line {i} lacks ts")
        rows.append(row)
    return raw, rows


def _check_cell(r: dict) -> None:
    if any(k not in r for k in (*_INT, *_BOOL, "route", "screen", "fallback", "total_ms", "task_id", "role")):
        _bad("cell row missing fields")
    if r["route"] not in _ROUTES or not isinstance(r["screen"], str) or not r["screen"]:
        _bad("cell route/screen malformed")
    if not all(_nonneg_int(r[k]) for k in _INT) or r["cell"] < 1:
        _bad("cell counts malformed")
    if not all(type(r[k]) is bool for k in _BOOL):
        _bad("cell flags malformed")
    if not _num(r["total_ms"]) or r["total_ms"] < 0:
        _bad("cell total_ms malformed")
    if r["fallback"] is not None and not (isinstance(r["fallback"], str) and r["fallback"]):
        _bad("cell fallback malformed")
    if r["route"] == "monty" and r["fallback"] is not None:
        _bad("a monty-route cell cannot carry a fallback reason")
    if r["fallback"] is not None and r["screen"] != "in_subset":
        _bad("a fallback requires the cell to have been screened in")
    for k in ("task_id", "role"):
        if r[k] is not None and not isinstance(r[k], str):
            _bad(f"cell {k} malformed")
    if any(k in r and not (_num(r[k]) and r[k] >= 0) for k in _OPT_MS):
        _bad("cell monty_ms/cpython_ms malformed")
    if any(k in r and not _nonneg_int(r[k]) for k in _OPT_INT):
        _bad("cell replayed/journal malformed")
    if "replay_diverged" in r and type(r["replay_diverged"]) is not bool:
        _bad("cell replay_diverged malformed")
    if "worker_reused" in r and type(r["worker_reused"]) is not bool:
        _bad("cell worker_reused malformed")
    if "lane_build" in r and not (isinstance(r["lane_build"], str) and r["lane_build"]):
        _bad("cell lane_build malformed")


def _reason(screen: str) -> str:
    return ":".join(screen.split(":")[:2])


def _p95(xs: list[float]) -> float:
    s = sorted(xs)
    return s[max(0, math.ceil(0.95 * len(s)) - 1)]


def native_rows(path: str | Path) -> tuple[dict, ...]:
    path = Path(path).resolve()
    raw, rows = _read(path)
    cells: list[dict] = []
    unavailable = unknown = 0
    seen: set[tuple] = set()
    for r in rows:
        ev = r.get("event")
        if ev is None:
            _check_cell(r)
            ident = (r["pid"], r["cell"], r["ts"])
            if ident in seen:
                _bad("duplicate cell row (pid, cell, ts)")
            seen.add(ident)
            cells.append(r)
        elif ev == "lane_unavailable":
            unavailable += 1
        else:
            unknown += 1
    digest = hashlib.sha256(raw).hexdigest()
    groups: dict[tuple, list[dict]] = {}
    for c in cells:
        groups.setdefault((c["role"] or "unknown", c.get("lane_build", "unknown")), []).append(c)
    out = []
    for (role, build) in sorted(groups):
        g = groups[(role, build)]
        reasons: dict[str, int] = {}
        for c in g:
            reasons[_reason(c["screen"])] = reasons.get(_reason(c["screen"]), 0) + 1
        screened = [c for c in g if c["screen"] == "in_subset"]
        fb = [c for c in screened if c["fallback"] is not None]
        counts = {"cells": len(g), "monty_route": sum(c["route"] == "monty" for c in g),
                  "screened_in": len(screened), "fallbacks": len(fb),
                  "replayed": sum(c.get("replayed", 0) for c in fb),
                  "replay_diverged": sum(bool(c.get("replay_diverged")) for c in fb),
                  "timed_out": sum(c["timed_out"] for c in g), "not_ok": sum(not c["ok"] for c in g),
                  "tasks": len({c["task_id"] for c in g if c["task_id"]}),
                  "lane_unavailable_file": unavailable, "unknown_events_file": unknown}
        base = {"path": str(path), "sha256": digest, "counts": counts,
                "first_ts": min(c["ts"] for c in g), "last_ts": max(c["ts"] for c in g),
                "ids_sha256": hashlib.sha256("\n".join(sorted(f"{c['pid']}:{c['cell']}:{c['ts']}" for c in g)).encode()).hexdigest()}
        sk = {"role": role, "lane_build": build}
        out.append({**base, "stratum": sk, "metric": ROUTE_SHARE, "value": counts["monty_route"] / counts["cells"],
                    "screen_reasons": dict(sorted(reasons.items()))})
        if screened:
            out.append({**base, "stratum": sk, "metric": FALLBACK_SHARE, "value": len(fb) / len(screened),
                        "screen_reasons": dict(sorted(reasons.items()))})
        # ONE latency tuple per role: the planning context admits at most 3 harness-tier claims, so a per-route
        # tuple would crowd the shares out. The per-route p95 and cell counts ride in the tuple's extra.
        by_route = {route: [float(c["total_ms"]) for c in g if c["route"] == route] for route in sorted({c["route"] for c in g})}
        out.append({**base, "stratum": sk, "metric": LATENCY, "value": _p95([float(c["total_ms"]) for c in g]),
                    "route_p95": {r: _p95(x) for r, x in by_route.items()},
                    "route_cells": {r: len(x) for r, x in by_route.items()}, "screen_reasons": {}})
    return tuple(out)


def units(path: Path) -> list[Path]:
    return [path] if Path(path).is_file() else []


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or "path" not in native:
        _bad("native row malformed")
    if native not in native_rows(native["path"]):
        _bad("native row does not rederive from the log")
    s, c, metric, v = native["stratum"], native["counts"], native["metric"], native["value"]
    date = datetime.datetime.fromtimestamp(native["last_ts"], tz=datetime.timezone.utc).date().isoformat()
    scope = f"role {s['role']}, lane build {s['lane_build']}"
    caveat = "Lane diagnostic, not task success."
    if metric == ROUTE_SHARE:
        unit, direction, reps = "ratio", "higher_better", c["cells"]
        basis = "REPL cells (one row per cell)"
        text = (f"Monty lane route share {v:.4f} ({scope}): {c['monty_route']} of {c['cells']} cells ran on Monty. "
                f"{caveat} Screen reasons {native['screen_reasons']}.")
    elif metric == FALLBACK_SHARE:
        unit, direction, reps = "ratio", "lower_better", c["screened_in"]
        basis = "cells screened in to the Monty subset (screen == in_subset)"
        text = (f"Monty lane fallback share {v:.4f} ({scope}): {c['fallbacks']} of {c['screened_in']} screened-in cells "
                f"fell back to CPython ({c['replay_diverged']} diverged on replay). {caveat}")
    else:
        unit, direction, reps = "ms", "lower_better", c["cells"]
        basis = "REPL cells, all routes"
        text = (f"Monty lane total_ms p95 {v:.2f} ms ({scope}) over {reps} cells; per-route p95 "
                f"{native['route_p95']}. {caveat}")
    mid = "monty-lane:" + hashlib.sha256(json.dumps([s, metric, native["ids_sha256"]], sort_keys=True).encode()).hexdigest()[:32]
    return ClaimTuple(
        measurement_id=mid, metric=metric, value=v, date=date, category="CANDIDATE", claim=text,
        metric_direction=direction, protocol_id="", reps=reps, reps_basis=basis, unit=unit,
        attestation_path=native["path"], attestation_sha256=native["sha256"],
        attestation_locator=f"{native['path']}#{metric}:{s['role']}",
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        applicability={"consumer": PLANNER_CONSUMER, "role": s["role"]},
        observation={"outcome_native": f"{metric}={v:.4f}" if unit == "ratio" else f"{metric}={v:.2f}"},
        extra={"adapter": ADAPTER_ID, "stratum": s, "counts": c, "screen_reasons": native["screen_reasons"],
               "route_p95": native.get("route_p95", {}),
               "lane_build": s["lane_build"], "first_ts": native["first_ts"], "last_ts": native["last_ts"],
               "limitation": "unsealed producer log; diagnostic lane shares, not task success; no promotion or default-on warrant"})


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "PLANNER_CONSUMER", "native_rows", "project", "units"]
