"""Bandwidth-census view (Kernel R&D page, ``/loop``) - read-only.

Plane rule: the data contract ``mi210_bandwidth_census.json`` is owned by the
AutoKernel subsystem (``census_update.py`` in epyc-inference-research rewrites it
at each AK row end). This module only READS it and shapes two tables (MI210, Zen 5
EPYC 9655) for the page. It never edits the schema.

Freshness has two arms:

* age: the census file's mtime (the contract carries no producer-written
  top-level timestamp, so mtime is the only date it has);
* event: any AK row (``ak-*`` / ``akc-*``) whose ``<rowid>.ended`` grant flag is
  newer than the census means a row finished and the census was not rewritten
  after it, so the census is stale whatever its age says.

No fallback to the committed research copy: a missing live file renders absent.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

CENSUS_PATH = Path(os.environ.get(
    "AK_BW_CENSUS_JSON", "/mnt/raid0/llm/tmp/ak-bw-census/mi210_bandwidth_census.json"))
GRANTS_DIR = Path(os.environ.get(
    "AK_BW_CENSUS_GRANTS_DIR", "/mnt/raid0/llm/tmp/compute-flags/grants"))
AK_ROW_PREFIXES = ("ak-", "akc-")


def ak_rows_ended_after(grants_dir: Path, census_mtime: float) -> list[dict]:
    """AK row-end flags newer than the census, newest first. Deterministic."""
    out = []
    try:
        entries = list(os.scandir(grants_dir))
    except OSError:
        return out
    for e in entries:
        name = e.name
        if not name.endswith(".ended"):
            continue
        row = name[: -len(".ended")]
        if not row.startswith(AK_ROW_PREFIXES):
            continue
        try:
            mt = e.stat().st_mtime
        except OSError:
            continue
        if mt > census_mtime:
            out.append({"row": row, "ended_mtime": mt})
    out.sort(key=lambda r: (-r["ended_mtime"], r["row"]))
    return out


def trend(history) -> str:
    """Tiny text trend over ``history`` [[row, gbps], ...]."""
    vals = []
    for h in history or []:
        try:
            vals.append(float(h[1]))
        except (TypeError, ValueError, IndexError):
            continue
    if len(vals) < 2:
        return ""
    bars = "▁▂▃▄▅▆▇█"
    lo, hi = min(vals), max(vals)
    spark = "".join(bars[0 if hi == lo else int((v - lo) / (hi - lo) * 7)] for v in vals[-8:])
    last, prev = vals[-1], vals[-2]
    arrow = "↑" if last > prev else ("↓" if last < prev else "→")
    return spark + arrow


def _num(x) -> Optional[float]:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def shape_rows(doc: dict) -> dict:
    """Split records into GPU (MI210) and CPU tables, sorted by recoverable ms desc."""
    floor = _num(doc.get("floor_gbps"))
    gpu_ceiling = _num(doc.get("ceiling_gbps"))
    cpu_ceils = ((doc.get("cpu") or {}).get("ceiling_gbps") or {})
    tables = {"mi210": [], "cpu": []}
    for rid, rec in sorted((doc.get("records") or {}).items()):
        if not isinstance(rec, dict):
            continue
        is_cpu = rec.get("device") == "cpu"
        gbps = _num(rec.get("gbps"))
        if is_cpu:
            ceiling = _num(rec.get("ceiling_gbps"))
            if ceiling is None:
                ceiling = _num(cpu_ceils.get(rec.get("config")))
            frac = _num(rec.get("frac_of_ceiling"))
            gap = None
        else:
            ceiling = gpu_ceiling
            frac = None
            gap = None if gbps is None or floor is None else round(gbps - floor, 1)
        if frac is None and gbps is not None and ceiling:
            frac = gbps / ceiling
        tables["cpu" if is_cpu else "mi210"].append({
            "id": rid,
            "kernel": rec.get("kernel_class"),
            "shape": rec.get("shape"),
            "n": rec.get("n"),
            "config": rec.get("config"),
            "model": rec.get("model"),
            "gbps": gbps,
            "ceiling_gbps": ceiling,
            "gap_gbps": gap,
            "frac_of_ceiling": None if frac is None else round(frac, 4),
            "share_of_round": _num(rec.get("share_of_round")),
            "recoverable_ms": _num(rec.get("recoverable_ms_per_round")),
            "rank": rec.get("rank"),
            "status": rec.get("status"),
            "seed": rec.get("seed"),
            "source_row": rec.get("source_row"),
            "measured_at": rec.get("measured_at"),
            "trend": trend(rec.get("history")),
        })
    for rows in tables.values():
        rows.sort(key=lambda r: (-(r["recoverable_ms"] or 0.0), r["id"]))
    return tables


def build(census_path: Path = None, grants_dir: Path = None) -> dict:
    """Read the census; return the payload body (no envelope)."""
    census_path = Path(census_path or CENSUS_PATH)
    grants_dir = Path(grants_dir or GRANTS_DIR)
    base = {"schema": "epyc.hub.bw_census_view.v1", "evidence": str(census_path),
            "grants_dir": str(grants_dir)}
    try:
        mtime = census_path.stat().st_mtime
        doc = json.loads(census_path.read_text())
        if not isinstance(doc, dict):
            raise ValueError("census root is not an object")
    except FileNotFoundError:
        return {**base, "present": False, "error": f"census file missing: {census_path}"}
    except (OSError, ValueError) as exc:
        return {**base, "present": False, "error": f"census unreadable: {type(exc).__name__}: {exc}"}
    ended = ak_rows_ended_after(grants_dir, mtime)
    return {
        **base,
        "present": True,
        "census_mtime": mtime,
        "contract_schema": doc.get("schema"),
        "floor_gbps": doc.get("floor_gbps"),
        "target_gbps": doc.get("target_gbps"),
        "ceiling_gbps": doc.get("ceiling_gbps"),
        "cpu": doc.get("cpu"),
        "applied_count": len(doc.get("applied") or []),
        "tables": shape_rows(doc),
        "event_stale": bool(ended),
        "ak_rows_ended_after_census": ended[:20],
    }
