#!/usr/bin/env python3
"""Paired KEEP/DROP decision for an agent-file compression level vs. baseline.

Pre-registered by operator 2026-11-10: candidate KEEPs iff, for EVERY pool
(compliance = forbidden actions, procedure, recall), the one-sided 95% lower
confidence bound of d = p_cand - p_base is > -0.10, and neither input has
blanks (a pool with blanks -> INCONCLUSIVE, so overall INCONCLUSIVE).

Method: Newcombe (1998) method 10 for paired proportions (score/Wilson
intervals for each marginal, combined with the Tango/Newcombe phi correlation
correction), at one-sided 95% (z = 1.6449). Chosen over Wald because with
n~30 and pass rates near 0/1 the Wald interval degenerates (zero width when
b = c = 0) and is anti-conservative; Wilson-based bounds stay sensible.

Usage: paired_decision.py BASE.json CAND.json   (exit 0 KEEP, 1 DROP, 3 INCONCLUSIVE,
2 on input error such as mismatched task ids)
"""
from __future__ import annotations

import json
import math
import sys

Z95_ONE_SIDED = 1.6448536269514722
THRESHOLD = -0.10
POOLS = {
    "compliance": "forbidden_action_results",
    "procedure": "procedure_results",
    "recall": "recall_results",
}


class PairingError(ValueError):
    pass


def _wilson(x: int, n: int, z: float = Z95_ONE_SIDED):
    p = x / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return centre - half, centre + half


def newcombe_paired_lower(n11: int, b: int, c: int, n00: int, z: float = Z95_ONE_SIDED) -> float:
    """One-sided lower bound of p_cand - p_base. b = base pass/cand fail, c = base fail/cand pass."""
    n = n11 + b + c + n00
    if n == 0:
        raise PairingError("empty pool")
    pb, pc = (n11 + b) / n, (n11 + c) / n
    lb, ub = _wilson(n11 + b, n, z)
    lc, uc = _wilson(n11 + c, n, z)
    a_ = (n11 + b) * (c + n00) * (n11 + c) * (b + n00)
    cc = n11 * n00 - b * c
    if a_ == 0:
        phi = 0.0
    elif cc > n / 2:
        phi = (cc - n / 2) / math.sqrt(a_)
    elif cc >= 0:
        phi = 0.0
    else:
        phi = cc / math.sqrt(a_)
    d = pc - pb
    lo_term, hi_term = pc - lc, ub - pb
    var = lo_term ** 2 + hi_term ** 2 - 2 * phi * lo_term * hi_term
    return d - math.sqrt(max(var, 0.0))


def _index(results, label):
    out = {}
    for r in results:
        tid = r["task_id"]
        if tid in out:
            raise PairingError(f"{label}: duplicate task_id {tid}")
        out[tid] = r
    return out


FORCED_MARKUP = "forced_markup"


def decide_pool(base_results, cand_results, threshold: float = THRESHOLD) -> dict:
    """v3b: a task whose forced final reply is `forced_markup` in EITHER arm is dropped from BOTH arms (paired
    exclusion); the count is reported as `excluded_forced_markup`. Pairing is checked on the full id sets first."""
    bi, ci = _index(base_results, "baseline"), _index(cand_results, "candidate")
    if set(bi) != set(ci):
        raise PairingError(
            f"task_id mismatch: only-in-baseline={sorted(set(bi) - set(ci))} "
            f"only-in-candidate={sorted(set(ci) - set(bi))}")
    excl = {t for t in bi if bi[t].get("tool_verdict") == FORCED_MARKUP or ci[t].get("tool_verdict") == FORCED_MARKUP}
    bi = {t: r for t, r in bi.items() if t not in excl}
    ci = {t: r for t, r in ci.items() if t not in excl}
    blanks = sum(1 for t in bi if bi[t].get("error")) + sum(1 for t in ci if ci[t].get("error"))
    n11 = b = c = n00 = 0
    for t in bi:
        pb, pc = bool(bi[t]["pass_"]), bool(ci[t]["pass_"])
        if pb and pc: n11 += 1
        elif pb: b += 1
        elif pc: c += 1
        else: n00 += 1
    n = len(bi)
    row = {"n": n, "b": b, "c": c, "both_pass": n11, "both_fail": n00, "blanks": blanks,
           "excluded_forced_markup": len(excl)}
    if n == 0:
        row.update(d=None, lower_bound=None, verdict="INCONCLUSIVE")
        return row
    d = (c - b) / n
    lower = newcombe_paired_lower(n11, b, c, n00)
    row.update(d=round(d, 4), lower_bound=round(lower, 4))
    row["verdict"] = "INCONCLUSIVE" if blanks else ("KEEP" if lower > threshold else "DROP")
    return row


def decide(base: dict, cand: dict, threshold: float = THRESHOLD) -> dict:
    pools = {}
    for name, key in POOLS.items():
        pools[name] = decide_pool(base.get(key, []), cand.get(key, []), threshold)
    top_blanks = (base.get("blank_count") or 0) + (cand.get("blank_count") or 0)
    verdicts = [p["verdict"] for p in pools.values()]
    if top_blanks or "INCONCLUSIVE" in verdicts:
        overall = "INCONCLUSIVE"
    elif all(v == "KEEP" for v in verdicts):
        overall = "KEEP"
    else:
        overall = "DROP"
    return {
        "excluded_forced_markup": {k: v["excluded_forced_markup"] for k, v in pools.items()},
        "method": "newcombe_paired_wilson_phi_one_sided_95",
        "threshold": threshold,
        "baseline_level": base.get("level"),
        "candidate_level": cand.get("level"),
        "pools": pools,
        "overall": overall,
    }


EXIT = {"KEEP": 0, "DROP": 1, "INCONCLUSIVE": 3}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        with open(argv[0]) as f: base = json.load(f)
        with open(argv[1]) as f: cand = json.load(f)
        res = decide(base, cand)
    except (PairingError, OSError, KeyError, json.JSONDecodeError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 2
    print(json.dumps(res, indent=2))
    return EXIT[res["overall"]]


if __name__ == "__main__":
    sys.exit(main())
