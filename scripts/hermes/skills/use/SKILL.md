---
name: use
description: Force a specific orchestrator role or model for this conversation. Bypasses frontdoor routing to use a deterministic model tier.
version: 1.0.0
metadata:
  hermes:
    tags: [routing, orchestrator, model-selection]
---

# /use — Force Orchestrator Role

Override the orchestrator's automatic routing to force a specific model tier or role.

## Usage

- `/use architect` — Route to architect-tier model (Qwen3.5-122B or REAP-246B)
- `/use biggest` — Force the largest available model (REAP-246B architect_coding)
- `/use frontdoor` — Stay on frontdoor (Qwen3.5-35B), no escalation
- `/use worker` — Route to worker_explore (Qwen3-Coder-30B-A3B)
- `/use auto` — Remove all overrides, return to normal MemRL-driven routing

## API Mapping

Each command maps to an extension field on the `/v1/chat/completions` request:

| Command | API Parameter | Value |
|---------|--------------|-------|
| `/use architect` | `x_orchestrator_role` | `"architect_coding"` |
| `/use biggest` | `x_force_model` | `"architect_qwen2_5_72b"` |
| `/use frontdoor` | `x_orchestrator_role` | `"frontdoor"` |
| `/use worker` | `x_orchestrator_role` | `"worker_explore"` |
| `/use auto` | (remove all `x_*` fields) | — |

## Notes

- Override parameters must be passed as strings, not integers
- `x_force_model` takes precedence over `x_orchestrator_role`
- Available roles listed at `GET /v1/models`
- Override persists for the duration of the conversation (Hermes manages session state)
