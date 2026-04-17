# Hermes Agent — Integration Index

**Status**: active
**Created**: 2026-03-15 (split from hermes-agent-index.md on 2026-03-20)
**Updated**: 2026-04-12
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
| [hermes-outer-shell.md](hermes-outer-shell.md) | A — User-Facing Shell | Phase 2 routing API done, skills done, streaming validated (Package E). Auth deferred. | LOW | 2026-04-08 |
| [orchestrator-conversation-management.md](orchestrator-conversation-management.md) | B — Cherry-Pick Patterns | ALL COMPLETE (B1-B7 + integration wiring) | Done | 2026-04-05 |
| ~~[open_source_orchestrator.md](../archived/open_source_orchestrator.md)~~ | Future | ARCHIVED (dormant stub, 71 days) | — | 2026-02-02 |

---

## Outstanding Tasks (Priority Order)

### P0 — Conversation Management (HIGH value, cherry-pick from Hermes/OpenGauss)

- [x] **B1: User Modeling** — ✅ 2026-04-05. `src/user_modeling/` package (profile_store, deriver, tools). 18 tests.
- [x] **B2: Context Compression** — ✅ 2026-04-05. `src/context_compression.py` (protected-zone, tool-pair sanitization, type-aware output). 22 tests.
- [x] **B5: Session Analytics + Token Budgeting** — ✅ 2026-04-05. `src/session_analytics.py` (SessionTokenBudget, analytics queries). 12 tests.

### P1 — Conversation Management (MEDIUM value)

- [x] **B6: Multi-Backend Abstraction** — ✅ 2026-04-05. `src/backends/server_lifecycle.py` (ServerLifecycle Protocol, llama/vLLM/TGI). 18 tests.
- [x] **B7: Prompt Injection Scanning** — ✅ 2026-04-05. `src/security/injection_scanner.py` (10 patterns + invisible unicode). 16 tests.

### P2 — Hermes Outer Shell (low urgency)

- [x] Phase 2: Config tuning — ✅ 2026-04-05. Config parameter mapping documented in handoff. Effective vs no-op params identified.
- [x] Design routing API — ✅ 2026-04-05. 3 new fields on `OpenAIChatRequest`: `x_max_escalation`, `x_force_model`, `x_disable_repl`. Wired in `openai_compat.py`. Slash command → API mapping documented.
- [ ] Auth flow for multi-user deployment — deferred (single-user only for now)
- [x] Hermes skill YAML files for `/use`, `/escalation`, `/nocode` commands — ✅ 2026-04-08. Three SKILL.md files in `scripts/hermes/skills/` (use/, escalation/, nocode/). Maps slash commands to `x_*` API override parameters.
- [x] Streaming + override param validation — ✅ 2026-04-06 (Package E). SSE streaming works, `x_force_model`/`x_max_escalation`/`x_disable_repl` validated. Note: override params must be strings, not ints.

### P3 — Conversation Management (LOW value)

- [x] **B3: Skill Hub Interop** — ✅ 2026-04-05. `src/skill_hub_interop.py` (SKILL.md parse/export, security scan). 13 tests.
- [x] **B4: Memory Curation Nudges** — ✅ 2026-04-05. Frontdoor prompt updated to use `user_conclude()` for cross-session persistence.

### P2.5 — Research-Driven Improvements (from 2026-04-12 intake)

- [x] H-8: Prototype MemPalace MCP integration with Hermes outer shell — `claude mcp add mempalace -- python -m mempalace.mcp_server`. 19 tools (palace reads, writes, KG, navigation, agent diary). Local-first (ChromaDB+SQLite), MIT. Gives Hermes persistent cross-session memory with 96.6% LongMemEval recall. Source: intake-326. -- Done 2026-04-12. Setup script at scripts/hermes/mempalace_setup.sh. MCP server config documented in hermes-config.yaml.
- [x] H-9: Add anti-rationalization tables to agent governance skills — adopt pattern from intake-337 (addyosmani/agent-skills). Each SKILL.md gets a "Rationalizations" section with excuse|rebuttal table to prevent LLM shortcutting of quality gates. Priority skills: research-intake, agent-file-architecture. Also tracked in non-inference-backlog Task 8. — ✅ 2026-04-12. Verification gates + anti-rationalization tables added to research-intake and agent-file-architecture SKILL.md.

### P4 — Open-Source Orchestrator (future)

- [ ] Validate MemRL routing produces measurable quality improvement
- [ ] Extract core abstractions into standalone package
- [ ] Write integration tests against Ollama + llama.cpp backends
- [ ] Publish on PyPI with minimal deps

---

## Dependency Graph

```
✅ P0.B1 (user modeling)        ──DONE (2026-04-05)──
✅ P0.B2 (context compression)  ──DONE (2026-04-05)──
✅ P0.B5 (session analytics)    ──DONE (2026-04-05)──
✅ P1.B6 (multi-backend)        ──DONE (2026-04-05)──
✅ P1.B7 (injection scanning)   ──DONE (2026-04-05)──
P2 (hermes outer shell)        ──Phase 2 near-complete (skills + streaming done, auth deferred)──
✅ P3.B3 (skill hub)            ──DONE (2026-04-05)──
✅ P3.B4 (memory curation)      ──DONE (2026-04-05)──
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
| MemPalace MCP setup | `epyc-root/scripts/hermes/mempalace_setup.sh` |
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

## Research Intake Update — 2026-04-12

### New Related Research
- **[intake-327] "Hermes Agent Self-Evolution"** (NousResearch/hermes-agent-self-evolution)
  - Relevance: Official Nous Research project for evolutionary improvement of Hermes Agent skills using DSPy+GEPA
  - Key technique: Reflective evolutionary search optimizing skills, tool descriptions, and prompts ($2-10/run via API)
  - Delta from current approach: Our Hermes integration focuses on cherry-picking patterns. This repo enables automated self-improvement of Hermes skills. MIT license. Multi-phase: skills (done), tools/prompts/code (planned).
- **[intake-337] "Agent Skills"** (addyosmani/agent-skills)
  - Relevance: Production engineering workflows (7 phases, 20 skills, anti-rationalization tables)
  - Key technique: Process-not-prose skill design with evidence-based verification gates
  - Delta from current approach: The anti-rationalization tables are a novel pattern — explicitly countering excuses for skipping quality gates. Worth reviewing for our skill/agent governance design.

## Deep Dives

- `research/deep-dives/opengauss-architecture-analysis.md` — 10 architectural patterns identified
- `research/deep-dives/langgraph-ecosystem-comparison.md` — Agent Protocol naming alignment

## Research Intake Update — 2026-04-17

### New Related Research
- **[intake-388] "Hermes Agent Reasoning Traces"** (huggingface.co/datasets/lambda/hermes-agent-reasoning-traces)
  - Relevance: 14,701 multi-turn tool-calling trajectories from Hermes Agent harness. Real tool execution (terminal, file ops, browser), not synthetic. Two configs: Kimi-K2.5 (7,646 samples, avg 24.3 turns) and GLM-5.1 (7,055 samples, avg 19.1 turns). Apache 2.0.
  - Key technique: ShareGPT format with `<think>` reasoning blocks + `<tool_call>` invocations + `<tool_response>` results. 9 task categories including Terminal & Coding, Repository Tasks, Browser Automation.
  - Delta from current approach: Our Hermes integration focuses on cherry-picking architectural patterns. This dataset provides real agent behavior traces that could be used for fine-tuning local models on agentic tool use — directly complementing the outer shell work.
- **[intake-393] "Hermes Agent Traces Filtered"** (huggingface.co/datasets/DJLougen/hermes-agent-traces-filtered)
  - Relevance: Quality-filtered subset (3,679 of 7,646 rows, ~48% kept). Filtered on reasoning depth, structural integrity, tool-call JSON validity, deliberate tool selection reasoning, self-correction patterns. 14x deeper think blocks, 2x self-correction rate.
  - Delta: Higher quality for fine-tuning — removes trivial/noisy traces. Designed as Stage 2 dataset on top of strong reasoning models.
