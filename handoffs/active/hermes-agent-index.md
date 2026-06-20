# Hermes Agent — Integration Index

**Status**: active
**Updated**: 2026-06-19
**Purpose**: dispatch surface for Hermes/OpenGauss-derived UX, shell, and agent-runtime work.

> Completed pre-2026-06-19 checklist and research-intake chronology was compacted to [`../archived/hermes-agent-index-history-through-2026-06-19.md`](../archived/hermes-agent-index-history-through-2026-06-19.md). Current implementation status lives in the owning handoffs below.

## Current Queue

| Priority | Work | Owner / source | Gate |
|---|---|---|---|
| MED | Hermes upstream pin bump and breaking-change audit | [`hermes-outer-shell.md`](hermes-outer-shell.md) P2.6 | File-inspection items can run now; smoke tests require an inference window. |
| MED | Downstream `x_*` override refactor | [`hermes-outer-shell.md`](hermes-outer-shell.md) Phase 2+ enhancement | Preserve `/v1/chat/completions` compatibility; coordinate with orchestrator API changes. |
| MED | Subagent + single-slot llama-server validation | [`hermes-outer-shell.md`](hermes-outer-shell.md) Phase 2 validation G | Requires controlled inference; do not overlap throughput-sensitive evidence windows. |
| LOW | Multi-user auth flow | [`hermes-outer-shell.md`](hermes-outer-shell.md) | Deferred while deployment remains single-user. |
| LOW | Open-source extraction sketch | Future/open-source track | Do not drive abstraction until MemRL/routing validation justifies it. |

## Additional Active References

| Handoff | Current role | Next action |
|---|---|---|
| [repl-turn-efficiency.md](repl-turn-efficiency.md) | Core REPL efficiency changes landed; S4 Omega A/B remains the active gate. | Measure turns/task, token cost/task, and accuracy delta before adding more REPL tool surfaces. |
| [security-review-skill.md](security-review-skill.md) | Security-review skill and slash command are landed; CI integration is deferred. | Wire CI/PR-summary gates only after a concrete enforcement workflow exists. |

## Closed Baseline

| Area | Status |
|---|---|
| Conversation management B1-B7 | Complete; detailed history lives in [`../completed/orchestrator-conversation-management.md`](../completed/orchestrator-conversation-management.md). |
| Hermes slash-command skills and drift guard | Complete through 2026-06-14; current files under `scripts/hermes/skills/`. |
| Streaming + override parameter validation | Complete; keep future adapter changes compatible with string-valued override params. |
| Tool-output compression downstream port | Complete through `epyc-orchestrator` `fe64140`; remaining telemetry/registration gates live in [`tool-output-compression.md`](tool-output-compression.md). |
| Open-source orchestrator stub | Archived; do not re-add without a new concrete extraction target. |

## Dependency Graph

```text
Hermes upstream pin bump
  -> breaking-change checklist
  -> inference smoke: basic chat / tool use / streaming / override / multi-turn

Orchestrator API changes
  -> update Hermes adapter docs and skills
  -> rerun drift checks

Context compression or tool-output changes
  -> coordinate with context-folding-progressive.md and tool-output-compression.md
```

## Cross-Cutting Concerns

- Hermes integration is external to the upstream checkout: keep EPYC customization in `scripts/hermes/` and orchestrator override surfaces rather than forking upstream code without a deliberate branch plan.
- The outer shell depends on stable `/v1/chat/completions` routing override parameters. API contract changes must be reflected in Hermes skill docs and drift checks.
- Context-compression changes overlap with `context-folding-progressive.md`; use one compaction policy owner per change.
- Skill and tool-output changes overlap with `tool-output-compression.md`; report token/latency claims with the measurement grammar.

## Key Files

| Resource | Path |
|---|---|
| Hermes upstream checkout | `/mnt/raid0/llm/hermes-agent` |
| EPYC Hermes setup | `scripts/hermes/` |
| Hermes skills | `scripts/hermes/skills/` |
| Hermes launch config | `scripts/hermes/config.example.yaml`, `scripts/hermes/launch.sh` |
| Orchestrator API | `/mnt/raid0/llm/epyc-orchestrator/src/api/` |

## Reporting

After completing a row, update the owning handoff, this index, and `progress/YYYY-MM/YYYY-MM-DD.md`. If the work changes orchestrator API behavior, also update `routing-and-optimization-index.md`.
