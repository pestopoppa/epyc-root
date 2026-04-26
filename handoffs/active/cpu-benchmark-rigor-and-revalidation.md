# CPU20 — Benchmark Rigor And Revalidation Gate

**Status**: ACTIVE (created 2026-04-26)
**Priority**: CRITICAL
**Categories**: hardware_optimization, inference_serving, benchmarking_methodology
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) (CPU20)
**Related**: [`cpu-optimization-thesis-pause-2026-04-26.md`](cpu-optimization-thesis-pause-2026-04-26.md), [`cpu-kernel-env-flags-inventory.md`](cpu-kernel-env-flags-inventory.md), [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md)

## Objective

Convert benchmarking from ad-hoc session behavior into a hard quality gate so optimization claims are reproducible, comparable, and safe for deployment decisions.

This handoff exists because prior sessions showed material conclusion drift from:
- baseline mismatch (`--numa distribute` used as baseline in some EP comparisons)
- stale/background `llama-*` processes contaminating runs
- wrong `LD_LIBRARY_PATH` causing v4 libs to be loaded instead of the experimental build
- code measured while preprocessor-guarded out of the active build

## Scope

Applies to all CPU tracks (CPU1-CPU24). No track is allowed to claim "win", "exhausted", or "deployable" without satisfying this gate.

## Canonical Protocol (must-pass)

### P0. Binary and environment identity

1. Print and capture:
   - `git -C /mnt/raid0/llm/llama.cpp-experimental rev-parse --short HEAD`
   - `readelf -d /mnt/raid0/llm/llama.cpp-experimental/build/bin/llama-bench | rg RUNPATH`
   - `echo "$LD_LIBRARY_PATH"`
2. Enforce canonical library order:
   - `/mnt/raid0/llm/llama.cpp-experimental/build/bin` first
3. Verify loaded libraries for one smoke run:
   - `LD_DEBUG=libs .../llama-bench ... 2>&1 | tee <run>/ld_debug.log`

### P1. Process hygiene

1. Before every benchmark batch:
   - `pgrep -af "llama"`
2. If any benchmark-related process remains, terminate and re-check.
3. Store pre-run and post-run process snapshots in artifacts.

### P2. System-state snapshot

Capture before each batch:
- `numactl --hardware`
- `cat /proc/sys/kernel/numa_balancing`
- `cat /sys/kernel/mm/transparent_hugepage/enabled`
- governor, SMT, and thread placement metadata
- host load summary (`uptime`, top-level CPU/memory)

### P3. Baseline policy

Canonical baseline for per-model comparisons:
- `taskset -c 0-95 -t 96 -fa 1 -p 0 -n 32 -r 2`
- no `--numa` flag unless explicitly testing that flag
- no optimization env vars unless explicitly testing that flag

Any claim compared to a non-canonical baseline must be labeled "non-canonical" and cannot drive production routing decisions.

### P4. Preprocessor-path verification

For every feature branch benchmarked:
1. Confirm feature symbols are present in built objects (`nm -D`, `strings`, or targeted log markers).
2. Confirm compile-time guards (`GGML_USE_OPENMP`, etc.) do not compile out the measured path.
3. Save one explicit proof artifact in the run folder.

### P5. Replication and cache policy

1. Run at least 3 reps for any claim stronger than ±2%.
2. Label each run as warm-cache or cold-cache.
3. Keep cache policy consistent within a comparison.

## Required Revalidation Set (first deliverable)

Re-run under this protocol:
1. EP frontdoor claim (Qwen3.6-35B Q8_0) at honest canonical baseline
2. EP >150B regression claim (REAP-246B, MiniMax-M2.7)
3. CPU1 3-flag stack (without `GGML_NUMA_WEIGHTS`) stability claim
4. CPU2 `GGML_NUMA_REPACK_INTERLEAVE` on/off effect

## Gate rules

A track may be marked "closed" only if:
1. It has protocol-compliant artifacts.
2. It has model-appropriate canonical baselines.
3. Any contradictory historical result is either reproduced or explicitly invalidated by protocol evidence.

If not, track status must be "needs revalidation", not "exhausted".

## Artifact structure

Store all outputs under:
- `data/cpu_optimization/<YYYY-MM-DD>-<track>-revalidation/`

Required files:
- `README.md` (exact commands)
- `system-state.txt`
- `process-pre.txt`, `process-post.txt`
- `ld_debug.log`
- `results.csv` (mean/std/reps)
- `decision.md` (pass/fail and why)

## Integration with other tracks

- **CPU21 / CPU24** cannot start closure analysis without CPU20 pass artifacts.
- **CPU22 / CPU23** must inherit CPU20 baseline protocol verbatim.
- **Phase H / I / J / K / L / M** (v5 shipping chain) is blocked until CPU20 revalidation set is complete.

## Success criteria

1. No further benchmark claim is later invalidated by environment/process/build-path mistakes.
2. All active CPU tracks explicitly reference protocol-compliant artifact bundles.
3. Production decisions cite canonical comparisons only.
