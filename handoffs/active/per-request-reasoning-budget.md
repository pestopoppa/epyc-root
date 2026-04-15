# Per-Request Reasoning Budget for Hybrid SSM+MoE Models

**Status**: READY (investigation needed in llama.cpp-experimental)
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

## Key Files

- `tools/server/server.cpp` — request parsing, thinking budget parameter
- `common/chat.cpp` — chat template application, `enable_thinking` logic
- `src/llama-sampling.cpp` — token sampling (forced token injection point)
- `tools/server/server-context.cpp` — slot management, generation loop

## Success Criteria

- `budget_tokens=0` on Qwen3.5 hybrid → empty `reasoning_content`, non-empty `content`
- `budget_tokens=512` → reasoning capped at ~512 tokens, then content follows
- No regression on pure MoE models
- Orchestrator can thread `thinking.budget_tokens` through ChatRequest per role
