# Champion consolidation audit — the 31 `fork/rescued-*` refs (2026-09-08)

**Status**: read-only audit, complete · executed by subagent for `ak-rebuild-20260828` · lane
`lane/ak-rebuild-20260828` · scope: what of the rescued kernel work is NOT in the champion and must be
folded before any further research runs.

## The operator directive this audit serves (2026-09-08, verbatim)

> "I want no more pure kernel inference research until we have a FULLY consolidated champion collecting
> all GPU AND CPU performance progress."

> "WE CANNOT AFFORD to lose performance progress on either the GPU or the CPU inference work. WE MUST
> FOCUS on consolidating all kept performance levers and persisting them."

The CPU session (INF-70 / `workspace-1c`) received the same directive directly and has parked all lever
campaigns. **No research relaunch after the fold window; consolidation only; relaunch is a separate
operator go.**

## Method (and why the obvious method would have lied)

The 31 `fork/rescued-*` refs were pushed by INF-70 from the swept scratch tree
`/mnt/raid0/llm/tmp/ak-loop-tree`. Classification was done by **`git cherry` PLUS a content grep** against
the champion `ak/champion/llama-cpp-0db32c06e3e5` at tip `bff30cebe`.

Patch-id equivalence alone is not sound here: **v9 was rebuilt from fresh upstream**, so a lever that is
semantically present in the champion has a different patch-id than the rescued commit that first
introduced it. `git cherry` reports such a commit as unmerged. Every "SUPERSEDED" verdict below therefore
rests on the *content* of the champion tree, not on patch-id arithmetic.

The same asymmetry runs the other way and is the sharper hazard: **folding a superseded decision back in
is a failure class ancestry checks cannot see and cherry-equivalence waves through** (INF-70's framing of
the must-not-fold finding in §C).

Fold candidate under evaluation: `inf70/fold-candidate-20260908` @ `ef81196d5` (base `bff30cebe`; contains
the champion plus `inf70/champion3` @ `9c4f73e29` plus `445e93a8`; **0 deletions**).

## Classification of all 31 rescued refs

### A. SUPERSEDED / ARCHIVE — 22 refs, nothing to fold

| ref | tip | class | evidence |
|---|---|---|---|
| `rescued-feature-dflash*` (DFlash family) | — | SUPERSEDED | live in champion, 22 files match |
| `rescued-feature-tree-spec*` / DySpec | — | SUPERSEDED | tree-spec/DySpec paths present in champion |
| `rescued-feature-mtp*` (MTP family) | — | SUPERSEDED | MTP live in champion, 20 files match |
| `rescued-port-qwen36*` | — | SUPERSEDED | patch-equivalent to champion content |
| `rescued-port-qwen4exp*` | — | SUPERSEDED | patch-equivalent to champion content |
| `rescued-anchor-v5` | — | ARCHIVE | historical anchor |
| `rescued-anchor-v6` | — | ARCHIVE | historical anchor |
| `rescued-anchor-v3` | — | ARCHIVE | historical anchor |
| `rescued-cpu-ep-intra-process` | — | ARCHIVE | self-documented NEGATIVE result |
| `rescued-cpu-ep-inter-process` | — | ARCHIVE | self-documented NEGATIVE result |
| `rescued-feature-lightning-attention` | — | ARCHIVE | model enablement only; no fleet model uses it |
| `rescued-feature-longcat` | — | ARCHIVE | model enablement only; no fleet model uses it |
| `rescued-feature-paged-attention` | — | ARCHIVE | dropped BY DESIGN in the v6→v9 rebuild; now durable on the fork |
| `rescued-feature-layer-skip-tide` | — | ARCHIVE | dropped BY DESIGN in the v6→v9 rebuild; now durable on the fork |
| `rescued-feature-freeze-recurrent-hsd` | — | ARCHIVE | dropped BY DESIGN in the v6→v9 rebuild; now durable on the fork |
| `rescued-feature-corpus-sidecar` | — | ARCHIVE | dropped BY DESIGN in the v6→v9 rebuild; now durable on the fork |
| `rescued-experimental-v9-ak-t1-hardening` | — | SUPERSEDED | present in champion |
| `ak/admission/remove-funsafe-math-20260831` | `3161d2dcf` | SUPERSEDED | patch-equivalent to `b861c32fa` (2026-08-31, "ggml-hip: remove -funsafe-math-optimizations (upstream parity, CH-7 admission)", 1 deletion in `ggml/src/ggml-hip/CMakeLists.txt`), an ancestor of BOTH the champion and the fold candidate; `git cherry` marks it `-`; `git grep funsafe-math` on the champion returns nothing |
| (remaining refs of the DFlash / tree-spec / MTP / port families) | — | SUPERSEDED | grouped evidence above |

Grouped evidence, restated so the table rows are not the only record: the DFlash lever set is live in the
champion across 22 files; the MTP lever set across 20 files; tree-spec/DySpec and the qwen36/qwen4exp
ports are patch-equivalent to champion content; the v3/v5/v6 anchors and the two `cpu-ep` branches are
history and self-documented negatives respectively; lightning-attention and LongCat are model enablement
with no fleet model behind them; the four by-design drops (paged attention, layer-skip TIDE,
freeze-recurrent HSD, corpus sidecar) were removed deliberately in the v6→v9 rebuild and are now durable
on the fork.

### B. CANDIDATES — unapplied performance work

**1. `rescued-ak-g15-chunked-gdn-20260823` @ `719a8529d` — the largest unrecovered GPU lever.**
Chunked GDN kernel; a port of upstream PR #24561 (unified MMA). Files:
`ggml/src/ggml-cuda/gated_delta_net.cu` **+527**, `tests/test-backend-ops.cpp` **+34**. The champion still
carries the source comment `//TODO: Add chunked kernel for even faster pre-fill`. Surface: **GPU PREFILL**
on GDN models (qwen35, qwen35moe, qwen3next).

**2. `rescued-ak-discovery-7e8da8ea-attempt1` @ `9f85ba2fb` — small GPU quantize lever.**
`ggml/src/ggml-cuda/quantize.cu` **+4/−1**: reciprocal-multiply plus a `__shfl_sync` broadcast replacing
the per-lane `roundf(xi/d)`. The champion still computes `roundf(xi / d)`.

**3. Four Q5_0 `vecdotq.cuh` variants** — `f9d74a2a3`, `d4b0a04e4`, `580e8d090`, `5d22a5463`.
Low value: Q5_0 is not a production quant, and the work is re-derivable. Recommendation: **decline**
unless a Q5_0 target appears.

### B2. REFUTED — do not fold

**A measured refutation is not a keep, and re-measuring a refuted lever is new research (stopped by the
operator).** Both items below were classified as candidates on first pass (absent from the champion, so
`git cherry` and content grep both call them unapplied) and were corrected from the record by INF-70 on
2026-09-08. Absence from the champion is exactly what a refuted lever looks like.

**`rescued-inf10-gemv-fusion` @ `ea8ca0609` — MEASURED AND REFUTED 2026-08-27.**
Default-OFF, env-gated fusion (`GGML_GEMV_FUSION_GATE_UP`, `GGML_GEMV_FUSION_QKV`; helpers
`add_fused_tensor`, `build_fused_tensor_data`); `src/llama-model.cpp` +120, `src/llama-model.h` +28,
`src/models/qwen35moe.cpp` +174/−45. Result at tg128, region-locked q0-q3, canonical env, 5×4 rotated:
**gate+up fusion −2.11%, QKV fusion +0.25%, both −0.57%** (verified window **−1.33%**). Correctness clean
(PPL 5.5410 identical across 4/4 arms). Mechanism: removing ~50 of ~590 barriers/token does not move
tg128 wall-clock; the +2.6% precedent was the DeltaNet native-fused `wqkv` cluster, a *different*
mechanism. Both boxes closed `[x]` in `handoffs/active/cpu-shape-specialized-gemv-decode.md`; evidence
`epyc-inference-research/data/gemv-fusion-2026-08-25/` with `SHA256SUMS`. Handoff conclusion: *"No further
barrier-fusion work is justified on this target."*

**`rescued-cpu-opt-q8-8x8-avx512bw` @ `1f8868307` + `af6701d00` — CLOSED appendix.**
AVX-512BW 8x8 Q8_0 GEMV (`ggml_gemv_q8_0_8x8_q8_0_generic`, `ggml_gemm_q8_0_8x8…`; `repack.cpp` +177) plus
a NUMA-interleaved CPU_REPACK buffer. The SIMD ukernel plan on that branch is an **explicitly CLOSED
appendix** (the 8×8 GEMM body is E3-gated, owned by `batched-decode-measurement.md`). The one measured
angle on the branch, `0467a5c17` (RMS_NORM intra-op parallel reduction), was **−8.8%** (4.41 → 4.02 t/s at
96t, Qwen3.6-27B Q8_0) and is kept env-gated `GGML_RMS_NORM_PARALLEL=1`, default OFF, as scaffolding.
Verdict on the axis: the 22% in `ggml_barrier` is barrier-**COUNT**-bound, and the Q8 axis closed with
*"the 4.4 t/s ceiling is genuinely architecture-bound."* Ignore the branch's other 56 commits (reverts and
negatives).

### C. MUST NOT FOLD — 1 commit

> **`rescued-feature-tree-draft-v6` commit `de447119f`** — "route Q8_0 `ne11<=1` MTP-verify to MMQ, +17.4%".

The champion's `mmvq.cu` carries the **LATER, contradicting** decision `akm-cdna2-q8-b4-mmvq-route`: Q8_0
`ne11<=4` through MMVQ, `ne11>=5` on MMQ — "the July crossover". The reversal is documented in-source.
**Folding `de447119f` would REGRESS the champion.**

The *other* GPU commits on that same branch are already in the champion and need no action: nwarps=4,
async prefetch, GDN bf16 +21.5%, and `GGML_CUDA_GDN_STATE_BF16` across 9 files.

### D. SINGLE-COPY REFS found in `/mnt/raid0/llm/llama.cpp` itself

INF-70's sweep covered only the scratch tree, so these existed in exactly one place. **All four were
pushed to the fork 2026-09-08 by `ak-rebuild-20260828`.**

| ref | tip | note |
|---|---|---|
| `ak/orphan-keeps-quantize-20260829` | (tag) | now on the fork |
| `ak/pre-anchor-fix-full-history` | `b04fad244` | history preservation |
| `ak/run14-01893a36-cumulative` | `01893a36c` | `akm-q4k-q8-sum-sidecar` +6.723%; the champion holds the NEWER `sum_lane` form of the same idea — **likely banked, not patch-equivalent** |
| `ak/admission/remove-funsafe-math-20260831` | `3161d2dcf` | pushed for durability, but **NOT an outstanding lever**: classified SUPERSEDED in §A — see the correction note below |

**Correction (2026-09-08, caught by the operator).** The audit's first pass asserted that "the champion STILL carries
`-funsafe-math-optimizations`" and filed `3161d2dcf` as an operator decision. **That was wrong.** Verified in the tree:
`git grep funsafe-math` on the champion returns nothing; `b861c32fa` (2026-08-31, "ggml-hip: remove
-funsafe-math-optimizations (upstream parity, CH-7 admission)", 1 deletion in `ggml/src/ggml-hip/CMakeLists.txt`) is an
ancestor of **both** the champion and the fold candidate, and `git cherry` marks `3161d2dcf` as already applied (`-`).
The decision was taken on 2026-08-31 under CH-7 and needs no re-litigation. Pushing the ref to the fork was still
correct (single-copy durability); folding it is a no-op.

Additionally, `ak/pre-reconcile-loop-20260831` and `ak/pre-reconcile-manual-20260831` are **fully contained
in the champion** and in the fold candidate.

## Could not determine (open questions, not blockers)

1. **8x8 vs 16x1 GEMV** — no measurement exists in the commits either way (the axis is closed regardless,
   see §B2).
2. **Acceptance verdicts of the `ak-discovery` attempts** — the records lived in the deleted scratch tree.
3. **Whether each of the ~8 by-design drops has a ratification artifact.**

## Consequences filed

Phase-2 tasks, one per surviving candidate with its own gate, are in
[`handoffs/active/autokernel-unified-surface-program.md`](../../handoffs/active/autokernel-unified-surface-program.md)
§4 P1b, together with the funsafe-math admission decision, the REFUTED list and the MUST-NOT-FOLD warning.
