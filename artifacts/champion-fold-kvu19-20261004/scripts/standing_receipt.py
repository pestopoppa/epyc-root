#!/usr/bin/env python3
"""ONE-champion standing receipt, SINGLE ARM (operator ruling 2026-10-04: "We have the production numbers
already. You just need to measure the champion.").

What it does
  1. Measures ONLY the champion build, with the EXACT protocol of the cited baseline record (below):
     1 warm-up launch, then 20 measured launches, each
        taskset -c 184-191 numactl --interleave=all <champion>/bin/llama-bench \
            -m Qwen3.8-27B-Q8_0.gguf -p 0 -n 128 -r 9 -ngl 99 -fa 1 -o json
     env LD_LIBRARY_PATH=<champion>/bin:/opt/rocm/lib (residency.loader_env), value = the tg128 row's avg_ts,
     residency sampled during every launch (residency.Sampler, >= 1 GiB VRAM or the launch is refused).
     This is bench.run_once as of research 4ede0e03 (the version that produced the record), reproduced here
     verbatim because the current run_once adds `--autokernel-harden` (13f8e63a, 2026-09-15), which changes
     what llama-bench measures (unique content/addresses + a full-device-sync hybrid pair per repetition).
  2. Takes the production baseline from the CITED RECORD, never re-measuring it:
        /mnt/raid0/llm/tmp/fold-window-20260908/fold2-result.json  (sha256 pinned below)
        g5_full.candidate_samples: 20 launches of ef81196d5 (/mnt/raid0/llm/tmp/build-fold-ef81196d5),
        FOLD-2 G5, 2026-09-08 (file mtime 11:16:25Z), median 31.301 tok/s.
     ef81196d5 is v10 (ffc1bac82) minus d0d70c5fe + ffc1bac82, which change only build_moe_ffn (never built for
     the dense 27B) and the NextN hparam read for gemma4-assistant only. Same recipe flags as the v10 store build.
  3. Writes through the loop's own writer, production.refresh(): the baseline slot passed is the v10 store build
     (it is built, so refresh measures nothing); the injected `compare` returns a bench.Comparison whose
     anchor_samples are the recorded ones. The UNPAIRED nature, the substitution and the host-drift caveat go in
     the provenance note (bundle key `anchor_guard_excursion`, the writer's only free-text slot).

Run ONLY via standing_receipt.sh. --dry-run validates everything and measures/writes nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics as st
import subprocess
import sys
import time

RESEARCH = Path("/mnt/raid0/llm/epyc-inference-research")
sys.path.insert(0, str(RESEARCH / "scripts" / "kernel_rnd"))

from autokernel.loop import bench, production, residency  # noqa: E402

RECORD = Path("/mnt/raid0/llm/tmp/fold-window-20260908/fold2-result.json")
RECORD_SHA256 = "71344d345080388fd181b6bbbe99bac4ba791e9b0e95c634e7b2c2fb48f434b0"
RECORD_ARM = "candidate_samples"          # the ef81196d5 arm of FOLD-2 G5
RECORD_COMMIT = "ef81196d5"
RECORD_BUILD = "/mnt/raid0/llm/tmp/build-fold-ef81196d5"
MODEL = Path("/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf")
PP, TG, REPS, WARMUP, LAUNCHES = 0, 128, 9, 1, 20
CPU_LIST = "184-191"
EXTERNAL_KILL_CODES = (-9, 137)
KILL_RETRIES, KILL_BACKOFF_S = 3, (5.0, 20.0, 60.0)


def load_record() -> list[float]:
    raw = RECORD.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != RECORD_SHA256:
        raise SystemExit(f"REFUSE: {RECORD} sha256 {digest} != pinned {RECORD_SHA256}")
    body = json.loads(raw)
    g5 = body["g5_full"]
    checks = {"candidate": (body.get("candidate"), RECORD_COMMIT), "surface": (g5.get("surface"), "tg128"),
              "model": (g5.get("model"), str(MODEL)), "pairs": (g5.get("pairs"), LAUNCHES),
              "resident": (g5["residency"]["resident"], g5["residency"]["invocations"])}
    bad = {k: v for k, v in checks.items() if v[0] != v[1]}
    if bad:
        raise SystemExit(f"REFUSE: cited record does not match the protocol: {bad}")
    samples = [float(x) for x in g5[RECORD_ARM]]
    if len(samples) != LAUNCHES:
        raise SystemExit(f"REFUSE: record arm has {len(samples)} samples, need {LAUNCHES}")
    return samples


def run_once_record_protocol(binary: Path) -> tuple[float, dict]:
    """bench.run_once at research 4ede0e03, verbatim argv/env/parse (no --autokernel-harden)."""
    argv = ["taskset", "-c", CPU_LIST, "numactl", "--interleave=all",
            str(binary), "-m", str(MODEL), "-p", str(PP), "-n", str(TG),
            "-r", str(REPS), "-ngl", "99", "-fa", "1", "-o", "json"]
    for attempt in range(KILL_RETRIES + 1):
        with residency.Sampler() as sampler:
            done = subprocess.run(argv, capture_output=True, text=True, timeout=3600,
                                  env=residency.loader_env(binary))
        if done.returncode in EXTERNAL_KILL_CODES and attempt < KILL_RETRIES:
            time.sleep(KILL_BACKOFF_S[min(attempt, len(KILL_BACKOFF_S) - 1)])
            continue
        break
    if done.returncode != 0:
        raise bench.BenchFailed(f"llama-bench rc={done.returncode}: {done.stderr[-400:]}")
    rows = json.loads(done.stdout)
    for row in rows:
        name = f"pp{row['n_prompt']}" if row["n_prompt"] else f"tg{row['n_gen']}"
        if name == f"tg{TG}":
            if row.get("autokernel_hardened"):
                raise bench.BenchFailed("row reports autokernel_hardened=true; protocol mismatch")
            return float(row["avg_ts"]), sampler.proof
    raise bench.BenchFailed(f"llama-bench produced no tg{TG} row")


def single_arm_compare(baseline: list[float]):
    def compare(_baseline_slot: Path, champion_build: Path):
        binary = Path(champion_build) / "bin" / "llama-bench"
        for i in range(WARMUP):
            v, _ = run_once_record_protocol(binary)
            print(f"  .. warm-up {i + 1}: {v:.3f} tok/s (discarded)", flush=True)
        samples, proofs, started = [], [], time.monotonic()
        for i in range(LAUNCHES):
            v, proof = run_once_record_protocol(binary)
            samples.append(v)
            proofs.append(proof)
            print(f"  .. launch {i + 1}/{LAUNCHES}: {v:.3f} tok/s resident={proof['resident']} "
                  f"peakVRAM={proof['peak_vram_bytes']}", flush=True)
        if not all(p["resident"] for p in proofs):
            raise bench.BenchFailed("a champion launch was not proven GPU-resident; refusing")
        return bench.Comparison(
            surface="tg128", anchor_samples=list(baseline), candidate_samples=samples,
            effect=st.median(samples) / st.median(baseline) - 1.0,
            estimator="median_over_median_UNPAIRED_champion_measured_vs_recorded_baseline",
            pairs=LAUNCHES,
            # The calibrated 0.638% floor is a PAIRED (same-session, alternating) floor. It does not apply to an
            # unpaired comparison across sessions; no floor is claimed (see the provenance note).
            noise_floor_pct=None, calibrated=False, model=str(MODEL),
            residency={"invocations": len(proofs), "resident": sum(p["resident"] for p in proofs),
                       "peak_vram_bytes": max(p["peak_vram_bytes"] for p in proofs),
                       "peak_kfd_processes": max(p["peak_kfd_processes"] for p in proofs),
                       "sclk_min_mhz": min((p.get("sclk_min_mhz") or 0) for p in proofs),
                       "sclk_max_mhz": max((p.get("sclk_max_mhz") or 0) for p in proofs),
                       "clock_stable": all(p.get("clock_stable") for p in proofs),
                       "baseline_residency": "recorded: 40/40 resident in fold2-result.json"},
            device_seconds=time.monotonic() - started,
            anchor_drift_pct=bench.drift_pct(baseline), candidate_drift_pct=bench.drift_pct(samples))
    return compare


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", type=Path, default=Path("/mnt/raid0/llm/autokernel/loop-memory"))
    ap.add_argument("--champion-build", type=Path, required=True)
    ap.add_argument("--champion-commit", required=True)
    ap.add_argument("--baseline-build", type=Path, required=True,
                    help="the v10 store build; refresh() records it as baseline.build and measures nothing")
    ap.add_argument("--note", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    baseline = load_record()
    for build in (args.champion_build, args.baseline_build):
        if not (build / "bin" / "llama-bench").is_file():
            print(f"REFUSE: no bin/llama-bench under {build}", file=sys.stderr)
            return 2
    if not MODEL.is_file():
        print(f"REFUSE: {MODEL} missing", file=sys.stderr)
        return 2
    frozen_commit, frozen_label = production.resolve_frozen()
    print(f"frozen production : {frozen_commit[:12]} ({frozen_label}); slot recorded {args.baseline_build}")
    print(f"baseline (cited)  : {RECORD} [{RECORD_ARM}] sha256 {RECORD_SHA256[:16]}..., "
          f"{RECORD_COMMIT} @ {RECORD_BUILD}, 2026-09-08, n={len(baseline)}, "
          f"median {st.median(baseline):.3f} mean {st.mean(baseline):.3f} tok/s")
    print(f"champion (measure): {args.champion_commit[:12]} @ {args.champion_build}, "
          f"{WARMUP} warm-up + {LAUNCHES} launches x (llama-bench -p 0 -n 128 -r 9 -ngl 99 -fa 1, taskset {CPU_LIST}, "
          f"numactl --interleave=all, no --autokernel-harden)")
    print(f"est. device time  : ~{(WARMUP + LAUNCHES) * 1647.4 / 40 / 60:.1f} min "
          f"(record: 1647.4 s for 40 launches = 41.2 s/launch)")
    print(f"store             : {args.store}")
    print(f"note              : {args.note}")
    if args.dry_run:
        print("DRY RUN -- record verified, wiring proven, nothing measured, nothing written.")
        return 0

    outcome = production.refresh(
        store=args.store, champion_commit=args.champion_commit, champion_build=args.champion_build,
        baseline_build=args.baseline_build, build_baseline=None,
        compare=single_arm_compare(baseline),
        on_step=lambda label: print(f"  .. {label}", flush=True), note=args.note)
    print(f"\nstanding  {outcome.reason}")
    if outcome.path:
        print(f"receipt   {outcome.path}")
    return 0 if outcome.published else 4


if __name__ == "__main__":
    raise SystemExit(main())
