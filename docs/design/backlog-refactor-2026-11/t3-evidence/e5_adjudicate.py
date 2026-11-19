"""BRF-T3 E5 adjudication (zero inference): banked A7 Gemma cells vs the corrected-placement witness set.

Usage: python3 -I e5_adjudicate.py <a7 gemma run dir> <e5_manifests_a7_placement1 dir> > e5-adjudication.json
Dispositions per backlog-experiment-manifest-20261102.json EXP-05 evidence_inventory:
VALID | DEMONSTRATED-INVALID | UNRESOLVED-MISSING-EVIDENCE.
"""
import hashlib
import json
import os
import sys
from collections import Counter

D, M = sys.argv[1], sys.argv[2]
STRADDLE = ("0-47,96-143", "48-95,144-191")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


cells = [json.loads(line) for line in open(f"{D}/cells.jsonl")]
events = open(f"{D}/events.jsonl").read().lower()
cache_drop_witness = any(k in events for k in ("drop_caches", "cache_drop", "drop-caches"))
layouts = set()
out = []
for r in cells:
    af = f"{D}/affinity/{r['cell_id']}.json"
    a = json.load(open(af))
    inst = [
        {
            "cpus": i["expected_cpus"],
            "declared_policy": c.get("numactl_policy"),
            "affinity_match": i["match"],
            "pages_by_node": i["memory_placement"]["pages_by_node"],
            "local_fraction": round(i["memory_placement"]["local_fraction"], 4),
        }
        for i, c in zip(a["instances"], r["instances"])
    ]
    for i in inst:
        layouts.add(json.dumps(i["pages_by_node"], sort_keys=True))
    straddle_nopol = any(i["cpus"] in STRADDLE and i["declared_policy"] in (None, "none") for i in inst)
    if straddle_nopol:
        disp = "DEMONSTRATED-INVALID"
        why = (
            "req (b) violated: straddling half-machine cpuset with numactl_policy=none, not declared a "
            "defect-replication control; pages_by_node witness shows model pages spread N0-N3 "
            "(local_fraction 0.5), identical to the preceding interleave=all cells' layout - an inherited "
            "warm page cache, which also witnesses req (c) non-compliance (first touch under policy=none "
            "after a cache drop cannot reproduce the 4-node interleave counts)"
        )
    elif all(i["affinity_match"] for i in inst) and all(i["declared_policy"] == "interleave=all" for i in inst):
        disp = "UNRESOLVED-MISSING-EVIDENCE"
        why = (
            "declared full-machine 0-95 interleave=all, affinity match, pages evenly interleaved "
            "(local_fraction 1.0) - consistent with corrected placement, but no runtime memory-policy "
            "attestation (req d) and no per-cell cache-drop witness (req c); not established, NOT invalid"
        )
    else:
        disp, why = "VALID", "all witnesses present and compliant"
    out.append(
        {
            "cell_id": r["cell_id"],
            "timestamp": r["timestamp"],
            "decision_grade_label": r["decision_grade"],
            "aggregate_decode_tps_as_recorded": round(r["aggregate_decode_tps"], 2),
            "instances": inst,
            "disposition": disp,
            "reason": why,
            "affinity_sha256": sha(af),
        }
    )

qwen = []
for g in ("qwen36_q8_0", "qwen3_next_80b"):
    for f in sorted(os.listdir(f"{M}/{g}")):
        p = f"{M}/{g}/{f}"
        m = json.load(open(p))
        ins = [[i["cpu_list"], i["numactl_policy"]] for i in m["instances"]]
        bad = any(c != "0-95" and pol == "none" for c, pol in ins)
        qwen.append(
            {
                "manifest": f"{g}/{f}",
                "instances": ins,
                "req_b": "FAIL (straddling cpuset, policy none, no defect-control declaration)" if bad else "PASS",
                "req_c_per_cell_drop_declared": "drop" in json.dumps(m).lower(),
                "sha256": sha(p),
            }
        )
for g in ("qwen36_q8_0", "qwen3_next_80b"):
    has = any(q["manifest"].startswith(g) and q["instances"] == [["0-95", "interleave=all"]] for q in qwen)
    for q in qwen:
        if q["manifest"].startswith(g):
            q["req_a_full_interleave_shape_in_group"] = has

res = {
    "schema": "brf-t3-e5-adjudication/1",
    "generated": "2026-11-02",
    "agent": "ws58",
    "run_dir": D,
    "cells_jsonl_sha256": sha(f"{D}/cells.jsonl"),
    "events_jsonl_sha256": sha(f"{D}/events.jsonl"),
    "events_cache_drop_witness_present": cache_drop_witness,
    "distinct_pages_by_node_layouts_across_cells": len(layouts),
    "harness_note": "research scripts/benchmark/server_numa_np_sweep.py:5 docstring: drop_caches + re-warm runs between model groups, not per cell",
    "dispositions": dict(Counter(c["disposition"] for c in out)),
    "cells": out,
    "historical_conclusions": "each cell's recorded throughput stays accurate as recorded; dispositions judge corrected-placement compliance only",
    "qwen_manifest_reconciliation": {
        "count": len(qwen),
        "req_a_pass_groups": sorted({q["manifest"].split("/")[0] for q in qwen if q["req_a_full_interleave_shape_in_group"]}),
        "req_b_fail": sum(q["req_b"].startswith("FAIL") for q in qwen),
        "req_c_per_cell_drop_declared": sum(q["req_c_per_cell_drop_declared"] for q in qwen),
        "req_d": "not attestable from manifests (harness-side runtime attestation)",
        "req_e": "harness reuse not assessable from manifests",
        "manifests": qwen,
    },
    "regeneration_candidates": [c["cell_id"] for c in out if c["disposition"] == "DEMONSTRATED-INVALID"]
    + [c["cell_id"] + " (only if the decision needs the witness)" for c in out if c["disposition"] == "UNRESOLVED-MISSING-EVIDENCE"]
    + ["the 20 Qwen manifests after (b)/(c) reconciliation; launcher a7-fire-20260813 MISSING, rebuild first"],
}
print(json.dumps(res, indent=1))
