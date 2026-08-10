# Historical ledger — superseded index narration (through 2026-08-10)

> **Historical ledger only; current work lives in [`../active/hermes-agent-index.md`](../active/hermes-agent-index.md).**
> Extracted 2026-08-10 in the index restructure: rows became thin and machine-parseable (`ID | Track | Handoff | Next action | Deps`), and status moved to generated state (`handoffs/active/.index-state.json` + the rollup block in `master-handoff-index.md`).
>
> Everything below is the index content **verbatim as of 2026-08-10**, preserved for provenance: closed rows, evidence citations, retracted rows, and campaign narration. It is not a task list — do not dispatch from it. Where a row here contradicts the active index, the active index wins.

---

# Hermes Agent — Integration Index

**Status**: active
**Updated**: 2026-07-21
**Purpose**: dispatch surface for Hermes/OpenGauss-derived UX, shell, and agent-runtime work.

> Completed pre-2026-06-19 checklist and research-intake chronology was compacted to [`../archived/hermes-agent-index-history-through-2026-06-19.md`](../archived/hermes-agent-index-history-through-2026-06-19.md). Current implementation status lives in the owning handoffs below.

## Current Queue

| Priority | Work | Owner / source | Gate |
|---|---|---|---|
| MED | Reference non-Hermes client live validation | [`hermes-outer-shell.md`](hermes-outer-shell.md) Phase P | Standalone Hermes `8099` `--send --stream` smoke passed 2026-07-21; the orchestrator `8000` override-semantics validation is still open. |
| MED | Hermes upstream pin bump and breaking-change audit | [`hermes-outer-shell.md`](hermes-outer-shell.md) P2.6 (cross-ref in hermes-outer-shell.md L278 corrected P2.5→P2.6 ✅ 2026-07-16) | Smoke harness passed 2026-07-21, but no upstream checkout was performed. Current `/mnt/raid0/llm/hermes-agent` is `main...origin/main [ahead 1]`; target selection/checkout remains open. |
| MED | tool-use-eval-contract — journal tool-call evidence under repaired contract | [`tool-use-eval-contract.md`](tool-use-eval-contract.md) | Post-2026-07-11: REPL code-extraction repaired (`extract_code_from_response`: `<end_prompt>` stripping, unanchored Gemma thinking-channel regex; toolrunner backend crash fixed; sentinel suite 4/5 pass). Remaining = journal shows nonzero `total_tool_calls` under the repaired `8be68732` prompt contract + usefulness evidence. This starves tool-output-compression P4e telemetry (1/100 required compressed-call observations), so it is upstream of that rollout decision. Owning-handoff open item: measure read-only multi-tool chains from full logs BEFORE any parallel-batching executor work. |
| DONE | Subagent + single-slot llama-server validation | [`hermes-outer-shell.md`](hermes-outer-shell.md) Phase 2 validation G | Closed 2026-07-21: `BULK-hermes-smokes-20260721T042834Z` passed 2/2 parallel subagents on one `8099` slot, with cleanup returning to quiet. |
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

- [x] **HA-RLM-1** — harvest ACP integration pattern for Hermes session management ✅ 2026-07-17 (B4, source-not-cloned → design-note from held artifacts): the concrete ACP prior art we hold is **OpenGauss `acp_adapter/server.py`** (session CRUD/**fork**/cancel, provider-based runtime credentials, structured tool/thinking/step/message callbacks, ThreadPool exec) — a *north-facing* editor↔agent adapter, NOT an inference surface. fast-rlm's own "session management" is the RLM-REPL-as-session model (context = a persistent REPL the sub-LM writes into), not an ACP server. **Net-new lift ≈ 0 for cooperation**: per HS-2 (B4), ACP does not change Hermes deference (which is `/v1`-body-injection, already landed). Harvest = *if* an ACP north adapter is ever wanted, reuse OpenGauss's `acp_adapter/` pattern (session fork + sanitized-tool-pair callbacks) on the Hermes core; gate on HS-2's Path-B trigger.
- [x] **HA-RLM-2** — evaluate MCP client design for tool-use delegation ✅ 2026-07-17 (B4): fast-rlm's transferable tool/delegation pattern is **schema-validated structured returns** (validate-on-`FINAL`, retry-not-restart, structured-return-as-attention-mask — intake-693), which is **ALREADY SHIPPED** in the orchestrator (`final_schema_validation`; `batch_llm_query(schema=)` `18b5ceb`; single `delegate(schema=)` `6426dd4`) — see tool-use-eval-contract.md 2026-06-27 update. Orchestrator already exposes an **MCP server** (`mcp__orchestrator__*`), so MCP-first is de-facto. **Net-new lift ≈ 0**; no separate fast-rlm MCP client to import. Residual optional follow-up = schema parity on the HTTP `/api/delegate` surface (still schema-free), already logged there.
- [x] **HA-RLM-3** — assess env injection patterns for sub-agent orchestration ✅ 2026-07-17 (B4): the sub-agent env/credential **inheritance boundary** is the harvestable pattern, and Hermes already implements the right shape — `delegate_task` children are `AIAgent`s that **inherit the parent `base_url`/api_key/toolsets** (`hermes-agent/tools/delegate_tool.py:157-188`, `MAX_DEPTH=2`), so each child re-fires `pre_llm_call` and defers to the Orch per-turn (A4 / HS-1b). Complementary held prior art = OpenGauss's per-backend credential/MCP-config/env staging (`autoformalize.py` `ManagedContext`). **Net-new lift ≈ 0** for the current single-host design; the only design note worth carrying is the credential-**placeholder egress** pattern (intake-696) already tracked in the Current-Queue LOW row — real secrets injected only on authorized outbound, sub-agents see placeholders. **Net-new lift ≈ 0.**
  - Note: ACP vs MCP is no longer a settled "MCP-first" lean — it is re-opened as a **harness-selection lever** owned by [`harness-selection-and-integration.md`](harness-selection-and-integration.md) HS-2 (ACP ROI could widen the field to all ACP-speaking open harnesses). Harvest patterns here; the protocol decision lives in the parent index. **RESOLVED 2026-07-17 (B4): HS-2 ROI = LOW → MCP-first stands; ACP = optional Path-B north adapter (see harness-selection-and-integration.md HS-2 findings + `research/acp-roi-analysis-2026-07.md`). The harvested patterns above are all already-shipped or ≈0-lift; no new component to import from fast-rlm.**

## Progress checklist

- [ ] Reference non-Hermes client live --send/streaming validation (quiet window)
  - [x] Standalone Hermes `8099` reference-client `--send --stream` smoke ✅ 2026-07-21 (`BULK-hermes-smokes-20260721T042834Z`, final 13/13)
  - [ ] Orchestrator `8000` override-semantics validation: role override, force-model, escalation cap, REPL disable, routing metadata, streaming
- [ ] Hermes upstream pin bump + breaking-change audit + smoke
  - [x] Standalone smoke harness and pin-audit leg validated ✅ 2026-07-21 (`BULK-hermes-smokes-20260721T042834Z`, final 13/13)
  - [ ] Actual upstream target selection/fetch/checkout/setup remains open; current Hermes checkout is ahead of `origin/main`
- [x] Subagent + single-slot llama-server validation (controlled inference) ✅ 2026-07-21 (`BULK-hermes-smokes-20260721T042834Z`, 2/2 parallel subagents, one slot, no wedge)
- [ ] Multi-user auth flow (deferred while single-user)
- [ ] repl-turn-efficiency S4 Omega A/B measurement gate (quiet window + MEASUREMENT.md protocol)
- [ ] tool-use-eval-contract native-tools sentinel/parity + cost-aware delegation
- [ ] tool-use-eval-contract: journal nonzero total_tool_calls + usefulness evidence under repaired 8be68732 contract; measure read-only multi-tool chains from full logs before parallel-batching executor work (also unblocks tool-output-compression P4e)
  - **Read-only multi-tool-chain measurement DONE ✅ 2026-07-17 (B4)** — ran `mine_repl_patterns.py` read-only over the full 3187-record `seeding_diagnostics.jsonl`: 807 REPL rows, 117 REPL+tools (14.5%), **30 multi-tool (3.7%), 30/30 read-only, 0/30 parallelized**, and all 30 are the identical `web_search×3` shape (2 per suite × 15 suites = synthetic, not organic). **Build-or-not verdict: NO-BUILD** a new parallel-batching REPL executor (existing `execute_parallel_calls()` already covers the batchable case and goes unused; independence unprovable from this log). Full block in [`tool-use-eval-contract.md`](tool-use-eval-contract.md) "Tool-Use Chain Analysis — 2026-07-17 (B4)". **The `journal nonzero total_tool_calls + usefulness` half remains OPEN (inference-gated)**, so this box stays unchecked.
- [ ] hermes-outer-shell: test x_max_escalation with full graph (depends on LangGraph migration) — hermes-outer-shell.md line ~252
- [ ] Live Hermes end-to-end smoke checklist: multi-turn, code exec, MEMORY.md persistence, latency, compression trigger, delegation (previously only implicit in the pin-bump row)
  - [x] P-SMOKE-1 standalone subset: health/chat/tool schema/streaming/override/multi-turn/reference-client/subagent ✅ 2026-07-21 (`BULK-hermes-smokes-20260721T042834Z`)
  - [ ] Hermes CLI-level code execution, `MEMORY.md` persistence, latency, and compression-trigger checks remain open.
