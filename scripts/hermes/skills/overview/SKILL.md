---
name: orchestrator-overrides
description: Index the EPYC orchestrator x_* request overrides exposed through Hermes command skills.
version: 1.0.0
metadata:
  hermes:
    tags: [routing, orchestrator, overview]
---

# Orchestrator Overrides

Use this as the entry point for Hermes commands that shape EPYC orchestrator routing.

## Override Inventory

| API field | Type | Effect | Consumed by |
|-----------|------|--------|-------------|
| `x_orchestrator_role` | string or null | Force a role from `GET /v1/models` and bypass frontdoor routing. | `/use` |
| `x_max_escalation` | string or null | Cap escalation at `A`, `B1`, `B2`, or `C`. | `/escalation` |
| `x_force_model` | string or null | Force one registry model and bypass role routing. Wins over `x_orchestrator_role`. | No dedicated command; advanced API override only |
| `x_disable_repl` | boolean | Skip REPL execution and request direct text. | `/nocode` |
| `x_show_routing` | boolean | Include routing metadata in the response for debugging. | No dedicated command; advanced API override only |

## Command Skills

| Command skill | Primary field | Use when |
|---------------|---------------|----------|
| `/use` | `x_orchestrator_role` | A conversation should stay on a known current role. |
| `/escalation` | `x_max_escalation` | A conversation needs a latency or quality ceiling. |
| `/nocode` | `x_disable_repl` | A conversation should avoid REPL/tool execution. |

## Drift Check

Keep this inventory aligned with `OpenAIChatRequest`:

```bash
python3 scripts/hermes/skills/check_drift.py
```

The checker compares the request-side `x_*` fields declared in
`/mnt/raid0/llm/epyc-orchestrator/src/api/models/openai.py` with the documented
fields under `scripts/hermes/skills/`.
