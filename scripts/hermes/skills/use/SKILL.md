---
name: use
description: Force a specific orchestrator role or model for this conversation. Bypasses frontdoor routing to use a deterministic current role.
version: 1.0.0
metadata:
  hermes:
    tags: [routing, orchestrator, model-selection]
---

# /use — Force Orchestrator Role

Override the orchestrator's automatic routing to force a specific model tier or role.

## Usage

- `/use architect` — Route to the current architect-tier role
- `/use biggest` — Route to the largest current hot role
- `/use frontdoor` — Stay on the current frontdoor role, no escalation
- `/use worker` — Route to the general worker role
- `/use auto` — Remove all overrides, return to normal MemRL-driven routing

## API Mapping

Each command maps to an extension field on the `/v1/chat/completions` request:

| Command | API Parameter | Value |
|---------|--------------|-------|
| `/use architect` | `x_orchestrator_role` | `"architect_general"` |
| `/use biggest` | `x_orchestrator_role` | `"architect_general"` |
| `/use frontdoor` | `x_orchestrator_role` | `"frontdoor"` |
| `/use worker` | `x_orchestrator_role` | `"worker_general"` |
| `/use auto` | (remove all `x_*` fields) | — |

## Notes

- `x_orchestrator_role`, `x_force_model`, and `x_max_escalation` are strings;
  boolean `x_*` overrides must be JSON booleans
- `x_force_model` takes precedence over `x_orchestrator_role`
- Available roles are listed at `GET /v1/models`; verify concrete role names
  before adding new command aliases
- Override persists for the duration of the conversation (Hermes manages session state)
