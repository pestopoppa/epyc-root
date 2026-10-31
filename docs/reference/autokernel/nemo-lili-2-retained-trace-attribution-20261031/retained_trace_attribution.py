#!/usr/bin/env python3
"""Verify stage attribution from the retained NEMO-LILI-2 rocprof kernel trace.

Uses exact repeated kernel sequences, not the 50 us idle-gap heuristic. The
first target graph in each request is prefill; the final S graph is partial.
"""
import csv
import hashlib
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV = ROOT / "smoke-normal/native/trace/prof_kernel_trace.csv"
RUN = ROOT / "smoke-normal/native/run.json"
OUT = ROOT / "smoke-normal/retained-trace-attribution.json"
# Ordered full kernel-name sequences in the retained, pinned source trace.
# These bind every dispatch, including non-SSM kernels, within each stage.
EXPECTED_SEQUENCE_SHA256 = {
    "target": "df701ccfc851d8590652cf44ac524601974358810185235ce94e3b182accbec6",
    "drafter": "c5e53967ff8dc7c46c4a7b854a7f55059c32fa9ef9b3f78d1f125bca459928de",
    "plain": "999ce0d299ff3f4cda16c87b6a81529d767203706f2f19f2a2628c8bd447a7e7",
}


def all_rows():
    result = []
    with CSV.open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row["Kind"] != "KERNEL_DISPATCH" or row["Kernel_Name"].startswith("__amd_rocclr"):
                continue
            result.append((int(row["Start_Timestamp"]), int(row["End_Timestamp"]), row["Kernel_Name"]))
    return sorted(result)


def bursts(rows):
    groups, current, end = [], [], None
    for row in rows:
        if end is not None and row[0] - end > 2_000_000_000:
            groups.append(current)
            current = []
        current.append(row)
        end = max(end or 0, row[1])
    if current:
        groups.append(current)
    return groups


def busy_ms(rows):
    return sum(end - start for start, end, _ in rows) / 1e6


def sequence_sha256(rows):
    return hashlib.sha256("\n".join(name for _, _, name in rows).encode()).hexdigest()


def summary(values):
    return {"n": len(values), "mean_ms": round(statistics.mean(values), 4),
            "median_ms": round(statistics.median(values), 4),
            "min_ms": round(min(values), 4), "max_ms": round(max(values), 4)}


def main():
    run = json.loads(RUN.read_text())
    assert run["status"] == "complete"
    assert run["teardown"]["verified_dead"]
    assert run["vram"]["nonzero_samples"] >= 5
    assert [m["label"] for m in run["marks"]] == ["warm", "S", "P"]
    S, P = bursts(all_rows())[-2:]
    scans = lambda rows: [i for i, row in enumerate(rows) if "ssm_scan_f32_group" in row[2]]
    ss, ps = scans(S), scans(P)
    assert len(ss) == 39 * 40 and len(ps) == 160 * 40
    target, drafter, plain = [], [], []
    for q in range(1, 37):
        start = ss[q * 40] - 15
        last_scan = ss[q * 40 + 39]
        end = next(i for i in range(last_scan + 1, len(S))
                   if "convert_unary<float, __hip_bfloat16>" in S[i][2])
        next_start = ss[(q + 1) * 40] - 15
        assert "k_get_rows_float" in S[start][2]
        assert "convert_unary<float, __hip_bfloat16>" in S[end][2]
        assert end - start == 2475 and next_start - end == 579
        assert sum("ssm_scan_f32_group" in row[2] for row in S[start:end]) == 40
        assert not any("ssm_scan_f32_group" in row[2] for row in S[end:next_start])
        assert sequence_sha256(S[start:end]) == EXPECTED_SEQUENCE_SHA256["target"]
        assert sequence_sha256(S[end:next_start]) == EXPECTED_SEQUENCE_SHA256["drafter"]
        target.append(busy_ms(S[start:end]))
        drafter.append(busy_ms(S[end:next_start]))
    for q in range(2, 159):
        start, end = ps[q * 40] - 8, ps[(q + 1) * 40] - 8
        assert "k_get_rows_float" in P[start][2]
        assert end - start == 1873
        assert sum("ssm_scan_f32_group" in row[2] for row in P[start:end]) == 40
        assert sequence_sha256(P[start:end]) == EXPECTED_SEQUENCE_SHA256["plain"]
        plain.append(busy_ms(P[start:end]))
    # The 37th target is full, but the following final partial target starts
    # three dispatches earlier. Keep that edge out of the paired round sample.
    edge_start = ss[37 * 40] - 15
    edge_last_scan = ss[37 * 40 + 39]
    edge_draft_start = next(i for i in range(edge_last_scan + 1, len(S))
                            if "convert_unary<float, __hip_bfloat16>" in S[i][2])
    assert edge_draft_start - edge_start == 2475
    assert sequence_sha256(S[edge_start:edge_draft_start]) == EXPECTED_SEQUENCE_SHA256["target"]
    assert ss[38 * 40] - 15 - edge_draft_start == 576
    rounds = [t + d for t, d in zip(target, drafter)]
    result = {
        "status": "COMPLETE",
        "source_csv": str(CSV),
        "source_csv_sha256": hashlib.sha256(CSV.read_bytes()).hexdigest(),
        "source_run_sha256": hashlib.sha256(RUN.read_bytes()).hexdigest(),
        "ordered_stage_sequence_sha256": EXPECTED_SEQUENCE_SHA256,
        "method": "40 target-only SSM scan dispatches per graph; exact repeated 2475-target/579-drafter/1873-plain dispatch fingerprints. GPU busy is the sum of individual kernel End-Start durations and can differ from elapsed span due to idle and overlap.",
        "scope": "36 identical interior speculative target+drafter pairs; 157 complete steady plain steps. S has 39 target graph groups: 1 prefill, 37 full verifications, 1 final partial verification. The 37th full verification has a 576-dispatch following interval (3 fewer than the 579 identical interior drafter intervals) and is excluded from paired means. P has 160 groups: 1 prefill, 1 first-edge plain decode, 157 identical interior plain steps, 1 final edge.",
        "target_verify_gpu_busy": summary(target),
        "drafter_gpu_busy": summary(drafter),
        "spec_round_gpu_busy": summary(rounds),
        "plain_token_gpu_busy": summary(plain),
        "round_vs_plain_busy_ratio": round(statistics.mean(rounds) / statistics.mean(plain), 4),
        "target_share_of_round_pct": round(100 * statistics.mean(target) / statistics.mean(rounds), 2),
        "draft_acceptance": {"accepted": run["marks"][1]["draft_n_accepted"], "generated": run["marks"][1]["draft_n"]},
        "wall_note": "P has long host/profiler idle; its 163.36 ms/token wall rate is not GPU busy and is excluded from the busy ratio.",
        "prior_analysis_verdict": "INVALID: 50us segmentation claimed 2454 plain segments for 160 tokens and one target segment for 38 rounds",
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"result": str(OUT), "target_ms": result["target_verify_gpu_busy"]["mean_ms"],
                      "drafter_ms": result["drafter_gpu_busy"]["mean_ms"],
                      "plain_ms": result["plain_token_gpu_busy"]["mean_ms"],
                      "ratio": result["round_vs_plain_busy_ratio"]}))


def checked():
    try:
        main()
    except (AssertionError, StopIteration, KeyError, IndexError, ValueError, TypeError, OSError) as exc:
        # Missing or changed graph signatures invalidate attribution. Refuse
        # to manufacture a stage split or ratio from a malformed trace.
        OUT.write_text(json.dumps({"status": "INCOMPLETE", "reason": type(exc).__name__ + ": " + str(exc)}, indent=2) + "\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(checked())
