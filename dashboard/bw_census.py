"""Bandwidth-census view (Kernel R&D page, ``/loop``) - read-only.

Plane rule: the data contract ``mi210_bandwidth_census.json`` is owned by the
AutoKernel subsystem (``census_update.py`` in epyc-inference-research rewrites it
at each AK row end). This module only READS it and passes through the producer's ranked
``surfaces[]`` (one row per (path, op), runs attached) plus the legacy per-device tables. It never edits the schema.

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
            "op": rec.get("op"),
            "op_path": rec.get("op_path"),
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


def shape_parity(doc: dict) -> Optional[dict]:
    """Roofline-parity view over ``doc['parity']`` (None when the census has none).

    Derived on read with the producer's published formula (ours % vs reference %,
    gap = max(0, ref - ours), score = gap x share_of_step, in pp); the hub never
    imports the producer. Ref status defaults to "recalled, not re-verified" so an
    unlabelled reference is never drawn as measured.
    """
    par = doc.get("parity")
    if not isinstance(par, dict):
        return None
    refs = par.get("refs") if isinstance(par.get("refs"), dict) else {}
    rows = []
    for o in par.get("ops") or []:
        if not isinstance(o, dict):
            continue
        ref = refs.get(o.get("ref")) if isinstance(refs.get(o.get("ref")), dict) else {}
        ours = _num(o.get("ours_pct"))
        gb, roof = _num(o.get("ours_gbps")), _num(o.get("roofline_gbps"))
        if ours is None and gb is not None and roof:
            ours = 100.0 * gb / roof
        ref_pct = _num(ref.get("pct"))
        # a null reference (no published measurement) has no gap and no score; never treat it as 0%
        gap = None if ours is None or ref_pct is None else max(0.0, ref_pct - ours)
        share = _num(o.get("share_of_step"))
        rows.append({
            "op": o.get("op"), "path": o.get("path"), "served": bool(o.get("served")),
            "ours_pct": None if ours is None else round(ours, 1),
            "ref": o.get("ref"), "ref_pct": ref_pct, "ref_bracket_pct": ref.get("bracket_pct"),
            "ref_status": ref.get("status") or "recalled, not re-verified",
            "ref_cite": ref.get("cite"), "ref_basis": ref.get("basis"),
            "gap_pp": None if gap is None else round(gap, 1),
            "share_of_step": share,
            "score": None if gap is None or share is None else round(gap * share, 2),
            "covered_by": o.get("covered_by") or "",
            "refresh_c21": bool(o.get("refresh_c21")),
            "source": o.get("source"),
        })
    rows.sort(key=lambda r: (not r["served"], -(r["score"] if r["score"] is not None else -1), str(r["op"])))
    return {"note": par.get("note"), "rows": rows, "refs": refs,
            "batch_dependence": par.get("batch_dependence")}


SURFACE_STATUSES = ("open", "covered", "needs_measurement", "ok")


def shape_surfaces(doc: dict, tables: dict) -> list[dict]:
    """The producer's ranked ``surfaces[]`` passed through, each with its census runs attached.

    Ranking is the producer's (saving_ms_per_step desc, nulls last); the hub only re-applies that order so a
    hand-edited file cannot reorder the page, and never fills a null (an unknown saving or gap stays null).
    """
    by_id = {r["id"]: r for rows in tables.values() for r in rows}
    out = []
    for s in doc.get("surfaces") or []:
        if not isinstance(s, dict):
            continue
        runs = []
        for rid in s.get("census_rows") or []:
            r = by_id.get(rid)
            if r is None:
                continue
            runs.append({"id": rid, "kernel": r["kernel"], "shape": r["shape"], "n": r["n"], "config": r["config"],
                         "gbps": r["gbps"], "pct_ceiling": None if r["frac_of_ceiling"] is None
                         else round(100 * r["frac_of_ceiling"], 1),
                         "measured_at": r["measured_at"], "source_row": r["source_row"]})
        runs.sort(key=lambda r: (str(r["measured_at"] or ""), r["id"]), reverse=True)
        out.append({**s, "covered_by": s.get("covered_by") or "",
                    "status": s.get("status") if s.get("status") in SURFACE_STATUSES else "open",
                    "saving_ms_per_step": _num(s.get("saving_ms_per_step")), "runs": runs,
                    # a KEEP touched this parity-only surface after its static ours % was taken (census_update mark_stale)
                    "stale": s.get("stale") is True, "stale_since": s.get("stale_since"), "stale_row": s.get("stale_row")})
    out.sort(key=lambda s: (s["saving_ms_per_step"] is None, -(s["saving_ms_per_step"] or 0.0)))
    return out


def shape_coverage(doc: dict) -> Optional[dict]:
    """The producer's registry-derived ``coverage`` (RSL-R1): uncovered-op count per served path, planned paths labelled.

    None when the census predates the key. A registry-unreadable census passes through as such (no counts invented)."""
    cov = doc.get("coverage")
    if not isinstance(cov, dict):
        return None
    paths = []
    for key, v in sorted((cov.get("paths") or {}).items()):
        if not isinstance(v, dict):
            continue
        ops = [str(o) for o in v.get("uncovered_ops") or []]
        paths.append({"key": key, "path": v.get("path"), "status": v.get("status") or "live",
                      "planned": v.get("status") == "planned", "n": v.get("n") or [],
                      "uncovered_count": len(ops), "uncovered_ops": ops})
    return {"status": cov.get("status") or "ok", "paths": paths, "mismatch": cov.get("mismatch") or [],
            "unmapped": cov.get("unmapped") or [], "uncovered_total": sum(p["uncovered_count"] for p in paths)}


def shape_family_rank(doc: dict) -> list[dict]:
    """The producer's ``family_rank`` (RSL-R4/R7), re-sorted by score desc with unpriced (null score) last; a null is never filled."""
    out = []
    for r in doc.get("family_rank") or []:
        if isinstance(r, dict) and r.get("family"):
            out.append({**r, "score": _num(r.get("score")), "kind": r.get("kind") or "family",
                        "status": "priced" if _num(r.get("score")) is not None else "unpriced"})
    out.sort(key=lambda r: (r["score"] is None, -(r["score"] or 0.0), str(r["family"])))
    return out


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
    tables = shape_rows(doc)
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
        "tables": tables,
        "target_pct": doc.get("target_pct"),
        "surfaces": shape_surfaces(doc, tables),
        "surface_groups": doc.get("surface_groups") or [],
        "parity": shape_parity(doc),
        "coverage": shape_coverage(doc),
        "family_rank": shape_family_rank(doc),
        "event_stale": bool(ended),
        "ak_rows_ended_after_census": ended[:20],
    }
