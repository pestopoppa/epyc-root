#!/usr/bin/env python3
"""M2 mining driver: DHM-2 guard audit, DHM-3 ITS pilot, DHM-4 labelling sheet, DHM-7.2 clustering.

One streaming pass over a projection run and its AgentRun conversion (same run id):

    nice -n 19 /usr/bin/python3 scripts/dev_harness/mine_m2.py \\
        --projection /mnt/raid0/llm/private/dev-harness-traces/projections/<run>

  --agentrun   defaults to <private-root>/agentrun/<run>   (content: tool calls, results, prompts)
  --out        defaults to <private-root>/mining/<run>

Inputs are read-only. Every output is PRIVATE (dh_privacy: 0700/0600, refused inside any git
work tree, the vault or a harness store):

  aggregate.json          dev-harness-aggregate.v1 (validated: counts only, no per-session keys)
  dhm2_hits.jsonl         one row per would-fire call (class, outcome, hook era, command excerpt)
  dhm3_its_pilot.json     the 5-lesson pilot, readable form of counts.dhm3
  dhm4_label_sheet.csv    100 interrupts + next operator message — the OPERATOR labels it
  dhm4_label_sheet.md     the same, formatted for reading, with the lesson-provenance template
  dhm72_members.jsonl     segment -> cluster
  run.json                inputs, timings, peak RSS

The aggregate's count tree is documented in scripts/dev_harness/mining_m2_aggregate.schema.json.
Single-threaded, stdlib + numpy (clustering and the regression only).
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):   # single-threaded BLAS
    os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
import json  # noqa: E402
import resource  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from collections import Counter  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dh_privacy  # noqa: E402
import m2_cluster  # noqa: E402
import m2_label_sheet  # noqa: E402
from m2_common import iter_units  # noqa: E402
from m2_guards import CLASSES, GuardAudit, unit_hits  # noqa: E402
from m2_lessons import ITSPilot, load_registry  # noqa: E402

RUN_SCHEMA = "dev-harness-mining-m2-run.v1"


def _jsonl(rows) -> str:
    return "".join(json.dumps(r, sort_keys=True, default=str) + "\n" for r in rows)


def run(a: argparse.Namespace) -> dict:
    t0 = time.time()
    proj = Path(a.projection)
    run_id = a.run_id or proj.name
    root = Path(a.private_root)
    agentrun_dir = Path(a.agentrun) if a.agentrun else root / "agentrun" / run_id
    out = dh_privacy.private_dir(Path(a.out) if a.out else root / "mining" / run_id)
    custody = None
    if getattr(a, "belief_declarations", None):
        import belief_run_custody as custody
        start = custody.begin(out, "m2", run_id, a.belief_declarations, __file__, [out / "aggregate.json", out / "run.json"])
    registry = load_registry(Path(a.registry)) if a.registry else load_registry()

    audit = GuardAudit()
    its = ITSPilot(registry)
    cands: list[dict] = []
    docs: list[dict] = []
    signal = Counter()
    n_units = 0
    t_pass = time.time()
    for u in iter_units(agentrun_dir, limit=a.limit_units):
        n_units += 1
        hits = unit_hits(u)
        audit.observe(u, hits)
        its.observe(u, hits)
        uc = m2_label_sheet.unit_candidates(u)
        cands += uc
        for c in uc:
            signal[(c["harness"], c["source"], c["role"], c["marker"])] += 1
        docs += m2_cluster.segment_docs(u)
    t_pass = time.time() - t_pass

    t_cl = time.time()
    embedder = None
    if a.embed_gguf:
        import m2_embed_gguf
        embedder = m2_embed_gguf.make_embedder(a.embed_gguf)
    cl_agg, cl_rows = m2_cluster.run(docs, k=a.k, embedder=embedder)
    t_cl = time.time() - t_cl

    items = m2_label_sheet.sample(cands, n=a.sheet_n)
    dh_privacy.private_write(out / "dhm4_label_sheet.csv", m2_label_sheet.render_csv(items))
    dh_privacy.private_write(out / "dhm4_label_sheet.md", m2_label_sheet.render_md(items, len(cands), run_id))
    dh_privacy.private_write(out / "dhm2_hits.jsonl", _jsonl(audit.rows))
    dh_privacy.private_write(out / "dhm72_members.jsonl", _jsonl(cl_rows))
    its_agg = its.aggregate()
    dh_privacy.private_write(out / "dhm3_its_pilot.json",
                             json.dumps({"meta": its.meta, "results": its_agg}, indent=1, sort_keys=True) + "\n")

    inter: dict = {}
    for (h, s, role, marker), n in sorted(signal.items()):
        inter.setdefault(h, {}).setdefault(s, {}).setdefault(role, {})[str(marker)] = n
    sheet_mix: dict = {}
    for it in items:
        sheet_mix.setdefault(it["harness"], Counter())[it["source"]] += 1
    agg = {
        "schema": dh_privacy.AGGREGATE_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": f"dev-harness mining M2 over projection run {run_id}",
        "spec": "scripts/dev_harness/mining_m2_aggregate.schema.json",
        "rules": (["DHM-4 sheet_items is the number of sampled label-sheet items"] if custody else [])
                 + [f"DHM-2 class {c}" for c in CLASSES] + its.meta_rules(),
        "notes": ("Would-fire = today's predicate over historical calls. Outcomes from the paired tool result. "
                  "DHM-4 labels come from the operator only. DHM-7.2 reports a cluster only with >=3 sessions "
                  "and >=2 days; the embedding is "
                  + (f"llama-embedding over {Path(a.embed_gguf).name}." if a.embed_gguf
                     else "hashed TF-IDF (no model).")),
        "counts": {
            "units": n_units,
            "dhm2": audit.aggregate(),
            "dhm3": its_agg,
            "dhm4": {"interrupt_candidates": len(cands), "sheet_items": len(items),
                     "interrupts_by_harness_source_role_marker": inter,
                     "sheet_mix": {h: dict(c) for h, c in sheet_mix.items()}},
            "dhm72": cl_agg,
        },
    }
    errs = dh_privacy.validate_aggregate(agg)
    dh_privacy.private_write(out / "aggregate.json", json.dumps(agg, indent=1, sort_keys=True) + "\n")
    summary = {
        "schema": RUN_SCHEMA, "run_id": run_id, "projection": str(proj), "agentrun": str(agentrun_dir),
        "out_dir": str(out), "units": n_units, "limit_units": a.limit_units,
        "aggregate_valid": not errs, "aggregate_errors": errs[:20],
        "would_fire_total": len(audit.rows), "interrupt_candidates": len(cands), "sheet_items": len(items),
        "cluster_docs": len(docs), "clusters_reported": cl_agg.get("clusters_reported"),
        "planted_recovered": cl_agg.get("planted_recovered"),
        "elapsed_s": {"pass": round(t_pass, 2), "cluster": round(t_cl, 2), "total": round(time.time() - t0, 2)},
        "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
    }
    dh_privacy.private_write(out / "run.json", json.dumps(summary, indent=1, sort_keys=True) + "\n")
    if custody:
        custody.finish(out, "m2", start, __file__, [out / "aggregate.json", out / "run.json"])
    return summary


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--projection", required=True, help="projections/<run> dir (its name is the run id)")
    p.add_argument("--agentrun", help="agentrun/<run> dir (default: sibling of the projection root)")
    p.add_argument("--out", help="output dir (default <private-root>/mining/<run>)")
    p.add_argument("--run-id")
    p.add_argument("--belief-declarations", help="prospective declarations captured before mining")
    p.add_argument("--private-root", default=str(dh_privacy.PRIVATE_ROOT))
    p.add_argument("--registry", help="lesson registry JSON (default scripts/dev_harness/lesson_registry.json)")
    p.add_argument("--limit-units", type=int, default=None)
    p.add_argument("--sheet-n", type=int, default=100)
    p.add_argument("--embed-gguf", help="small embedding GGUF run through llama-embedding (CPU, -t 1) instead of the "
                   "hashed TF-IDF; e.g. /mnt/raid0/llm/models/granite-embedding-97m-multilingual-r2-Q8_0.gguf")
    p.add_argument("--k", type=int, default=None, help="k-means k (default sqrt(n/2), clamp [7, 80])")
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    if os.environ.get("DEV_HARNESS_ALLOW_NOT_NICE") != "1" and os.nice(0) < 10:
        os.nice(19 - os.nice(0))
    s = run(a)
    print(json.dumps(s, indent=1, sort_keys=True))
    return 0 if s["aggregate_valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
