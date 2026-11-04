#!/usr/bin/env python3
"""Aggregate-only review of the retained KPF-61 third smoke responses.

Reads the retained JSON internally but emits no prompt, response content, or token text.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED = {
    "0-cold-test.response.json": "84a66e5b0a52b4ab911201c026d5ec8dea5ed33460a06e1f41d5778207f0ede2",
    "0-reorder-test.response.json": "d51f129c8aaa37092e7169039ac167808000b08123f7314e392e22b7215950af",
}
DEFAULT_ATTEMPT = Path("/mnt/raid0/llm/tmp/kvfork/kpf61-cpu-permutation-20261104/out/attempts/e4dfd06df16f49258ee5bdf2ab52c0e8")
DEFAULT_CAPSULE = Path("/mnt/raid0/llm/worktrees/mains/h-heterogeneous-slot-fabric-residency/docs/reports/kv-cache/kpf61-third-smoke-20261104/SUMMARY.json")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--attempt-dir", type=Path, default=DEFAULT_ATTEMPT)
    ap.add_argument("--capsule", type=Path, default=DEFAULT_CAPSULE)
    args = ap.parse_args()
    capsule = json.loads(args.capsule.read_text())
    responses = {}
    actual_hashes = {}
    for name, expected in EXPECTED.items():
        path = args.attempt_dir / name
        actual = sha256(path)
        declared = capsule["native_file_hashes"][name]
        if actual != expected or declared != expected:
            raise SystemExit(f"hash binding failed for {name}")
        actual_hashes[name] = actual
        # These fields alone are retained for analysis; text and prompt fields are ignored.
        raw = json.loads(path.read_text())
        responses[name] = {
            "tokens": raw["tokens"],
            "rows": raw["completion_probabilities"],
        }

    cold = responses["0-cold-test.response.json"]
    reordered = responses["0-reorder-test.response.json"]
    a, b = cold["rows"], reordered["rows"]
    if len(a) != len(b):
        raise SystemExit("probability-row count mismatch; cannot produce paired aggregate")
    top_lengths = [[len(row["top_logprobs"]) for row in rows] for rows in (a, b)]
    if any(length != 32 for side in top_lengths for length in side):
        raise SystemExit("expected exactly 32 top_logprobs entries in every retained row")
    deltas = [abs(float(x["logprob"]) - float(y["logprob"])) for x, y in zip(a, b)]
    set_differences = sum(
        {int(z["id"]) for z in x["top_logprobs"]} != {int(z["id"]) for z in y["top_logprobs"]}
        for x, y in zip(a, b)
    )
    order_differences = sum(
        [int(z["id"]) for z in x["top_logprobs"]] != [int(z["id"]) for z in y["top_logprobs"]]
        for x, y in zip(a, b)
    )
    out = {
        "capsule": str(args.capsule),
        "attempt_dir": str(args.attempt_dir),
        "source_sha256": actual_hashes,
        "comparison": "paired JSON response aggregates; no prompt/text emitted",
        "token_counts": [len(cold["tokens"]), len(reordered["tokens"])],
        "token_id_arrays_equal": cold["tokens"] == reordered["tokens"],
        "probability_row_counts": [len(a), len(b)],
        "top_logprobs_lengths": [sorted(set(side)) for side in top_lengths],
        "top_logprobs_exactly_32_all_rows": True,
        "selected_token_ids_equal_all_rows": all(int(x["id"]) == int(y["id"]) for x, y in zip(a, b)),
        "selected_logprob_different_rows": sum(float(x["logprob"]) != float(y["logprob"]) for x, y in zip(a, b)),
        "selected_logprob_abs_delta_min": min(deltas),
        "selected_logprob_abs_delta_max": max(deltas),
        "top32_id_set_different_rows": set_differences,
        "top32_id_order_different_rows": order_differences,
        "row0_selected_token_id": int(a[0]["id"]),
        "row0_selected_logprob": [float(a[0]["logprob"]), float(b[0]["logprob"])],
        "scope": "single Qwen3.5-0.8B public-control CPU publisher smoke; not 35B or full KPF-61 gate",
        "limitations": [
            "comparison uses retained completion-probability rows, not full logits",
            "no numerical tolerance or equivalence threshold was applied",
            "aggregate mismatch does not identify cause",
        ],
    }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
