# Run-to-run nondeterminism in 27B DFlash2 (GPU) and Q38FN MTP (CPU) — mechanism and identity-gate protocol

Date: 2026-11-22. Scope: experimental llama.cpp trees (source cited from
`/mnt/raid0/llm/llama.cpp-experimental-dtree-phase-20261122` @ `284a03e2d`). Evidence is the existing row
output only. **No new compute was run for this note**: the mechanism comes from the code and the r2/r3 row
contrast below. The live A/A row is proposed in §4.

Triggers: three false correctness failures on 2026-11-22. They were tree device accept
(`ak-dtree-cuts-gpu-20261122`), q8wv split16 (`ak-q8wv-split16-gpu-20261122-r2`, knob never engaged) and
the Q38FN replay "defect" (`ak-rsreplay-q4x-bisect-cpu-20261122-r3`). Prior work: speculative-decoding.md
DF2-13 / DF2-13-CLASSIFY (warm/cold token-33 divergence), and the farows-inplace r2 note "OFF itself
nondeterministic".

## 1. Mechanism

Greedy speculative decoding is a fixed point. If every kernel were bit-deterministic, the draft, the verify
batch shape and the accepted stream would all repeat exactly. The decode only wanders when some input
outside the token stream perturbs the logits by a few ulps **and** a near-tie sits on the path. After that,
spec decode amplifies the flip: a flipped token changes the draft and the verify batch width, so later
kernels take different tile paths, and the stream never re-converges. There are two independent
perturbation sources.

### 1a. GPU, 27B DF2: float atomics in the Q8_MF V5 small-M matmul (proven nondeterministic in code)

- `ggml/src/ggml-cuda/mmq-q8-mf.cu:1303-1313` (V5, `GGML_HIP_Q8_MF=6`) states it directly: "a split
  [half-tile] is added with global_atomic_add_f32 into dst, which the pre-pass zeroes".
- The add is at `mmq-q8-mf.cu:1432` (`unsafeAtomicAdd(o, v)` for non-`full` half-tiles). The dst zeroing
  is at `:191`.
- Float addition is not associative, and the arrival order of the 2+ workgroups that share a boundary
  half-tile depends on scheduling. Every split output therefore carries ulp-level run-to-run noise.
- `GGML_HIP_Q8_MF_MIN=1` routes even n=1 decode and every verify width ≤16 through V5, so the drafter and
  target see this noise on every layer.
- Contrast: V2/V3 reduce stream-K partials in fixed workgroup order (`mmq-q8-mf.cu:566`, comment "WG
  order: deterministic"). wvsk is deterministic by construction (`mmq-q8-wvsk.cu:8-16`).
- Evidence: every `ak-dtree-cuts` arm sets `GGML_HIP_Q8_MF=6, MF_MIN=1`. The pure A/A pair `L2==L@1` (same
  env) failed on prompt 1 in 2 of 3 blocks. The prompt-0 position-224 flip (token 4016 vs 369) shows up in
  OFF arms too. A/A identity across all 21 pair×block cells: 13/21 equal, with no env-dependence.

**Secondary GPU source (arms without MF, such as q8wv r2).** ggml never calls `rocblas_set_atomics_mode`.
The handle is created at `ggml/src/ggml-cuda/common.cuh:1529`, and the GEMMs at
`ggml/src/ggml-cuda/ggml-cuda.cu:1724/1739` run under rocBLAS's default `rocblas_atomics_allowed`. In that
mode Tensile may pick global-split-U kernels that accumulate with atomics, for example for f16/bf16
drafter weights or for batch widths above the MMVQ/MMQ range. This source is *suspected*, not proven. The
row in §4 isolates it.

### 1b. CPU, Q38FN MTP: history-dependent KV-cell layout after concurrent speculative rollback

- On CPU at fixed threads, ggml-cpu matmul work-stealing (`ggml-cpu.c:620/754`, `current_chunk`) assigns
  whole output chunks to a thread, so per-element sums do not depend on which thread computes them.
  Kernel atomics are not the CPU source.
- The source is the state the request inherits. In r3, phase S (sequential, `cache_prompt=false`) runs
  after phase C: 12 prompts in **concurrent** batches of 4 on np4. Phase-C batch composition depends on
  HTTP arrival timing, and with MTP n-max 4 the per-slot draft and rollback (`seq_rm`) depths vary too.
  Phase C therefore leaves a timing-dependent pattern of holes in the unified KV cache.
- `llama_kv_cache::find_slot` (`src/llama-kv-cache.cpp:916`) places phase-S cells into those holes.
  `get_n_kv` (`:1322`) pads to `used_max_p1`. Attention for the same logical sequence then runs over a
  different physical cell order, a different masked-cell interleave and a different `n_kv`. That changes
  the FA/softmax accumulation order and chunking: ulp noise, then a near-tie flip.
- Evidence (contrast within the same build and store, `45a8173e4`):
  - r2 used a fresh server and one request per server. It was **NOT_REPRODUCED on all 4 configs**.
  - r3 used reused slots after the concurrent phase. plain np4 and mtp1 np4 were CLEAN (no or fixed-depth
    rollback). mtp4 np4 was AA_NOISY: OFF2 and ON both diverge from OFF at the same tokens (prompt 1 tok
    65, prompt 3 tok 75) in both rounds.
  - Two discrete outcomes recurring at the same positions is the signature of a near-tie, not of a defect.
    mtp4np1 (serialized phase C) was clean in round 1, with a single ON-only flip in round 2 (tok 110 / 75)
    that the same near-tie positions explain.

Logit margins at the divergence points were **not** captured. The dtree oracle samples every 32 tokens
(`margin` is 0.0 where it is not recorded), and r3 logs no logprobs. The near-tie claim rests on the
bistable same-position pattern and still needs the margin capture in §4.

## 2. Inherent or fixable

Both sources are fixable. Neither one is an inherent property of greedy decoding.

| Source | Fix (behind `GGML_DETERMINISTIC=1`, default off) | Estimated cost |
|---|---|---|
| Q8_MF V5 atomic tail | Write split half-tile partials to scratch and reduce in fixed WG order (the V3 path), or fall back to V3 (MF=3) | V2/V3 boundary-drain cost was measured at ~5-8% of the op (`mmq-q8-mf.cu:64-65`). Q8 matmul is most of decode, so expect ~3-5% e2e on 27B DF2. V3 fallback = the measured V3→V5 gap. |
| rocBLAS atomics | `rocblas_set_atomics_mode(h, rocblas_atomics_not_allowed)` after `cublasCreate` | Usually <2% on these shapes. Only non-quantized GEMMs are affected. |
| CPU KV layout | Gates only: fresh server or `seq_rm` + defrag per request in identity phases. Production serving does not need bit-reproducibility. | 0 (gate-side) |

Even with all three fixes, an A/B arm that legitimately changes kernel paths (a new verify width, a new
tile) can flip a near-tie. Deterministic mode makes **A/A** exact. It cannot make **A/B** byte-identical.
The identity gate has to be statistical for A/B either way.

## 3. Identity-gate protocol (replaces single-sample `OFF2 == OFF`)

1. **State control.** Each identity request runs on a fresh server, or a fresh slot with `cache_prompt=false`
   and no preceding concurrent phase. Concurrency phases are reported for information and never gate.
2. **A/A floor in the same row.** Run arms OFF×R and ON×R (R≥3) over N≥8 prompts × 256 tokens, interleaved.
   Record the per-request first-divergence index and the **top-2 logprob margin** there (`n_probs: 2` on
   the replay request at the divergence index).
3. **Classify each divergence.** *Tie* = top-2 margin at first divergence ≤ τ (τ = 0.05 nat, or ≤ 2× the
   largest A/A margin seen in the row). *Defect* = margin > τ, or garbage or degeneration (repeat-loop,
   invalid UTF-8) after divergence.
4. **Decision.** PASS iff (a) zero *defect* divergences in ON, and (b) the ON-vs-OFF divergence rate (per
   request) ≤ the A/A rate + a Wilson 95% one-sided bound at that N·R. FAIL_CORRECTNESS needs ≥1 *defect*
   divergence, or a rate excess beyond the bound in **two** rounds. Anything else is NOISY_PASS (report the
   rates).
5. **Knob witness first.** No identity verdict unless the knob's engagement witness fired (q8wv r2 had
   `split16_witness=false` on the e2e arms). A null witness is MISSING_INPUT, not FAIL.
6. When `GGML_DETERMINISTIC=1` lands, A/A must be 0/N·R. A nonzero A/A count under it is itself a defect.

## 4. Q38FN replay allowlist exclusion (`6a6868547`)

The exclusion's premise ("ON != OFF on 2/4 while OFF2 == OFF", R4) was a single-sample A/A on reused slots.
r3 reproduced the same divergence **in OFF2**, so the defect is not attributable to replay. Do not lift the
exclusion on that alone: r3 still has one ON-only flip (mtp4np1 r2), and no margin evidence exists.

**Lift row** — `ak-rsreplay-q4x-lift-cpu-<date>`:
- Build: store `cpu-20261121-45a8173e4-rs-replay`, or a revert of `6a6868547` on current champion.
- Workload: Q38FN, mtp4, np1 **and** np4, fresh server per arm.
- Arms: OFF×3 and ON×3 (`LLAMA_RS_REPLAY=1`), interleaved.
- Prompts: 8 × 256 tokens with top-2 margin capture at divergence. 24 threads, q0-q2.
- Decision: §3. Lift iff PASS on both np configs.
- Estimate: ~6 server launches × 8 req × 256 tok. At measured Q38FN CPU rates this is ≈ 1.5-2 h. Book that
  plus 25%.
