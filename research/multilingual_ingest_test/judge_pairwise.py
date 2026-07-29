#!/usr/bin/env python3
"""LLM-as-judge pairwise comparison of pipeline summaries.

Per handoffs/active/internal-kb-rag.md § "Multilingual Ingest Quality-Gap":
- Judge is gemma4-26B-A4B (worker_general) — out-of-loop relative to Pipeline A
  (which uses ingest_long_context = Qwen3-Next-80B).
- Pairwise: A vs B, B vs C, A vs C — randomize presentation order to control
  position bias.
- Normalize summary lengths before judging to reduce verbosity bias.

Defaults to DRY-RUN; pass --execute to actually call the judge endpoint.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from itertools import combinations
from pathlib import Path

import yaml


def load_config(repo_root: Path) -> dict:
    with (repo_root / "config.yaml").open() as f:
        return yaml.safe_load(f)


def extract_summary(po: dict) -> str:
    steps = po.get("steps", [])
    if not steps:
        return ""
    last = steps[-1]
    if last.get("_dry_run"):
        return ""
    return (last.get("completion") or "").strip()


def load_pipeline_outputs(inputs_root: Path, pipelines: list[str]) -> dict[str, dict[str, str]]:
    """Returns {sample_id: {pipeline: summary}}."""
    bag: dict[str, dict[str, str]] = {}
    for pn in pipelines:
        pn_dir = inputs_root / pn
        if not pn_dir.exists():
            continue
        # Take rep0 only — averaging across reps is the eval script's job.
        for f in sorted(pn_dir.glob("*_rep0.json")):
            po = json.loads(f.read_text())
            sid = po.get("sample_id")
            if not sid:
                continue
            summary = extract_summary(po)
            if not summary:
                continue
            bag.setdefault(sid, {})[pn] = summary
    return bag


def load_samples(samples_path: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for ln in samples_path.read_text().splitlines():
        if not ln.strip():
            continue
        obj = json.loads(ln)
        out[obj["id"]] = obj
    return out


def normalize_length(summary: str, max_chars: int = 800) -> str:
    """Soft length cap; if longer, truncate at last sentence boundary."""
    if len(summary) <= max_chars:
        return summary
    truncated = summary[:max_chars]
    # Back off to a sentence boundary if one exists in the last 150 chars
    last_period = max(truncated.rfind(". "), truncated.rfind("。"))
    if last_period >= max_chars - 200:
        return truncated[: last_period + 1]
    return truncated


def call_judge(prompt: str, cfg: dict, dry_run: bool) -> dict:
    ep = cfg["endpoints"]["worker_general"]
    body = {
        "model": ep["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200,
        "temperature": 0.0,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if dry_run:
        return {"_dry_run": True, "endpoint": ep["url"], "body": body}
    import requests  # type: ignore
    t0 = time.time()
    resp = requests.post(ep["url"], json=body, timeout=ep["timeout_s"])
    elapsed = time.time() - t0
    resp.raise_for_status()
    data = resp.json()
    return {
        "_dry_run": False,
        "elapsed_s": elapsed,
        "completion": data["choices"][0]["message"]["content"],
    }


def parse_verdict(completion: str) -> str:
    """Extract X/Y/TIE from the judge's reply."""
    head = completion.strip().splitlines()[0].strip().upper() if completion.strip() else ""
    # Strip quotes / punctuation
    head = head.strip("\"'.,!? ")
    if head in {"X", "Y", "TIE"}:
        return head
    # Fallback: scan first 40 chars
    snippet = completion.strip()[:40].upper()
    for token in ("TIE", "X", "Y"):
        if token in snippet:
            return token
    return "UNPARSEABLE"


def judge_pair(sample: dict, pair_name: str, pa: str, pb: str, summary_a: str,
               summary_b: str, cfg: dict, dry_run: bool, rng: random.Random) -> dict:
    """Judge one (pipeline_a vs pipeline_b) pair on one sample.

    Randomizes which pipeline is shown as X vs Y. Returns the unmapped verdict
    plus the mapping for downstream win-rate computation.
    """
    swap = rng.random() < 0.5
    x_pipeline, y_pipeline = (pb, pa) if swap else (pa, pb)
    x_summary, y_summary = (summary_b, summary_a) if swap else (summary_a, summary_b)
    prompt = cfg["prompts"]["judge_pairwise"].format(
        source=sample["content"][:2000],
        summary_x=normalize_length(x_summary),
        summary_y=normalize_length(y_summary),
    )
    r = call_judge(prompt, cfg, dry_run)
    verdict_xy = parse_verdict(r.get("completion", "")) if not dry_run else "DRY"
    # Map back: if X was pb (swap), then X-wins means pb-wins
    if verdict_xy == "TIE" or verdict_xy in {"UNPARSEABLE", "DRY"}:
        verdict_actual = verdict_xy
    elif verdict_xy == "X":
        verdict_actual = x_pipeline
    else:  # Y
        verdict_actual = y_pipeline
    return {
        "sample_id": sample["id"],
        "stratum": sample.get("stratum"),
        "pair": pair_name,
        "pa": pa, "pb": pb,
        "shown_as": {"X": x_pipeline, "Y": y_pipeline},
        "judge_verdict_xy": verdict_xy,
        "verdict_actual_winner": verdict_actual,
        "raw": r,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", required=True, type=Path,
                   help="Pipeline output directory (e.g., data/pipeline_outputs/)")
    p.add_argument("--samples", required=True, type=Path,
                   help="samples.jsonl (for source text)")
    p.add_argument("--output", required=True, type=Path,
                   help="Output directory for per-pair verdict files")
    p.add_argument("--pipelines", default="A,B,C")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    repo_root = Path(__file__).resolve().parent
    cfg = load_config(repo_root)
    pipelines = [s.strip() for s in args.pipelines.split(",") if s.strip()]
    pairs = list(combinations(pipelines, 2))

    inputs_root = args.inputs if args.inputs.is_absolute() else repo_root / args.inputs
    samples_path = args.samples if args.samples.is_absolute() else repo_root / args.samples
    out_root = args.output if args.output.is_absolute() else repo_root / args.output

    summaries = load_pipeline_outputs(inputs_root, pipelines)
    samples = load_samples(samples_path)

    n_planned = sum(1 for sid in summaries if all(p in summaries[sid] for p in pipelines)) * len(pairs)
    print(f"[judge] {len(samples)} samples, {len(pairs)} pairs, "
          f"{n_planned} judgments planned; mode={'EXECUTE' if args.execute else 'DRY-RUN'}")
    if args.execute and not args.yes:
        try:
            ans = input("[judge] proceed? [y/N] ").strip().lower()
        except EOFError:
            ans = "n"
        if ans != "y":
            print("[judge] aborted.")
            return 1

    out_root.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    results: list[dict] = []
    for sid, per_pipeline in summaries.items():
        if not all(p in per_pipeline for p in pipelines):
            continue
        sample = samples.get(sid)
        if not sample:
            continue
        for (pa, pb) in pairs:
            pair_name = f"{pa}vs{pb}"
            r = judge_pair(sample, pair_name, pa, pb,
                           per_pipeline[pa], per_pipeline[pb],
                           cfg, dry_run=not args.execute, rng=rng)
            results.append(r)
            fname = f"{sid}_{pair_name}.json"
            (out_root / fname).write_text(json.dumps(r, ensure_ascii=False, indent=2))

    summary_path = out_root / "_summary.json"
    summary_path.write_text(json.dumps({"n": len(results), "results": results},
                                       ensure_ascii=False, indent=2))
    print(f"[judge] wrote {len(results)} judgments to {out_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
