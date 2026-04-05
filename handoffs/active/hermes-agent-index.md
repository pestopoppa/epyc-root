# Hermes Agent — Integration Index

**Status**: active
**Created**: 2026-03-15 (split from hermes-agent-index.md on 2026-03-20)
**Updated**: 2026-04-04
**Source**: intake-117 (hermes-agent), intake-172/173 (OpenGauss fork)
**Purpose**: Entry point for agents working on agent UX, conversation management, and external frontend integration.

---

## Agent Operating Instructions

1. Read **Outstanding Tasks** to find work items
2. Path A (outer shell) and Path B (cherry-pick) are **independent** — work either without blocking on the other
3. After completing work: update checkbox here, update handoff document, update `progress/YYYY-MM/YYYY-MM-DD.md`
4. B2 context compression must coordinate with `context-folding-progressive.md` — see Cross-Cutting Concerns

---

## Background

Hermes Agent (Nous Research) is an open-source autonomous AI agent with persistent memory, self-improving skills, and user modeling. OpenGauss (Math, Inc.) is a production fork specialized for Lean 4 theorem proving — 170 stars in 1 day, proving the architecture works for vertical domains.

Key findings from analysis (2026-03-15) and deep dive (2026-03-20):

- Memory system: 2 bounded flat files + FTS5 cross-session search + context compression via auxiliary LLM
- Skill system: mature (agentskills.io standard, hub aggregating 7 sources, security scanning pipeline)
- User modeling: Honcho (Plastic Labs) — dialectic LLM-to-LLM reasoning about user preferences
- Fully model-agnostic — works with any OpenAI-compatible endpoint via `base_url`
- OpenGauss adds: multi-backend abstraction (Claude Code + Codex), ACP server, swarm coordination, session analytics

---

## Subsystem Status

| Handoff | Path | Status | Priority | Last Updated |
|---------|------|--------|----------|-------------|
| [hermes-outer-shell.md](hermes-outer-shell.md) | A — User-Facing Shell | Phase 1 infra complete, Phase 2 config next | LOW | 2026-03-25 |
| [orchestrator-conversation-management.md](orchestrator-conversation-management.md) | B — Cherry-Pick Patterns | active, 7 work items | B1/B2 HIGH | 2026-04-04 |
| [open_source_orchestrator.md](open_source_orchestrator.md) | Future | stub (awaiting MemRL validation) | LOW | 2026-02-02 |

---

## Outstanding Tasks (Priority Order)

### P0 — Conversation Management (HIGH value, cherry-pick from Hermes/OpenGauss)

- [ ] **B1: User Modeling** — Episodic store + Deriver cron for preference extraction. ~300 lines. `src/user_modeling/` (to create)
- [ ] **B2: Context Compression** — Protected-zone (first N + last M), tool-pair sanitization, type-aware tool output summary. ~230 lines. **Must sequence after context-folding Phase 1.** `src/context_compression.py` (to create)
- [ ] **B5: Session Analytics + Token Budgeting** — `ORCHESTRATOR_MAX_SESSION_TOKENS` env var; compact at 70%, hard-stop at 100%. `src/graph/session_log.py` (extend)

### P1 — Conversation Management (MEDIUM value)

- [ ] **B6: Multi-Backend Abstraction** — Refactor llama-server management into backend interface; support vLLM/TGI
- [ ] **B7: Prompt Injection Scanning** — 10-pattern scanner from OpenGauss (~30 lines); defer until user-uploaded context

### P2 — Hermes Outer Shell (low urgency)

- [ ] Phase 2: Config tuning — user preference overrides, Hermes API parameter mappings
- [ ] Design routing API: `routing_override`, `max_escalation`, `force_model` parameters
- [ ] Auth flow for multi-user deployment

### P3 — Conversation Management (LOW value)

- [ ] **B3: Skill Hub Interop** — agentskills.io format export, security scanning
- [ ] **B4: Memory Curation Nudges** — In-session behavioral only; cross-session requires B1

### P4 — Open-Source Orchestrator (future)

- [ ] Validate MemRL routing produces measurable quality improvement
- [ ] Extract core abstractions into standalone package
- [ ] Write integration tests against Ollama + llama.cpp backends
- [ ] Publish on PyPI with minimal deps

---

## Dependency Graph

```
P0.B1 (user modeling)           ──independent──
P0.B2 (context compression)    ──depends on context-folding Phase 1──
P0.B5 (session analytics)      ──independent──
P1.B6 (multi-backend)          ──independent──
P1.B7 (injection scanning)     ──independent (defer until user uploads)──
P2 (hermes outer shell)        ──depends on orchestrator stabilization──
P3.B3 (skill hub)              ──independent──
P3.B4 (memory curation)        ──depends on B1──
P4 (open-source)               ──depends on MemRL validation──
```

---

## Cross-Cutting Concerns

1. **B2 context compression ↔ context-folding Phase 1/3b**: Both modify session compaction behavior. Context-folding Phase 1 (two-level condensation) should land first as the structural upgrade, then B2's protected-zone logic layers on top. B2's `_sanitize_tool_pairs()` could be extracted as a standalone prerequisite. **Updated 2026-04-05**: Phase 3b (role-aware compaction profiles) introduces per-role `CompactionProfile` structs — B2's role taxonomy must align with these profiles. Also tracked in `routing-and-optimization-index.md` Cross-Cutting Concern #8.

2. **B1 user modeling ↔ routing quality**: User preference data (from Honcho-style dialectic reasoning) can feed routing decisions — e.g., a user who prefers detailed explanations routes to architect more often. This feeds into `routing-intelligence.md` MemRL Q-value training data.

3. **Hermes outer shell ↔ orchestrator API stability**: The outer shell depends on a stable `/v1/chat/completions` endpoint with routing override parameters. Changes to the API contract in the orchestrator must be reflected in the Hermes adapter layer.

4. **Open-source ↔ all subsystems**: Extracting a standalone package requires generalizing the model registry, benchmark adapters, reward computation, Q-learning router, and mode selection. This is gated on MemRL validation and should not drive premature abstraction.

---

## Reporting Instructions

After completing any task:
1. Check the task checkbox in this index
2. Update the relevant handoff document
3. Add entry to `progress/YYYY-MM/YYYY-MM-DD.md`
4. If B2/B5 changes affect session compaction, flag in `routing-and-optimization-index.md` (Cross-Cutting Concern #7-8)

---

## Key File Locations

| Resource | Path |
|----------|------|
| Hermes Agent repo | `/mnt/raid0/llm/hermes-agent` |
| Hermes setup scripts | `epyc-root/scripts/hermes/` |
| Orchestrator session log | `epyc-orchestrator/src/graph/session_log.py` |
| Context compression (to create) | `epyc-orchestrator/src/context_compression.py` |
| User modeling (to create) | `epyc-orchestrator/src/user_modeling/` |
| Orchestrator API | `epyc-orchestrator/src/api/` |
| OpenGauss analysis | `research/deep-dives/opengauss-architecture-analysis.md` |
| LangGraph comparison | `research/deep-dives/langgraph-ecosystem-comparison.md` |

---

## Research Context

| Intake ID | Title | Relevance |
|-----------|-------|-----------|
| intake-117 | Hermes Agent | Original discovery |
| intake-144 | Deep Agents | Architectural parallel (LangGraph) |
| intake-145 | Agent Protocol | API standard (Runs/Threads/Store) |
| intake-171 | FormalQualBench | Agent harness benchmark |
| intake-172 | OpenGauss (blog) | Production hermes-agent fork |
| intake-173 | OpenGauss (repo) | Implementation details |
| intake-254 | Goose | Lead/worker routing, tool-output summarization |
| intake-255 | Clido | Per-session token budgeting, multi-provider profiles |

## Deep Dives

- `research/deep-dives/opengauss-architecture-analysis.md` — 10 architectural patterns identified
- `research/deep-dives/langgraph-ecosystem-comparison.md` — Agent Protocol naming alignment
