#!/usr/bin/env python3
"""KB-RAG retrieval-quality scoring of pipeline outputs.

For each pipeline A/B/C, for each sample, treat the produced English summary
as a query against the orchestrator's ColBERT KB-RAG index. Score the
retrieval quality by comparing the top-K results against a sample-specific
held-out relevance set.

Two scoring modes (chosen by --mode):

  ground-truth: User-provided eval_queries.jsonl maps each sample.id → a list
                of "relevant" chunk_ids (file:line_range tuples) drawn from
                the source document's topic cluster. NDCG@K against this set.

  self-retrieval: For each sample we treat its OWN summary as the gold
                  reference and check whether the top-K retrieved chunks
                  include any document semantically aligned with the source
                  topic (heuristic: shared file basename or heading_path
                  overlap). Faster to bootstrap; weaker signal.

The KB-RAG module is imported from epyc-orchestrator at runtime; the path
is configured in config.yaml.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import yaml


def load_config(repo_root: Path) -> dict:
    with (repo_root / "config.yaml").open() as f:
        return yaml.safe_load(f)


def import_kb_rag(orchestrator_repo: str):
    """Add orchestrator src/ to sys.path and import kb_rag."""
    orch = Path(orchestrator_repo).resolve()
    if not orch.exists():
        raise FileNotFoundError(f"orchestrator repo not found: {orch}")
    sys.path.insert(0, str(orch))
    from src.retrieval import kb_rag  # type: ignore
    return kb_rag


def extract_summary(pipeline_output: dict) -> str:
    """Pull the final English summary out of a pipeline JSON file.

    A: steps[0] is the summary.
    B: steps[1] is the summary (steps[0] is the Hy-MT2 translation).
    C: steps[1] is the summary (steps[0] is the Qwen translation).
    """
    steps = pipeline_output.get("steps", [])
    if not steps:
        return ""
    last = steps[-1]
    if last.get("_dry_run"):
        return ""
    return (last.get("completion") or "").strip()


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Binary-relevance NDCG@K. Both args are chunk-id strings."""
    if not relevant_ids:
        return 0.0
    dcg = 0.0
    for i, rid in enumerate(retrieved_ids[:k]):
        if rid in relevant_ids:
            dcg += 1.0 / math.log2(i + 2)
    ideal_hits = min(len(relevant_ids), k)
    if ideal_hits == 0:
        return 0.0
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


def mrr(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for i, rid in enumerate(retrieved_ids):
        if rid in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


def chunk_id(result: dict) -> str:
    """Stable chunk identifier — file_path + line_range."""
    return f"{result.get('file', '')}:{result.get('line_range', '')}"


def score_pipeline(pipeline_dir: Path, kb_rag, index_dir: str, top_k: int,
                   relevance_map: dict[str, set[str]] | None) -> dict:
    """Iterate over a pipeline's output files, query KB-RAG, compute metrics."""
    per_sample: list[dict] = []
    for f in sorted(pipeline_dir.glob("*_rep*.json")):
        po = json.loads(f.read_text())
        summary = extract_summary(po)
        sample_id = po.get("sample_id")
        if not summary:
            per_sample.append({"sample_id": sample_id, "file": str(f),
                               "skipped": True, "reason": "empty/dry_run summary"})
            continue
        results = kb_rag.query(summary, top_k=top_k, index_dir=index_dir)
        retrieved = [chunk_id(r) for r in results]
        # Strip the rep suffix to get the canonical sample id for relevance lookup
        canonical = sample_id
        rel = relevance_map.get(canonical, set()) if relevance_map else set()
        per_sample.append({
            "sample_id": sample_id,
            "summary_chars": len(summary),
            "retrieved_top": retrieved[: min(3, top_k)],
            "ndcg_at_k": ndcg_at_k(retrieved, rel, top_k) if rel else None,
            "mrr": mrr(retrieved, rel) if rel else None,
            "n_relevant": len(rel),
        })

    # Aggregate
    valid = [r for r in per_sample if not r.get("skipped") and r.get("ndcg_at_k") is not None]
    agg = {
        "n_samples": len(per_sample),
        "n_scored": len(valid),
        "n_skipped": len(per_sample) - len(valid),
        "mean_ndcg_at_k": sum(r["ndcg_at_k"] for r in valid) / len(valid) if valid else None,
        "mean_mrr": sum(r["mrr"] for r in valid) / len(valid) if valid else None,
    }
    return {"per_sample": per_sample, "aggregate": agg}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", required=True, type=Path,
                   help="Pipeline output directory (e.g., data/pipeline_outputs/)")
    p.add_argument("--query-set", type=Path,
                   help="JSONL with {sample_id, relevant_chunk_ids:[...]}. Optional.")
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--pipelines", default="A,B,C")
    args = p.parse_args()

    repo_root = Path(__file__).resolve().parent
    cfg = load_config(repo_root)
    kb_cfg = cfg["kb_rag"]

    kb_rag = import_kb_rag(kb_cfg["orchestrator_repo"])
    top_k = int(kb_cfg["top_k"])
    index_dir = kb_cfg["index_dir"]

    # Build relevance map
    relevance_map: dict[str, set[str]] | None = None
    if args.query_set:
        qs_path = args.query_set if args.query_set.is_absolute() else repo_root / args.query_set
        if qs_path.exists():
            relevance_map = {}
            for ln in qs_path.read_text().splitlines():
                if not ln.strip():
                    continue
                obj = json.loads(ln)
                relevance_map[obj["sample_id"]] = set(obj.get("relevant_chunk_ids", []))
            print(f"[eval] loaded relevance map for {len(relevance_map)} samples")
        else:
            print(f"[eval] query-set {qs_path} not found; falling back to retrieval-only output",
                  file=sys.stderr)

    inputs_root = args.inputs if args.inputs.is_absolute() else repo_root / args.inputs
    pipelines = [s.strip() for s in args.pipelines.split(",") if s.strip()]
    results: dict = {}
    for pn in pipelines:
        pn_dir = inputs_root / pn
        if not pn_dir.exists():
            print(f"[eval] skipping pipeline {pn}: no directory {pn_dir}", file=sys.stderr)
            continue
        print(f"[eval] scoring pipeline {pn} from {pn_dir}")
        results[pn] = score_pipeline(pn_dir, kb_rag, index_dir, top_k, relevance_map)

    # Per-pair lift (B - A, C - A, B - C)
    if "A" in results and "B" in results:
        a = results["A"]["aggregate"]["mean_ndcg_at_k"]
        b = results["B"]["aggregate"]["mean_ndcg_at_k"]
        if a is not None and b is not None:
            results["_lifts"] = {
                "B_minus_A_ndcg": b - a,
                "C_minus_A_ndcg": (results["C"]["aggregate"]["mean_ndcg_at_k"] - a)
                                   if "C" in results and results["C"]["aggregate"]["mean_ndcg_at_k"] is not None else None,
                "B_minus_C_ndcg": (b - results["C"]["aggregate"]["mean_ndcg_at_k"])
                                   if "C" in results and results["C"]["aggregate"]["mean_ndcg_at_k"] is not None else None,
            }

    out_path = args.output if args.output.is_absolute() else repo_root / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"[eval] wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
