# Hermes Agent — Integration Index

**Status**: active
**Updated**: 2026-07-06
**Purpose**: dispatch surface for Hermes/OpenGauss-derived UX, shell, and agent-runtime work.

> Completed pre-2026-06-19 checklist and research-intake chronology was compacted to [`../archived/hermes-agent-index-history-through-2026-06-19.md`](../archived/hermes-agent-index-history-through-2026-06-19.md). Current implementation status lives in the owning handoffs below.

## Current Queue

| Priority | Work | Owner / source | Gate |
|---|---|---|---|
| MED | Reference non-Hermes client live validation | [`hermes-outer-shell.md`](hermes-outer-shell.md) Phase P | Dry-run `scripts/hermes/reference_openai_client.py` now covers `x_*`, streaming, native `tools`, and `tool_choice`; live `--send` override/streaming validation requires a quiet inference window. |
| MED | Hermes upstream pin bump and breaking-change audit | [`hermes-outer-shell.md`](hermes-outer-shell.md) P2.6 | `scripts/hermes/hermes_pin_audit.py` reports current pin/target/smoke gates; target choice + checkout + smoke tests require a quiet window. |
| MED | Subagent + single-slot llama-server validation | [`hermes-outer-shell.md`](hermes-outer-shell.md) Phase 2 validation G | Requires controlled inference; do not overlap throughput-sensitive evidence windows. |
| LOW | Multi-user auth flow | [`hermes-outer-shell.md`](hermes-outer-shell.md) | Deferred while deployment remains single-user. |
| LOW | Open-source extraction sketch | Future/open-source track | Do not drive abstraction until MemRL/routing validation justifies it. |
| LOW | Centaur credential-egress-proxy (intake-696) — evaluate a placeholder-credential egress-proxy pattern (agents see placeholders; real secrets injected only on authorized outbound) as a credential-hygiene design note for the outer shell; see hermes-outer-shell.md RIU 2026-06-20. The other Centaur/eve/ruflo patterns are duplicative of existing work (HOS-Pattern-S / strategy_store / pi-agent hooks); ruflo federation out-of-scope. | [`hermes-outer-shell.md`](hermes-outer-shell.md) RIU 2026-06-20 | Design note only; no implementation gate (added 2026-06-20 via research-intake batch deep-dive). |

## Additional Active References

| Handoff | Current role | Next action |
|---|---|---|
| [repl-turn-efficiency.md](repl-turn-efficiency.md) | Core REPL efficiency changes landed; S4 Omega A/B remains the active gate. | Measure turns/task, token cost/task, and accuracy delta before adding more REPL tool surfaces. |
| [security-review-skill.md](security-review-skill.md) | Security-review skill and slash command are landed; CI integration is deferred. | Wire CI/PR-summary gates only after a concrete enforcement workflow exists. |
| [tool-use-eval-contract.md](tool-use-eval-contract.md) | Note refreshed 2026-06-28: the batched child-LLM structured-return path (`18b5ceb`) and single-delegate REPL schema path (`6426dd4`) are both shipped; a server-side delegate already exists (`chat_delegation.py`). | Real future deltas = native-tools sentinel/parity in a clean window and cost-aware capable→cheaper-worker delegation mode. |

## Closed Baseline

| Area | Status |
|---|---|
| Conversation management B1-B7 | Complete; detailed history lives in [`../completed/orchestrator-conversation-management.md`](../completed/orchestrator-conversation-management.md). |
| Hermes slash-command skills and drift guard | Complete through 2026-06-14; current files under `scripts/hermes/skills/`. |
| Downstream `x_*` override plugin refactor | Complete 2026-07-06; upstream Hermes plugin command/request-hook plumbing plus EPYC `epyc-orchestrator-overrides` plugin are implemented and statically validated. Root-side regression coverage now verifies plugin command registration, session-scoped `extra_body` injection, clear semantics, and explicit `tool_choice=none` preservation. |
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
| Hermes EPYC plugins | `scripts/hermes/plugins/` |
| Hermes launch config | `scripts/hermes/config.example.yaml`, `scripts/hermes/launch.sh` |
| Orchestrator API | `/mnt/raid0/llm/epyc-orchestrator/src/api/` |

## Reporting

After completing a row, update the owning handoff, this index, and `progress/YYYY-MM/YYYY-MM-DD.md`. If the work changes orchestrator API behavior, also update `routing-and-optimization-index.md`.
