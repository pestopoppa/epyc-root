#!/usr/bin/env python3
"""KEEP-TAIL-1: report p95 timing inflation (P) and the widened floor (F) beside every GPU A/B.

    P = p95 timing inflation of one arm, in percent:  (p95 / median - 1) * 100 over its timed samples
    F = max(2.00, sqrt(2) * P)                         two independent arms add in quadrature

Reporting is always safe and applies to every row. ENFORCEMENT (refusing a keep whose effect
sits inside F, and journalling the refusal) applies only to rows named in `scope.json`: the
FUTURE GPU A/B rows main-inf22 acked (H8b r2 / H8B-E2E, FA r5, C8 increments). Nothing is
retroactive and C7r's gate is untouched: `applies()` is False for it, so `verdict()` reports
P/F and leaves `refused` False.

Usage (library): verdict(row_id, effect_pct, samples_a, samples_b, region=...) -> dict.
CLI: keep_tail.py ROW_ID EFFECT_PCT A_SAMPLES_JSON B_SAMPLES_JSON [--journal PATH]
"""
from __future__ import annotations

import fnmatch
import json
import math
from pathlib import Path
import statistics
import sys
import time

FLOOR_BASE_PCT = 2.00
SCOPE_FILE = Path(__file__).with_name("scope.json")
REGION_KEYS = ("warm_up", "timed_loop", "compile_import_check")
DEFAULT_JOURNAL = Path("/workspace/logs/keep_tail_refusals.jsonl")


def p95_inflation_pct(samples) -> float:
    xs = sorted(float(x) for x in samples)
    if len(xs) < 5:
        raise ValueError("p95 needs at least 5 timing samples")
    if any(not math.isfinite(x) or x <= 0 for x in xs):
        raise ValueError("timing samples must be finite and positive")
    k = 0.95 * (len(xs) - 1)  # linear interpolation, numpy 'linear' convention
    lo, hi = math.floor(k), math.ceil(k)
    p95 = xs[lo] + (xs[hi] - xs[lo]) * (k - lo)
    return (p95 / statistics.median(xs) - 1.0) * 100.0


def widened_floor_pct(p_pct: float) -> float:
    return max(FLOOR_BASE_PCT, math.sqrt(2.0) * p_pct)


def load_scope(path: Path = SCOPE_FILE) -> list[str]:
    return list(json.loads(Path(path).read_text("utf-8"))["enforced_row_patterns"])


def applies(row_id: str, scope=None) -> bool:
    return any(fnmatch.fnmatchcase(row_id, p) for p in (scope if scope is not None else load_scope()))


def verdict(row_id: str, effect_pct: float, samples_a, samples_b, *, region: dict | None = None,
            scope=None, journal: Path | None = None) -> dict:
    """Always reports P_a, P_b, P and F. `refused` is only ever True for an in-scope row."""
    pa, pb = p95_inflation_pct(samples_a), p95_inflation_pct(samples_b)
    p = max(pa, pb)
    f = widened_floor_pct(p)
    declared = isinstance(region, dict) and all(isinstance(region.get(k), str) and region[k] for k in REGION_KEYS)
    enforced = applies(row_id, scope)
    inside = abs(effect_pct) < f
    out = {"schema": "epyc.keep_tail.v1", "row_id": row_id, "effect_pct": effect_pct,
           "P_a_pct": round(pa, 4), "P_b_pct": round(pb, 4), "P_pct": round(p, 4), "F_pct": round(f, 4),
           "region_declared": declared, "enforced": enforced,
           "effect_inside_tail": inside, "refused": False, "reason": None}
    if enforced and not declared:
        out.update(refused=True, reason=f"timing region undeclared (need {list(REGION_KEYS)})")
    elif enforced and inside:
        out.update(refused=True, reason=f"effect {effect_pct:+.2f}% inside the reported tail floor F={f:.2f}% (P={p:.2f}%)")
    if out["refused"]:
        j = Path(journal) if journal is not None else DEFAULT_JOURNAL
        j.parent.mkdir(parents=True, exist_ok=True)
        with open(j, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({**out, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, sort_keys=True) + "\n")
    return out


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    journal = None
    if "--journal" in a:
        i = a.index("--journal"); journal = Path(a[i + 1]); del a[i:i + 2]
    row, eff, sa, sb = a
    r = verdict(row, float(eff), json.loads(sa), json.loads(sb), journal=journal)
    print(json.dumps(r, sort_keys=True))
    return 3 if r["refused"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
