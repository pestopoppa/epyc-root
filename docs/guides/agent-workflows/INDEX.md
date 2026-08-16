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

## Scope Note (2026-08-16)

These guides are workflow depth docs, not persona prompts. The eight task-based persona files
moved to `agents/archived/` under the Loop-Owned Fleet doctrine collapse (P1-5). Guides named
after a former persona keep their name for continuity — read them as *how this kind of work is
done*, not as *who does it*. Assignment is roster id plus lane plus typed brief; see
`agents/archived/README.md`.
