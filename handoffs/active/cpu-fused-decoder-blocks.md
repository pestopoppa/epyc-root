# CPU Fused Decoder Blocks (batch-1 decode megakernel)

**Status**: **PLAN APPROVED by operator 2026-08-30** — bit-exactness prioritized (NMSE ≤1e-4 acceptable fallback); qwen4exp-first with the GDN family in mind; op-based execution model (direct fast-path acceptable if diligent); decode prioritized, pp desirable; plan persisted before work begins.
**Created**: 2026-08-30
**Priority**: HIGH — the last identified path to 20-60 t/s batch-1 CPU decode
**Categories**: hardware_optimization, inference_serving, local_inference, kernel_architecture
**Workstream**: Inference Acceleration
**Parent index**: [`inference-research-index.md`](inference-research-index.md) (row INF-64)
**Related**:
- [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) (INF-10) — the direct predecessor: same diagnosis (barrier/op-count-bound, not BW), 4 fusion arms REFUTED, the +2.6% DeltaNet-native-fused-wqkv precedent this project scales up
- [`batched-decode-measurement.md`](batched-decode-measurement.md) — the NUMA×placement canonical recipe (interleave+no-mmap), the same family's reference numbers
- [`autokernel-research-loop.md`](autokernel-research-loop.md) — the GPU megakernel/persistent-kernel literature (L4 lever) this project is the CPU analogue of
- `handoffs/active/master-handoff-index.md` — the router

## The measured problem (2026-08-29/30, qwen4exp IQ4_XS UD, interleave baseline)

Batch-1 decode = ~74 ms/token (~13.5 t/s, t48; t64 sweet spot ~14). Breakdown, all in situ:
- ~28 ms real gemv work (expert mul_mat_id ~9.4 ms at ~65 μs/call median; dense ~18 ms) — at the machine's real memory rate (~100-180 GB/s in situ)
- ~46 ms of non-gemv dispatch: ~5,850 nodes × ~5-8 μs each (barrier + dispatch + tiny elementwise compute)
- Four clean-room kernel experiments (fused hc_mix op, elementwise chain fusion ×3, gemv software pipelining) all measured NEUTRAL or NEGATIVE in situ despite clean-room wins up to +55%. The per-node machinery cost is irreducible per-node; the only way down is fewer, fatter nodes.

## The idea

Collapse the ~6,800-node decode graph to ~100 nodes: **one fused op per layer** (GGML_OP_GATED_DELTA_NET_FUSED_LAYER ×36 + GGML_OP_FULL_ATTN_FUSED_LAYER ×12 + PLE/head tail). The layer's math runs as one sequential kernel — data flows in registers/L2, no graph barriers between the layer's micro-ops. The per-node machinery runs once per layer instead of once per micro-op.

**Target**: ~28 ms gemv + ~96×15 μs fused overhead (~1.5 ms) + state/attention (~5 ms) ≈ 35-45 ms → **22-28 t/s**, with gemv micro-tuning inside the fused kernels (where dispatch can no longer eat it) reaching 30-40.

## Operator decisions (locked 2026-08-30)

1. **Numerics contract**: bit-exactness PRIORITIZED (mirror the decomposed op order internally); NMSE ≤1e-4 acceptable where bit-exactness costs too much freedom. The arch test's CPU-vs-GPU NMSE bar applies as the floor.
2. **Scope**: qwen4exp-first; the GDN family (qwen3.5/qwen3next/qwen35moe) served by the same fused ops if it isn't disproportionate — the layer structure is shared via `llm_build_delta_net_base`.
3. **Execution model**: op-based (new GGML ops, ~100-node graph, fits the scheduler/backends). A direct decode fast-path outside the graph is permitted if it becomes clearly better — diligence required (the blast radius is real).
4. **Priority**: decode first; pp acceleration via the same ops (batched) is desirable but secondary.

## Phases

| Phase | Deliverable | Milestone / gate |
|---|---|---|
| **0** | Measurement infra: fix the logit-dump tool (was crashing), standard A/B harness at the interleave baseline, in-situ profiler runs (all present from prior rounds) | reproducible fused-vs-decomposed logit diff ≤1e-4 |
| **1** | Fused GDN-layer function (36 layers): hc_mix + qkvz + conv + GDN scan (the ggml_gated_delta_net kernel) + output proj + MoE (router/top-k/topk-norm weights/expert dots/shexp) + hc_combine; recurrent + conv state in/out | decode 74 → ~45 ms; logit diff + greedy generation + arch test |
| **2** | Fused full-attn layer function (12 layers): QSA indexer (top-k blocks) + attention + gate + MoE; KV cache + indexer cache interfaces | decode → ~38 ms |
| **3** | PLE + head + tail; the process_ubatch hook; full fused decode | full fused decode + logit-diff validation |
| **4** | Thread-pool integration + gemv/activation micro-opt INSIDE the fused kernels (safe now — no dispatch to lose it) | 30-40 t/s |

Checklist (the dashboard gate — flipped as the phases land):
- [x] Phase 0: logit-dump tool fixed and verified; A/B harness + in-situ profiler established
- [x] Phase 1: fused GDN-layer function committed (`e57e1d542`) — compiles clean, single-threaded
- [ ] Phase 1 gate: logit diff ≤1e-4 + greedy generation + arch test (needs the hook)
- [x] Phase 3 partial: fused_head + fused_decode_token skeleton committed (`2d699f02c`)
- [ ] Phase 2: full-attn layer function
- [ ] Phase 3: PLE + head + hook + full fused decode
- [ ] Phase 4: thread-pool integration + fused-kernel micro-opt

## Validation strategy (learned the hard way — the arch test is self-consistent and cannot see graph-math errors)

1. **Logit comparison** (the dump tool, fixed in Phase 0): fused vs decomposed per-token, ≤1e-4, per layer type, before any perf claim.
2. **Greedy generation test** (Paris-style) — the real gate; every change.
3. **test-llama-archs** — necessary, insufficient.
4. **In-situ profiler** (`GGML_CPU_PROF` + `[mm_prof]/[mmid_prof]`) — the ONLY trustworthy perf instrument; clean-room numbers have lied 4/4 times.

## Risks

- **Numerics**: the fused op's internal order must mirror the decomposed (bit-exact) or stay within the NMSE — the hc_mix revert (the 2·sigmoid fold bug) is the standing warning: graph-math errors pass the arch test and show as garbage generation.
- **State machinery**: the recurrent/conv state + QSA indexer + PLE interfaces are the hardest correctness surface — Phase 1 deliberately picks the uniform layer type first.
- **The MoE routing** (dynamic expert selection) inside a fused kernel.
- Effort: 4-8 focused sessions; the branch `exp/cpu-fusion-qwen4exp-20260829` and the worktree `/mnt/raid0/llm/llama.cpp-cpu-fusion-20260829` are the workspace (champion `270b48ed6` + 4 qwen4exp backports + confirmed fusion ops mean_d1/moe_topk_norm + profiling tooling).

## Phase 0 DONE (2026-08-30) — tooling + fast-path hook design

- Logit-dump tool fixed and verified: `/tmp/qwen4exp-builds/dump_logits2` — the `-1` text_len convention is gone in this API (caused `std::length_error` in `llama_vocab::tokenize`); the two-pass tokenize returns the negative buffer size; the tool now writes the full 248,320 logits to a file for the fused-vs-decomposed diff.
- A/B harness: `numactl --interleave=all` + `-mmp 0`, t48/t64, IQK=1, the in-situ profiler (`GGML_CPU_PROF` + `[mm_prof]/[mmid_prof]`) — all established from the prior rounds.
- **Fast-path hook design**: `llama_context::process_ubatch` (src/llama-context.cpp:1320) is the single hook point — after the mctx apply, a branch: `model.supports_fused_decode() && gtype == LLM_GRAPH_TYPE_DEFAULT && batch-1 decode && CPU backend` → the fused decode writes the logits into the `llm_graph_result` and returns; the graph machinery untouched otherwise. State access via the memory context (the hybrid-idx cast, like the graph does); weights via the model's layers. The user permitted the direct fast-path blast radius.

## Phase 1 progress (2026-08-30) — foundation committed

- `src/models/qwen4exp-fused.cpp` committed (`6321806b3`): the kernel-mirror helpers (FusedMM, lora_mm, hc_rms_norm_gamma, hc_stream_mean, hc_mix) — each mirrors the graph's exact function/order for bit-exactness. Single-threaded for now (correctness first).
- `e57e1d542` committed the FULL fused GDN-layer function: hc_mix + qkvz + conv state + 4-tap causal conv + l2 norms + the ggml_gated_delta_net kernel (scratch ctx + 1-thread pool) + z-gated rms + ssm_out + fused_moe (softmax router, argsort top-k, topk-norm weights, expert dots, shared expert) + hc_combine x2. Every op mirrors the graph's function/order for bit-exactness. Single-threaded (correctness first). Compiles clean, tree green.
- Next: thread-pool integration (the mms + the GDN kernel at nth>1), then the full-attn layers + PLE + head, then the process_ubatch hook + logit-diff validation.

## Current tree state (starting point)

- Branch `exp/cpu-fusion-qwen4exp-20260829` @ `7cdd7c97b` — clean, arch suite 0 FAILs, "Paris" verified.
- The measurement recipe: `numactl --interleave=all` + `-mmp 0`, t48/t64, IQK=1, the in-situ profiler.
- Decode baseline: ~12.4-14.9 t/s depending on the box state.
