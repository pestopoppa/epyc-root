# Gemma-Challenge Kernel Techniques → v7-Experimental Candidates

**Status**: active — onegraph structural check ✅ + HIP graph infra verified ✅ (2026-07-11). Scope: lossless only (numerical-exact allowed). Next: MI210 smoke-test + benchmark.
**Categories**: speculative_decoding, hardware_optimization, quantization, local_inference
**Source**: intake-798 — "The Gemma Challenge and the Case for Agent Collabs" (HF + Google DeepMind)
**Related**: [`speculative-decoding-mtp-refresh.md`](speculative-decoding-mtp-refresh.md) (onegraph deep-dive lives here), [`gpu-drafter-mi200-investigation.md`](gpu-drafter-mi200-investigation.md) (GPU-graph home), [`v6-iqk-promotion.md`](v6-iqk-promotion.md) / [`kernel-reconciliation-audit.md`](kernel-reconciliation-audit.md) (the v7 workflow), [`gemma4-mtp-drafter-evaluation.md`](../completed/gemma4-mtp-drafter-evaluation.md)

## Objective

The Gemma Challenge (100+ agents, 6 days) drove `google/gemma-4-E4B-it` inference 5× — the **same MTP-drafter family and model family as our production `worker_general`** (gemma-4-26B-A4B, Google official assistant head). **v7 was never promoted to production**, so the `llama.cpp-experimental` line is a clean slot to fold the *validated, quality-preserving* subset of these techniques into a v7 candidate — via the mandated four-step experimental workflow (fresh-pull production → build → validate-no-regression → promote), never touching frozen production kernels.

## Governance rails (non-negotiable, per CLAUDE.md)

- **Production kernels are FROZEN.** All work on `llama.cpp-experimental` (fresh-pulled from current production tip first, so the iqk AVX-512 GEMM + CPU forward-ports are already present — do not repeat the 2026-06-22 GPU-opts fork that silently lacked the entire iqk subsystem).
- **Quality gate is the gate, not TPS.** The challenge's own lesson: a **PPL-only** gate was gamed (top lossy submission held PPL but lost **15 GPQA-Diamond / 40 MMLU-Pro** points). Any v7 candidate must pass downstream evals (MMLU-Pro + GPQA-Diamond), production sampling (seed 42), per [`MEASUREMENT.md`](../../MEASUREMENT.md) + eval-tower — **not** PPL alone. This is a hard prerequisite, especially for the lossy techniques below.
- **Inference is operator-gated** (`feedback_no_concurrent_inference`); bench only via codified recipes with approval.

## Technique candidates (from intake-798 submissions)

| Technique | Lossy? | Our-regime fit | v7 workflow slot | Open question |
|---|---|---|---|---|
| **`onegraph`** — drafter is Q-only, KV-shared, no cross-position deps ⇒ multi-position warm-up is redundant; fold warm-up into the 7-step drafting loop, record as ONE GPU graph, single-launch replay | **Lossless** (no output change) — fastest lossless: 315 TPS | GPU-drafter path (MI210/HIP graphs) directly; **structural insight may port to CPU** MTP drafter loop | GPU-graph capture → `gpu-drafter-mi200-investigation.md`; CPU-warm-up-redundancy → `speculative-decoding-mtp-refresh.md` | **✅ STRUCTURAL + HIP INFRA ✅ (2026-07-11)**: P1-P3 satisfied. HIP graph capture already implemented (vendor-agnostic, `GGML_HIP_GRAPHS=ON` default, CDNA2 >> AMPERE arch gate). Draft loop at `speculative.cpp:1663-1667` is structurally uniform — graph-capturable. **Remaining: smoke-test + benchmark on MI210.** |
| **Task-targeted fine-tuned drafter** — drafter fine-tuned on the eval's math/science prompt distribution to raise acceptance rate α | Lossy **as executed** (overfit to eval set); the *method* (raise α on our real workload) can be lossless | CPU + GPU spec-dec; raises α for both | Drafter-training track (new); gate via rescue-rate on real task corpus | Can we lift α on our real frontdoor/worker workload without overfitting? (`feedback_measure_alpha_before_specdec_investment` — measure α first; `frontier-f1-real-task-corpus.md` for the distribution) |
| **CUDA-graph capture throughout decode** — capture the decode routine as a replayable graph to cut per-step launch/bookkeeping overhead | Lossless (kernel-level) | GPU only (HIP graph equivalent on MI210) | `gpu-drafter-mi200-investigation.md` / `gpu-acceleration-path.md` | **✅ HIP GRAPH INFRA PRESENT (2026-07-11)**: vendor-agnostic, complete API mapping. Overlaps with `onegraph` — same infrastructure. **Remaining: benchmark decode + MTP paths on MI210.** |
| **Vocabulary pruning** — drop rarely-used vocab rows to shrink the output projection / embedding | **Lossy** (contributed to the 15/40-pt degradation) | Applies to any regime, but degrades downstream | Explore-only, hard-gated on MMLU-Pro/GPQA | Is there a *lossless* vocab-prune band (truly-dead tokens only) that survives the downstream gate? High risk. |
| **Layer removal / depth pruning** | **Lossy** (part of the 491.8-TPS lossy stack) | Any regime, degrades quality | Explore-only, hard-gated; likely reject | Almost certainly fails our quality gate; document as a cautionary boundary, low priority. |

## Prioritization (proposed, operator to confirm)

**Scope: lossless only.** Numerical-exactness is acceptable where bit-exactness is not achievable (per past-session precedent). Lossy techniques (vocab prune, layer removal) are OUT OF SCOPE.

1. **`onegraph` GPU-graph capture** (lossless, highest value): **structural check ✅ + HIP infrastructure ✅ (2026-07-11)**. All 3 preconditions satisfied. HIP graph capture is already implemented (vendor-agnostic, `GGML_HIP_GRAPHS=ON` default, MI210 arch gate passes). **Next: smoke-test + benchmark on MI210** — verify graph capture works with MTP draft loop, measure per-token graph launch latency vs. direct dispatch. Coordinate with `gpu-drafter-mi200-investigation.md`.
2. **Drafter-α uplift** (potentially lossless): measure current α on the real task corpus before any fine-tuning investment; only pursue if α headroom is real and generalizes beyond the eval set.

## Tasks

- [x] **K1 — `onegraph` precondition check**: verify the Q-only / KV-shared / no-cross-position preconditions hold for our gemma-4-26B-A4B assistant-head drafter ✅ 2026-07-11 — all 3 satisfied
- [ ] **K2 — HIP graph smoke-test on MI210**: build v7-candidate with `GGML_HIP_GRAPHS=ON`, verify graph capture works with MTP draft loop on MI210; measure per-token graph launch latency vs. direct dispatch. No port needed — infrastructure is already present.
- [ ] **K3 — CPU warm-up-redundancy test**: separately test whether removing the redundant drafter warm-up helps the CPU MTP worker (structural insight may port even without GPU graphs)
- [ ] **K4 — drafter-α baseline**: measure current acceptance α on the real task corpus ([`frontier-f1-real-task-corpus.md`](frontier-f1-real-task-corpus.md)) BEFORE any fine-tuned-drafter investment (`feedback_measure_alpha_before_specdec_investment`)
- [ ] **K5 — quality-gate wiring**: confirm any v7 candidate is gated on MMLU-Pro + GPQA-Diamond (production sampling, seed 42), NOT PPL alone — the challenge's PPL-only gate was gamed for 15/40-pt loss

## GPU Graph Capture Feasibility (2026-07-11)

**Verdict: ALREADY SUPPORTED** — no port needed. The `experimental-v7-candidate` branch has a complete, vendor-agnostic graph capture infrastructure that maps 1:1 from CUDA to HIP.

### Existing Infrastructure

| Component | Location | Status |
|---|---|---|
| HIP graph API mappings | `ggml/src/ggml-cuda/vendors/hip.h:124-145` | Complete — 1:1 `#define` aliases, all 16 CUDA graph APIs mapped |
| Graph struct + LRU cache | `ggml/src/ggml-cuda/common.cuh:1203-1207` | `ggml_cuda_graph` with warmup, UID tracking, node property comparison |
| Capture + replay flow | `ggml/src/ggml-cuda/ggml-cuda.cu:4468+` | `ggml_backend_cuda_graph_compute`: capture → instantiate → launch → `GraphExecUpdate` fast path |
| CMake enable | `ggml/CMakeLists.txt:216` | `GGML_HIP_GRAPHS=ON` by default |
| MI210 arch gate | `ggml-cuda.cu:4456` | CDNA2 (`0x100090a`) >> AMPERE threshold — passes |

### Speculative Decoding Integration

Graph capture operates transparently at the backend level (`llama_decode` → `encode` → `graph_compute` → `ggml_backend_cuda_graph_compute`). No speculative-specific graph logic exists — the graph captures whatever `ggml_cgraph` is submitted. **This is the onegraph opportunity**: the `is_mem_shared` draft loop's uniform body means the same graph shape across iterations, maximizing cache hits.

### Known Limitations

- Split buffers disable graphs entirely (multi-GPU layer splitting)
- `MUL_MAT_ID` with non-quantized tensors or `ne[2] > mmvq_mmid_max` disables graphs
- Requires ROCm 5.7+ (verify system version)
- No speculative-specific tuning — graph cache key is first-node-pointer, not shape-aware

### Effort (validation-only, not port)

Smoke-test on MI210: ~1 day. Validate + benchmark with MTP: 2-3 days.

## Onegraph Structural Verification (2026-07-11)

**Verdict: ALL THREE preconditions SATISFIED.** The gemma4 assistant drafter on our fork (`experimental-v7-candidate`) is structurally eligible for the onegraph optimization.

### P1: Q-only — SATISFIED

`src/models/gemma4-assistant.cpp:61-63`: only `wq` and `wo` tensors per layer (no `wk`/`wv`). Forward pass at `:143-154` calls `build_attn` with `nullptr` for K and V. `llama-graph.cpp:2596-2606` skips KV store when `k_cur`/`v_cur` are null — reads K/V from shared cache only.

### P2: KV-shared — SATISFIED

`src/llama-model.cpp:2169-2197`: `GEMMA4_ASSISTANT` creates `llama_kv_cache_iswa` with `mem_other` = target model's memory and a `share` callback mapping assistant layers to target layers. `src/llama-kv-cache.cpp:190-198`: when `share` is set and `other` is non-null, K/V tensors are direct views into the source cache. `speculative.cpp:1370`: `is_mem_shared = llama_get_ctx_other(ctx_dft) == ctx_tgt` evaluates true.

### P3: No cross-position dependencies — SATISFIED

`speculative.cpp:1663-1667`: every draft token decodes at the **same position** `dp.n_past`. No `seq_rm`, no KV rebuild, no batch prefix — just a single-token decode at the fixed position with the h-row carryover. Each step consumes `(token, h_row)` and produces `(token, h_row)` where `h_row` comes from `llama_get_embeddings_nextn_ith`.

### Warm-up vs Draft Loop Equivalence

- **Warm-up (`process()`, `:1430-1546`)**: for `is_mem_shared`, the catch-up decode block (`:1465`) is **entirely skipped** — only copies hidden states from the target (`:1527-1543`). **Zero drafter compute.**
- **Draft loop (`draft()`, `:1548-1697`)**: uniform single-token decode at `dp.n_past` per iteration (`:1663-1667`). Batch is cleared and rebuilt each iteration. **No structural difference between first and subsequent iterations** — every step runs the identical graph with only data values changing.

**Implication for GPU-graph capture**: the draft loop's uniform body is exactly what the onegraph optimization requires. A HIP graph captured for one iteration is replayable for all iterations — the only state that changes is the input token + h-row, which are external to the graph (batch embeddings). The CPU path is already optimal (minimal decode at fixed position, no warm-up overhead).

## Notes

- The challenge ran on A10G/GPU with E4B (small Gemma); our production worker is **CPU MTP on a 26B-A4B** with the MI210 as the GPU path — so GPU-graph techniques land on the MI210 drafter track, while the drafter-α and warm-up-redundancy *insights* are the CPU-transferable ones.
- All intake-798 numbers (315 / 491.8 TPS, ±15/40 eval deltas, PPL ≤ 2.42) are OBSERVATION-grade (challenge-internal, single-config, self-reported) — hypotheses only, re-measure on our stack before any keep/promote per MEASUREMENT.md.
- Submission-level detail (per-result `method` fields, taskforce notes) is available on the challenge leaderboard/bucket for a deeper follow-up if a technique graduates past the structural check.
