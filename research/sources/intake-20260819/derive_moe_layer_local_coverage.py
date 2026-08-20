#!/usr/bin/env python3
"""Re-derive the layer-local MoE expert-coverage figures cited by intake-1185 / intake-1200.

WHY THIS EXISTS: those figures were quoted across a whole intake batch with no script behind
them, so they looked unreproducible (recorded as defect D11). They are not -- the underlying
artifact is properly provenanced and SHA256SUM'd. This script is the missing derivation, so the
next reader re-runs it instead of re-litigating it.

THE POINT OF THE MEASUREMENT: the 2026-07-17 no-go was decided on the GLOBAL AGGREGATE
(top_32 = 15.19%, Gini 0.0664, entropy 0.9987), which is the wrong unit for a cache whose
allocation unit is a (layer, expert) TENSOR. Per-layer, the same data shows materially more skew.

Usage:  python3 derive_moe_layer_local_coverage.py [path/to/expert-routing-skew.counts.json]
"""
from __future__ import annotations

import json
import statistics
import sys

DEFAULT = (
    "/mnt/raid0/llm/epyc-inference-research/data/"
    "expert_routing_skew_glm52_20260717T_production_representative/"
    "expert-routing-skew.counts.json"
)


def main(path: str = DEFAULT) -> int:
    with open(path) as fh:
        data = json.load(fh)

    agg = data["aggregate"]
    layers = data["layers"]

    # Every layer carries an identical selection count, so the selection-weighted mean over
    # layers equals the unweighted mean of per-layer shares. Assert it rather than assume it --
    # if a future artifact violates this, the means below would be silently wrong.
    totals = {layer["total_selections"] for layer in layers}
    assert len(totals) == 1, f"layers have unequal selection counts: {sorted(totals)[:5]}"

    print(f"artifact           : {path}")
    print(f"layers             : {len(layers)}  x  {totals.pop():,} selections each")
    print(f"aggregate          : entropy_norm {agg['entropy_norm']:.4f}  gini {agg['gini']:.4f}")

    ginis = [layer["gini"] for layer in layers]
    entropies = [layer["entropy_norm"] for layer in layers]
    print(f"per-layer gini     : median {statistics.median(ginis):.4f}  max {max(ginis):.4f}")
    print(f"per-layer entropy  : median {statistics.median(entropies):.4f}  min {min(entropies):.4f}")

    print("\nWEIGHTED TRAFFIC COVERAGE  (per-layer mean vs the global aggregate)")
    print(f"  {'budget':>8}  {'per-layer':>10}  {'aggregate':>10}  {'ratio':>6}")
    for key in ("top_8", "top_16", "top_32", "top_64", "top_128"):
        vals = [layer["top_shares"][key] for layer in layers if key in layer["top_shares"]]
        if not vals:
            continue
        local = statistics.mean(vals)
        glob = agg["top_shares"].get(key, 0.0)
        ratio = (local / glob) if glob else float("nan")
        print(f"  {key:>8}  {local * 100:9.1f}%  {glob * 100:9.1f}%  {ratio:5.2f}x")

    print(
        "\nREADING: layer-local skew is worth 2.45x the global statistic AT top_32 -- not 'about 2.4x\n"
        "at every budget', which is how this was first reported. The advantage DECAYS with budget:\n"
        "3.98x at top_8 down to 1.42x at top_128. Quote the ratio with its budget attached.\n"
        "The aggregate Gini of 0.07 reports near-uniformity; per-layer it is 0.45. A gate decided\n"
        "on the aggregate was decided on the wrong unit -- which is what reopened this question.\n"
        "This does NOT by itself make expert caching pay: see intake-1200 for the bottleneck\n"
        "argument (we are RAM-resident and do not fetch), which is a separate and stronger objection."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
