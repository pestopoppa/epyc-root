# Agent Workflows

Operational detail for role workflows lives here, not in role prompts.

## Guides

- `docs/guides/agent-workflows/research-writer.md`
- `docs/guides/agent-workflows/benchmark-analyst.md`
- `docs/guides/agent-workflows/safety-reviewer.md`
- `docs/guides/agent-workflows/verification-failure-catalogue.md` — eight measured ways a check passes for the WRONG reason, each with its own tell and test; mutation-test the guard, and confirm the mutation is visible AND counted

## Design Rule

- Keep `agents/*.md` concise and role-specific.
- Keep durable, procedure-heavy guidance in this folder.
