#!/usr/bin/env python3
"""Read-only, bounded Vidya context for a complete v10 KV-quant sweep.

Reads only previously ingested ledger frames. A native sweep sidecar is never a
fallback, and a partial matrix cannot masquerade as a decision-ready comparison.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from fold import fold
from ledger import Ledger

DEFAULT_LEDGER = Path(__file__).resolve().parents[2] / ".vidya/ledger.jsonl"
PREFIX = "kvq:"
SOURCE_KIND = "kv-quant-27b-v10-measurement"
METRICS = {"gpu_decode_tps", "gpu_prefill_tps"}
ARMS = {"A_f16_kv", "B_q8_0_kv", "C_q4_0_kv"}
DEPTHS = {"d2k", "d32k"}


def context(ledger_path: Path, *, as_of: str) -> dict:
    def unavailable(reason: str, *, frontier: int | None = None,
                    run: str | None = None, claim_ids: list[str] | None = None) -> dict:
        return {"schema": "epyc.vidya.kvq_planner_context.v1",
                "status": "unavailable", "reason": reason, "as_of": as_of,
                "frontier": frontier, "state_hash": None, "run": run,
                "claim_ids": claim_ids or [],
                "text": f"Vidya v10 KV-quant: unavailable ({reason})."}

    if not ledger_path.is_file():
        return unavailable("no ingested ledger")
    ledger = Ledger(ledger_path)
    errors = ledger.verify()
    if errors:
        return unavailable("ledger integrity failed")
    frames = [record.frame for record in ledger.read_all()]
    result = fold(frames, as_of=as_of)
    cutoff = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    sources: dict[str, tuple[str, str]] = {}
    claims: dict[str, tuple[str, str]] = {}
    for frame in frames:
        created = (frame.get("pubinfo") or {}).get("created_at")
        if created and datetime.fromisoformat(created.replace("Z", "+00:00")) > cutoff:
            continue
        assertion = frame.get("assertion") or {}
        typ = frame.get("frame_type", "")
        if typ.endswith("source_observed/v1") and assertion.get("source_kind") == SOURCE_KIND:
            locator = assertion.get("locator", "")
            if not locator.startswith(PREFIX):
                continue
            key = locator.split("|", 1)[0].split(":")
            if len(key) != 5:
                continue
            _, run, arm, depth, metric = key
            if arm in ARMS and depth in DEPTHS and metric in METRICS:
                sources[assertion["source_id"]] = (run, f"{arm}:{depth}:{metric}")
        elif typ.endswith("claim_proposed/v1"):
            claims[assertion.get("source_id", "")] = (
                assertion.get("claim_id", ""), assertion.get("display_text", ""))
    runs: dict[str, dict[str, tuple[str, str]]] = defaultdict(dict)
    for source_id, (run, key) in sources.items():
        if source_id in claims:
            runs[run][key] = claims[source_id]
    expected = {f"{arm}:{depth}:{metric}" for arm in ARMS for depth in DEPTHS for metric in METRICS}
    complete = sorted((run, rows) for run, rows in runs.items() if set(rows) == expected)
    if not complete:
        return unavailable("no complete ingested 3-arm × 2-depth × 2-metric run",
                           frontier=result.frontier)
    run, rows = complete[-1]
    claim_ids = [rows[key][0] for key in sorted(rows)]
    lines = [f"Vidya v10 KV-quant: latest complete ingested run {run}; frontier {result.frontier}.",
             "Bench-only, bursty rates; no serving-rate comparison or production promotion authority.",
             "-fa on fixed; mixed K/V structurally absent; K and V separate; compare within each prefill depth."]
    for key in sorted(rows):
        claim_id, text = rows[key]
        belief = result.beliefs.get(claim_id)
        if belief is None or not belief.pro_paths or belief.retracted_support:
            return unavailable(f"latest complete run {run} has inactive evidence",
                               frontier=result.frontier, run=run,
                               claim_ids=claim_ids)
        grade = belief.pro.as_dict()
        caution = " review required" if belief.review_required else ""
        # The producer puts separate K/V buffer sizes at the end of the claim.
        # Keep that tail even when the attestation locator makes a claim long.
        excerpt = text if len(text) <= 390 else f"{text[:250]} ... {text[-130:]}"
        lines.append(f"{key} claim_id={claim_id} grade={grade}{caution}: {excerpt}")
    return {"schema": "epyc.vidya.kvq_planner_context.v1",
            "status": "available", "reason": "", "as_of": as_of,
            "frontier": result.frontier, "state_hash": result.state_hash(),
            "run": run, "claim_ids": claim_ids, "text": "\n".join(lines)}


def render(ledger_path: Path, *, as_of: str) -> str:
    return context(ledger_path, as_of=as_of)["text"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).isoformat())
    parser.add_argument("--json", action="store_true", help="Emit text and evidence manifest")
    args = parser.parse_args()
    result = context(args.ledger, as_of=args.as_of)
    print(json.dumps(result, sort_keys=True) if args.json else result["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
