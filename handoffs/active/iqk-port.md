# iqk-kernel port into v6 (ik_llama iqk_mul_mat → production-consolidated-v6)

**Status**: IN PROGRESS (started 2026-06-25). Operator greenlit full port (both stages) "proceed systematically … do not stop until done and verified no quality regression + performance increase."
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

### Stage 2 — MoE mul_mat_id (NOT started; where the stack prize is)
- [ ] Correctness: unit round-trip quantize_row_q8_2_x4; single Q4_K·F32 + Q8_0·F32 mul_mat cosine-sim/max-abs-err vs v6 reference (flag OFF) ; gemma-31B dense Q4_K_M coherent decode (chat template) flag ON vs OFF.
- [ ] Perf: canonical llama-bench dense (gemma-31B Q4_K_M) flag ON vs OFF — confirm uplift toward ik's +15-64%.
### Stage 2 — MoE mul_mat_id + Q5_K/Q6_K (+3-5d)
- [ ] Vendor/enable mul_mat_id path (iqk MoE) + hook into ggml_compute_forward_mul_mat_id.
- [ ] Enable Q5_K/Q6_K routes.
- [ ] Correctness: gemma-26B-A4B + Qwen3.6-35B MoE coherent (chat) flag ON vs OFF; eval-suite parity (operator-run).
- [ ] Perf: canonical llama-bench MoE (gemma-26B, Qwen3.6-35B Q8) flag ON vs OFF.
### Verification (operator bar: no quality regression + perf increase)
- [ ] cosine-sim/max-abs-err vs F32 ref within tol on all touched quants.
- [ ] decode + prefill llama-bench uplift ON vs OFF (toward the ik deltas above).
- [ ] eval-suite parity flag ON vs OFF (operator-run; flag for them).

## Key files
- v6 hook: `ggml/src/ggml-cpu/ggml-cpu.c:1245`; blocks: `ggml/src/ggml-common.h:242,281,317`; enum `ggml/include/ggml.h:398`
- ik kernels: `iqk/iqk_mul_mat.cpp:507`, `iqk_gemm_kquants.cpp:2674,2700,2761`, `iqk_gemm_legacy_quants.cpp:2084`, `iqk_quantize.cpp:923,1093`, `iqk_config.h`
- detail memory: `[[project_ik_llama_iqk_kernel_advantage]]`

## Reporting
Update this handoff's checkboxes + progress log after each sub-step. Commit on the `iqk-port` branch. No production push.
