# Per-Request Reasoning Budget for Hybrid SSM+MoE Models

**Status**: INVESTIGATION COMPLETE (Steps 1-2 done 2026-04-17; Steps 3-4 need running server)
**Created**: 2026-04-15
**Priority**: MEDIUM (unblocks per-request reasoning control, autopilot tuning)
**Categories**: llama.cpp, inference
**Depends on**: None
**Related**: [`v3-hybrid-ssm-regression.md`](v3-hybrid-ssm-regression.md), [`bulk-inference-campaign.md`](bulk-inference-campaign.md)

---

## Problem

`thinking.budget_tokens: 0` in the `/v1/chat/completions` request body does not suppress reasoning on Qwen3.5 hybrid SSM+MoE models. The server returns 210 chars of `reasoning_content` and empty `content` despite budget=0.

Works correctly on pure MoE models (Qwen3-Coder-30B — returns content, no reasoning).

Current workaround (2026-04-15): Removed `--jinja` flag from architect_general entirely. Without `--jinja`, llama-server uses generic ChatML template with no thinking scaffolding. Previous `--reasoning off` workaround was insufficient — the jinja template itself primed the model into think mode. This is even coarser — no reasoning capability at all, no per-request control.

## Why This Matters

Per-request reasoning control would enable:
1. Orchestrator sets `budget_tokens=0` for architect_general (structured TaskIR output, no thinking needed)
2. Orchestrator sets `budget_tokens=512` for architect_coding (useful for plan design)
3. AutoPilot tunes budget per role via NumericSwarm (explore quality-vs-speed tradeoff)
4. No server restarts — all control at API level

## Reproduction

```bash
# Server running WITH reasoning enabled (default --jinja, no --reasoning off)
# Qwen3.5-35B-A3B hybrid on port 8280

# budget=0 should produce NO reasoning — but it does (210 chars)
curl http://localhost:8280/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":64,"thinking":{"budget_tokens":0}}'
# → reasoning_content: 210 chars, content: empty

# Same request on pure MoE (Qwen3-Coder-30B, port 8082) works correctly
# → reasoning_content: none, content: "2 + 2 = 4"
```

## Investigation Plan

1. **Find budget enforcement**: In `llama.cpp-experimental`, search `tools/server/server.cpp` and `common/chat.cpp` for where `budget_tokens` is checked during token sampling/generation
2. **Trace hybrid code path**: The hybrid SSM+MoE models have recurrent layers that process tokens sequentially. Check if the `</think>` forced injection happens before or after the recurrent state update — if after, the SSM may have already committed to a reasoning trajectory
3. **Test fix**: When `budget_tokens=0`, inject `</think>` as the very first generated token (before any SSM state update). Verify on Qwen3.5-35B-A3B
4. **Test budget>0**: Verify that `budget_tokens=N` correctly caps reasoning at N tokens then transitions to content

## Investigation Results (2026-04-17, Steps 1-2)

### Budget Enforcement Pipeline (Fully Traced)

The reasoning budget is enforced via a **sampling-level state machine** — not a model-level control. The complete flow:

1. **Request parsing**: `server-common.cpp:1108-1118` reads `thinking.budget_tokens` → `reasoning_budget_tokens`
2. **Sampler init**: `sampling.cpp:260-299` creates `common_reasoning_budget_init()` with budget, start/end tag tokens, and prefill tokens
3. **State machine**: `reasoning-budget.cpp:59-127` implements:
   - `IDLE` → wait for `<think>` tag tokens
   - `COUNTING` → decrement remaining budget per generated token
   - `FORCING` → force `</think>` + fallback message by setting all other logits to -∞
   - `DONE` → passthrough (no more budget control)
4. **Logit forcing**: `reasoning-budget.cpp:129-149` — when `FORCING`, sets all logits to `-INFINITY` except the next forced token

### Root Cause: SSM State Update Race

The bug is specific to **hybrid SSM+MoE models** (Qwen3.5-A3B):

- **Attention layers** process the full context bidirectionally — budget forcing works because logit manipulation happens before the next token is committed
- **SSM/Mamba layers** update their recurrent state **during each token generation step** (`llama-context.cpp:3345-3354` accesses `llama_memory_hybrid`)
- When `budget_tokens=0`, the state machine promotes from `COUNTING` to `FORCING` at init (`reasoning-budget.cpp:201-204`), but the **prefill matching** (`reasoning-budget.cpp:221-246`) must first detect `<think>` in the prefill before promotion happens
- On hybrid models, the first generated token after `<think>` triggers an SSM state update that commits the model to a reasoning trajectory, even though the sampler is about to force `</think>`

### Proposed Fix (Steps 3-4, needs running server)

**Fix A** (minimal): In `reasoning-budget.cpp:200-204`, ensure `FORCING` state is set BEFORE the first token is generated when `budget=0` AND `<think>` is detected in prefill. Current code does this, but the SSM has already processed the prefill with `<think>` visible — the fix may need to strip `<think>` from the SSM prefill or inject `</think>` into the prefill itself.

**Fix B** (robust): For hybrid models, when `budget_tokens=0`, do not include `<think>` in the generation prompt at all. This means the chat template should suppress the think scaffold when budget=0 — modify `chat.cpp:1313-1331` to check budget before setting `thinking_start_tag`.

**Fix C** (workaround): Already deployed — remove `--jinja` flag entirely. Loses all thinking capability but avoids the SSM state commitment issue.

### Verified Test Protocol (for Steps 3-4)

```bash
# Test 1: budget=0 → no reasoning (the bug)
curl localhost:8280/v1/chat/completions -d '{"model":"auto","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":64,"thinking":{"budget_tokens":0}}'

# Test 2: budget=512 → capped reasoning
curl localhost:8280/v1/chat/completions -d '{"model":"auto","messages":[{"role":"user","content":"Prove sqrt(2) is irrational"}],"max_tokens":1024,"thinking":{"budget_tokens":512}}'

# Test 3: No regression on pure MoE (port 8082)
curl localhost:8082/v1/chat/completions -d '{"model":"auto","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":64,"thinking":{"budget_tokens":0}}'
```

## Key Files (Updated with Line Numbers)

| File | Lines | Purpose |
|------|-------|---------|
| `tools/server/server-common.cpp` | 1108-1118 | Request budget parsing (OAI format) |
| `tools/server/server-common.cpp` | 1636-1644 | Anthropic format parsing |
| `tools/server/server-task.cpp` | 488-506 | Budget param extraction + tokenization |
| `common/chat.cpp` | 1313-1331 | Think tag setup for chat templates |
| `common/sampling.cpp` | 260-299 | Sampler init with reasoning budget |
| `common/reasoning-budget.cpp` | 59-127 | **State machine** (IDLE→COUNTING→FORCING→DONE) |
| `common/reasoning-budget.cpp` | 129-149 | **Logit forcing** (-∞ for non-forced tokens) |
| `common/reasoning-budget.cpp` | 200-204 | **Budget=0 promotion** (COUNTING→FORCING) |
| `common/reasoning-budget.cpp` | 221-246 | **Prefill detection** (initial state from prefill) |
| `src/llama-context.cpp` | 3345-3354 | **Hybrid SSM memory access** (root cause) |

## Success Criteria

- `budget_tokens=0` on Qwen3.5 hybrid → empty `reasoning_content`, non-empty `content`
- `budget_tokens=512` → reasoning capped at ~512 tokens, then content follows
- No regression on pure MoE models
- Orchestrator can thread `thinking.budget_tokens` through ChatRequest per role

## Research Intake Update — 2026-04-17

### Adaptive Reasoning Budget via Attention Entropy (Halo Framework)
- **[intake-392]** "Limited Reasoning Space" (arxiv:2602.19281) proposes replacing fixed token budgets with **entropy-based adaptive control**
- **Mechanism**: Monitor mean attention entropy across layers during inference (O(1), <1% overhead). When accumulated uncertainty exceeds threshold → trigger semantic compression (summarize reasoning so far) + context reset.
- **Results**: 76.4% on RULER (3x over AdaCoT), 1.29x token overhead vs Tree-of-Thoughts' 3.5x. Tested on Qwen2.5 (7B/72B), Mixtral, DeepSeek-V2-Lite.
- **No public implementation** — but architecturally simple. The Observer reads attention distributions already computed during inference. Could be exposed as a per-layer entropy metric in llama-server API.
- **Relevance**: Once budget_tokens enforcement works (the core problem above), entropy monitoring becomes the natural next step — adaptive budget instead of fixed cap. The Observer could feed the orchestrator a real-time "model is diverging" signal that triggers early `</think>` injection.
- **Implementation path**: (1) Expose per-layer attention entropy in llama-server, (2) orchestrator reads entropy signal, (3) orchestrator adjusts budget_tokens dynamically per-request based on entropy trend.
