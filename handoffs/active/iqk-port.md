# iqk-kernel port into v6 (ik_llama iqk_mul_mat → production-consolidated-v6)

**Status**: ✅ STAGE 1 + STAGE 2 COMPLETE + VERIFIED (2026-06-25). Both stages done, all 3 stack quant patterns covered (dense Q4_K, MoE Q4_K, MoE Q8_0), correct + crash-free, measured speedups. Operator greenlit full port (both stages) "proceed systematically … do not stop until done and verified no quality regression + performance increase." Remaining: operator-run eval-suite parity (deploy gate, flagged below) + optional secondary wins (residual prefill src1-fusion, FA hook, larger MoE).
**Worktree**: `/mnt/raid0/llm/llama.cpp-v6-iqk` (branch `iqk-port` off `production-consolidated-v6` @ a4e2b4f86). Production `/mnt/raid0/llm/llama.cpp` stays on `production-consolidated-v5` — NEVER touch.
**Source**: `/mnt/raid0/llm/ik_llama.cpp/ggml/src/iqk/` (branch production-gemma4-mtp). NOT indexed in gitnexus; self-contained.

## Objective
Graft ik_llama's `iqk_mul_mat` quantized-GEMM kernels into v6 so v6 gets ik-class CPU speed AND keeps its framework/MTP/features. A full port retires ik entirely (single-kernel consolidation).

## Prize (canonical llama-bench, same-GGUF pure-kernel, v6→ik)
- decode tg128: gemma-26B Q4_K_M +19% (41.7→49.6), Qwen3.6-35B Q8 +36% (25.2→34.3), gemma-31B dense Q4_K_M +15% (7.4→8.6)
- prefill pp512: gemma-26B +53%, **Qwen3.6-35B Q8 +148% (~2.5×)**, gemma-31B +64%
- (these are the ik-vs-v6 deltas the port aims to close on v6)

## Feasibility (scoped 2026-06-25, GO / moderate-leaning-easy)
- **block_q4_K / block_q8_0 BYTE-IDENTICAL** ik↔v6 (same offsets; enum Q4_K=12, Q8_0=8) → iqk reads v6 tensors zero-conversion.
- **REPACK-FREE**: `_R4`/`_R8` types compiled out; prefill `_r8` repack is internal to the gemm files on standard Q4_K. No on-disk repacked types, no `-rtr`.
- **Hook**: v6 `ggml/src/ggml-cpu/ggml-cpu.c:1245` `ggml_compute_forward_mul_mat`; insert iqk fast-path branch ~line 1284 (after asserts, before from_float). ik ref integration: `ik_llama.cpp/ggml/src/ggml.c:16934-17008`.
- **Activation type**: iqk Q4_K/Q8_0 kernels require typeB == `GGML_TYPE_Q8_2_X4`. Need `block_q8_2`/`block_q8_2_x4` structs (ik `ggml-common.h:281`) into v6 `ggml-common.h`, an internal Q8_2_X4 type id (above v6 enum ceiling 42), and ONE runtime quantizer `quantize_row_q8_2_x4` (ik `iqk_quantize.cpp:1093` → template `quantize_row_q8_1_x4_T` `:923`).
- **CMake**: no change needed — `-march=native` (GGML_NATIVE=ON) on Zen5 defines `__AVX512F/BW/DQ/VL/VNNI/BF16__` which ik's `HAVE_FANCY_SIMD` (`iqk_config.h`) gates on. Just add iqk `.cpp` to ggml-cpu target sources (inherit ARCH_FLAGS).
- **NOT bit-exact** vs v6 (v6 activation=Q8_K, iqk=Q8_2_X4 → different rounding). Correctness bar = cosine-sim / max-abs-err vs F32 reference + eval-suite parity (NOT bitwise). Runtime A/B via env toggle preferred (one build).
- **divergence**: `ggml_compute_params` differs ({shared} vs {threadpool,use_ref}) — iqk core takes raw ith/nth so unaffected; only the hook touches `params->threadpool`/`ggml_barrier`. Structural (modular ggml-cpu) not semantic.

## Plan / checkboxes
### Stage 1 — dense Q4_K + Q8_0 mul_mat (flag-gated, 3-5d)
- [x] Vendor iqk dir → `ggml/src/ggml-cpu/iqk/` (all files copied; CMake compiles only iqk_mul_mat, iqk_gemm_kquants, iqk_gemm_legacy_quants, iqk_quantize_min, iqk_stubs, iqk_dispatch). Flash/delta-net region in iqk_mul_mat.cpp `#if 0`-guarded (fa/ not vendored).
- [x] block_q8_2/block_q8_2_x4/QK8_2 added to ggml-common.h; GGML_TYPE_Q8_2/Q8_2_X4 as #defines (98/99) in iqk_config.h (NOT in v6 ggml_type enum — activation-only).
- [x] iqk_quantize_min.cpp = ONLY quantize_row_q8_2_x4 + template (extern "C", matches header).
- [x] iqk_stubs.cpp = return-false stubs for UNUSED families (IQ/trellis/bitnet/float — registry shows ZERO usage); REAL kernels for all quants we run (Q4_K/Q5_K/Q6_K/Q2_K/Q3_K + Q8_0/Q4_0/Q5_0/Q6_0/Q4_1/Q5_1).
- [x] iqk_dispatch.cpp `ggml_iqk_try_mul_mat`: quantize src1 F32→Q8_2_X4 into wdata + ggml_barrier + iqk_mul_mat_4d (mirrors ik ggml.c:17003). Runtime gate env GGML_IQK=1. Hooked at ggml-cpu.c:1285; decl in ggml-cpu-impl.h.
- [x] CMake: iqk sources + include dir + GGML_USE_IQK_MULMAT define.
- [x] Build — CLEAN (llama-server + llama-bench). Integration fixes: immintrin (v6 ggml-impl.h dropped it), Q8_2_X4 type, 50 enum #defines + 16 block structs (ext headers), block_q8_K.sum-from-bsums, iq4k_values, SWIGLU sentinel, ktquants stub, minimal iqk_quantize.h. Commits fec061dea/060977240/2fdb4f97d on branch iqk-port.
- [x] **Correctness PASS**: gemma-31B Q4_K, GGML_IQK=1 engages ([iqk] ACTIVE) + output BYTE-IDENTICAL to GGML_IQK=0 (v6 baseline). Direct Q4_K x Q8_2_X4 path is correct.
- [x] **Perf: ~0 (Stage-1 dense, gemma-31B)** — same-build A/B tg128 7.92->7.95, pp512 155->156. Reasons: (1) dense decode is BW-bound (kernel ~neutral); (2) the prefill speedup lives in the dequant/repack path which HEAP-CORRUPTS (malloc corrupted top size, intermittent, in iqk_convert_q4_k_q8_1_r8/mul_mat_NxM) -> disabled for stability -> lost the prefill win.
- [x] **CRASH FIXED** (commit 715383cde): the dequant-path crash was a `type_traits[]` OOB READ (ASAN), not heap corruption — `is_dequant_better` returns ik-only types (Q8_0_R8=208/Q8_K_R16=397) passed to v6's `ggml_row_size`, indexing past the 42-entry table. Fix = `iqk_row_size()` shim (ik block-size formulas) at the 3 dequant call sites. No crash -t16/48/64/96; byte-identical.
- [x] **PREFILL GAP CLOSED** (commit c9bf4dad4): iqk was at +16% vs ik's +62% because `GGML_USE_CPU_REPACK` intercepted >85% of Q4_K matmuls (ffn/attn) on v6's generic-C kernel BEFORE the iqk hook. Fix = guard in `ggml_repack_get_optimal_repack_type` (repack.cpp:4528) returning nullptr for iqk-supported types when GGML_IQK=1, so they stay plain MUL_MAT for iqk. Mirrors ik (no CPU_REPACK).
- [x] **STAGE-1 PERF (gemma-31B Q4_K_M, same-build GGML_IQK on/off, VERIFIED)**: prefill pp512 **155.9→232.5 (+49%**, ~92% of ik's 252); decode tg128 **8.66→9.34 (+7.9%**). Decode was repack-starved, NOT BW-capped (earlier "neutral" finding superseded). Byte-identical output; no crash. Residual prefill gap (232 vs 252) = cross-op src1 fusion (secondary win, deferred).

### Stage 2 — MoE mul_mat_id (✅ COMPLETE)
- [x] **MoE hook** `ggml_iqk_try_mul_mat_id` (iqk_dispatch.cpp): OWNS Q8_2_X4 src1 quantize (v6's stock Q4_K vec_dot_type is Q8_K — wrong for iqk), builds per-expert `matrix_rows` with v6 stride (`ids->ne[0]*ids->ne[1]`, not ik's ne12), loops `iqk_mul_mat_moe` per expert. Hooked at top of `ggml_compute_forward_mul_mat_id` (ggml-cpu.c, after asserts before wdata carve); decl in ggml-cpu-impl.h.
- [x] **Q5_K/Q6_K routes**: already covered by `iqk_typeA_supported` (kquants) from Stage 1; no separate enable needed.
- [x] **Legacy-MoE extension** (commit 91745611f): MoE hook typeA check widened from hardcoded kquants list → `iqk_typeA_supported` (adds Q8_0/Q4_0/Q5_0/Q4_1/Q5_1) so Q8_0 MoE experts (Qwen3.6-35B Q8 frontdoor) route to iqk too.
- [x] **Correctness gemma-26B-A4B MoE Q4_K** (chat, ON vs OFF): MoE ACTIVE, **byte-identical** (565==565 chars, both coherent sky+primes), no crash/segv.
- [x] **Correctness Qwen3.6-35B MoE Q8_0** (chat, ON vs OFF): dense+MoE both ACTIVE, both correct (Paris+primes, coherent), **early-identical then late FP-cascade** (495 vs 505) — expected for the non-bit-exact dequant/repack prefill path (distribution-preserving per [[project_q8_8x8_avx512bw_outcome]]), NOT a numerical bug. No crash.
- [x] **Perf gemma-26B-A4B MoE Q4_K** (same-build ON/OFF): pp512 577.7→707.5 (**+22.5%**), tg128 44.5→48.5 (**+8.8%**).
- [x] **Perf Qwen3.6-35B MoE Q8_0** (same-build ON/OFF): pp512 401.0→500.6 (**+24.9%**), tg128 26.3→26.4 (**neutral** — Q8_0 is 8-bit → decode fully BW-bound, kernel can't help; no regression).

### ✅ FINAL RESULTS — full stack coverage (same-build GGML_IQK on/off, prod untouched on v5)
| Model | Path | Quant | Prefill pp512 | Decode tg128 | Correctness |
|-------|------|-------|---------------|--------------|-------------|
| gemma-4-31B | dense | Q4_K_M | 155.9→232.5 **+49%** | 8.66→9.34 **+7.9%** | byte-identical |
| gemma-4-26B-A4B | MoE | Q4_K_M | 577.7→707.5 **+22.5%** | 44.5→48.5 **+8.8%** | byte-identical |
| Qwen3.6-35B-A3B | MoE | Q8_0 | 401.0→500.6 **+24.9%** | 26.3→26.4 ~0 (BW-bound) | correct, FP-cascade |

### Verification (operator bar: no quality regression + perf increase)
- [x] Correctness: gemma dense + both MoE families coherent + correct; Q4_K byte-identical, Q8_0 distribution-preserving (early-identical, FP-cascade only). No crash on -t16/48/64/96.
- [x] Prefill llama-bench uplift ON vs OFF: +22.5% to +49% across all 3 patterns.
- [x] Decode llama-bench uplift: +7.9–8.8% on Q4_K (4-bit, not yet BW-saturated); neutral on Q8_0 (8-bit, BW-bound — expected, no regression).
- [ ] **eval-suite parity flag ON vs OFF (operator-run — DEPLOY GATE)**: the Q8_0 MoE path is non-bit-exact by design; per MEASUREMENT.md, eval-suite parity (not bit-compare) is the gate before any v6+iqk promotion. Flagged for operator.

### ✅ FULL-STACK MAX-OPTIMIZATION OVERVIEW (2026-06-25) — current performance ON the v6-iqk kernel
All numbers GGML_IQK=1 on `/mnt/raid0/llm/llama.cpp-v6-iqk/build` (branch iqk-port), `[iqk] ACTIVE` verified each run. Host 28-day uptime → absolute t/s are throttle-suspect OBSERVATIONS; deltas are same-window. Operator-run eval still the deploy gate.

**Base single-stream (llama-bench, canonical `-t96 -fa1 -mmp0 -p512 -n128 -r3`):**
| Model | quant | pp512 | tg128 | notes |
|-------|-------|------:|------:|-------|
| Qwen3.5-9B (hybrid SSM) | Q4_K_M | 555.6 | 26.4 | new |
| gemma-4-26B-A4B MoE | Q4_K_M | 707.5 | 48.5 | prior (byte-identical vs OFF) |
| Qwen3.5-27B (hybrid SSM) | Q4_K_M | 184.2 | 7.4 | new |
| Qwen3.6-27B **dense** | Q4_K_M | 185.3 | 4.0 | new (27B active → BW-heavy) |
| gemma-4-31B **dense** | Q4_K_M | 232.5 | 9.3 | prior |
| Qwen3.6-35B-A3B MoE (frontdoor) | Q8_0 | 500.6 | 26.4 | prior |
| Qwen3-Next-80B-A3B SSM-MoE | Q4_K_M | 230.8 | 19.4 | new (iqk hits FFN/expert GEMMs only) |
| Qwen3.5-122B-A10B MoE | Q4_K_M | 212.3 | 8.8 | new (3-shard) |

**MTP "full optimization" decode (llama-server /completion, draft-mtp, tuned n-max; base = same /completion path, NOT llama-bench):**
| Model | base | MTP peak | gain | opt n-max | draft accept |
|-------|-----:|---------:|-----:|:---------:|:-----------:|
| gemma-4-26B-A4B (Q4 MoE, worker) — **Q8 head** | 37.4 | 53.5 | **+43%** | 2 | 0.67 |
| └ same model with f16 head (suboptimal) | 42.1 | 52.8 | +25% | 2 | 0.75 |
| Qwen3.5-9B (hybrid) | 23.2 | 41.6 | **+79%** | 4 | 0.60 |
| gemma-4-31B (Q4 **dense**) | 5.2 | 15.4 | **+197%** | 6 | 0.43 |
| Qwen3.6-35B-A3B (Q8 MoE, **frontdoor**) | 20.7 | 41.8 | **+103%** | 4 | 0.82 |
| Qwen3.6-27B (Q4 **dense**) | 4.4 | 12.2 | **+177%** | 4 | 0.81 |
| Qwen3.5-27B (hybrid-SSM **dense**) | 2.3 | 5.6 | **+146%** | 4 | 0.70 |

**MTP findings:**
- **n-max must be tuned per model** (over-drafting wastes CPU verify compute): MoE/hybrid peak at n2–4, **dense keeps scaling to n6** (verify batch = ONE weight read amortized over N tokens; MoE re-reads N× experts so gains saturate early).
- **iqk is NEUTRAL on the MTP verify batch** (gemma-26B n4: 48.2 iqk-on / 48.1 iqk-off) → iqk + MTP compose cleanly, **no kernel change needed for MTP**.
- **MTP head coverage (6 of 8 models — ALL that have an MTP path)**: gemma-26B (v6 head on disk), Qwen3.5-9B (embedded NEXTN), gemma-31B (**remapped** ik→v6), Qwen3.6-35B frontdoor (**downloaded** NEXTN), Qwen3.6-27B + Qwen3.5-27B dense (**downloaded** unsloth NEXTN, +177%/+146%). Only Qwen3.5-122B (GDN/recurrent wall) + Qwen3-Next-80B (SSM serial) have NO MTP path → their max = base iqk.
- **Dense MTP is the biggest win** (verify batch amortizes ONE weight read over N tokens): the 4 dense/slow models gained +146% to +197%; the slow dense 27B pair (4.4/2.3 t/s) ~tripled.
- **DRAFT-HEAD PRECISION is a major lever** (empirical — overturned a bandwidth estimate): gemma-26B with an **f16** assistant head (855 MB) is **−28%** vs the **Q8** head (461 MB) at identical acceptance (same-window chat draft=2: f16 33.48 vs Q8 42.78 t/s). The f16 `token_embd` (262144×1024) dominates the draft pass. **Requantized to Q8** (`gemma-4-26B-A4B-it-assistant-v6-Q8_0.gguf`, built `llama-quantize` to make it) → now the canonical worker head. Only gemma-26B had a separate f16 head; gemma-31B head already Q8; all Qwen NEXTN heads are embedded at model quant (shared token_embd) → no equivalent lever.
- **v6-iqk now BEATS ik_llama on the worker** (same-window, gemma-26B MTP draft=2, chat): v6-iqk+Q8head **42.78** t/s (accept 0.80) vs ik_llama PR#1744 **38.63** (accept 0.66) = **+11%** → single-kernel consolidation gap not just closed, v6-iqk wins. (Recorded ik warm-stack peak 76.5 t/s and v6 42.8 are NOT comparable — host at 28-day uptime, THP drift swings absolutes; only same-window deltas valid.)

**New artifacts (2026-06-25):**
- `/mnt/raid0/llm/models/gemma-4-31B-it-assistant-v6-Q8_0.gguf` — gemma-31B MTP head remapped from the ik `gemma4_mtp` head → v6 `gemma4-assistant` (arch+tensor+metadata rename, synthesized `rope_freqs` validated vs the 26B v6 head). Remap script: `/mnt/raid0/llm/tmp/remap_gemma31b_assistant.py`. Runtime-validated (loads, drafts, coherent, +197%).
- `/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf` — frontdoor NEXTN MTP GGUF, downloaded from `unsloth/Qwen3.6-35B-A3B-MTP-GGUF` (Q8_0, 37.8 GB, exact-size verified). 1 NEXTN layer, 0.82–0.93 acceptance.
- `/mnt/raid0/llm/models/Qwen3.6-27B-MTP-Q4_K_M.gguf` (17.1 GB) + `/mnt/raid0/llm/models/Qwen3.5-27B-MTP-Q4_K_M.gguf` (17.1 GB) — dense NEXTN MTP GGUFs, downloaded from `unsloth/Qwen3.6-27B-MTP-GGUF` / `unsloth/Qwen3.5-27B-MTP-GGUF` (exact-size verified). +177% / +146%.
- `/mnt/raid0/llm/models/gemma-4-26B-A4B-it-assistant-v6-Q8_0.gguf` (461 MB) — **canonical worker MTP head**, requantized from the f16 head (Q8 is −28%-faster draft pass; built the `llama-quantize` target in the v6-iqk build to make it).
- (downloading) `Qwen3.5-122B-A10B-MTP-GGUF/UD-Q4_K_M/*` — architect MTP head (78.3 GB, 3 shards) from `unsloth/Qwen3.5-122B-A10B-MTP-GGUF`; earlier "no MTP" dismissal was WRONG (qwen35moe = frontdoor arch).
- Sweep data + scripts under `/mnt/raid0/llm/tmp/iqk_sweep_2026-06-25/` and `/mnt/raid0/llm/tmp/iqk_*sweep*.sh`, `iqk_newheads_mtp.sh`, `iqk_mtp_runner.sh`.

## NUMA Phase-3B — NUMA-concurrent MTP topology suite (✅ COMPLETE + CORRECTED `--no-mmap`, all 7 models, 2026-06-25/26)

> **SUPERSEDED — the earlier mmap-shared NUMA-concurrent numbers were CONTAMINATED.** The first NUMA suite
> ran with **mmap** under `numactl --cpunodebind=N --membind=N`, so the N concurrent quarter instances all
> shared **ONE page-cache copy on a single node** → bandwidth-starved; the full cells then inherited the
> quarter loads' node-local page placement when run after them in the same matrix. The contaminated table
> (committed earlier @ ~`8f1c55a7`: gemma-26B 4×quarter **43.46**, gemma-31B/122B "dense prefers 1×full",
> etc.) is **RETRACTED**. The corrected `--no-mmap` results below replace it. Root cause + A/B evidence at
> the bottom of this section.

Re-measures the NUMA-topology × MTP throughput matrix on the v6-iqk kernel under the **clean-host + private
node-local protocol**: **`--no-mmap`** (a private node-local weight copy per instance instead of one shared
mmap page-cache copy), quiesced host, and `drop_caches` **between models** (so one model's quarter loads no
longer contaminate the next model's full cells). Sweep data:
`/mnt/raid0/llm/tmp/iqk_sweep_2026-06-25/numa_mtp.<model>.jsonl`. **Aggregate t/s across instances**
(per-instance = aggregate / n_inst, where quarter n=4, full n=1, half n=2). **All 7 models complete**
(gemma-26B, gemma-31B, Qwen3.6-27B, Qwen3.5-27B, Qwen3.6-35B, Qwen3-Next-80B, Qwen3.5-122B); every cell
re-verified against the FIXED jsonl.

### Full 7-model FIXED matrix — aggregate t/s, `--no-mmap` private node-local
| Model | type | q_off | **q_on** | f_off | **f_on** | h_off | **h_on** | best (agg) |
|-------|------|------:|---------:|------:|---------:|------:|---------:|:----------:|
| gemma-26B | small MoE (worker) | 73.88 | **109.61** | 34.86 | 49.07 | 54.58 | 83.33 | 4×quarter |
| gemma-31B | dense | 7.18 | **30.05** | 7.40 | 23.85 | 6.14 | 17.49 | 4×quarter |
| Qwen3.6-27B | dense | 6.81 | 20.00 | 5.54 | 15.78 | 6.62 | **20.22** | quarter≈half |
| Qwen3.5-27B | hybrid-SSM dense | 6.38 | **18.71** | 5.60 | 14.37 | 6.44 | 16.77 | 4×quarter |
| Qwen3.6-35B | frontdoor Q8 MoE | 42.11 | **71.89** | 22.72 | 42.28 | 36.83 | 65.31 | 4×quarter |
| Qwen3-Next-80B | SSM-MoE ingest (NO MTP) | **49.23** | n/a | 23.78 | n/a | 39.75 | n/a | 4×quarter |
| Qwen3.5-122B | architect MoE | 17.96 | **28.30** | 10.60 | 18.01 | 15.62 | 26.19 | 4×quarter |

(q=4×quarter/4 inst, f=1×full/1 inst, h=2×half/2 inst; MTP-on values are the median of 3 reps in the jsonl
`agg_tps`; bold = best aggregate-throughput operating point. Qwen3.6-27B quarter 20.00 ≈ half 20.22 — a tie.)

### Per-model topology rule (FIXED — quarter wins broadly)
- **4×quarter wins aggregate throughput for EVERY model** (6/7 outright; Qwen3.6-27B quarter 20.00 ≈ half
  20.22 — a tie), **including the large/dense models** (gemma-31B dense 30.05 > full 23.85; Qwen3.5-122B-A10B
  28.30 > full 18.01). With a **private node-local weight copy per instance (`--no-mmap`)** there is no
  shared-cache bandwidth penalty, so the parallelism of 4 quarters dominates across the board.
- **The earlier "dense / large-active prefers 1×full" conclusion was purely the mmap-sharing contamination
  artifact and is RETRACTED.** 1×full now wins only **single-stream LATENCY** (per-instance t/s: full = the
  whole aggregate on one instance; a quarter instance gets aggregate/4).
- **2×half is never the best** — always between quarter and full across all 7 models (still confirms
  `[[project_dual_half_concurrency_negative]]`; quarters or full only, never two halves).

### MTP gains (universal; compounds on dense / low-active)
- MTP helps **every** MTP-capable model. Dense / low-active models gain most at the quarter operating point
  (the verify batch amortizes ONE full weight read over N draft tokens): gemma-31B dense 4×quarter 7.18 → 30.05
  (**+319%**), Qwen3.6-35B Q8 frontdoor 4×quarter 42.11 → 71.89 (**+71%**), gemma-26B worker 4×quarter 73.88 →
  109.61 (**+48%**). Qwen3-Next-80B (SSM-MoE) has no MTP path → base iqk is its max.

### ARCHITECT MTP CONFIRMED LIVE (still holds under the fix)
**Qwen3.5-122B-A10B + MTP** loads and drafts with **NO spec-assertion crash / GDN wall**, end-to-end
(download → load → draft → measure). The prior "no-MTP / GDN-wall / 0.56× dead-end" dismissal is **refuted
end-to-end** (it was measured on an old fork with no `draft-mtp`, stale). Under the FIXED protocol its best
aggregate operating point is **4×quarter+MTP 28.30 t/s** (> full 18.01, > half 26.19) — the architect now
falls in the same "quarter wins aggregate throughput" bucket as the rest of the stack (the earlier
"large-active → 1×full" placement was the contamination artifact).

### Topology rule (FIXED) — short form
- **All models** → **4×quarter (+MTP where available)** wins aggregate throughput with **`--no-mmap`**
  (private node-local copy per instance). Quarter wins outright for 6/7; Qwen3.6-27B quarter≈half.
- **1×full** wins only **single-stream LATENCY** (per-instance t/s), not aggregate throughput.
- **2×half is always worst-or-middle** — never the best (confirms `[[project_dual_half_concurrency_negative]]`).
- Production analogue: **`numa-private-weights-quarter-roles.md`** — wire the ignored `no_mmap` prior into the
  generic `_build_role_command` so `frontdoor` / `ingest_long_context` / `vision_escalation` quarters run the
  fast private `--no-mmap` path that `worker_general` already realizes.

Per-model best-operating-points feed the v6 promotion-plan registry NUMA topology fields
(`/mnt/raid0/llm/tmp/v6_promotion_plan.md`, PG-2 "NUMA topology per role" clause) — now reading
**4×quarter+MTP for all roles** (throughput), 1×full reserved for latency-bound single-stream paths.

### Corrected root cause (CRITICAL — the prior NUMA conclusion was WRONG)
The contaminated first suite used **mmap** with `numactl --cpunodebind=N --membind=N`, so the N concurrent
quarter instances shared **ONE page-cache copy pinned to a single node** → bandwidth-starved; and the full
cells inherited the quarter loads' node-local page placement when run after them in the same matrix.
- **A/B proof (gemma-26B 4×quarter):** **43.5 t/s (shared mmap) → 119.5 t/s (`--no-mmap` private node-local)
  = ~2.7×.** A dedicated-config A/B (both arms clean) read 64–73 t/s — so the launch **params were fine**; the
  bug was **mmap-sharing + cross-cell cache contamination**, not membind or thread settings.
- **The `numactl --membind` hypothesis was already refuted** by an even earlier note (membind vs interleave =
  9.92 vs 10.05, settings A/B 11.73 vs 11.88) — **do not reintroduce it.** membind is neither the cause nor
  the fix; the fix is `--no-mmap` (a private copy per instance) + `drop_caches` between models.
- **FIX = `--no-mmap`** (private node-local weight copy per instance, no shared page cache) **+ `drop_caches`
  between models** (so one model's quarter loads don't contaminate the next model's full cells). With the fix,
  4×quarter wins aggregate throughput for ~all models — including the large/dense ones.
- **Lesson:** the prior "small/low-active→4×quarter, large-dense→1×full" split was an artifact of shared-mmap
  bandwidth starvation under multi-instance load. Absolutes remain **throttle-suspect** (4-week uptime +
  ~12 h sustained bench → cross-model drift); only the **per-model topology / MTP deltas** in the FIXED window
  are load-bearing. Cross-reference: `/mnt/raid0/llm/tmp/orchestrator_numa_finding.md` (per-role mmap audit;
  handed off separately as `numa-private-weights-quarter-roles.md`).

### Suite status — COMPLETE (FIXED)
All 7 `numa_mtp.<model>.jsonl` files written with `--no-mmap` and verified cell-by-cell; the NUMA topology
phase is CLOSED. No models outstanding.

## Key files
- v6 hook: `ggml/src/ggml-cpu/ggml-cpu.c:1245`; blocks: `ggml/src/ggml-common.h:242,281,317`; enum `ggml/include/ggml.h:398`
- ik kernels: `iqk/iqk_mul_mat.cpp:507`, `iqk_gemm_kquants.cpp:2674,2700,2761`, `iqk_gemm_legacy_quants.cpp:2084`, `iqk_quantize.cpp:923,1093`, `iqk_config.h`
- detail memory: `[[project_ik_llama_iqk_kernel_advantage]]`

## Reporting
Update this handoff's checkboxes + progress log after each sub-step. Commit on the `iqk-port` branch. No production push.
