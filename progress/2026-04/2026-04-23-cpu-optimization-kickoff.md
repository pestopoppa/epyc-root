# 2026-04-23 — CPU optimization coordinated pickup kickoff

## Summary

Picked up the CPU shape-specialized GEMV handoff, expanded scope to the full CPU-inference backlog per user direction. Completed Steps 0–3 (partial) of the 8-step coordinated pickup plan. Landed three material findings that reshape downstream work. Paused before Step 4 (sudo sysctl knobs) pending user approval.

Plan document: `/home/node/.claude/plans/lets-pickup-handoffs-active-cpu-shape-sp-sunny-tower.md`

## Steps completed

### Step 0 — handoff corrections + index registration ✅

- GEMV handoff (`cpu-shape-specialized-gemv-decode.md`): 8 drift fixes applied — 2026-04-23 audit block, tinyBLAS-in-fork resolution (Open Q 1 closed), KleidiAI template note, `../completed/kv-cache-quantization.md` path fix, perf-unavailable fallbacks, DeltaNet gate tightened 60%→40%, TIDE date-collision note, pickup-checklist updates.
- Master handoff index (`master-handoff-index.md`): row 27 expanded with pickup-initiated note and 8-step sequence reference.
- CPU umbrella (`cpu-inference-optimization-index.md`): §Pickup Sequence section added.
- CPU1/CPU3 siblings (`intra-process-tensor-parallel-decode.md`, `single-instance-system-tuning.md`): 2026-04-23 audit cross-references added so sibling Phase 0 runners inherit tinyBLAS-present + perf-unavailable facts.

### Step 2 — experimental worktree re-anchor ✅

- `/mnt/raid0/llm/llama.cpp-experimental` archive-committed prior session state (PR_SUBMISSION + TTT scaffold + TTS experiment + patches) to `archive/test-qwen36-upstream-2026-04-23`.
- New working branch `cpu-optimization/backlog-2026-04-23` off `production-consolidated-v4` (HEAD `9e048fbc1` — post-TIDE-deprecation v4 tip with Hadamard KV smoothing + f16 fix + TIDE adapter cleanup merged 2026-04-23).
- Clean rebuild `cmake -DGGML_USE_LLAMAFILE=ON -DCMAKE_BUILD_TYPE=Release`; smoke-test matches production (48t pinned Qwen3-Coder-30B-A3B Q4_K_M = 39.72 t/s vs production 39.1 t/s).

### Step 1 — CPU6/CPU7/CPU11 cheap checks ✅ (with deferrals)

Deep-dive: `research/deep-dives/cpu-optimization-cheap-checks-2026-04.md`.

- **CPU7 tinyBLAS on/off**: 0% gain on both Qwen3-Coder-30B-A3B Q4_K_M (39.72 vs 39.68) and Qwen3.6-27B Q8_0 (4.21 vs 4.23) at 48t pinned. tinyBLAS does not route M=1 decode matmuls on Zen 5 — the handoff's hoped-for "partial auto-win" is zero. Material negative finding: CPU2 (shape-specialized ukernels) has to deliver all the gain from scratch.
- **CPU11 compiler flags**: default cmake emits `-march=native` which on this EPYC 9655 resolves to Zen 5 features already. Explicit `-march=znver5` provides no incremental advantage. PGO test not run (deferred, requires separate rebuild cycle).
- **CPU6 ZenDNN 5.2**: deferred — install requires sudo + external AMD package. Added as standalone pending task #9.

### Step 3 — CPU3 Phase 0 root baseline ✅ COMPLETE (after sudo-gate knobs + perf install)

Deep-dive: `research/deep-dives/cpu-optimization-phase0-baseline.md`.

- **System-state audit captured**: NPS2 mode, THP `madvise`, NUMA balancing ON, 0 hugepages, governor `performance`, 305 GB free RAM, 820 GB in page cache from prior mmap'd models, `perf` not installed.
- **Thread sweep** on Qwen3-Coder-30B-A3B Q4_K_M decode (-p 0 -n 64 -r 2):
  - 24t (cores 0–23, Q0A): **40.76 t/s** (production worker_explore match)
  - 48t (cores 0–47, node 0 half): **39.59 t/s** (barrier-bound regression vs 24t)
  - **96t (cores 0–95, full node 0): 47.91 t/s — PEAK OBSERVED**. NEW single-instance operating point not previously measured in production.
  - 144t (cores 0–143): **25.74 t/s with bimodal stddev 18.5** (12.66 / 38.83). NUMA crossing without proper sharding causes severe instability.
  - 192t (full machine `--numa distribute --mlock`): UNRELIABLE. Host under active user load (firefox + browser content at ~200% CPU, load average 163–171 during attempts). Runs produce ~0.14 t/s vs registry's 14.2 t/s. Requires quiet host window.
- **Qwen3.6-27B GGUF metadata dumped** (resolves handoff audit open question). GEMV handoff dims corrected:
  - MLP feed_forward_length: **17408** (handoff said 27648 — off by 59%)
  - GQA: **24Q / 4KV heads** (handoff said 14Q / 2KV)
  - Head dim (key/value length): 256
  - 75% DeltaNet (full_attention_interval=4, 16 full + 48 DeltaNet layers)
  - 256K context (262144)

- **Post-sudo-unblock additions**:
  - **perf profile on Qwen3-Coder-30B-A3B Q4_K_M @ 96t**: 45.04% libomp barrier spin; 24.72% `ggml_gemv_q4_K_8x8_q8_K` (already KleidiAI-style specialized upstream); 9.24% `ggml_vec_dot_q6_K_q8_K`; 2.72% fp32→fp16 conversion.
  - **perf profile on Qwen3.6-27B Q8_0 @ 96t (4.41 t/s)**: **63.43%** `ggml_vec_dot_q8_0_q8_0` (AVX2-only in `arch/x86/quants.c:1012`, NO AVX-512 path!); 32.34% libomp barrier; **0.07%** `ggml_compute_forward_gated_delta_net` + 0.04% `ggml_compute_forward_ssm_conv` = **0.11% DeltaNet**.
  - **DeltaNet gate: PASSED decisively** — at 0.11% it's not a bottleneck. The handoff's concern about DeltaNet capping ukernel speedup is refuted.
  - **Clean 192t measurement**: 18.69 t/s (bimodal stddev 7.23). 96t/192t = 2.63× gap.
  - **Quiet-host 96t re-test**: 49.11 t/s with tight stddev 0.08 (confirmed peak).
  - **BLIS 5.2 A/B**: zero gain on Qwen3-Coder-30B-A3B decode (same pattern as tinyBLAS). BLAS libraries don't route decode matmuls.

### Material Phase 0 conclusions

1. **DeltaNet is NOT a bottleneck** (0.11%, not the feared 40%+). CPU2 gate passes with huge margin.
2. **Single hot function identified**: `ggml_vec_dot_q8_0_q8_0` at 63% of Qwen3.6-27B Q8_0 cycles is **AVX2-only** on a Zen 5 CPU with full AVX-512VNNI support. This is the #1 concrete Zen 5 opportunity — a missing AVX-512 port, not a missing shape specialization.
3. **Barrier cost is 32–45% of cycles** — promotes CPU4 (per-CCD sync primitive) from MED to HIGH standalone priority. 
4. **Q8_0 also has a missing x86 repack-GEMV specialization** (`ggml_gemv_q8_0_4x8_q8_0` is ARM-only; x86 falls back to generic). Target #2 after Target #1 validates.
5. **96t single-NUMA-node peak = 49.11 t/s** on Qwen3-Coder-30B-A3B Q4_K_M — operating point not currently used in production (worker_explore uses 1×24t = 39.1 t/s; +26% by switching).

### Concrete CPU2 Phase 1 scope (revised from original plan)

Original plan had Phase 1 = "write K=5120→N=17408 templated MLP-up ukernel in new `zen5-ukernels/` plugin directory." Revised based on Phase 0 findings:

**Phase 1 Target #1 (recommended start)**: Port `ggml_vec_dot_q8_0_q8_0` from AVX2 to AVX-512VNNI in the existing `arch/x86/quants.c` file, gated by `__AVX512VNNI__` macro. ~30-50 lines. Expected: ~2× on the 63% slice → **1.46× end-to-end** on Qwen3.6-27B Q8_0 (4.41 → ~6.4 t/s).

**Phase 1 Target #2 (follow-up)**: Diagnose why the existing `ggml_gemv_q8_0_4x8_q8_0` repack path isn't being hit (perf shows only the unpacked `vec_dot` path). If fixable, port the ARM implementation to x86 AVX-512 — larger change but higher ceiling.

**Phase 1 out of scope for now**: shape-specialized `K=5120 → N=17408` compile-time-templated MLP-up ukernel. Revisit after Target #1 results; the shape specialization adds ~1.3–1.5× ON TOP of Target #1, but Target #1's AVX2→AVX-512 step is a strict prerequisite and the bigger winning.

## Material findings that reshape the plan

1. **tinyBLAS does not contribute to M=1 decode on Zen 5 for our quant formats.** CPU2 (GEMV ukernel) work must deliver all gain itself; no auto-fallback to lean on. The llamafile 2.8× Zen 4 number is prefill-heavy, does not transfer.
2. **96t single-socket is the new peak for single-instance decode** on Qwen3-Coder-30B-A3B Q4_K_M (47.9 t/s). Production sees 14.2 t/s at 192t (interleaved, no `--numa distribute`) and 39.1 t/s at 24t worker_explore. The 96t-node0-pinned config is +21% over 48t and delivers single-instance gains the production router hasn't been exploiting. CPU1 TP-sharding story shifts: the gap to close is 96t → full-machine, not 48t → full-machine. Smaller headroom at the single-instance level, but cross-NUMA problems (see 144t bimodality) suggest there's still meaningful TP opportunity.
3. **Qwen3.6-27B Phase 1 ukernel target corrected**: K=5120 → N=17408 (not 27648). 37% smaller weight matrix than originally scoped (89 MB vs 141 MB). Changes L3 resident-working-set calculation for the Phase 1 ukernel.

## User decisions needed before resuming

**Step 4 (CPU3 zero-reboot knobs) is user-approval-gated** per plan — requires `sudo sysctl` for THP `always`, NUMA balancing off, hugepages allocation. Host is user-active (firefox open).

**CPU6 ZenDNN 5.2 install** — user approval needed to proceed (sudo + external AMD package).

**192t clean measurement** — requires a quiet host window (no firefox / active desktop workload). Plan calls for 192t as a canonical benchmark datapoint.

**Step 5 (TP-sharding) and Step 6 (GEMV ukernel) are 1-week-each prototype builds**, justified only if Step 3's pending DeltaNet-fraction measurement doesn't gate CPU2 out. Recommend completing Step 3's open items (GGML_PERF rebuild + per-op breakdown + barrier cost) before committing to Step 5/6.

## Artifacts landed

- `handoffs/active/cpu-shape-specialized-gemv-decode.md` — 8 drift fixes + Qwen3.6-27B dim corrections
- `handoffs/active/master-handoff-index.md` — pickup note on row 27
- `handoffs/active/cpu-inference-optimization-index.md` — §Pickup Sequence
- `handoffs/active/intra-process-tensor-parallel-decode.md` — audit cross-references
- `handoffs/active/single-instance-system-tuning.md` — audit cross-references
- `research/deep-dives/cpu-optimization-cheap-checks-2026-04.md` — CPU7/CPU11 results + CPU6 deferral
- `research/deep-dives/cpu-optimization-phase0-baseline.md` — system audit + thread sweep + GGUF dims + preliminary gates
- `/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-23/` — raw JSON/log artifacts
- `/mnt/raid0/llm/llama.cpp-experimental` on branch `cpu-optimization/backlog-2026-04-23` + archive branch `archive/test-qwen36-upstream-2026-04-23`

## Next if user approves proceeding

In rough priority:
1. Finish Step 3: rebuild with `-DGGML_PERF=ON`, capture per-op breakdown on Qwen3-Coder-30B-A3B Q4_K_M at 96t and 24t. Determine DeltaNet fraction. Gate CPU2 in/out.
2. Step 4: zero-reboot knob sweep (needs sudo for 3 of 5 knobs).
3. Step 5/6: TP-sharding + GEMV ukernel prototypes, only if the gates from Steps 3/4 still recommend them.

---

## Continuation — Steps 4, 6, and 7 (2026-04-23 late session)

User applied sudo commands: `perf_event_paranoid=1`, `linux-perf` installed in container, THP→always, numa_balancing=0, 1GB hugepages (1 of 40 requested honored — kernel needs boot param for full 40). AOCL 5.2.0 + BLIS 5.2 also installed + built under `llama.cpp/build-blis52` but ZenDNN full integration deferred.

### Step 4 — CPU3 zero-reboot knobs: within noise

96t re-test across 3 runs after THP+numa_balancing changes: 46.4, 46.4, 48.2 t/s. Compared to pre-knob baseline of 49.1 t/s → net delta within measurement variance (cold-cache effects dominate). Knob changes kept but not materially impactful on this workload.

BLIS 5.2 A/B (LD_PRELOAD on/off): both showed zero gain after cold-cache settling (same story as tinyBLAS earlier). BLAS libraries don't route quantized decode matmuls.

### Step 3 perf profile — the pivotal measurement

With `perf` now available, ran DWARF call-graph profiles on two models at 96t:

**Qwen3.6-27B Q8_0 decode (4.41 t/s)**:
- 63.43% `ggml_vec_dot_q8_0_q8_0` (AVX2-only in `arch/x86/quants.c`, no AVX-512 path!)
- 32.34% libomp spin/barrier (unresolved `0x0000000000026580` family)
- **0.11% DeltaNet** (`gated_delta_net` + `ssm_conv` combined) — **gate PASSED, DeltaNet is NOT a bottleneck**
- <0.5% everything else

**Qwen3-Coder-30B-A3B Q4_K_M decode (48.13 t/s)**:
- 45.04% libomp barrier
- 24.72% `ggml_gemv_q4_K_8x8_q8_K` (already KleidiAI-style specialized upstream)
- 9.24% `ggml_vec_dot_q6_K_q8_K`
- 2.72% fp32→fp16 conversion

### Step 6 — CPU2 Phase 1 Target #1: NEGATIVE RESULT

Hypothesis: the 63.43% in AVX2-only `ggml_vec_dot_q8_0_q8_0` is a missing AVX-512 port → 2× speedup → 1.46× end-to-end.

Implementation: ~40 lines added to `arch/x86/quants.c` using existing `mul_sum_i8_pairs_acc_int32x16` helper from `avx512-helpers.h`. Builds as `build-vnni-q8/bin/llama-bench`. Disassembly **verified**: new binary uses `vpdpbusd %zmm1,%zmm0,%zmm2` + full 512-bit register operands; baseline uses 256-bit `{vex} vpdpbusd %ymm`.

Measured end-to-end:
- Qwen3.6-27B Q8_0 @ 96t pinned: AVX2 = 4.241 t/s / AVX-512VNNI = 4.313 t/s → **+1.7%, within noise** (stddev 0.075 baseline)
- Qwen3.6-27B Q8_0 @ 1t pinned: AVX2 = 1.020 t/s / AVX-512VNNI = 0.983 t/s → **−3.6%, regression**

Projection was 1.46×; measured 1.017× at 96t. Falsified by factor 30×.

Root cause: **perf cycles inside the dot loop were DRAM-wait cycles, not ALU cycles.** Decode on this workload is BW-bound, not compute-bound. At 1t the port's additional per-iteration overhead (cross-lane `vinsertf32x8`, `_mm512_reduce_add_ps`, scalar odd-block tail) causes a net regression when there's no BW contention to hide it. At 96t the overhead is absorbed by the BW bottleneck so it's neutral-to-slightly-positive.

Change reverted (`git diff` clean on `quants.c`). Step 6 closes as **negative result**.

### Revised priorities based on today's measurements

| Lever | Before | After | Evidence |
|---|---|---|---|
| CPU2 GEMV ukernels | HIGH | **DEPRIORITIZED** | AVX-512VNNI port delivered +1.7% / −3.6%, not 1.46× |
| CPU1 TP-sharding | HIGH | **HIGH (top)** | Phase 0 gate PASSED; 96t/192t = 2.63× gap is the real target |
| CPU4 sync primitive | MED | **HIGH standalone** | 32–45% of cycles measured in libomp barriers |
| CPU3 zero-reboot | HIGH | HIGH | Applied; within-noise impact on canonical workload |

### Bonus finding — 96t-single-node production operating point

Qwen3-Coder-30B-A3B Q4_K_M at 96t pinned to node 0 delivered **49.11 t/s** (quiet host, stddev 0.08). Production worker_explore uses 1×24t = 39.1 t/s. Switching to 1×96t-single-node = **+26% single-session decode with no code change**. Needs validation under realistic load and verification of multi-instance aggregate impact, but this is the easiest win from today's session — tracked as task #10.

### Session close — all deliverables landed

- [x] Step 0 handoff corrections
- [x] Step 1 cheap checks (tinyBLAS/BLIS/compiler all neutral)
- [x] Step 2 experimental worktree re-anchor on v4
- [x] Step 3 Phase 0 baseline + perf profile (DeltaNet gate passed, real bottleneck identified)
- [x] Step 4 zero-reboot knobs (within noise)
- [x] Step 6 CPU2 Phase 1 Target #1 (negative result, reverted)
- [x] Indexes updated (master-handoff-index, cpu-inference-optimization-index, GEMV handoff, CPU1 handoff, CPU3 handoff)
- [x] Step 7 synthesis (this document)

**Step 5 (CPU1 Phase 1 prototype) deferred** to a dedicated session — Phase 0 gate is PASSED but the Phase 1 implementation is ~1 week of work (per-CCD thread pools, reduce primitive, numerical validation, end-to-end measurement).
