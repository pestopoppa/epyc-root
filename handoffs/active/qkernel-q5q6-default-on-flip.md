# Q5_K + Q6_K AVX-512BW 8x8 Kernels — Validation + Default-ON Flip

**Status**: REFRESHED 2026-05-28 — Phase A gate failed 2026-05-04; default flip NO-GO; Q5/blanket work deprioritized
**Created**: 2026-05-04
**Updated**: 2026-05-28 (master-index failure state reconciled into handoff)
**Categories**: hardware_optimization, inference_serving
**Priority**: MEDIUM (compounds with shipped Q8_0 8x8; unblocks blanket `Q{5,6,8}_K` repack default flip)
**Parent**: [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md)
**Related**:
- [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) Prioritized Task List CPU2 row
- [`model-registry-v5-deployment-draft.yaml`](model-registry-v5-deployment-draft.yaml) — env block source
- [`llama-cpp-kernel-push-rebase.md`](llama-cpp-kernel-push-rebase.md) — v5 kernel push tracker

## 2026-05-28 Audit Reset — Executor Start Here

Do not run this as a fresh validation stub. The Q6_K default-on gate already ran and failed.

| Item | Current disposition |
|---|---|
| Q6_K PPL gate | PASS: 5/5 bit-exact in `data/cpu_optimization/2026-05-04-q6k-default-on-validation/findings.md`. |
| Q6_K 96t perf gate | FAIL: aggregate geomean -0.28%, REAP-246B -1.01%; default stays OFF. |
| Q6_K low-thread utility | Still valid as opt-in via `GGML_Q6_K_8X8_AVX=1` for low-thread or diagnostic runs. |
| Q5_K body | Deprioritized until a fresh profile shows Q5_K remains material after Q6/Q8 state. |
| Blanket `Q{5,6,8}_K` default-on | No-go under current production workload; compounding rationale falsified. |

Reopen only if at least one condition changes:

- Production workload shifts to low-thread decode where Q6_K's single-thread win matters.
- A new kernel branch materially changes the Q6_K implementation.
- CPU20-compliant profiling shows Q5_K/Q6_K scale/min paths are again a top bottleneck.

## Why this exists

Q4_K_M decode is the dominant production code path (Coder-30B-A3B, REAP-246B-A35B, Qwen3-Next-80B, gemma-4-31B, SuperGemma4-31B and the entire dense Q4 roster). The Q4_K_M dispatch path **calls into Q6_K and Q8_0 8x8 GEMV kernels via the superblock scale path**:

- Session 14 measurement: Q6_K = **18.2% of Q4_K_M decode cycles**
- Session 14 measurement: Q5_K = **4.6% of Q4_K_M decode cycles**

Q8_0 8x8 AVX-512BW has shipped (`project_q8_8x8_avx512bw_outcome` — +31.8% at 1t, +1-3% at 12-96t BW-saturated). The natural follow-on is the same SIMD treatment for Q6_K and Q5_K so the blanket `Q{5,6,8}_K x86 repack default-ON` flip can land coherently (per `cpu-shape-specialized-gemv-decode.md:123`).

Expected aggregate effect on Q4_K_M decode once both are default-ON: **+2-7%** across the Q4 roster, multi-thread BW-saturated regime. Single-thread effect larger but production-irrelevant.

## Current state (verified 2026-05-04)

| Kernel | Branch state | Default | Comment in code |
|---|---|---|---|
| Q8_0 8x8 AVX-512BW | ✅ in `production-consolidated-v5` | `GGML_Q8_0_8X8_AVX=1` opt-in, **OFF** | accurate |
| Q6_K 8x8 AVX-512BW | ✅ in `production-consolidated-v5` (commit `529fcbd6a` + Session 18 prefetch `69ad1ae2b`) | `GGML_Q6_K_8X8_AVX=1` opt-in, **OFF** | **stale** — line 1786-1787 says "currently a stub that calls the generic reference"; body at line 1650 is fully implemented (~130 lines of intrinsics) |
| Q5_K 8x8 AVX-512BW | ❌ not written; only generic scalar at `repack.cpp:?` | n/a | n/a |

**Verification**:
```bash
cd /mnt/raid0/llm/llama.cpp-experimental
git merge-base --is-ancestor 529fcbd6a production-consolidated-v5 && echo "Q6_K body in v5"
```

## Phased plan

### Phase A — Q6_K validation under v5 — CLOSED NO-GO 2026-05-04

**Gate**: PPL bit-exact + multi-thread perf signal **before** flipping default-ON.

#### A.1 — PPL bit-exact gate

Per `cpu-shape-specialized-gemv-decode.md:1647-1649`:
> Bit-exact target: matches generic `ggml_gemv_q6_K_NxM_q8_K_generic_impl<8,8>` modulo arithmetic-equivalent reordering. PPL gate on 32-chunk WikiText-2 is the validation requirement before flipping default.

```bash
# Compare PPL with kernel OFF vs ON on production lineup (5 models)
for env_val in 0 1; do
  for model in Coder-30B-A3B-Q4 REAP-246B-Q4 Qwen3-Next-80B-Q4 gemma-4-31B-Q4 SuperGemma4-31B-Q4; do
    GGML_Q6_K_8X8_AVX=$env_val \
      OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active \
      numactl --interleave=all -- taskset -c 0-95 \
      llama-perplexity -m $model -t 96 -fa 1 --mmap 0 \
      -f wikitext-2-raw/wiki.test.raw --chunks 32
  done
done
```

**Pass criterion**: PPL Δ ≤ 0.01 (well within run-to-run noise) for all 5 models, both runs.

#### A.2 — Multi-thread perf gate

```bash
# 96t canonical decode tg32, n=5 reps, both env states
for env_val in 0 1; do
  for model in Coder-30B-A3B-Q4 REAP-246B-Q4 Qwen3-Next-80B-Q4 gemma-4-31B-Q4 SuperGemma4-31B-Q4; do
    GGML_Q6_K_8X8_AVX=$env_val \
      OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active \
      numactl --interleave=all -- taskset -c 0-95 \
      llama-bench -m $model -t 96 -fa 1 --mmap 0 -p 0 -n 32 -r 5
  done
done
```

**Pass criterion**: aggregate (geometric mean across 5 models) Δ ≥ +0.5% with σ ≤ 1% per model. Per-model regression > -1% on any model = fail.

**Pre-flight**: Coder-30B Q4_K_M tripwire (~47-49 t/s cold-boot, ~58 t/s warmed) before each perf run.

#### A.3 — Default-ON flip if A.1 + A.2 pass

Single-line code change in `ggml/src/ggml-cpu/arch/x86/repack.cpp:1788-1790`:
```cpp
// Before
const char * env = std::getenv("GGML_Q6_K_8X8_AVX");
return env != nullptr && env[0] == '1';
// After (default-on, env=0 to opt-out)
const char * env = std::getenv("GGML_Q6_K_8X8_AVX");
return env == nullptr || env[0] != '0';
```

Also fix the stale comment at line 1786-1787 ("currently a stub") — the body has been implemented since Session 17.

#### A.4 — Update parent handoff

Mark Q6_K row in `cpu-shape-specialized-gemv-decode.md:126` from "follow-up" to "validated + default-on".

### Phase B — Q5_K kernel body (1-2 weeks)

Algorithm template lives in `arch/arm/repack.cpp` NEON reference (the same source that Q6_K Session 17 mirrored). Q5_K block layout per super-block:

- 256 weights / super-block (`QK_K`)
- 16 sub-blocks × 16 weights/sub-block
- Each weight = 5 bits = 4 bits in `qs[128]` + 1 bit in `qh[32]`
- Per-sub-block i6 scale + i6 minimum (12 bytes total per super-block)
- Super-block `d` (FP16) and `dmin` (FP16) for scale/min-of-mins

#### B.1 — Dispatcher scaffolding

Mirror Session 16 pattern: add `#if defined(__AVX512F__) && defined(__AVX512BW__)` block + `gemv_q5_K_8x8_q8_K_avx512bw` stub + env-gated dispatcher. Comments documenting the planned algorithm for handoff continuity. Keep stub calling generic reference. Default-OFF env `GGML_Q5_K_8X8_AVX`.

#### B.2 — Algorithm design (estimated complexity)

Q5_K is **harder than Q6_K** in two ways:
1. **Dual scale/min path**: every sub-block has both a scale AND a min, both i6 (split across `scales[12]` packed bytes). The min path requires an additional bias subtraction with the `dmin` super-block scale. Q6_K only had the `-32` constant offset.
2. **5-bit weight unpack**: `q5 = qh_bit | (ql_4 + offset)` — bit-extract from `qh` per-weight is more fiddly than Q6_K's 2-bit-from-qh path.

Key intrinsic moves:
- **Bias precompute** — same shape as Q6_K Session 17, except summed twice (once for the `-mins` term, once for `bsums × scales`)
- **5-bit assembly** — `qh` bit selection via VPMOVB2M / VPTESTMB + masked OR; `ql_4` via VPAND+VPSRLW pair as in Q6_K
- **Inner loop body** — VPMADDUBSW(unsigned q5, signed q8) + VPMADDWD reduce → matches Q6_K Session 17 line 1747-1750 exactly
- **Scale × accumulator** — `acc * d` and `bias * dmin` separately, FMA into row accumulator

Estimated body size: **~200-220 lines of intrinsics** (~50% larger than Q6_K's ~130 lines, mostly from the dual scale/min handling).

#### B.3 — Implementation iteration

Same protocol as Q6_K Session 17:
1. Generic-equivalent scalar reference for testing
2. Inner loop intrinsic-by-intrinsic against generic on a single super-block, scalar `printf` diff at every stage (ql nibble extract → qh bit extract → q5 assembly → VPMADDUBSW partial → reduce → scale/min apply)
3. PPL bit-exact gate on Coder-30B
4. Multi-thread perf measurement under canonical
5. **Profile gate first**: if Q5_K ends up <2% of total cycles after Q6_K is on (BW-saturation may amortize the savings), demote to LOW and consider Q4_K_M-direct ukernel instead

#### B.4 — Default-ON flip if gates pass

Same pattern as A.3.

### Phase C — Blanket `Q{5,6,8}_K` repack default flip (1 hour)

Per `cpu-shape-specialized-gemv-decode.md:123`:
> Safe to flip default ON in a follow-up once Q6_K and Q5_K get the same 8x8 SIMD treatment so a blanket `Q{5,6,8}_K x86 repack` enable-flip makes sense holistically.

Once A.3 + B.4 are landed, remove all three `GGML_Q{5,6,8}_K_8X8_AVX` env gates. Single commit, default-on for everyone, env vars deprecated.

**Validation**: re-run the Phase A.2 perf sweep across the production lineup with **clean v5+1** binary (no env vars). Aggregate Δ should match A.2 + B.3 sums. Persist canonical numbers to `data/cpu_optimization/2026-XX-XX-q5q6-blanket-default-on/`.

### Phase D — Q4_K_M-specific ukernel (gated, may not happen)

Per `cpu-shape-specialized-gemv-decode.md:331,340`:
> Q4_K_M's block structure (32 weights per block, 6-bit superblock scales) requires gather/broadcast operations in the inner loop. If the dequant can't be fused efficiently into the AVX-512 FMA, the ukernel may lose to a plain Q8_0 ukernel despite the BW savings — same lesson as TurboQuant vs Hadamard.

**Gate**: only run Phase D if Phase C aggregate gain is **< 2%** on the Q4 MoE roster. If C delivers ≥ 2%, the kernel ceiling is the BW saturation limit (per `cpu-shape-specialized-gemv-decode.md:165` → 96.6% backend-stalled), and a Q4_K_M-specific ukernel will not move the needle further on this hardware. Defer indefinitely.

If pursued: scope is ~1 week of careful kernel work + a measure-first commit (write reference scalar, write SIMD, compare both bit-exact, gate on perf delta vs plain-Q8_0-via-superblock-path, only ship if SIMD beats fallback by ≥ 0.5%).

## Decision gates summary

| Phase | Gate | Decision |
|---|---|---|
| A.1 PPL | Δ ≤ 0.01 across 5 models | proceed to A.2 |
| A.2 perf | Aggregate Δ ≥ +0.5%, no per-model regression > -1% | proceed to A.3 |
| A.3 default-flip | (none — code change after gates pass) | merge to v5 patchset |
| B.3 PPL+perf | bit-exact + ≥ +0.5% aggregate, no regression | proceed to B.4 |
| B.4 default-flip | (none — code change) | merge |
| C clean re-bench | aggregate matches A+B sums | merge blanket flip; close Phase D unless D gate triggers |
| D gate | Phase C aggregate < 2% on Q4 roster | start D; otherwise defer indefinitely |

## Constraints

- All work in `/mnt/raid0/llm/llama.cpp-experimental` per `feedback_experimental_repo`.
- All bench runs gated on per-run user approval per `feedback_no_concurrent_inference`.
- Tripwire required before each Phase A.2 / B.3 / C run per `feedback_canonical_baseline_protocol`.
- PPL gate non-negotiable before any default-ON flip per `cpu-shape-specialized-gemv-decode.md:1648`.

## Effort estimate

- Phase A (Q6_K validate + flip): ~3 h serial bench + 30 min code change
- Phase B (Q5_K body): ~1-2 weeks of kernel work + iteration + validation
- Phase C (blanket flip): ~1 h + bench validation
- Phase D (Q4_K_M direct, gated): ~1 week + validation

Total under-the-line work: ~2-3 weeks if Phase D triggers; ~1-2 weeks if not.

## Persistence + reporting

- Phase A bundle → `data/cpu_optimization/2026-XX-XX-q6k-default-on-validation/`
- Phase B bundle → `data/cpu_optimization/2026-XX-XX-q5k-kernel-body/`
- Phase C bundle → `data/cpu_optimization/2026-XX-XX-q5q6-blanket-default-on/`
- Update `cpu-shape-specialized-gemv-decode.md` Recommended follow-ups list as each phase completes
- Move handoff to `completed/` once Phase C lands (Phase D forks into its own handoff if triggered)
