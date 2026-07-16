# Hermes Agent — Integration Index

**Status**: active
**Updated**: 2026-07-14
**Purpose**: dispatch surface for Hermes/OpenGauss-derived UX, shell, and agent-runtime work.

> Completed pre-2026-06-19 checklist and research-intake chronology was compacted to [`../archived/hermes-agent-index-history-through-2026-06-19.md`](../archived/hermes-agent-index-history-through-2026-06-19.md). Current implementation status lives in the owning handoffs below.

## Current Queue

| Priority | Work | Owner / source | Gate |
|---|---|---|---|
| MED | Reference non-Hermes client live validation | [`hermes-outer-shell.md`](hermes-outer-shell.md) Phase P | Dry-run `scripts/hermes/reference_openai_client.py` now covers `x_*`, streaming, native `tools`, and `tool_choice`; live `--send` override/streaming validation requires a quiet inference window. |
| MED | Hermes upstream pin bump and breaking-change audit | [`hermes-outer-shell.md`](hermes-outer-shell.md) P2.6 (cross-ref in hermes-outer-shell.md L278 corrected P2.5→P2.6 ✅ 2026-07-16) | `scripts/hermes/hermes_pin_audit.py` reports current pin/target/smoke gates; target choice + checkout + smoke tests require a quiet window. |
| MED | tool-use-eval-contract — journal tool-call evidence under repaired contract | [`tool-use-eval-contract.md`](tool-use-eval-contract.md) | Post-2026-07-11: REPL code-extraction repaired (`extract_code_from_response`: `<end_prompt>` stripping, unanchored Gemma thinking-channel regex; toolrunner backend crash fixed; sentinel suite 4/5 pass). Remaining = journal shows nonzero `total_tool_calls` under the repaired `8be68732` prompt contract + usefulness evidence. This starves tool-output-compression P4e telemetry (1/100 required compressed-call observations), so it is upstream of that rollout decision. Owning-handoff open item: measure read-only multi-tool chains from full logs BEFORE any parallel-batching executor work. |
| MED | Subagent + single-slot llama-server validation | [`hermes-outer-shell.md`](hermes-outer-shell.md) Phase 2 validation G | Requires controlled inference; do not overlap throughput-sensitive evidence windows. |
| LOW | Multi-user auth flow | [`hermes-outer-shell.md`](hermes-outer-shell.md) | Deferred while deployment remains single-user. |
| LOW | Open-source extraction sketch | Future/open-source track | Do not drive abstraction until MemRL/routing validation justifies it. |
| LOW | Centaur credential-egress-proxy (intake-696) — evaluate a placeholder-credential egress-proxy pattern (agents see placeholders; real secrets injected only on authorized outbound) as a credential-hygiene design note for the outer shell; see hermes-outer-shell.md RIU 2026-06-20. The other Centaur/eve/ruflo patterns are duplicative of existing work (HOS-Pattern-S / strategy_store / pi-agent hooks); ruflo federation out-of-scope. | [`hermes-outer-shell.md`](hermes-outer-shell.md) RIU 2026-06-20 | Design note only; no implementation gate (added 2026-06-20 via research-intake batch deep-dive). |

## Additional Active References

| Handoff | Current role | Next action |
|---|---|---|
| [repl-turn-efficiency.md](repl-turn-efficiency.md) | Core REPL efficiency changes landed; S4 Omega A/B remains the active gate. **GATED**: requires a quiet inference window + a MEASUREMENT.md-cited protocol run — not a silently perpetual row (owning handoff untouched 30 days as of 2026-07-14). | Measure turns/task, token cost/task, and accuracy delta before adding more REPL tool surfaces. |
| [security-review-skill.md](security-review-skill.md) | Security-review skill and slash command are landed; CI integration is deferred. | Wire CI/PR-summary gates only after a concrete enforcement workflow exists. |
| [tool-use-eval-contract.md](tool-use-eval-contract.md) | Promoted to the Current Queue (MED row above) 2026-07-14 — see there for post-2026-07-11 state. | — |

## Closed Baseline

| Area | Status |
|---|---|
| Conversation management B1-B7 | Complete; detailed history lives in [`../completed/orchestrator-conversation-management.md`](../completed/orchestrator-conversation-management.md). |
| Hermes slash-command skills and drift guard | Complete through 2026-06-14; current files under `scripts/hermes/skills/`. |
| Downstream `x_*` override plugin refactor | Complete 2026-07-06; upstream Hermes plugin command/request-hook plumbing plus EPYC `epyc-orchestrator-overrides` plugin are implemented and statically validated. Root-side regression coverage now verifies plugin command registration, session-scoped `extra_body` injection, clear semantics, and explicit `tool_choice=none` preservation. |
| Streaming + override parameter validation | Complete; keep future adapter changes compatible with string-valued override params. |
| Tool-output compression downstream port | Complete through `epyc-orchestrator` `fe64140` (P4c/P4d landed 2026-06-14/28); remaining scope per owning handoff = P4e rollout decision (awaiting >=100 compressed-call observations) + P3d A/B — see [`tool-output-compression.md`](tool-output-compression.md). |
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
- **Harness selection is an OPEN decision** (Hermes vs OpenCode vs an ACP-speaker) governed by the parent strategy index [`harness-selection-and-integration.md`](harness-selection-and-integration.md) — the orchestrator-vs-harness thesis + the cooperation→open-source requirement live there; this index and `hermes-outer-shell.md` are the **Hermes-candidate** track under it.

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

## Research Intake Update — 2026-07-08: fast-rlm Harness Patterns (rec-010)

**Source**: fast-rlm (intake-783)

**Key finding**: RecursiveLM patterns for structured agent orchestration, MCP integration, and session management. Tool inheritance boundaries and env injection patterns are applicable to our harness design.

**Harvestable patterns**:
1. **ACP integration pattern**: structured session management with tool inheritance boundaries
2. **MCP client design**: tool registry and lifecycle management
3. **Session management**: structured handoff and context preservation patterns
4. **Env injection**: controlled environment variable passing to sub-agents

**Applicability to EPYC**: These patterns are relevant to our Hermes outer shell and orchestrator API design, particularly for sub-agent delegation and tool-use patterns.

- [ ] **HA-RLM-1** — harvest ACP integration pattern for Hermes session management
- [ ] **HA-RLM-2** — evaluate MCP client design for tool-use delegation
- [ ] **HA-RLM-3** — assess env injection patterns for sub-agent orchestration
  - Note: ACP vs MCP is no longer a settled "MCP-first" lean — it is re-opened as a **harness-selection lever** owned by [`harness-selection-and-integration.md`](harness-selection-and-integration.md) HS-2 (ACP ROI could widen the field to all ACP-speaking open harnesses). Harvest patterns here; the protocol decision lives in the parent index.

## Progress checklist

- [ ] Reference non-Hermes client live --send/streaming validation (quiet window)
- [ ] Hermes upstream pin bump + breaking-change audit + smoke
- [ ] Subagent + single-slot llama-server validation (controlled inference)
- [ ] Multi-user auth flow (deferred while single-user)
- [ ] repl-turn-efficiency S4 Omega A/B measurement gate (quiet window + MEASUREMENT.md protocol)
- [ ] tool-use-eval-contract native-tools sentinel/parity + cost-aware delegation
- [ ] tool-use-eval-contract: journal nonzero total_tool_calls + usefulness evidence under repaired 8be68732 contract; measure read-only multi-tool chains from full logs before parallel-batching executor work (also unblocks tool-output-compression P4e)
- [ ] hermes-outer-shell: test x_max_escalation with full graph (depends on LangGraph migration) — hermes-outer-shell.md line ~252
- [ ] Live Hermes end-to-end smoke checklist: multi-turn, code exec, MEMORY.md persistence, latency, compression trigger, delegation (previously only implicit in the pin-bump row)
