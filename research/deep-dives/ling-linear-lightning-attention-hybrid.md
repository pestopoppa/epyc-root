# Ant Group Ling-Linear-2.0 / Ring-Linear / Lightning Attention — Deep Dive

**Source intake**: intake-503 (arxiv:2510.19338, "Every Attention Matters: An Efficient Hybrid Architecture for Long-Context Reasoning")
**Date**: 2026-04-29
**Status**: FACT-CHECKED against llama.cpp upstream as of 2026-04-29

## TL;DR

Ant Group's **Ling-Linear-2.0** family (Ring-mini-linear-2.0 16B/957M-active, Ring-flash-linear-2.0 104B/6.1B-active) couples Lightning Attention (linear, fixed power-law decay) with periodic softmax layers at empirically-tuned ratios M=4 and M=7. Continued from Ling-mini-base-2.0 with +600B tokens.

**llama.cpp status: NO SUPPORT.** Lightning Attention has no kernel in upstream llama.cpp, no merged or in-progress PR. This is the hardest of the three deep-dive subjects to actually adopt.

The most actionable angle here is **architectural reference**, not deployment.

## What's actually new in Ling-Linear-2.0

The paper's framing — "every attention matters" — is roughly: linear attention is fast but loses recall; sparse attention is fast but discards information; standard attention is full-fidelity but expensive. Use them together at empirically-tuned ratios.

**Specific contributions**:

1. **Hybrid ratio M sweep**. Most prior hybrids (Jamba, Minimax-01) use a single fixed ratio (1:1, 7:1). Ant Group runs a scaling-law sweep over M and lands at M=4 for 16B and M=7 for 104B. The takeaway is that *optimal ratio depends on model size* — larger models can absorb more linear layers without losing reasoning capacity. This is the most cleanly transferable finding.
2. **FP8 LingHe kernel library**. Open-sourced. Aligns training and inference operators to prevent precision drift in the BF16 KV recurrence — this is a real engineering pain point in linear-attention hybrids that the paper documents Section 7.
3. **MTP layers retained from Ling 2.0**. Multi-token prediction passes through unchanged — the linear-attention substitution doesn't break MTP-as-drafter pattern.
4. **Open weights + open kernels** at industrial scale (16B and 104B variants on HuggingFace).

What's *not* new:

- **Lightning Attention itself** dates to arxiv:2401.04658 (Qin et al., 2024). The fixed power-law decay is from that paper.
- **Hybrid linear/softmax** at scale is Minimax-01 (arxiv:2501.08313, January 2025) — Ling-Linear arrives 9 months later.
- **MoE 1/32 activation ratio + MTP** is inherited from Ling 2.0; not a Ling-Linear contribution.

So the *novelty* is (M-sweep finding) + (open FP8 kernels) + (industrial-scale open release). Architectural novelty is incremental.

## llama.cpp upstream state (verified 2026-04-29)

| Search | Result |
|--------|--------|
| Lightning Attention PRs | **NONE** |
| Ling-linear / Ring-flash PRs | **NONE** |
| Linear attention infrastructure | Some Mamba/SSM work via existing `llm_build_*_delta_net` patterns; nothing for fixed-decay linear attention specifically |
| MiniMax-01 (the 7:1 hybrid sibling) PRs | **NONE** found in repo |

Confirmed via `git log --grep="lightning attention\|ling.linear\|ant.group\|ling-flash\|ring-flash"` against local clone + GitHub PR search.

This makes Ling-Linear the *opposite* situation from V3.2/DSA: V3.2 has a draft PR being actively iterated by a known contributor; Ling-Linear has nothing. Adoption would require us (or someone else) to implement Lightning Attention from scratch in ggml.

## Why Lightning Attention is a non-trivial port to llama.cpp CPU

The Lightning Attention forward pass is a recurrence:

```
state_t = state_{t-1} * decay + V_t @ K_t^T
output_t = Q_t @ state_t
```

with **fixed power-law decay** per head (not learned per-token like Gated DeltaNet). The `state` is a `d × d` matrix per head, growing fixed-size (constant memory per layer regardless of context).

Implementation challenges:

1. **No existing ggml op for fixed-decay state update**. Gated DeltaNet (which we DO support, in Qwen3.5/3.6 hybrid models) uses a learned per-token decay → `llm_build_recurrent_delta_net` pattern. Lightning Attention's fixed decay would need a new variant.
2. **BF16 KV-state precision drift** (Section 7 of the Ant Group paper) — the recurrence accumulates error. Authors solve this with FP32 accumulation + careful train/infer operator alignment via LingHe. Replicating this in ggml requires either (a) a fp32 recurrence accumulator (memory cost: 2× state size) or (b) careful kernel design avoiding the drift. **Our quantized KV path is a separate problem on top**.
3. **FP8 LingHe is GPU-only**. The training-time kernels are tied to NVIDIA Hopper-class FP8 ops. CPU port requires a clean-room reimplementation.
4. **Training/inference alignment requirement**. The paper makes a big deal of this: if the inference forward pass differs from training even slightly, the linear recurrence amplifies the divergence. Our llama.cpp fork doesn't currently have this problem because we don't train (we only run inference) — but it does mean the *exact* numerics of the upstream PyTorch implementation must be mirrored, with no clever shortcuts.

The closest analogue in our experience: porting Gated DeltaNet for Qwen3.5 took several weeks. Lightning Attention would be similar effort or harder due to the fixed-decay constraint.

## Sizing reality

| Variant | Total | Active | Q4_K_M size | Fits 1.1 TB RAM? | EPYC decode estimate |
|---------|-------|--------|-------------|------------------|---------------------|
| Ring-mini-linear-2.0 | 16.4B | 957M-1.6B | ~9 GB | trivially | 80-120 t/s extrapolating from Q-scorer territory |
| Ring-flash-linear-2.0 | 104B | 6.1B-7.4B | ~55 GB | yes | ~25-35 t/s extrapolating |

**Ring-mini at 957M active is genuinely Q-scorer / drafter territory.** If we had Lightning Attention support, this would be a serious candidate for replacing our routing classifier or as a small-MoE drafter.

The 16B/957M active sizing is also notable for being **smaller in active params than Qwen3-Coder-30B-A3B** (3B active) — meaning even after accounting for the linear-attention CPU-friendliness penalty, Ring-mini should be faster than our deployed coder MoE per token. This makes Ring-mini the most interesting *theoretical* deployment target in this deep-dive trio.

## Reasoning benchmarks (paper's claims)

| Benchmark | Ring-mini-linear-2.0 (16B/0.96B-active) | Ring-flash-linear-2.0 (104B/6.1B-active) |
|-----------|------------------------------------------|------------------------------------------|
| AIME-25 | 73.65% | 86.51% |
| GPQA-Diamond | 65.69% | 74.49% |
| Inference cost vs 32B dense | n/a | ~1/10 |
| Inference cost vs original Ring | n/a | ≥50% reduction |

For reference: our deployed Qwen3-Coder-30B-A3B at AIME ≈ 35-40% range. Qwen3.5-35B-A3B (frontdoor) gets ~70-80% on AIME-25. Ring-flash-linear at 86.51% AIME-25 is genuinely strong reasoning performance.

**Caveat (Tier 2b from intake-503)**: NO RULER / NIAH / LongBench numbers published. The "long-context" claim rests on indirect reasoning benchmarks. This is a real gap — for a paper titled "Every Attention Matters: An Efficient Hybrid Architecture for **Long-Context** Reasoning" to skip the standard long-context retrieval stress tests is a yellow flag.

## What's actionable for our stack — CORRECTED 2026-04-29 PM

The "defer indefinitely / multi-week port" framing in the prior version of this doc was **wrong**. A direct audit of `llama.cpp-experimental` (HEAD `9f6191581` on `master`) finds that the Lightning Attention forward pass is essentially **already implemented** as `GGML_OP_GATED_LINEAR_ATTN`. We don't need to write the kernel from scratch.

**The audit findings**:

| Symbol | Location | Relevance to Lightning Attention |
|--------|----------|----------------------------------|
| `GGML_OP_GATED_LINEAR_ATTN` enum | `ggml/include/ggml.h:561` | The op exists |
| `ggml_gated_linear_attn(ctx, k, v, q, g, state, scale)` | `ggml/include/ggml.h:2589` | API signature already accepts `g` as a tensor — feeding a constant power-law decay tensor is the entire mechanical difference between GLA and Lightning Attention |
| `ggml_compute_forward_gla_f32` | `ggml/src/ggml-cpu/ops.cpp:10605` | Full CPU implementation, multi-threaded across heads, head-size × head-size state per head — exactly the recurrence structure Lightning Attention needs |
| `llm_build_delta_net_base` | `src/models/models.h:23` | Base class for hybrid linear-attention models — Qwen3.5, Qwen3-next, Kimi-linear, Qwen3.5-MoE all derive from it |
| `llm_build_kimi_linear` | `src/models/models.h:369` | Closest existing template (also linear attention; learned not fixed decay) |

**Lightning Attention vs Gated Linear Attention difference is exactly one thing**: GLA's `g` is learned per-token; Lightning Attention's decay is fixed power-law per-head. **Implementation = feed `g` as a constant tensor of fixed-decay values to the existing op.** Zero new ggml ops needed for v1.

**Realistic effort for a v1 port**:

| Phase | Scope | LOC est. | Time est. |
|-------|-------|----------|-----------|
| L1 | Scoping confirmation: re-read GLA op semantics, verify state-shape match, check ARM/x86 backend coverage | 0 | ~1 day |
| L2 | GGUF converter: extend `convert_hf_to_gguf.py` for Ant Group tensor naming (Ring-mini-linear-2.0 first) | ~50 | ~1 day |
| L3 | Model variant: `llm_build_ring_linear` derived from `llm_build_delta_net_base` in `src/models/`; hyperparameter wiring (chunk size, fixed-decay coefficient `g`, M-ratio) | ~150 | ~1-2 days |
| L4 | Test path: load Ring-mini Q4_K_M GGUF, smoke-decode, reasoning quality spot-check | 0 | ~1 day **[GATED on inference approval per `feedback_no_concurrent_inference.md`]** |
| L5 (optional v2) | Dedicated `GGML_OP_LIGHTNING_ATTN` op exploiting constant `g` (precompute `g^t` powers in chunked form for prefill speedup) | ~300-500 | ~1 week |

**Total v1: 3-5 days of focused work.** v2 optimization adds ~1 week if the v1 numbers warrant it.

**Why this matters**: Ring-mini-linear-2.0 is **957M active params, 16B total** — well inside our drafter / Q-scorer territory. A working port unlocks:
- A new candidate small drafter for spec-dec experiments
- Reasoning capability at the 86.51% AIME-25 level (Ring-flash) on hardware that fits comfortably in 1.1 TB RAM
- A reference data point for the M-sweep finding (M=4 vs M=7) on our own measurement infrastructure
- Continuation of the `log-linear-gated-deltanet-readiness.md` "intermediate path" thesis

This is now an **active port**, tracked at `/workspace/handoffs/active/lightning-attention-port.md` (created 2026-04-29 same day). The "wait for someone else to volunteer" framing was lazy; the GLA-op finding makes us the volunteer.

## Risks / caveats

1. **NO published long-context retrieval numbers**. The paper's title makes long-context a headline claim but RULER/NIAH/LongBench are absent. Suggests the long-context advantage may be narrower than positioned.
2. **Linear attention recall failure modes** are well-documented in the literature — pure linear attention loses fidelity on retrieval-heavy tasks. Authors acknowledge this; the M=4/M=7 ratios are an *engineering compromise*, not a solution to the linear-attention recall problem.
3. **BF16 KV-state drift requires FP32 accumulation** in the recurrence path. Our deployed Hadamard q4_0 KV path would conflict with this (4× more aggressive precision reduction). Even with llama.cpp Lightning Attention support, deploying with our quantized KV would likely require backing off to higher precision.
4. **Fixed power-law decay** (not learned per-token like Gated DeltaNet) means less expressivity per linear layer. The M=4 ratio compensates but at the cost of more layers being linear — the architecture is rigid.
5. **FP8 LingHe kernels are GPU-only**. Even if Lightning Attention lands in llama.cpp, the FP8 efficiency claims don't transfer to CPU.
6. **Reproduction sensitivity**: paper notes performance highly sensitive to decay coefficient (power-law vs linear swing 0.04 in training loss). Brittle to faithful kernel parity. Our llama.cpp port (if we ever do one) would have to match upstream numerics exactly.

## Action items (ranked) — CORRECTED 2026-04-29 PM

1. **Pursue the v1 port via existing GLA op** — this is now the active plan. Tracked at `/workspace/handoffs/active/lightning-attention-port.md` with phases L1-L4 (and optional L5 for the dedicated op). Effort 3-5 days for v1.
2. **Add to `multiscreen-attention-evaluation.md` Section 1 priority ranking** — flip from "monitor only — too early, no artifacts" to "active port via existing GLA op". Already in the existing same-day expansion sub-section as intake-503; the priority ranking line needs a flip.
3. **Read Section 7 of the paper in detail** — the train/infer alignment + BF16 drift discussion remains independently informative; particularly relevant for L1 scoping (do we need FP32 accumulation in our recurrence path? Our existing Qwen3.5/3.6 GDN forward pass may already have unidentified drift issues that the paper's methodology would surface).
4. **Read `llm_build_kimi_linear` end-to-end before starting L3** — closest existing template. Lightning Attention is essentially "kimi-linear with constant decay coefficient". Mirroring its structure should keep L3 boilerplate light.
5. **L5 (dedicated op) decision deferred to after L4** — only proceed if v1 numbers show meaningful prefill bottleneck attributable to repeated `g` lookups vs. precomputed powers. v1 may be sufficient.
6. **Drafter evaluation as a separate follow-up after L4 ships** — Ring-mini-linear-2.0 (957M active) as a candidate drafter for Qwen3-Coder-30B-A3B target. Architecture mismatch (Ring uses Lightning Attention; Qwen uses Gated DeltaNet) makes it a research question, but the size + reasoning quality combination warrants the experiment.

## Cross-references

- `/workspace/handoffs/active/multiscreen-attention-evaluation.md` — sub-quadratic attention survey; Ling-Linear added as Section-1 cluster member
- `/workspace/handoffs/active/log-linear-gated-deltanet-readiness.md` — sibling architecture (different lineage: log-linear-state vs fixed-decay-state); both are CPU-friendly intermediate paths
- `/workspace/handoffs/active/qwen36-27b-cpu-feasibility.md` — sizing comparison anchor for Ring-mini
- intake-502 (KSA), intake-505 (MiMo), intake-506 (V3.2) — siblings in same expansion run; KSA is closest paradigm cousin (both = sequence-level compression via learned tokens vs learned scoring)
- arxiv:2401.04658 (parent Lightning Attention paper, Qin et al. 2024) — foundational
- arxiv:2501.08313 (Minimax-01) — predecessor at 7:1 hybrid

## Notes

The original "monitor only" framing was wrong. Lesson recorded: **before claiming an implementation effort is multi-week, audit the existing op space.** A 30-second `grep -nE "(GGML_OP_GATED_LINEAR_ATTN|llm_build_delta_net_base)"` against `llama.cpp-experimental` revealed the kernel + base class were already in place. The framing failure was extrapolating "no PR exists upstream" → "we'd have to write the kernel from scratch", which is what happens when the audit step is skipped.

The correct action is the v1 port (3-5 days) tracked in `lightning-attention-port.md`.
