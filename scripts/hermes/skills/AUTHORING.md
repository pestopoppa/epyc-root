# Hermes Skill Authoring Rubric

Use this rubric for every file under `scripts/hermes/skills/`. The model is the
Venice-style cross-runtime skill pattern: one compact `SKILL.md` per capability,
with enough endpoint detail that an agent does not invent parameters.

## Required Shape

Every Hermes skill must stay under 500 lines and use this order:

1. YAML frontmatter with `name`, `description`, `version`, and Hermes tags.
2. H1 heading naming the slash command or capability.
3. A short lead paragraph stating when to use the skill.
4. Usage examples.
5. Endpoint or API mapping table.
6. One `curl` example.
7. One SDK example when the skill maps to HTTP or OpenAI-compatible calls.
8. Gotchas section with failure modes and stale-data checks.

If the skill is not HTTP-facing, replace the endpoint section with the exact
runtime surface it changes: config file, environment variable, plugin hook, or
local command.

## Endpoint And Override Tables

When a skill targets the orchestrator OpenAI-compatible API, include this
minimum table:

| Field | Required Content |
|---|---|
| Method | Usually `POST` |
| Path | Usually `/v1/chat/completions` |
| Transport | JSON over HTTP, OpenAI-compatible |
| Local default | `http://127.0.0.1:8000/v1/chat/completions` unless the skill targets standalone Hermes backend |

For `x_*` overrides, include command, API parameter, JSON type, and value.
Current schema source of truth:

`/mnt/raid0/llm/epyc-orchestrator/src/api/models/openai.py::OpenAIChatRequest`

Known current fields:

| Field | JSON Type | Meaning |
|---|---|---|
| `x_orchestrator_role` | string or null | Force an orchestrator role from `GET /v1/models` |
| `x_max_escalation` | string or null | Cap escalation at `A`, `B1`, `B2`, or `C` |
| `x_force_model` | string or null | Force a registry model and bypass normal routing |
| `x_disable_repl` | boolean | Skip REPL execution and request direct text |
| `x_show_routing` | boolean | Include routing metadata in the response |

## Examples

Each skill should include one copy-pastable `curl` command and, when useful, one
OpenAI Python SDK example using `extra_body` for `x_*` fields. Keep examples
small and deterministic. Avoid model IDs unless the skill is explicitly about a
single model; prefer current role names or `GET /v1/models` discovery.

## Gotchas

Every skill must include gotchas that are specific enough to prevent stale
operator behavior. At minimum, consider:

- Does this skill mutate Hermes session state? Document how to reset it.
- Does it require a live orchestrator API, a standalone Hermes backend, or only
  local config edits?
- Does it use `x_force_model`? State that it bypasses routing and wins over
  `x_orchestrator_role`.
- Does it use booleans? Show JSON booleans (`true`/`false`), not strings.
- Does it mention a role/model? Tell the reader how to verify it is still live.
- Does it imply validation? Mark inference-required validation separately from
  no-inference lint or schema checks.

## Validation

For doc-only edits:

```bash
python3 scripts/hermes/skills/check_authoring.py  # if present
find scripts/hermes/skills -name '*.md' -print0 | xargs -0 wc -l
git diff --check -- scripts/hermes/skills
```

Until `check_authoring.py` exists, manually verify:

- every skill has YAML frontmatter;
- every skill is under 500 lines;
- every orchestrator override appears in the current `OpenAIChatRequest` schema;
- reset modes remove stale `x_*` fields rather than sending empty strings.

## Do Not

- Do not copy stale model names from historical handoffs.
- Do not describe unvalidated inference behavior as proven.
- Do not mix Hermes UX state, orchestrator routing state, and llama-server
  launch config in the same table.
- Do not bury the endpoint or override mapping after long prose.
- Do not add broad troubleshooting essays; link to the handoff or runbook when
  detail exceeds the 500-line skill cap.
