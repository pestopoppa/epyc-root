# Agent Workflows

Operational detail for *how a kind of work is done* lives here, not in agent prompts.

## Guides

- `docs/guides/agent-workflows/research-writer.md`
- `docs/guides/agent-workflows/benchmark-analyst.md`
- `docs/guides/agent-workflows/safety-reviewer.md`
- `docs/guides/agent-workflows/verification-failure-catalogue.md` — eight measured ways a check passes for the WRONG reason, each with its own tell and test; mutation-test the guard, and confirm the mutation is visible AND counted
- `docs/guides/agent-workflows/coordinator-escalation.md` — the canonical ladder for unreachable sessions, guard refusals and nudge rate limits, with its timer constants; four other files defer to it as the full ladder
- `docs/guides/agent-workflows/handoff-index-authoring.md` — the thin-row contract for authoring and editing handoff domain indices: an index is a dispatch surface, not a status report or an evidence ledger
- `docs/guides/agent-workflows/orchestrator-lifecycle.md` — lifecycle and stabilization-closure guidance for orchestrator work in `epyc-orchestrator`: API-only reload, contention probes, response diagnostics as acceptance criteria
- `docs/guides/agent-workflows/test-suite-conventions.md` — the two measured vacuous-pass shapes, the `test_*.py` = must-be-collectable naming rule, the sanctioned bridge stanzas, and why an exemption can be correct

## Design Rule

- Keep `agents/*.md` concise and scoped to the roster roles assigned in
  `coordination/session-bus/config.yaml` (`main`, `coordinator-agent`, `reviewer`, `retired`,
  `service`) — not to task personas; splitting work into per-task personas is a measured
  anti-pattern (`agents/shared/OPERATING_CONSTRAINTS.md` → *Parallel Subagent Fan-Out*, "When NOT
  to fan out").
- Keep durable, procedure-heavy guidance in this folder.

## Scope Note (2026-08-16)

These guides are workflow depth docs, not persona prompts. The eight task-based persona files
moved to `agents/archived/` under the Loop-Owned Fleet doctrine collapse (P1-5). Guides named
after a former persona keep their name for continuity — read them as *how this kind of work is
done*, not as *who does it*. Assignment is roster id plus lane plus typed brief; see
`agents/archived/README.md`.
