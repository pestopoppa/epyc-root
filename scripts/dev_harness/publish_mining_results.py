#!/usr/bin/env python3
"""Reduce a full mining run to ONE committable aggregate and publish it through the privacy gate.

Drops DHM-7.2 cluster ``top_terms`` (hashed-TF-IDF terms are transcript-derived), keeps counts/rates only,
then ``dh_privacy.publish_aggregate`` (validate_aggregate + raw_trace_publish_preflight)."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import dh_privacy as p


def build(run_dir: Path, *, allow_partial: bool = False, include_rules: bool = False) -> dict:
    m2 = json.loads((run_dir / "aggregate.json").read_text())
    c = dict(m2["counts"])
    rules = list(m2["rules"]) if include_rules else []
    for cl in c["dhm72"]["clusters"].values():
        cl.pop("top_terms", None)
    m1 = run_dir / "m1/aggregates"
    for key, name in (("dhm1", "dhm1"), ("dhm1_history", "dhm1_history"), ("dhm5", "dhm5"),
                      ("oab_lb1", "oab_lb1"), ("ufh14_lb8", "ufh14_lb8")):
        path = m1 / f"{name}.aggregate.json"
        if not path.exists() and allow_partial:
            continue
        source = json.loads(path.read_text())
        c[key] = source["counts"]
        if include_rules:
            rules.extend(source["rules"])
    run = json.loads((run_dir / "run.json").read_text())
    c["run"] = {k: run[k] for k in ("units", "interrupt_candidates", "cluster_docs", "clusters_reported",
                                   "planted_recovered", "sheet_items", "would_fire_total")}
    return {"schema": p.AGGREGATE_SCHEMA, "generated_at": m2["generated_at"],
            "source": "dev-harness mining full run " + run["run_id"] + " (M1 + M2), reduced; top_terms dropped",
            "spec": "scripts/dev_harness/mining_m2_aggregate.schema.json",
            "notes": m2["notes"], "rules": rules, "counts": c}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("dest", type=Path)
    parser.add_argument("--belief-declarations", type=Path,
                        help="producer-authored JSON with metadata and metric declarations at publication")
    args = parser.parse_args()
    doc = build(args.run_dir, allow_partial=bool(args.belief_declarations),
                include_rules=bool(args.belief_declarations))
    if args.belief_declarations:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vidya"))
        from adapters.dev_harness_aggregate import publish_with_beliefs
        declarations = json.loads(args.belief_declarations.read_text())
        if set(declarations) != {"metadata", "metrics"}:
            parser.error("belief declarations require exactly metadata and metrics")
        out = publish_with_beliefs(doc, args.dest, metadata=declarations["metadata"],
                                   metrics=declarations["metrics"], private_root=p.PRIVATE_ROOT,
                                   orchestrator_root=p.ORCHESTRATOR_ROOT,
                                   run_dir=args.run_dir, declarations_path=args.belief_declarations)
    else:
        out = p.publish_aggregate(doc, args.dest)
    print("published", out, out.stat().st_size)
