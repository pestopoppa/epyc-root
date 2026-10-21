#!/usr/bin/env python3
"""TOC-SP-11: external-corpus cross-check for the TOC-SP-5 window-binding gate.

Column-only read of the public Exgentic v2 traces dataset
(huggingface.co/datasets/Exgentic/agent-llm-traces-v2, pinned revision): only the
top-level scalar columns are fetched by parquet column projection over HTTP range
requests -- the ``spans`` column (message bodies) is never requested.  Zero inference.

``max_tokens`` here is NOT the request parameter.  In the dataset's own build
script (``scripts/build_agent_llm_traces.py``, ``_recompute_aggregates``) it is the
per-session MAXIMUM over surviving chat spans of
``gen_ai.usage.input_tokens + gen_ai.usage.output_tokens`` -- the peak per-span
prompt-plus-completion size.  It is compared against 0.60 / 0.85 of 65,536 and
262,144 as the window-binding proxy, which slightly over-states the prompt peak.

Needs pyarrow + fsspec[http] (use a scratch venv).  Usage:
  toc_sp11_exgentic_window_crosscheck.py OUT.json [--revision SHA]
"""
import argparse
import json
from collections import defaultdict

import fsspec
import pyarrow.parquet as pq

REPO = "Exgentic/agent-llm-traces-v2"
REVISION = "4b8ad4ab198438e5a170f9171c19c6a2cf7c1814"
COLUMNS = ["harness", "benchmark", "models", "status", "success", "steps", "max_tokens"]
WINDOWS = (65536, 262144)
FRACTIONS = (0.60, 0.85)


def url(i: int, rev: str) -> str:
    return f"https://huggingface.co/datasets/{REPO}/resolve/{rev}/data/train/{i:04d}.parquet"


def load(rev: str):
    rows, files = [], []
    fs = fsspec.filesystem("http")
    i = 0
    while True:
        u = url(i, rev)
        if not fs.exists(u):
            break
        with fs.open(u, "rb") as fh:
            pf = pq.ParquetFile(fh)
            assert "spans" not in COLUMNS
            t = pf.read(columns=COLUMNS)
        files.append({"file": f"data/train/{i:04d}.parquet", "rows": t.num_rows,
                      "schema_columns": pf.schema_arrow.names})
        rows.extend(t.to_pylist())
        i += 1
    return rows, files


def share_table(rows, key):
    groups = defaultdict(list)
    for r in rows:
        groups[key(r)].append(r["max_tokens"])
    out = []
    for g, vals in sorted(groups.items(), key=lambda kv: str(kv[0])):
        vals = [v for v in vals if v is not None]
        rec = {"group": g, "n": len(vals), "max_tokens_median": sorted(vals)[len(vals) // 2] if vals else None,
               "max_tokens_max": max(vals) if vals else None}
        for w in WINDOWS:
            for f in FRACTIONS:
                thr = f * w
                k = sum(1 for v in vals if v > thr)
                rec[f"share_gt_{f:.2f}x{w}"] = k / len(vals) if vals else None
                rec[f"count_gt_{f:.2f}x{w}"] = k
        out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--revision", default=REVISION)
    a = ap.parse_args()
    rows, files = load(a.revision)
    rep = {
        "dataset": REPO, "revision": a.revision, "files": files, "columns_read": COLUMNS,
        "n_rows": len(rows), "windows": WINDOWS, "fractions": FRACTIONS,
        "max_tokens_definition": "per-session max over surviving chat spans of "
        "gen_ai.usage.input_tokens + gen_ai.usage.output_tokens (build_agent_llm_traces.py "
        "_recompute_aggregates); not the request max_tokens parameter",
        "all": share_table(rows, lambda r: "ALL"),
        "by_benchmark": share_table(rows, lambda r: r["benchmark"]),
        "by_harness": share_table(rows, lambda r: r["harness"]),
        "by_benchmark_harness": share_table(rows, lambda r: f"{r['benchmark']} / {r['harness']}"),
        "by_success": share_table(rows, lambda r: f"success={r['success']}"),
        "null_max_tokens": sum(1 for r in rows if r["max_tokens"] is None),
    }
    with open(a.out, "w") as fh:
        json.dump(rep, fh, indent=1, sort_keys=True, default=str)
    print(json.dumps({k: rep[k] for k in ("n_rows", "null_max_tokens")}), len(files), "files")


if __name__ == "__main__":
    main()
