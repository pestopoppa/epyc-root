#!/usr/bin/env python3
"""Reduce a full mining run to ONE committable aggregate and publish it through the privacy gate.

Drops DHM-7.2 cluster ``top_terms`` (hashed-TF-IDF terms are transcript-derived), keeps counts/rates only,
then ``dh_privacy.publish_aggregate`` (validate_aggregate + raw_trace_publish_preflight)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import dh_privacy as p

def build(run_dir: Path) -> dict:
    m2 = json.loads((run_dir / "aggregate.json").read_text())
    c = dict(m2["counts"])
    for cl in c["dhm72"]["clusters"].values():
        cl.pop("top_terms", None)
    m1 = run_dir / "m1/aggregates"
    for key, name in (("dhm1", "dhm1"), ("dhm1_history", "dhm1_history"), ("dhm5", "dhm5"),
                      ("oab_lb1", "oab_lb1"), ("ufh14_lb8", "ufh14_lb8")):
        c[key] = json.loads((m1 / f"{name}.aggregate.json").read_text())["counts"]
    run = json.loads((run_dir / "run.json").read_text())
    c["run"] = {k: run[k] for k in ("units", "interrupt_candidates", "cluster_docs", "clusters_reported",
                                   "planted_recovered", "sheet_items", "would_fire_total")}
    return {"schema": p.AGGREGATE_SCHEMA, "generated_at": m2["generated_at"],
            "source": "dev-harness mining full run " + run["run_id"] + " (M1 + M2), reduced; top_terms dropped",
            "spec": "scripts/dev_harness/mining_m2_aggregate.schema.json",
            "notes": m2["notes"], "rules": [], "counts": c}

if __name__ == "__main__":
    run_dir, dest = Path(sys.argv[1]), Path(sys.argv[2])
    out = p.publish_aggregate(build(run_dir), dest)
    print("published", out, out.stat().st_size)
