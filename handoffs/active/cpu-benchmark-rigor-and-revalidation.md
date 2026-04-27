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

### P3. Baseline policy (REVISED 2026-04-26 late evening — CPU21 affinity wins integrated)

**PRIMARY canonical** =
```
OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active \
  numactl --interleave=all --physcpubind=0-95 \
  llama-bench -t 96 -fa 1 -p 0 -n 32 -r 3
```

(cold-cache; mmap mode irrelevant per 2x2 matrix verification — both `--mmap 0` and `--mmap 1` produce equivalent results within noise when `--interleave=all` is active).

**Canonical numbers on this config (2026-04-26 evening, post-CPU21)**:
- Qwen3-Coder-30B-A3B Q4_K_M: **47.08 ± 0.15 t/s**
- Qwen3.6-35B-A3B Q8_0: **23.04 ± 0.01 t/s**
- Qwen3-Coder-REAP-246B-A35B Q4_K_M: **6.33 ± 0.00 t/s**
- (Next-80B + gemma-26B not yet re-measured at this stack but expected to gain similar +3-8%)

**OpenMP env vars are non-optional**: the CPU21 sweep showed `OMP_PROC_BIND=spread OMP_PLACES=cores` delivers +3-8% across all model classes vs default. `OMP_WAIT_POLICY=active` adds another +0.5% (and importantly avoids the catastrophic `passive` mode at −81.6%). The combined stack is additive (or near-additive). See `data/cpu_optimization/2026-04-26-cpu21/SUMMARY.md`.

**`OMP_WAIT_POLICY=passive` is a deployment trap** — produces 5.5× regression (8.04 vs 43.82 on Coder-30B) when threads sleep on barriers instead of spinning. Add a guard at session start: refuse to bench if `$OMP_WAIT_POLICY = passive`.

**Why revised**: the historic `taskset -c 0-95 -t 96 -fa 1` baseline (mmap=1 default) is sub-optimal — it relies on file-mmap first-touch placement which scatters or clusters weight pages depending on which thread first faults each page. Many "+X% optimization wins" measured against that baseline collapse to noise when re-measured against the proper config. See compounding-matrix data 2026-04-26 (`data/cpu_optimization/2026-04-26-compounding/`):

| Optimization | "Win" against historic mmap=1 | Real Δ on proper canonical |
|---|---|---|
| EP frontdoor on Qwen3.6-35B Q8_0 | +17% (14.63→17.18) | +1.6% (20.81→21.15) — noise |
| EP regression on REAP-246B | −47% | 0% (5.94→5.92) — neutral |
| CPU2 auto-mbind on Q8_0 | +6% | 0% — redundant with --interleave=all |
| CPU1 3-flag on Coder-30B | +1.8% (warmed) | +0.6% — noise |

**Secondary canonical** (production-relevant) = `taskset -c 0-95 -t 96 -fa 1 -p 0 -n 32 -r 3` (mmap=1, warmed). Required for direct comparison with current production deployment which uses mmap=1.

**Two-baseline reporting requirement**: any new claim must report deltas against BOTH the proper cold canonical AND the warmed mmap=1 reference. Mismatches between the two indicate baseline-artifact wins.

**Model-specific note (REVISED late 2026-04-26 — asymmetry resolved)**: the earlier "Next-80B and REAP-246B prefer warmed mmap=1" finding was a measurement artifact. The historical 23.25 (Next) / 6.85 (REAP) numbers required hours-to-days of warming for numa_balancing to migrate pages into model-specific access patterns. 5-run warming doesn't reach those values (Next stays at 13.5 with mmap=1+taskset; REAP stays at 3.3). The cold `--interleave=all` config reaches 89-100% of long-warmed performance immediately on every model. **PRACTICAL: use `numactl --interleave=all` as the SINGLE canonical for all models. No model-specific config needed.** The 5-13% gap on Next/REAP to long-warmed steady-state is real but unreachable in practical timeframes (5-run warming with numa_balancing=1 only nudges Next 13.5 → 14.0). Asymmetry data: `data/cpu_optimization/2026-04-26-asymmetry/SUMMARY.md`.

Any claim compared to a non-canonical baseline must be labeled "non-canonical" and cannot drive production routing decisions.

### P4. Preprocessor-path verification

For every feature branch benchmarked:
1. Confirm feature symbols are present in built objects (`nm -D`, `strings`, or targeted log markers).
2. Confirm compile-time guards (`GGML_USE_OPENMP`, etc.) do not compile out the measured path.
3. Save one explicit proof artifact in the run folder.

### P5. Replication and cache policy (UPDATED 2026-04-27 evening — sample-size requirements tightened)

Rep-count thresholds matched to claimed delta size (per measurement-methodology lesson learned in CPU22 Phase 3, where a 3-rep Next-80B result showed +6.3% but converged to neutral at 5 reps):

| Claimed delta | Minimum reps | Rationale |
|---|---|---|
| ≥10% | 3 reps | Comfortably above noise floor; 3-rep std typically <0.5% |
| 5-10% | 5 reps | Below 3-rep stability; 5 reps to constrain CI |
| 2-5% | 5 reps | Pure noise-floor zone for this hardware; 5 reps minimum |
| ≤2% | 10 reps | Sub-noise; 10 reps with explicit std reporting required |

Always report mean ± std alongside the delta. Never report a sub-2% claim from a 3-rep measurement. Any sub-5% claim must include the per-rep raw values in the artifact bundle so a reader can verify the std calculation.

Other policies:
1. Label each run as warm-cache, cold-cache, or steady-state (per P5a).
2. Keep cache policy consistent within a comparison.
3. For position-effect-sensitive measurements (warm position 1 vs 2 vs N within a sweep), randomize order across reps OR run an explicit position-confound check.

### P5a. Cold-cache vs warmed-baseline distinction (added 2026-04-26 post-L3aaN-revert)

Empirical finding from the post-revert verification: the historical "canonical NPS4 baseline" of **43.57 ± 0.10 t/s on Coder-30B Q4_K_M** was a steady-state value reached after 1.5+ days of repeated benchmarking. From a fresh boot with caches dropped, the same `taskset -c 0-95 -t 96 -fa 1` command produces **22.92 ± 0.13 t/s** — about half the historical reference. After one warm-up pass it climbs to 32.40; further warming continues to improve. The difference is page-cache placement: with `mmap 1` (default), GGUF pages are placed by first-touch on whichever node faulted them, and that initial scattering is what produces the 22-23 t/s cold figure.

**Replacement for cold-cache canonical**: `--mmap 0 + numactl --interleave=all --physcpubind=0-95 -t 96 -fa 1` reproduces 42.41 ± 0.23 t/s immediately on Coder-30B without warming dependency. This should be the canonical config for any cross-system or cross-session comparison where warming history differs.

Required labels on every measurement going forward:
- **cache state**: cold (post-`drop_caches` or post-reboot) / warmed (after N prior benches) / steady-state (after >1 hour of activity)
- **mmap mode**: `mmap 1` (file-backed, default) / `mmap 0` (anon-allocated)
- **numa hint**: `taskset` only / `numactl --interleave=all` / `--numa distribute` / EP / etc.

Any historical claim that compares a cold result against a warmed baseline (or vice versa) must be flagged "non-canonical comparison" and re-run before driving production decisions.

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

## Artifact-bundle backfill policy (added 2026-04-27 evening per peer review)

CPU20 was documented and in force from 2026-04-26 onward, but a peer review on 2026-04-27 evening identified that **closure claims for CPU21, CPU23, CPU24, and CPU25 were declared without producing the full required artifact bundle**. The seven required files per closure (per the Artifact structure section above) are:

1. `README.md` — exact commands run
2. `system-state.txt` — `numactl --hardware`, `numa_balancing`, THP setting, governor, SMT, host load summary
3. `process-pre.txt` — pre-run `pgrep -af "llama"`
4. `process-post.txt` — post-run `pgrep -af "llama"`
5. `ld_debug.log` — `LD_DEBUG=libs` smoke run
6. `results.csv` — mean/std/reps tabulated
7. `decision.md` — explicit pass/fail/partial verdict

### Backfill rule

Any track marked "closed" before this policy was enforced (CPU21, CPU23, CPU24, CPU25) MUST EITHER:
- Have its retroactive artifact bundle reconstructed from logs already in the artifact directory + a fresh system-state snapshot + a re-run smoke command for `ld_debug.log`, OR
- Be explicitly downgraded from "closed" to "needs revalidation" with a `decision.md` stating "retroactive backfill incomplete; track downgraded".

Papering over the gap (e.g., creating empty placeholder files, or fabricating a `decision.md` without supporting artifacts) is NOT acceptable.

### Tracks requiring backfill

| Track | Existing artifacts | Missing files | Backfill action |
|---|---|---|---|
| CPU21 | `data/cpu_optimization/2026-04-26-cpu21/` (16 logs + SUMMARY.md + cpu21_followup.sh) | README.md, system-state.txt, process-pre/post.txt, ld_debug.log, results.csv, decision.md | Phase 2.5 of remediation plan |
| CPU23 | `data/cpu_optimization/2026-04-27-cpu23/` (12 raw bench logs) | README.md, system-state.txt, process-pre/post.txt, ld_debug.log, results.csv, decision.md (the existing SUMMARY.md needs to be augmented per Phase 2.2) | Phase 2.5 |
| CPU24 | `data/cpu_optimization/2026-04-26-cpu24/` (3 perf-stat logs + perfrecord/ + scripts/) | README.md, system-state.txt, process-pre/post.txt, ld_debug.log, results.csv, decision.md (the existing perfstat logs are the underlying data; need formal extraction) | Phase 2.5 |
| CPU25 | (no directory exists yet — NUMA_MIRROR runs were ad-hoc) | All seven | Phase 2.5 — create `data/cpu_optimization/2026-04-27-cpu25-numa-mirror/` and reconstruct from session log + re-run a smoke bench for `ld_debug.log` |

Backfill is tracked in the closure-inflation remediation plan (Phase 2.5).
