# 2026-07-20 — K28 fused chunked GDN kernel: research/design handoff

**Session type**: planning/research (no code). **Trigger**: operator asked what "real fused kernel"
improvement the parallel codex agent could make for K28 after it closed the two cheap GDN levers,
and requested a detailed research handoff to pass to that agent.

**Note on ownership**: the K28 / GDN thread and the `mi210-big-model-and-acceleration-roadmap.md`
owner task belong to the parallel codex session. This session only produced a design/SOTA research
handoff (no kernel work, no edits to codex-owned handoffs/indices). Cross-linking the new handoff
into the K28 task + `inference-acceleration-index.md` is left for operator approval (see Deferred).

## Deliverable

`handoffs/active/k28-fused-chunked-gdn-kernel-research.md` (new, ~324 lines) — a research handoff
answering "what real fused kernel improvement could be made" for the GDN long-prefill recurrence,
cross-referenced against the SOTA and paired with a cheap ROI decision gate.

## What was established (audit of the v7 experimental GDN stack)

- **Bottleneck is named in-code**: `ggml/src/ggml-cuda/gated_delta_net.cu:74` is a fully sequential
  token loop; `:191` reads `//TODO: Add chunked kernel for even faster pre-fill`. The op-microbench
  (K28.1) shows **effective BW falling with prompt length** (64→51.17, 1024→26.87 GB/s, ~1.7% of
  MI210 peak) — the signature of a serial-dependency-bound kernel, i.e. real headroom.
- **Three code paths** (`src/models/delta-net-base.cpp`): `build_delta_net_fused` (the sequential
  custom kernel, used for decode + prefill), `build_delta_net_chunking` (real FLA-style chunked
  algorithm but built from ~150+ generic ggml ops → op-dispatch/HBM-roundtrip bound), and
  `build_delta_net_autoregressive`. The codex A/B (fused beats generic-chunked +6%) is evidence
  against the *generic-ggml decomposition*, not against chunking.
- **Tried/falsified ledger**: banked = nwarps 2→4 (+4.6%), async prefetch (+3.3%), bf16 state
  (+21.5% @B32). Falsified = further occupancy rewrite, compact-LDS, graph-vs-fused switch,
  single-stream bf16. Reconciled: bf16 state is neutral single-stream but a live **batched-decode**
  lever (same `GGML_CUDA_GDN_STATE_BF16` mechanism, two regimes). Only untried lever = the
  algorithmic restructure to a fused chunked-matmul kernel.
- **Feasibility infra found**: `ggml/src/ggml-cuda/mma.cuh` already has a full AMD MFMA abstraction
  for gfx90a (consumed by `fattn-mma-f16.cuh`) — the template to reuse. `lightning-indexer.cu` uses
  raw `nvcuda::wmma` and is NVIDIA-only — the trap to avoid.

## SOTA deep-dive (8 sources, folded into 4 appendices of the handoff)

Four parallel research agents extracted source-anchored detail:

- **DeltaNet (arXiv:2406.06484) + Gated DeltaNet (arXiv:2412.06464)** — the chunked equations, the
  UT-transform `T = (I + strictLower(diag(β)KKᵀ))⁻¹ diag(β)` (**sign is PLUS**), the serial-vs-parallel
  split (O(L/C) inter-chunk scan + O(C) per-chunk solve are the only serial parts), and the gated
  W/U asymmetry (W-side plain KKᵀ, Ũ-side Γ⊙KKᵀ). Chunked-vs-recurrent speedup up to ~30× (grows
  with L and d_head).
- **FLA `chunk.py` + FlashQLA** — FLA's 5-kernel decomposition (chunk ∈ {16,32,64}, BC=16 block
  inverse, bf16-in/fp32-accum, IEEE-fp32 solve, memory-bound `fused_recurrent` decode), confirmed
  ROCm support; FlashQLA (SM90/SM100-only) technique port-map: TMA/warpgroup/wgmma don't port to
  CDNA2, single-launch-fusion/algebraic-reformulation/gate-decay-context-parallel do.
- **TFLA (arXiv:2503.14376) + AttentionEngine (arXiv:2502.15349)** — TFLA's second-level
  intra-chunk parallelism → optimal chunk 128–256 (`L_opt ∝ √(d·I)`, re-sweep for CDNA2);
  AttentionEngine 3.3×/2.0× on MI250 (CDNA2) but **does not cover GDN** (oracle, not code source).
- **llama.cpp PRs + AMD MFMA notes** — prior-art chain (#19504 op, #20340 chunked-path-enable,
  #20391/#20361 backends, #19375 graph-only); **issue #20354** is the open AMD-perf gap (~11.8 t/s
  on ROCm from register spilling + warp-32 assumptions). Complete gfx90a MFMA intrinsic table
  (bf16 `_1k` tiles, per-lane VGPR costs, no async-copy/TMA, rocWMMA missing small-K → #509).

## Recommendation (in the handoff)

A single **fused chunked-recurrence kernel**, **fusion-first (FP32)** then **MFMA/bf16** — but gated
behind a **Phase 0** attribution (GDN's share of GPU prefill wall-clock + a throwaway prototype),
because K28 is lever **#7/11**, MI210 is **not live production**, and the GDN model (Qwen3.6-35B-A3B)
is served on **CPU** → any result is **observation-grade** until v7 promotes and P-GPU-1 reruns.
Higher-EV adjacent lever flagged: batched-decode state bandwidth (the banked +21.5%@B32 direction).

## Deferred / for operator

- Cross-link the new handoff from `mi210-big-model-and-acceleration-roadmap.md` (K28 task) and
  `inference-acceleration-index.md` (lever #7). Not done here — those files are codex-owned and
  index changes need operator approval.
- The handoff is **not committed to `main`** — this session's commit lands on the shared
  `spec-dec-mtp-refresh-2026-06-22` branch (69 ahead / 53 behind main); promoting that branch would
  publish the parallel agent's entire in-flight spec-dec-MTP campaign, which is an operator decision.
