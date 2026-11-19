#!/usr/bin/env python3
"""Offline M-12k reducer; never invokes inference or changes the episodic store.

Input is a JSON object with `suite` and `records`. Suite entries have id, prompt,
answers (accepted exact strings), and seeds (nonempty integer list). Each record
has id, seed, arm (on/off), prompt, answer, latency_s, mock_mode, real_mode,
episodic_lookups_effective, backend_seed, store_sha256 and serving_config_sha256.
The two digests bind the frozen store and the whole serving configuration, not
the routed-to model (routing is the treatment). Optional prompt_tokens and
output_tokens_reported must be exact complete request-local totals or null.

Receipts must come from the producer, not be reconstructed by this reducer.
ChatRequest currently has no seed field and no effective-switch echo: this
format is a consumer contract, not a claim that the live API supplies receipts.
The switch covers pipeline routing lookups, not model-initiated REPL recalls.
Exact-match grading is suitable only for suites designed for exact answers.
Outputs are descriptive paired deltas, never a significance or promotion gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics


def _number(value, name, integer=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0
            or (integer and not isinstance(value, int))):
        raise ValueError(f"invalid {name}: {value!r}")
    return value


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("missing or invalid content digest")
    return value


def score_pairs(suite, records):
    """Require full paired coverage before emitting any arm averages."""
    expected = {}
    ids = set()
    for item in suite:
        ident = item["id"]
        if not isinstance(ident, str) or not ident or ident in ids:
            raise ValueError("empty or duplicate suite id")
        ids.add(ident)
        if not isinstance(item["prompt"], str) or not item["prompt"]:
            raise ValueError("empty prompt")
        answers, seeds = item["answers"], item["seeds"]
        if not isinstance(answers, list) or not answers or not all(isinstance(a, str) and a.strip() for a in answers):
            raise ValueError("nonempty accepted answer strings required")
        if not isinstance(seeds, list) or not seeds or len(set(seeds)) != len(seeds):
            raise ValueError("nonempty unique seeds required")
        for seed in seeds:
            _number(seed, "seed", integer=True)
            expected[ident, seed] = item
    if not expected:
        raise ValueError("empty suite")

    cells = {}
    pins = set()
    for record in records:
        key = record["id"], record["seed"]
        _number(record["seed"], "seed", integer=True)
        arm = record["arm"]
        if key not in expected or arm not in ("on", "off") or (*key, arm) in cells:
            raise ValueError("unexpected or duplicate cell")
        if record["prompt"] != expected[key]["prompt"]:
            raise ValueError("prompt mismatch")
        if record.get("mock_mode") is not False or record.get("real_mode") is not True:
            raise ValueError("real inference receipt required")
        if record.get("episodic_lookups_effective") is not (arm == "on"):
            raise ValueError("effective memory switch receipt mismatch")
        _number(record.get("backend_seed"), "backend_seed", integer=True)
        if record["backend_seed"] != key[1]:
            raise ValueError("backend seed mismatch")
        pins.add((_digest(record.get("store_sha256")),
                  _digest(record.get("serving_config_sha256"))))
        _number(record["latency_s"], "latency_s")
        if not isinstance(record["answer"], str):
            raise ValueError("answer string required")
        for name in ("prompt_tokens", "output_tokens_reported"):
            if record.get(name) is not None:
                _number(record[name], name, integer=True)
        cells[*key, arm] = record
    if len(cells) != 2 * len(expected):
        raise ValueError("incomplete paired coverage")
    if len(pins) != 1:
        raise ValueError("store or serving configuration changed")

    arms = {}
    correctness = {}
    for arm in ("on", "off"):
        rows = [cells[*key, arm] for key in expected]
        correct = [r["answer"].strip() in {a.strip() for a in expected[key]["answers"]}
                   for key, r in zip(expected, rows)]
        correctness[arm] = correct
        costs = {}
        for name in ("prompt_tokens", "output_tokens_reported"):
            values = [r.get(name) for r in rows]
            costs[name + "_mean"] = (statistics.mean(values)
                                      if all(v is not None for v in values) else None)
            costs[name + "_missing"] = sum(v is None for v in values)
        arms[arm] = {"n": len(rows), "correct": sum(correct),
                     "accuracy": statistics.mean(correct),
                     "latency_s_mean": statistics.mean(r["latency_s"] for r in rows),
                     **costs}
    canonical = json.dumps(suite, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {"schema": "epyc.frontdoor-memory-pairs.v1",
            "suite_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
            "store_sha256": next(iter(pins))[0],
            "serving_config_sha256": next(iter(pins))[1],
            "arms": arms,
            "on_minus_off_accuracy": arms["on"]["accuracy"] - arms["off"]["accuracy"],
            "on_minus_off_latency_s": arms["on"]["latency_s_mean"] - arms["off"]["latency_s_mean"],
            "on_only_correct": sum(a and not b for a, b in zip(correctness["on"], correctness["off"])),
            "off_only_correct": sum(b and not a for a, b in zip(correctness["on"], correctness["off"])),
            "interpretation": "descriptive only; higher accuracy and lower latency/token cost are better"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text())
        result = score_pairs(data["suite"], data["records"])
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f"refused: {error}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
