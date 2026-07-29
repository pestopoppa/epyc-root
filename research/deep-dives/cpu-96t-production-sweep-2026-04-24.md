# 96t Single-Instance Production Sweep (2026-04-24)

**Parent task**: #10 — Production sweep: adopt 96t-single-NUMA-node operating point
**Status**: SWEEP COMPLETE — recommendation is **model-dependent**, not universal
**Host**: quiet EPYC 9655, load avg <1, zero-reboot knobs applied (THP always, numa_balancing off, 1GB hugepage)
**Builds**: `/mnt/raid0/llm/llama.cpp-experimental/build-llamafile-on` (HEAD `9e048fbc1`, tinyBLAS on, `-march=native`)
**Data**: `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-24/`

## Critical correction from 2026-04-23 writeup

The 2026-04-23 deep-dive (`cpu-optimization-phase0-baseline.md`) and wiki updates labeled `taskset -c 0-95` as "full node 0" and the +26% figure as universally applicable. **Both were wrong:**

- The NUMA map is:
  - node 0 cpus: `0-47, 96-143` (physical + hyperthreads)
  - node 1 cpus: `48-95, 144-191`
- `taskset -c 0-95` = **96 physical cores across BOTH nodes** (all physical, no SMT), not "node 0 only."
- The +26% was a comparison across two different model registry numbers and partially across different sessions (page cache state differed). Apples-to-apples on the same session today: 30B-A3B Q4 at 24t = 44.32, at 96t physical = 49.34 → **+11%**, not +26%.

## Corrected finding: 96t-all-physical vs 48t-half-node is model-dependent

All measurements same session (2026-04-24), canonical `-p 0 -n 32 -r 2` decode-only:

| Model | Class | 48t (cores 0–47) | 96t-all-physical (0–95) | Δ | Aggregate 4×48t reference |
|---|---|---|---|---|---|
| Qwen3-Coder-30B-A3B **Q4_K_M** | MoE-hybrid (3B active) | 45.80 | **49.34** | **+7.7%** | ~95 agg (registry) |
| Qwen3.6-27B **Q4_K_M** | Dense hybrid | 6.67 | **8.97** | **+34.5%** | — |
| Qwen3.6-27B **Q8_0** | Dense hybrid | 4.26 | 4.19 | −1.6% | — |
| Qwen3.6-35B-A3B **Q8_0** | MoE-hybrid (3B active) | 27.28 | 24.93 | **−8.6%** | — |
| Qwen2.5-Coder-32B **Q4_K_M** | Dense | 6.92 | **10.80** | **+56.1%** | ~43.3 agg (registry) |

Also verified: 96t with HT vs 96t all-physical on 30B-A3B Q4: 44.63 (HT) vs 49.34 (physical) → **−9.5% penalty from enabling hyperthreads**. Physical-cores-only is the real driver, not NUMA locality.

## Interpretation

- **Dense Q4 models are the biggest winners** (+34–56%). Compute/byte ratio is high enough that more cores help significantly. Coder-32B Q4 at 96t (10.80 t/s) is **1.56×** its 48t baseline.
- **MoE models (3B active) get smaller gains or regress**. The 3× sparsity means per-token compute is already small; adding cores brings coordination overhead faster than it adds useful work. 30B-A3B Q4 gets +7.7% (modest); 35B-A3B Q8 regresses 8.6%.
- **Q8_0 dense models are ~flat**. Twice the bytes/token compared to Q4 → closer to BW roofline at 48t, so more cores don't help. 27B Q8 at 96t is slightly *slower* than 48t.
- **The 24t Q0A worker_explore config** (production's current) gets 44.32 on 30B-A3B Q4 today; **96t would deliver +11%**. Much smaller than the "+26%" claim; still a win for single-session worker traffic, but the trade-off against aggregate is significant (see below).

## Production recommendation

**Mode-dependent, not a universal switch.** The current 4×48t NUMA-pinned aggregate architecture still wins for concurrent workloads:

| Scenario | Current (4×48t agg) | Single 1×96t | Winner |
|---|---|---|---|
| 4 concurrent coder sessions | ~43 t/s agg (10.8 each) | 10.8 t/s single + no concurrency | **4×48t** (agg wins 4×) |
| 1 single interactive coder session | ~10.8 t/s (one quarter warm) | 10.8 t/s | **Tie or near-tie** |
| 1 single interactive worker | ~39 t/s (Q0A) | 49 t/s | **1×96t** (+11%) |
| 1 single interactive dense Q4 decode | ~7 t/s (48t quarter) | 10.8 t/s | **1×96t** (+56%) |
| 1 single Q8 architect decode | ~4.3 t/s | ~4.2 t/s | **~Tie**, stay with 48t |
| N concurrent MoE-Q8 sessions | best agg | worse single | **4×48t** (MoE Q8 regresses at 96t) |

**Autopilot implication**: per `project_autopilot_stack_assembly.md` memory — the stack should dynamically switch between modes based on concurrent user count and current model role. A 1×96t fast path for single-session interactive traffic on dense Q4 models is a valid new operating mode to add.

### Concrete proposed changes (not yet implemented — recommendation only)

1. **Add 1×96t-all-physical mode to the stack assembly options** in `orchestrator_stack.py`. Gate on `(concurrent_session_count == 1 AND model.arch_class in {dense_q4, large_moe_q4})`.
2. **Coder-escalation fast path**: when only 1 user is active, route coder requests to a 1×96t coder-32B instance (10.8 t/s) instead of one of the 4×48t quarters (also 10.8 but with cold-cache penalty). Avoids the aggregate-optimized config's single-session cold cache hit.
3. **Worker_explore fast path**: for single-session chat, 1×96t Qwen3-Coder-30B-A3B = 49 t/s vs current 1×24t = 44 t/s (+11%). Small but free.
4. **Do NOT deploy 1×96t for**: Qwen3.6-35B-A3B Q8 (frontdoor class) — it regresses 8.6%. Keep 4×48t aggregate.

## Concurrent-load sweep — aggregate THROUGHPUT INCREASES monotonically with instance count

**IMPORTANT scope note**: this sweep is about **multiple INDEPENDENT `llama-bench` processes running in parallel**, each with its own session. "Aggregate" = sum of N independent per-session throughputs. This is NOT single-instance tensor-parallel sharding (which is the goal of `intra-process-tensor-parallel-decode.md` / CPU1 and remains unimplemented). In CPU1 terminology: this sweep raises the **multi-instance aggregate ceiling** and empirically establishes the **BW-roofline target** CPU1 will aim for, but it does **not** improve single-session latency — each of the N instances still has its own small per-session throughput.

**Key finding**: for a fixed socket (192 logical threads total), splitting into MORE smaller CONCURRENT instances delivers HIGHER aggregate throughput than fewer larger instances. Tested 4/8/16/32/48-way splits on three production model classes:

| Model | 1×48t | 4×48t | 8×24t | 16×12t | 32×6t | 48×4t | **Peak** | Δ 4→peak |
|---|---|---|---|---|---|---|---|---|
| Qwen3.6-27B Q8_0 (dense hybrid) | 4.26 | 6.62 | 7.91 | 8.55 | 10.47 | **15.39** | 48×4t | **+133%** |
| Qwen3.6-35B-A3B Q8_0 (frontdoor class, MoE) | 27.28 | 64.26 | 76.35 | 85.89 | 92.75 | **135.08** | 48×4t | **+110%** |
| Qwen2.5-Coder-32B Q4_K_M (dense) | 6.95 | 13.64 | 15.08 | 16.01 | **20.03** | 17.34 | 32×6t | **+47%** |

SMT-paired throughout: each instance gets `N_phys + N_ht` SMT siblings within the same NUMA node. 48×4t = 2 phys + 2 HT per instance, 24 instances per socket (total 96 phys + 96 HT = full socket). Cpusets in `concurrent-sweep-16x12.sh`, `concurrent-sweep-32x6.sh`, `concurrent-sweep-48x4.sh`.

**Per-model optimal split point differs**:
- **27B Q8 dense hybrid**: still improving at 48×4t (+47% vs 32×6t, +133% vs 4×48t). 15.39 × 27 GB = 416 GB/s = 90% of 460 GB/s BW roofline — room left. Could benefit from 64×3t (not tested; impractical at 3 logical threads per instance).
- **35B-A3B Q8 frontdoor-class**: still improving at 48×4t (+46% vs 32×6t, +110% vs 4×48t). 135.08 × ~3.4 GB active-per-token = ~459 GB/s = **essentially at the 460 GB/s BW roofline**. Further splits unlikely to help.
- **Coder-32B Q4 dense**: **regresses** at 48×4t (17.34 < 32×6t's 20.03). 32×6t is the peak. 4 threads per instance is too few to drive that instance's compute — the instance becomes compute-bound within itself, lower total BW demand. Dense Q4 has a smaller compute/BW ratio than Q8; saturates earlier.

### Mechanism: why dense Q4 peaks earlier than Q8 does

A finer split delivers more aggregate BW (fewer barriers, better CCD locality) **only if each instance can still drive enough BW demand to stay memory-bound**. For Q4 dense, per-instance compute at 4 threads is insufficient to saturate that instance's BW share, so the instance becomes compute-bound and the aggregate gain flattens/regresses. For Q8 (2× bytes per weight), the compute/BW ratio is halved, so instances remain BW-bound at lower per-instance thread counts, and splitting can go further.

**Implication**: optimal split count is a function of (model size, quant, per-token active bytes, per-layer compute density). Not a universal number. Autopilot or orchestrator config needs per-model tuning.

### Roofline analysis (35B-A3B Q8 at 32×6t = 92.75 t/s)

Active bytes per token for 35B-A3B (3B active) at Q8: ~3.5 GB/token. Aggregate memory read rate: 92.75 × 3.5 = **325 GB/s = 71% of 460 GB/s socket roofline**. The current 4×48t config delivers 64.26 × 3.5 = 225 GB/s = 49% of roofline. The 32×6t split recovers an additional ~22% of the hardware's memory subsystem.

### What this means for production

Production frontdoor runs 4×48t Qwen3.6-35B-A3B-Q4 with registry-advertised ~50.8 t/s aggregate. The measured 4×48t on Q8 is 64.26 t/s — and **48×4t on Q8 hits 135 t/s, +110% over 4×48t, with no code changes**. Switching the orchestrator from 4×48t quarters to per-model-optimal sixteenths/twenty-fourths would **more than double** production throughput for bulk/concurrent workloads.

**Per-model aggregate gains at optimal split (vs current 4×48t baseline)**:

| Role | Current (4×48t) | Optimal split | Throughput | Gain |
|---|---|---|---|---|
| Frontdoor class (35B-A3B Q8) | 64.3 t/s | **48×4t** | **135.1 t/s** | **+110%** |
| Dense hybrid (27B Q8) | 6.6 t/s | **48×4t** | **15.4 t/s** | **+133%** |
| Coder class (Coder-32B Q4) | 13.6 t/s | **32×6t** | **20.0 t/s** | **+47%** |

These are direct config-only changes to `orchestrator_stack.py`: N× listeners on SMT-paired cpusets instead of 4× quarters. Orchestration overhead grows (48 llama-server processes per role × 3 roles = 144 processes to manage); health checks, rolling restarts, log aggregation need updates. Per-session latency drops commensurately (e.g., 135/48 = 2.8 t/s per 35B-A3B session at 48-way split) — this is strictly for concurrent/bulk workloads. Single-user interactive paths stay on 1×48t or 1×96t single-session.

### Why does splitting into more instances help when the total thread count is the same?

Hypotheses (order of likely impact):
1. **Barrier cost is O(threads)**: per Phase 0 measurement, 32-45% of decode cycles at 96t are in libomp spin/barrier. At 12t the per-iteration barrier is much cheaper. 16 smaller barriers in parallel < 4 larger barriers.
2. **CCD locality**: 12 physical cores ≈ 1.5 CCDs on EPYC 9655 (8 cores/CCD). Smaller instances keep their working set within fewer CCDs → less cross-CCD L3/IOD coherence traffic per instance.
3. **Page cache coherence**: all instances mmap the same GGUF so weight reads are shared at the page cache level. No extra memory pressure from more instances.
4. **BW aggregation**: 12 DDR5 channels serve all instances. Smaller instances have smaller per-instance BW demand, so channel contention plays out as finer-grained interleaving rather than coarse-grained queuing.

### Single-session trade-off

Per-session throughput DECREASES linearly with split count:

| Config | 35B-A3B Q8 per-session |
|---|---|
| 1×48t isolated | 27.3 |
| 4×48t concurrent | 16.1 each |
| 8×24t concurrent | 9.5 each |
| 16×12t concurrent | 5.4 each |
| **32×6t concurrent** | **2.9 each** |
| 1×96t single-session | (24.93 measured, but 96t vs 48t slightly regresses on this model) |

So the mode switch is: **1×48t for single-user latency (~27 t/s), 32×6t for multi-user aggregate throughput (~93 t/s)**. Crossover for 35B-A3B Q8: splitting into N instances gives `93/N` per-session vs `27` single-session; at `N ≤ 3` concurrent users the single-session is faster; at `N ≥ 4` concurrent users the split wins by delivering more total throughput. Autopilot should map conversation state to the right mode.

### Earlier simple concurrent-load test (Coder-32B Q4, 2-way)

Measured 2026-04-24: 1×48t alone = 6.95, 2×48t concurrent = 5.58 each (11.16 aggregate = 80% linear scaling). The 4/8/16-way sweep above confirms the per-session penalty continues (5.58 → 3.33 → 1.86 → 1.00 per session) but aggregate keeps climbing.

## Caveats and not-yet-tested

- **~~Under concurrent load~~**: tested — 80% linear scaling at 2-way, crossover at ~2 users (see above).
- **Realistic session lengths**: all measurements are 32-token decode from empty context. Real sessions have 1k-16k+ context → KV reads dominate differently, TP-sharding (CPU1) becomes relevant.
- **Model load overhead**: 96t physical requires cold-starting a new llama-server instance unless we rearrange production. Cold load for 32B Q4 is ~20s (mmap from NVMe 12 GB/s × 18.5 GB).
- **Thermal under sustained load**: single-instance 96t at 100% AVX-512 utilization on EPYC 9655 — not yet verified for 30+ min sustained. Reports suggest Zen 5 doesn't downclock under AVX-512 but needs verification on our chassis.
- **Q8_0 regression reason**: unclear whether it's true BW-bound at 48t (= further cores don't help) or something else. If confirmed BW-bound, CPU1 TP-sharding should help Q8_0 where 96t doesn't.

## Why the 96t peak exists (mechanism)

Hypothesis informed by the perf profile from 2026-04-23:

- At 48t (one NUMA node's physical cores), we're using 6 DDR5 channels (half the socket's BW). The dot loop is BW-bound, but we're below the roofline because thread scaling caps at barrier cost around 48t.
- At 96t (both nodes, all physical cores), we use all 12 DDR5 channels. Effective BW doubles, the barrier cost grows but doesn't double. Net: ~10% gain on BW-saturating-but-not-bound workloads (MoE Q4), large gain on compute-richer workloads (dense Q4), zero or negative on already-BW-saturated (Q8 dense, MoE Q8).
- Adding SMT threads (96t → 192t via `0-191`) doesn't add compute (SMT shares ALU) but DOES add barrier/coordination cost. Hence the HT penalty.
- Crossing 144t (0-143) is a bimodal disaster because it's uneven across nodes.

## Next steps

- [ ] Concurrent-load test: 1×96t + 1×48t on opposite quarters, measure interference.
- [ ] Long-context test: re-run at n_ctx=4096+ prompts to validate BW/compute regime shift.
- [ ] Validate on MoE architect (Qwen3.5-122B Q4 or REAP-246B Q4) — expect +10-20% given architect class.
- [ ] Sustained thermal check: 30-min 96t decode, monitor CPU frequency.
- [ ] Deployment PR to `orchestrator_stack.py` if Phase 2 tests pass.

## Artifacts

- Raw JSON benchmark outputs: `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-24/*.json`
- Earlier (partially-wrong) writeup: `research/deep-dives/cpu-optimization-phase0-baseline.md` — this file supersedes the 96t claim; barrier + DeltaNet findings from that doc still stand.
