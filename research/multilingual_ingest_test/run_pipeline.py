#!/usr/bin/env python3
"""Run Pipeline A / B / C over the curated samples.jsonl.

Defaults to DRY-RUN (per feedback_speed_verify_via_llama_bench and
feedback_no_concurrent_inference) — prints the curl-equivalent calls without
hitting any endpoint. Pass --execute to actually call the endpoints (each
pipeline emits a confirmation prompt unless --yes is also passed).

Pipelines (per handoffs/active/internal-kb-rag.md):
  A: snippet → ingest_long_context (thinking ON) → English summary
  B: snippet → Hy-MT2 specialist translate → ingest_long_context summary
  C: snippet → ingest_long_context translate (thinking OFF) → ingest_long_context summary
     [confound check: structural decomposition without specialist]

Output per sample-pipeline pair: data/pipeline_outputs/{pipeline}/{sample_id}.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

# Avoid importing requests if dry-run is the only path used; lazy-load.


@dataclass
class Endpoint:
    name: str
    url: str
    model: str
    thinking: bool
    timeout_s: int
    max_tokens: int


def load_config(repo_root: Path) -> dict:
    with (repo_root / "config.yaml").open() as f:
        return yaml.safe_load(f)


def endpoint_from_cfg(name: str, cfg: dict) -> Endpoint:
    e = cfg["endpoints"][name]
    return Endpoint(
        name=name,
        url=e["url"],
        model=e["model"],
        thinking=e.get("thinking", False),
        timeout_s=e.get("timeout_s", 120),
        max_tokens=e.get("max_tokens", 512),
    )


def build_request(prompt: str, ep: Endpoint) -> dict:
    """OpenAI-compatible /v1/chat/completions body."""
    body = {
        "model": ep.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": ep.max_tokens,
        "temperature": 0.0,  # reproducibility — see handoff "Sampling stochasticity"
    }
    if ep.thinking:
        body["chat_template_kwargs"] = {"enable_thinking": True}
    else:
        body["chat_template_kwargs"] = {"enable_thinking": False}
    return body


def call_endpoint(ep: Endpoint, body: dict, dry_run: bool) -> dict:
    """Call the endpoint or return a dry-run placeholder."""
    if dry_run:
        return {
            "_dry_run": True,
            "endpoint": ep.name,
            "url": ep.url,
            "body": body,
        }
    import requests  # type: ignore
    t0 = time.time()
    resp = requests.post(ep.url, json=body, timeout=ep.timeout_s)
    elapsed = time.time() - t0
    resp.raise_for_status()
    data = resp.json()
    return {
        "_dry_run": False,
        "endpoint": ep.name,
        "elapsed_s": elapsed,
        "response": data,
        "completion": data["choices"][0]["message"]["content"],
        "usage": data.get("usage"),
    }


def pipeline_a(sample: dict, cfg: dict, dry_run: bool) -> dict:
    """A: snippet → ingest_long_context → English summary."""
    ep = endpoint_from_cfg("ingest_long_context", cfg)
    prompt = cfg["prompts"]["summarize_a_and_c_step2"].format(content=sample["content"])
    body = build_request(prompt, ep)
    r = call_endpoint(ep, body, dry_run)
    return {"sample_id": sample["id"], "pipeline": "A", "steps": [r]}


def pipeline_b(sample: dict, cfg: dict, dry_run: bool) -> dict:
    """B: snippet → Hy-MT2 translate → ingest_long_context summary."""
    ep_mt = endpoint_from_cfg("hymt2_specialist", cfg)
    ep_sum = endpoint_from_cfg("ingest_long_context", cfg)
    p_mt = cfg["prompts"]["translate_b_hymt2"].format(content=sample["content"])
    r_mt = call_endpoint(ep_mt, build_request(p_mt, ep_mt), dry_run)
    if dry_run:
        translated = "<DRY_RUN_TRANSLATION>"
    else:
        translated = r_mt["completion"]
    p_sum = cfg["prompts"]["summarize_a_and_c_step2"].format(content=translated)
    r_sum = call_endpoint(ep_sum, build_request(p_sum, ep_sum), dry_run)
    return {"sample_id": sample["id"], "pipeline": "B", "steps": [r_mt, r_sum]}


def pipeline_c(sample: dict, cfg: dict, dry_run: bool) -> dict:
    """C: snippet → ingest_long_context translate (thinking OFF) → summary (thinking ON).

    Confound check — does the lift come from structural decomposition rather than
    from the Hy-MT2 specialist specifically?
    """
    ep_base = endpoint_from_cfg("ingest_long_context", cfg)
    # Step 1: translation with thinking OFF (decomposition)
    ep_translate = Endpoint(
        name=ep_base.name + "_translate",
        url=ep_base.url,
        model=ep_base.model,
        thinking=False,
        timeout_s=ep_base.timeout_s,
        max_tokens=ep_base.max_tokens,
    )
    p_translate = cfg["prompts"]["translate_c_step1"].format(content=sample["content"])
    r_t = call_endpoint(ep_translate, build_request(p_translate, ep_translate), dry_run)
    if dry_run:
        translated = "<DRY_RUN_TRANSLATION>"
    else:
        translated = r_t["completion"]
    # Step 2: summarization with thinking ON
    p_sum = cfg["prompts"]["summarize_a_and_c_step2"].format(content=translated)
    r_s = call_endpoint(ep_base, build_request(p_sum, ep_base), dry_run)
    return {"sample_id": sample["id"], "pipeline": "C", "steps": [r_t, r_s]}


PIPELINES = {"A": pipeline_a, "B": pipeline_b, "C": pipeline_c}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--samples", required=True, type=Path)
    p.add_argument("--pipelines", default="A,B,C", help="Comma-separated subset (e.g., A,C)")
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--execute", action="store_true",
                   help="Actually call endpoints (default: dry-run)")
    p.add_argument("--yes", action="store_true",
                   help="Skip interactive confirmation when --execute is set")
    p.add_argument("--reps", type=int, default=1,
                   help="Repetitions per sample-pipeline (1 for temperature=0)")
    args = p.parse_args()

    repo_root = Path(__file__).resolve().parent
    cfg = load_config(repo_root)
    pipelines = [s.strip() for s in args.pipelines.split(",") if s.strip()]
    for pn in pipelines:
        if pn not in PIPELINES:
            print(f"[run] unknown pipeline: {pn}", file=sys.stderr)
            return 2

    samples_path = args.samples if args.samples.is_absolute() else repo_root / args.samples
    if not samples_path.exists():
        print(f"[run] samples not found: {samples_path}", file=sys.stderr)
        return 2
    samples = [json.loads(ln) for ln in samples_path.read_text().splitlines() if ln.strip()]
    print(f"[run] loaded {len(samples)} samples; pipelines={pipelines}; reps={args.reps}; "
          f"mode={'EXECUTE' if args.execute else 'DRY-RUN'}")

    if args.execute and not args.yes:
        # Per feedback_speed_verify_via_llama_bench / feedback_no_concurrent_inference:
        # never auto-launch inference without explicit approval.
        print("[run] --execute set without --yes; requiring confirmation.")
        print(f"[run] About to call {len(samples) * len(pipelines) * args.reps} endpoint requests.")
        print(f"[run] Endpoints involved: {', '.join(sorted({cfg['endpoints'][n]['url'] for n in {'ingest_long_context','worker_general','hymt2_specialist'}}))}")
        try:
            ans = input("[run] proceed? [y/N] ").strip().lower()
        except EOFError:
            ans = "n"
        if ans != "y":
            print("[run] aborted by user.")
            return 1

    out_root = args.output if args.output.is_absolute() else repo_root / args.output
    out_root.mkdir(parents=True, exist_ok=True)

    n_done = 0
    for pn in pipelines:
        pn_dir = out_root / pn
        pn_dir.mkdir(exist_ok=True)
        fn = PIPELINES[pn]
        for sample in samples:
            for rep in range(args.reps):
                result = fn(sample, cfg, dry_run=not args.execute)
                result["rep"] = rep
                fname = f"{sample['id']}_rep{rep}.json"
                (pn_dir / fname).write_text(json.dumps(result, ensure_ascii=False, indent=2))
                n_done += 1

    print(f"[run] wrote {n_done} output files under {out_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
