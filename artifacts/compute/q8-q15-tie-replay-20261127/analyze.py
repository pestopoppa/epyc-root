#!/usr/bin/env python3
"""Validate the replay bytes and reduce the paired, interleaved head timing."""
import argparse
import csv
import hashlib
import json
import os
import statistics
from pathlib import Path


THREADS = (1, 8, 24)
ARMS = ("fp32", "q8", "q15", "native_q8")


def read_rows(path, delimiter=","):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream, delimiter=delimiter))


def digest(path):
    if not path.is_file():
        return None
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def summarize_decisions(rows, fixtures):
    by = {(r["fixture"], int(r["threads"]), r["arm"]): r for r in rows}
    assert len(by) == len(rows) == 88 * len(THREADS) * len(ARMS) + 72
    summary = {}
    for threads in THREADS:
        split_summary = {}
        for split in ("calibration", "heldout", "stress"):
            by_split = [f for f in fixtures if f["kind"] == split]
            assert len(by_split) == {"calibration": 24, "heldout": 48, "stress": 16}[split]
            metrics = {"n": len(by_split), "new_mismatch_ids": [], "restored_ids": []}
            for arm in ARMS:
                selected = [by[(f["id"], threads, arm)] for f in by_split]
                metrics[arm] = {
                    "mismatch_ids": [r["fixture"] for r in selected if r["greedy_id"] != r["fp32_id"]],
                    "max_logit_error": max(float(r["max_abs_error"]) for r in selected),
                    "median_logit_rmse": statistics.median(float(r["rmse"]) for r in selected),
                    "minimum_gap": min(float(r["gap"]) for r in selected),
                }

            q8_wrong = set(metrics["native_q8"]["mismatch_ids"])
            q15_wrong = set(metrics["q15"]["mismatch_ids"])
            metrics["new_mismatch_ids"] = sorted(q15_wrong - q8_wrong)
            metrics["restored_ids"] = sorted(q8_wrong - q15_wrong)
            if split != "stress":
                metrics["native_replay_vs_captured_ids"] = [
                    f["id"] for f in by_split
                    if by[(f["id"], threads, "native_q8")]["greedy_id"] != by[(f["id"], 8, "captured")]["greedy_id"]
                ]
            if split == "stress":
                valid = []
                for f in by_split:
                    ref = by[(f["id"], threads, "fp32")]
                    intended_pair = {f["stress_token_0"], f["stress_token_1"]}
                    matches_gap = abs(float(ref["stress_realized_signed_gap"]) - float(f["target_signed_gap"])) <= 0.00002
                    if intended_pair == {ref["greedy_id"], ref["second_id"]} and matches_gap:
                        valid.append(f)
                metrics["intended_pair_and_gap_ids"] = [f["id"] for f in valid]
                metrics["valid_near_ids"] = [f["id"] for f in valid if abs(float(f["target_signed_gap"])) <= 0.01]
                metrics["valid_wide_ids"] = [f["id"] for f in valid if abs(float(f["target_signed_gap"])) > 0.01]
                assert metrics["valid_near_ids"] and metrics["valid_wide_ids"], "no qualifying engineered near/wide controls"
            split_summary[split] = metrics
        summary[str(threads)] = split_summary
    fp32_and_packed_thread_changes = {
        arm: [f["id"] for f in fixtures if len({
            by[(f["id"], threads, arm)]["greedy_id"] for threads in THREADS
        }) != 1]
        for arm in ARMS
    }
    return summary, fp32_and_packed_thread_changes


def summarize_timing(timings):
    by = {(int(r["threads"]), int(r["round"]), r["arm"]): float(r["ns_per_run"]) for r in timings}
    names = ("native_q8", "q8", "q8_repeat", "q15", "q15_prepacked", "pack_q8", "pack_q15")
    rounds = range(8)
    assert len(by) == len(timings) == len(THREADS) * len(rounds) * len(names)
    assert all(value > 0 for value in by.values())
    summary = {}
    for threads in THREADS:
        arms = {arm: [by[(threads, r, arm)] for r in rounds] for arm in names}
        ratios = {
            arm: [base / can for base, can in zip(arms["q8"], arms[arm])]
            for arm in ("q8_repeat", "q15", "q15_prepacked", "native_q8")
        }
        native_ratios = [base / can for base, can in zip(arms["native_q8"], arms["q15"])]
        floor = statistics.median(abs(1.0 - x) for x in ratios["q8_repeat"])
        summary[str(threads)] = {
            "median_ns": {arm: statistics.median(values) for arm, values in arms.items()},
            "paired_throughput_vs_matched_q8": {
                arm: {"values": values, "median": statistics.median(values), "range": [min(values), max(values)]}
                for arm, values in ratios.items()
            },
            "paired_q15_throughput_vs_actual_native_q8": {
                "values": native_ratios, "median": statistics.median(native_ratios),
                "range": [min(native_ratios), max(native_ratios)],
            },
            "matched_q8_AA_median_absolute_ratio_deviation": floor,
            "pack_ns_per_input_element": {
                arm: statistics.median(arms[arm]) / 1024 for arm in ("pack_q8", "pack_q15")
            },
        }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--model", type=Path, required=True)
    args = parser.parse_args()
    out = args.output
    weight = read_rows(out / "weights.tsv", "\t")[0]
    fixtures = read_rows(out / "fixtures.tsv", "\t")
    assert len(fixtures) == 88
    width, vocab = int(weight["width"]), int(weight["vocab"])
    assert width == 1024
    assert (out / "weights.q8_0").stat().st_size == int(weight["bytes"])
    assert (out / "activations.f32").stat().st_size == 88 * width * 4
    assert (out / "captured-logits.f32").stat().st_size == 72 * vocab * 4
    for threads in THREADS:
        assert (out / f"head-t{threads}.f32").stat().st_size == 88 * len(ARMS) * vocab * 4
    checks = read_rows(out / "signed-pairs.csv")
    assert checks == [{
        "cases": "4098",
        "max_abs_q8_q15_block": "134213632",
        "full_signed_pair_exact": "2147483648",
        "dpwssd_wrap": "-2147483648",
        "dpwssds_sat": "2147483647",
    }]
    accumulator_rows = int(sum(1 for _ in read_rows(out / "block-accumulators.csv")))
    assert accumulator_rows >= 88 * 2 * 32
    decision_rows = read_rows(out / "decisions.csv")
    decisions, thread_changes = summarize_decisions(decision_rows, fixtures)
    timing = summarize_timing(read_rows(out / "timings.csv"))
    assert all(not thread_changes[a] for a in ("fp32", "q8", "q15")), "fixed-row accumulations changed with thread width"
    new_heldout_mismatches = sorted(set().union(*(
        set(x["heldout"]["new_mismatch_ids"]) for x in decisions.values()
    )))
    timing_clear = {}
    for t in THREADS:
        entry = timing[str(t)]
        med = entry["paired_throughput_vs_matched_q8"]["q15"]["median"]
        native = entry["paired_q15_throughput_vs_actual_native_q8"]["median"]
        floor = entry["matched_q8_AA_median_absolute_ratio_deviation"]
        timing_clear[str(t)] = med > 1 + floor and native >= 1
    result = {
        "schema": "epyc.q8_q15_head_replay.v1",
        "verdict": "NO_KEEP" if new_heldout_mismatches or not all(timing_clear.values()) else "KEEP_DIAGNOSTIC",
        "model": args.model.name,
        "model_sha256": digest(args.model),
        "kernel_source": "ffc1bac82eeca6f9099e1ccd9ba49703c460a115",
        "row_id": os.getenv("FILLER_ID"),
        "granted_cpu_list": os.getenv("FILLER_CPUS"),
        "physical_cpu_list": os.getenv("Q15_PHYSICAL_CPUS"),
        "fixture_counts": {"natural": 72, "heldout": 48, "stress": 16},
        "weight": weight,
        "decisions": decisions,
        "greedy_thread_changes": thread_changes,
        "new_heldout_mismatch_ids": new_heldout_mismatches,
        "top_two_oracle": {"block_records_checked": accumulator_rows, "signed_pair_extremes": checks[0]},
        "timing": timing,
        "throughput_gate_above_floor_and_native": timing_clear,
        "reference": "FP32 accumulation using identical dequantized GGUF Q8 static weights and unquantized activations",
        "evidence_dir": str(out.resolve()),
        "sha256": {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()},
    }
    tmp = out / "RESULT.tmp"
    tmp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    tmp.replace(out / "RESULT.json")


if __name__ == "__main__":
    main()
