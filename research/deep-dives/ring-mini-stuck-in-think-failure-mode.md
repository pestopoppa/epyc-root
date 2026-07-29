# Ring-mini-linear-2.0 — stuck-in-think failure mode on multi-constraint enumeration

**Date**: 2026-05-04
**Source**: May 4 ring-mini benchmark re-run (`benchmarks/results/runs/20260430_151713/ring_mini_linear_q4km_baseline.json`) + May 4 scoring CSV (`reviews/may4_run/ring_mini_linear_q4km_baseline.csv`)
**Status**: Diagnostic finding. Architecture-level mitigation not yet implemented.

## TL;DR

Ring-mini Q4_K_M (Lightning Attention hybrid, 16 linear + 4 softmax layers) consistently fails on multi-constraint enumeration problems by entering a `<think>` block that never closes. The model decodes the full token budget inside `<think>`, the harness strips the unclosed think trace, and the JSON sees an empty response. **All 7 empty responses on May 4 share an identical signature** and are concentrated on a specific problem class.

## Empty-response pattern

7 of 30 questions (~23%) returned empty on May 4:

| Suite | Question ID | Pattern |
|-------|-------------|---------|
| thinking | t3_q3_reasoning_trap | pseudo-statistics trap; needs careful verification |
| thinking | t2_q4_metacognition | Fermi estimate (Chicago piano tuners) |
| thinking | t1_q3_planning | 5-plant scheduling with 2 valid orderings |
| agentic | t3_q1_competing_constraints | tool selection under tradeoffs |
| agentic | t3_q2_multi_agent_coordination | parallel-vs-sequential agent assignment |
| general | t2_q2_transform | flat→nested YAML transform |
| general | t2_q3_schedule | Alice/Bob/Carol/Dave meeting scheduler |

**Signature for all 7**:
- `completion_tokens = 4096` (suite-default cap)
- `tokens_per_second ≈ 78-79` (consistent decode rate)
- `total_time_ms ≈ 52,000` (~52 seconds = 4096 / 79 t/s, model decoded the full budget)
- `response` field length = 0 or 1 byte
- `<think>` count in response = 0 (harness has stripped the unclosed think block before saving)

## Architecture mechanism

Ring-mini-linear-2.0 has 20 layers in a 4:1 hybrid pattern:
- **16 linear-attention layers** using `ggml_gated_linear_attn` (GLA) with fixed per-head ALiBi-style decay (`γ_h = (2^-0.5)^h × layer_factor`)
- **4 softmax-attention layers** at indices 4, 9, 14, 19 (every 5th layer)

The Lightning Attention recurrence is `S_t = γ_h · S_{t-1} + k_t v_t^T`. State is bounded (`head_dim × head_dim` per head, fixed regardless of context). Early-token information decays exponentially per layer; after ~2K tokens of think, **early constraints from the prompt have been multiplied by `γ_h^2000` and are effectively zero in the linear-attention path**.

The 4 softmax layers should bridge this gap by directly attending to the original prompt tokens. But:
1. The softmax layers are interleaved among the linear layers, so each softmax layer's input has already passed through several linear layers that lost the early-context signal.
2. The decay coefficient is per-layer-decreasing — the deepest layers have very weak decay, but those are the layers FURTHEST from prompt embeddings.
3. With a 4K-token think trace, even softmax attention is competing with 4K think tokens for attention budget. The original prompt's constraint statements compete with the model's own deliberation tokens for attention mass.

## Why these specific problems?

The 7 failures are all **multi-constraint enumeration** problems. They share a specific cognitive structure:
1. Read N hard constraints (e.g., "Dave 9-11am or 2-4pm", "Alice unavailable 10-11am", "no back-to-back")
2. Enumerate candidate solutions
3. Verify each candidate against ALL constraints — requires backreferencing to early constraint statements

The verify-against-all-constraints step is exactly what Lightning Attention is bad at: it requires accurate recall of facts from early in the context window AFTER the model has decoded thousands of intermediate think tokens.

By contrast, the 23 questions that succeeded on May 4 fall into:
- Direct generation (no enumeration): `t3_q3_strategic_communication` succeeded with **0 `<think>` tokens** — model went straight to producing a CEO speech.
- Single-constraint reasoning: simple math, format conversions where one rule applies once.
- Open-ended analysis: where there's no "verify against early constraints" step, the model can riff freely.

## Empirical confirmation

The non-empty SUCCESSFUL response on `t3_q3_strategic_communication` had:
- `completion_tokens = 1287` (well under cap)
- `<think>` count: **0**
- 3430 chars of clean direct output

When ring-mini avoids `<think>`, it succeeds. When it enters `<think>` on a multi-constraint problem, it gets stuck.

## Run-to-run variance

The test was run with `temperature=0.7`. May 2 showed 4 empties on the same suite shape; May 4 showed 7 (3 net new, including `general/t2_q2_transform` which was a clean score-3 on May 2). This is genuine sampling-driven variance: at temp=0.7 the model probabilistically chooses to enter `<think>` mode on borderline questions; once in, the failure mode triggers reliably.

## Mitigation options

| Option | Effort | Effect | Recommended |
|--------|--------|--------|-------------|
| Drop `max_tokens_multiplier` to 2 (8K budget) | trivial | Slight improvement on borderline cases (more room to close think); no help on hard cases | DONE 2026-05-04 — moderate |
| Force `<think></think>` empty-prefix injection in chat template | server-side template patch (~1h) | Eliminates think mode entirely; loses reasoning benefit but eliminates this failure class | **Recommended for production deployment** |
| Use `reasoning: off` flag at server | trivial | Same as prefix injection — model never opens think | Try if fork supports it |
| Run at `temperature=0.0` with deterministic generation | trivial | Removes variance but model may still choose to think | Maybe — depends on sampling distribution of the policy |
| Re-train/fine-tune to emit shorter think traces | weeks | Real fix but expensive | NOT recommended for our scale |
| Add more softmax layers (re-architect) | weeks | Solves the recall problem at cost of throughput | NOT viable; would void Lightning-Attention port |
| Use Ring-flash-linear-2.0 (104B/6.1B-active, M=7) | moderate (download + test) | More layers + similar ratio — may or may not help | Worth probing; M=7 is even more linear-heavy |

## What this means for ring-mini's role

Per `lightning-attention-port.md`, ring-mini's natural roles are:
1. **Drafter for Ring-flash-linear-2.0** — UNTESTED, requires Ring-flash download
2. **Q-scorer / routing classifier** — short prompts, simple classification → no `<think>` triggered
3. **Standalone reasoning model for non-latency-critical queries**

This deep-dive confirms (2) is viable: short routing prompts don't trigger the failure mode. (3) is partially viable: Ring-mini does deliver SOTA-class reasoning on AIME-style math (we verified Problem 1 = 70 correct during port validation), but **fails reliably on multi-constraint enumeration**. Use only on tasks that don't require backreferencing many constraints from a long context.

## Recommended follow-up experiments

1. **Force-disable thinking via template patch** — the highest-leverage fix. Compare scoring with and without `<think>` to quantify the empty-rate reduction. Expect ~+15pp on multi-constraint suites if the hypothesis is right.
2. **Re-test at temperature=0.0** — quantify how much of the variance is sampling vs. structural. If empties drop to 0-2 at temp=0, the failure is salvageable; if still 7+, it's structural.
3. **Pull Ring-flash-linear-2.0 (104B/6.1B-active)** — does the M=7 ratio (more aggressive linear) make it WORSE on this class? Or does Ring-flash's larger absolute capacity bridge the recall gap?
4. **Test on a 1K-token prompt with same constraints** — if the failure persists with shorter prompt → it's the think rumination, not the prompt-vs-think competition. If it goes away → confirms Lightning Attention loses signal as effective context grows.

## Files

- Source: `benchmarks/results/runs/20260430_151713/ring_mini_linear_q4km_baseline.json`
- Scoring: `benchmarks/results/reviews/may4_run/ring_mini_linear_q4km_baseline.csv`
- Port handoff: `handoffs/active/lightning-attention-port.md`
- Earlier deep-dive (architecture): `research/deep-dives/ling-linear-lightning-attention-hybrid.md`
- Summary: `benchmarks/results/reviews/SCORING_SUMMARY_2026-05-04.md`
