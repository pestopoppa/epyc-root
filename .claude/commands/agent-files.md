# Agent Files Workflow

Refactor or create role files under `agents/` using the canonical schema and shared policy model.

**Scope, 2026-08-16**: a *role* is a role the session-bus roster actually assigns
(`coordination/session-bus/config.yaml`: `main`, `coordinator-agent`, `reviewer`, `retired`,
`service`). Do NOT create task-based persona files — the eight that existed were archived to
`agents/archived/` under the Loop-Owned Fleet doctrine collapse (P1-5) because nothing consumed
them. Deep procedure belongs in `docs/guides/agent-workflows/`, not in a new role prompt.

## Required Flow

1. Read `agents/AGENT_INSTRUCTIONS.md`.
2. Read shared policy:
   - `agents/shared/OPERATING_CONSTRAINTS.md`
   - `agents/shared/ENGINEERING_STANDARDS.md`
   - `agents/shared/WORKFLOWS.md`
3. Update only role-specific behavior in `agents/<role>.md`.
4. Move long operational procedures to `docs/guides/agent-workflows/`.
5. Run:
   - `python3 scripts/validate/validate_agents_structure.py`
   - `python3 scripts/validate/validate_agents_references.py`

## Role Schema

Each role file must contain these section headers (validators and the schema hook check
presence; additional role-specific `##` sections are allowed):

- `## Mission`
- `## Use This Role When`
- `## Inputs Required`
- `## Outputs`
- `## Workflow`
- `## Guardrails`
