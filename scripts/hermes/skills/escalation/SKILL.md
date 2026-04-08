---
name: escalation
description: Cap or restore the escalation tier for this conversation. Controls how far the orchestrator can escalate from frontdoor to specialist models.
version: 1.0.0
metadata:
  hermes:
    tags: [routing, orchestrator, escalation]
---

# /escalation — Cap Escalation Tier

Control how far the orchestrator can escalate requests through the model tier chain.

## Usage

- `/escalation off` — Frontdoor only, no escalation (tier A)
- `/escalation B1` — Allow escalation up to coder tier
- `/escalation B2` — Allow escalation up to architect tier
- `/escalation full` — Remove cap, full escalation chain (default behavior)

## API Mapping

| Command | API Parameter | Value |
|---------|--------------|-------|
| `/escalation off` | `x_max_escalation` | `"A"` |
| `/escalation B1` | `x_max_escalation` | `"B1"` |
| `/escalation B2` | `x_max_escalation` | `"B2"` |
| `/escalation full` | (remove `x_max_escalation`) | — |

## Escalation Tiers

```
A  — Frontdoor only (Qwen3.5-35B, fastest)
B1 — + Coder escalation (Qwen2.5-Coder-32B)
B2 — + Architect escalation (Qwen3.5-122B / REAP-246B)
C  — + Worker specialist (full chain, default)
```

## Notes

- Override parameters must be passed as strings
- Capping escalation reduces latency but may reduce quality on hard tasks
- Use `/escalation off` for quick factual queries where speed matters most
