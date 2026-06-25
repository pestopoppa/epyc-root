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

## Key files
- v6 hook: `ggml/src/ggml-cpu/ggml-cpu.c:1245`; blocks: `ggml/src/ggml-common.h:242,281,317`; enum `ggml/include/ggml.h:398`
- ik kernels: `iqk/iqk_mul_mat.cpp:507`, `iqk_gemm_kquants.cpp:2674,2700,2761`, `iqk_gemm_legacy_quants.cpp:2084`, `iqk_quantize.cpp:923,1093`, `iqk_config.h`
- detail memory: `[[project_ik_llama_iqk_kernel_advantage]]`

## Reporting
Update this handoff's checkboxes + progress log after each sub-step. Commit on the `iqk-port` branch. No production push.
