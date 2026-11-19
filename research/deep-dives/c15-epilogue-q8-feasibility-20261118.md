# C15-EPI-Q8 feasibility: producers write q8_1 in their epilogue (2026-11-18)

**Question.** Can the kernels that produce MMVQ inputs write q8_1 directly, so the standalone `quantize_q8_1` launches
disappear from MI210 27B Q8_0 decode, and is the saving at least 1.5% of decode?
**Inputs.** INF48-GATEUP-PROBE (`research/deep-dives/inf48-gateup-probe-20261118.md`): all `quantize_q8_1` together are
3.56% of decode GPU busy time, at about 4.5 us per launch. C15-MMVQ-FUSED-Q8 (`research/deep-dives/c15-mmvq-fused-q8-feasibility-20261118.md`)
rejected folding the quantize into MMVQ.
**Source read.** C14 `eee3da838` in `/mnt/raid0/llm/llama.cpp-experimental`. Read only, through `git show` / `git grep`.

## (1) Which producers feed the ~4 quantizes per layer

3.56% of 1052 ms over 32 tokens is about 37.5 ms. At 4.5 us per launch that is about 8300 launches, or 260 per token, or
4.06 per layer over 64 layers. The `mmvq_q8_1_graph_cache` (mmvq.cu, `ggml_cuda_mul_mat_vec_q`, on by default under HIP
graphs for Q4_K/Q6_K/Q8_0 with ncols=1) already dedups every later MMVQ that reads the same `src1`. So each launch that
remains is the first MMVQ consumer of one distinct activation. From `src/models/qwen35.cpp`:

| # | Activation | Producer node(s) | Current fusion path at C14 | Can it write q8_1? |
|---|---|---|---|---|
| 1 | attention / GDN input (`attn_norm`, 5120) | `RMS_NORM` → `MUL(w)` | `{RMS_NORM, MUL}` → `ggml_cuda_op_rms_norm_fused`, `rms_norm_f32<1024,true>` | yes |
| 2 | attention output before `wo` / `ssm_out` (6144) | GDN (48 layers): `build_norm_gated` = `RMS_NORM`, `MUL(ssm_norm)`, `SILU(z)`, `MUL`. Full attention (16 layers): FA → `SIGMOID(gate)` → `MUL` | `{UNARY, MUL}` → `ggml_cuda_op_unary_mul` (SILU / SIGMOID), `unary_gated_op_kernel`. The consumer reads it through a reshape | yes |
| 3 | FFN input (`attn_post_norm`, 5120) | `RMS_NORM` → `MUL(w)` | same as #1 | yes |
| 4 | FFN-down input (17408) | gate+up MMVQ with the GLU fused in (`ggml_cuda_mm_fusion_args`, INF48) | output rows are spread across many MMVQ workgroups, so no workgroup owns a 32-wide q8_1 block's amax | **no**, not without a cross-workgroup reduction |

Upstream-style fusions present: `{RMS_NORM, MUL[, ADD]}`, `{UNARY, MUL}` (SILU/SIGMOID/SOFTPLUS), fused gate/up+GLU MMVQ,
and the q8_1 graph cache (dd161d519, c0d42d81c, 61bdb185c). None of them emits q8_1.

## (2) Is the f32 output still needed?

The f32 output must stay. Kernel-correct designs therefore write q8_1 **beside** the f32, never instead of it:
- `attn_norm` also feeds `ssm_beta`/`ssm_alpha` (their weight types are not guaranteed to be q8_0) and any non-MMVQ path.
- `ffn_residual` is the residual-add output, not the norm output. The norm output itself has only the gate/up consumer.
  Even so, the f32 write is the graph's contract, and dropping it would need allocator-level liveness.
- Writing f32 too costs 20-24 KB of stores in an already latency-bound kernel, which is noise.

## (3) Realistic saving

- Removable: #1, #2 and #3, which is 3 × 64 = 192 of about 260 launches per token. That is ≈ 3/4 × 3.56% ≈ **2.6% upper
  bound**. If the full-attention `SIGMOID·MUL` does not fuse at run time, only the 48 GDN layers count for #2, giving ≈2.3%.
- Epilogue cost: per element, two 5-step 32-lane reductions (amax, sum), one divide and one byte store, plus one `half2`
  per 32 elements. In the single-workgroup 1024-thread rms_norm (5 elements per thread) that adds ≈0.2-0.4 us. In the
  grid-wide unary_mul it is ≈0.1-0.2 us. HIP graphs hide the dispatch gaps, so INF48 measured 0 us idle before MMVQ.
  The saving is therefore the quantize kernel's own busy time, ≈4.5 us each.
- **Net estimate ≈ 1.6-2.4% of decode**, above the 1.5% implementation bar. The row's KEEP bar is 1.01.

## (4) Invasiveness

The change is bounded at 323 lines, tests included, across 9 files. It reuses the existing cache, so MMVQ is untouched:
- `mmvq.cu`: `ggml_cuda_mmvq_q8_1_graph_cache_reserve(ctx, consumer_src1)` pre-registers the cache entry that the MMVQ
  would create (same capture-id reset, same match key, `q4k_isum=false`) and returns its arena buffer. It returns nullptr
  outside an active capture, on another stream, for ne0 % 512 != 0, or when an entry already exists.
- `ggml-cuda.cu`: in `ggml_cuda_try_fuse`, the `{RMS_NORM, MUL}` and `{UNARY, MUL}` branches find the first later
  `MUL_MAT` (within 64 nodes) whose `src1` is the producer or a zero-offset RESHAPE/VIEW chain of it, with a Q8_0/Q6_K
  `src0`. They reserve the entry and pass the buffer to the producer. Knob `GGML_HIP_EPILOGUE_Q8=1`, default off. A one-time
  WARN line `GGML_HIP_EPILOGUE_Q8 engaged` serves as the engagement proof.
- `norm.cu`: `rms_norm_mul_q8_1_f32<1024>`, a single-row copy of the generic `<1024, true>` path plus the epilogue.
  `unary.cu`: `unary_gated_op_q8_1_kernel`. Shared helper `epilogue-q8.cuh` with the same `d = amax/127`,
  `q = roundf(x/d)` math as `quantize_q8_1_1d<false>`, so `d` and `qs` are bit-identical. Only `ds.y` (the float sum)
  may differ in reduction order, and q8_0/q6_K MMVQ do not read it.
- Q4_K consumers are excluded because their isum layout needs a different `ds.y`. The FFN-down input (#4) is out of scope.
- tests: `[C15-EPI-Q8]`, 14 whole-graph cases (norm→Q8_0/Q6_K MUL_MAT with a second f32 consumer, and SILU/SIGMOID gated
  →reshape→MUL_MAT; widths 1024/1536/5120/6144) appended last and tagged `c15_epi_q8`. The epilogue engages only under
  graph capture, so a pass is necessary, not sufficient. The served A/B carries the identity proof.

## (5) Upstream

Nothing comparable. The C14 history has no producer-side q8_1 write (`git log -i --grep=quantiz` filtered for
fuse/norm/epilogue, and a `norm|glu` × `q8_1|quantiz` regex). The only hits are the CPU INF-64 and AK-ASM-H14/H15 fusions, which do not
quantize. Upstream CUDA hides quantize latency with PDL, which is CUDA-only.

## Decision

**IMPLEMENTED, unmeasured.** Branch `llama.cpp-experimental-c15-epi-q8-20261118` on `fork`: `7b0314f3b` (feature +
tests) and `e0b5d2637` (engaged log line), on top of C14 `eee3da838`. Nothing was compiled or run locally.
Prepared, **unpublished** row `/mnt/raid0/llm/tmp/c15-epi-q8-gpu-20261118` (READY-TO-PUBLISH). It does an in-row HIP
build, runs tbo `-o C15_EPILOGUE_Q8` with the knob off and on (parsed by `rowlib/tbo_parse.py`), then 6 A-B-B-A pairs of
27B Q8_0 single-slot decode. Pre-registered: KEEP iff decode geomean A/B ≥ 1.01, ≥ 4 valid pairs, the engaged line in
every B visit and in no A visit, and AA-calibrated mean-based greedy identity. Futility: geomean < 1.003 after 4 pairs.
Open risks the row resolves:
- whether the full-attention `SIGMOID·MUL` fuses at run time (if it does not, about 0.3% is lost);
- whether MMVQ is the consumer path for every Q8_0 projection at ne11=1.
