---
name: skill-name
description: One sentence describing the user-visible command or capability.
version: 0.1.0
metadata:
  hermes:
    tags: [orchestrator]
---

# /command - Short Capability Name

One short paragraph explaining what this skill does, when to use it, and what
orchestrator behavior it changes. Keep the first paragraph operational: name
the command, the endpoint it affects, and the exact override field family.

## Usage

- `/command mode` - What the mode does
- `/command off` - How to remove or reverse the override

## Endpoint

| Field | Value |
|---|---|
| Method | `POST` |
| Path | `/v1/chat/completions` |
| Transport | OpenAI-compatible JSON |
| Local default | `http://127.0.0.1:8000/v1/chat/completions` |

## Override Mapping

| Command | API Parameter | JSON Type | Value |
|---|---|---|---|
| `/command mode` | `x_orchestrator_role` | string | role from `GET /v1/models` |
| `/command direct` | `x_disable_repl` | boolean | `true` |
| `/command route` | `x_show_routing` | boolean | `true` |
| `/command auto` | remove `x_*` fields | n/a | n/a |

## cURL

```bash
curl -sS http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "orchestrator",
    "messages": [{"role": "user", "content": "Explain the tradeoff."}],
    "x_orchestrator_role": "frontdoor",
    "x_show_routing": true
  }'
```

## Python SDK

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="local")

response = client.chat.completions.create(
    model="orchestrator",
    messages=[{"role": "user", "content": "Explain the tradeoff."}],
    extra_body={
        "x_orchestrator_role": "frontdoor",
        "x_show_routing": True,
    },
)
print(response.choices[0].message.content)
```

## Gotchas

- Verify override names against
  `epyc-orchestrator/src/api/models/openai.py::OpenAIChatRequest` before
  editing this skill.
- Do not hardcode deprecated roles or model IDs. Use `GET /v1/models` or the
  current orchestrator registry when examples need a concrete role.
- Boolean overrides are JSON booleans, not strings.
- `x_force_model` bypasses routing and takes precedence over
  `x_orchestrator_role`; use it only when a specific registry model is required.
- Reset commands must remove stale `x_*` fields from Hermes session state, not
  send an empty string.
