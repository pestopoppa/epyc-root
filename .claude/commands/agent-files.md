# Agent Files Workflow

Refactor or create role files under `agents/` using the canonical schema and shared policy model.

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
