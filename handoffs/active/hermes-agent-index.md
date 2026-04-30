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

### P2.6 — Upstream Release Integration (from 2026-04-24 intake-454 deep-dive)

Source: [`research/deep-dives/hermes-agent-v2026-4-23-release.md`](../../research/deep-dives/hermes-agent-v2026-4-23-release.md). Major upstream release (v0.11.0 / v2026.4.23): 1,556 commits / 761 PRs / 29 contributors since v0.9.0. **Key finding from deep-dive**: `/mnt/raid0/llm/hermes-agent` is NOT a fork — it tracks upstream cleanly with only an untracked `HERMES.md`. All EPYC customization is external (`scripts/hermes/` + orchestrator `x_*` overrides). Recommendation: bump the pin, do not rebase.

- [ ] **P2.6.1 — D — Pin bump v2026.3.23 → v2026.4.23** (~2–4 h; bare checkout = no inference, smoke tests = inference)
  - Currently pinned at `v2026.3.23-43-ge5691eed` per `git -C /mnt/raid0/llm/hermes-agent describe --tags`
  - Steps: `git -C /mnt/raid0/llm/hermes-agent fetch && git -C /mnt/raid0/llm/hermes-agent checkout v2026.4.23` + re-run `scripts/hermes/setup.sh` (or current setup script)
  - Smoke-test 5 validation scenarios (basic chat / tool use / streaming / one `x_*` override / multi-turn) — **REQUIRES INFERENCE — Wave 2**
- [ ] **P2.6.2 — H-verify breaking-change checklist** (mostly file inspection — non-inference; one item needs running model)
  - [ ] Config schema diff: `diff scripts/hermes/config.example.yaml <new release example config>` — flag any new required keys (`max_spawn_depth`, plugin config, execution mode candidates per deep-dive)
  - [ ] state.db VACUUM behavior: confirm first-startup VACUUM delay does not exceed expected window; consider pre-warming or background VACUUM in setup script
  - [ ] Slash-command namespace clash: scan our `scripts/hermes/skills/*/SKILL.md` for `/steer`, `/clear`, `/use`, `/escalation`, `/nocode` etc. — confirm none collide with new upstream native commands
  - [ ] Ink TUI CLI contract: verify our scripted/headless invocations of `hermes` (in `scripts/hermes/launch.sh` and similar) still work with the Ink rewrite — flag any changed flags/exit-codes
  - [ ] ChatCompletions transport refactor probe: hit our orchestrator's `/v1/chat/completions` with the new client — **REQUIRES INFERENCE — Wave 2**
  - [ ] Compressor fallback-chain interaction: confirm the new fallback chain does not conflict with our `provider: "main"` auxiliary config; inspect config-loading order
- [ ] **P2.6.3 — Downstream port to compressor** — see [`tool-output-compression.md`](tool-output-compression.md) Phase 3d (E)
- [ ] **P2.6.4 — Downstream refactor of `x_*` overrides** — see [`hermes-outer-shell.md`](hermes-outer-shell.md) Phase 2+ Enhancement (F)
- [ ] **P2.6.5 — Subagent + single-slot llama-server validation** — see [`hermes-outer-shell.md`](hermes-outer-shell.md) Phase 2 Validation (G); **REQUIRES INFERENCE — Wave 2**

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

## Research Intake Update — 2026-04-17

### New Related Research (Agent Architecture Cluster)

- **[intake-394] "Evolver: GEP-Powered Self-Evolution Engine for AI Agents"** (repo: EvoMap/evolver)
  - Relevance: Hermes self-evolution governance — auditable Gene/Capsule/EvolutionEvent JSONL assets, strategy-preset intent mixer, protected-source-files safety pattern.
  - Delta: pattern comparison against our PromptForge/GEPA (intake-327) and MiniMax-M2.7 self-evolution (intake-328) lineage. Not a component adoption.

- **[intake-395] "Claude-Mem: Persistent Memory Compression System for Claude Code"** (repo: thedotmack/claude-mem)
  - Relevance: Hermes memory / LLM-Wiki cluster — productionized 3-layer MCP retrieval (search → timeline → get_observations) with ~10x token savings claim; lifecycle-hook capture taxonomy.
  - Delta: adopt patterns only (AGPL-3.0, Bun/Node); overlaps intake-135 (Cognee), intake-268–270 (Karpathy LLM Wiki ecosystem), intake-277 (Hermes LLM Wiki skill), intake-321 (Karpathy CLAUDE.md).

- **[intake-397] "Open Agents — Vercel-Labs Reference App"** (repo: vercel-labs/open-agents)
  - Relevance: outer-shell / durable-workflow reference — agent outside sandbox, Workflow SDK reconnect-to-stream, snapshot-based resume.
  - Delta: TS/Vercel stack; pattern extraction only. See hermes-outer-shell.md for detailed mapping.

- **[intake-399] "GenericAgent: minimal self-evolving autonomous agent framework"** (repo: lsdefine/GenericAgent)
  - Relevance: minimalism constraint (~3K LOC, 100-line loop, 9 atomic tools, <30K context) + L0–L4 memory taxonomy directly adjacent to Hermes + MemPalace (intake-326) architecture.
  - Delta: design-space anchor for Hermes loop minimality and a concrete 5-tier memory taxonomy template.

## Research Intake Update — 2026-04-18

### New Related Research

- **[intake-411] "Qwen-Agent — Agent Framework by Alibaba/Qwen"** (repo: QwenLM/Qwen-Agent)
  - Relevance: Reference agent framework (16.1k stars, Apache-2.0) with MCP server integration, parallel function calling, Docker-sandboxed code interpreter, and RAG for 1M-token contexts. Directly comparable to Hermes outer-shell architecture.
  - Key patterns: MCP-first tool ecosystem, Gradio-based GUI for rapid deployment, DashScope + OpenAI-compatible model backends (vLLM, Ollama).
  - Delta from current approach: Hermes uses persistent memory + self-improving skills (deeper autonomy); Qwen-Agent is more framework-oriented (broader tool ecosystem, MCP-native). The parallel function calling and MCP integration patterns are reference-quality for hermes-outer-shell.md Phase 2 routing API. Not adopt_component (Alibaba DashScope dependency, Python-only).

- **[intake-412] "DeepPlanning: Benchmarking Long-Horizon Agentic Planning"** (arxiv:2601.18137)
  - Relevance: Benchmark for multi-step agent planning with verifiable constraints (travel + shopping domains). 26 models evaluated. Even GPT-5.2-high only achieves 44.6% case accuracy — frontier models struggle with global constraint optimization.
  - Key insight: Reasoning-equipped models consistently outperform non-reasoning variants. Parallel tool use improves effectiveness-efficiency trade-offs. Rule-based automated scoring (not LLM-based eval).
  - Delta: Evaluation methodology for agent planning quality — potential benchmark addition for assessing orchestrator planning capabilities. Cross-refs ch07 benchmark construction philosophy.

## Research Intake Update — 2026-04-24

### New Related Research

- **[intake-450] "Venice Skills — Agent Skills for the Venice.ai API"** (`github.com/veniceai/skills`)
  - Relevance: canonical cross-runtime SKILL.md authoring style guide; Hermes is a first-class target runtime per their docs (`$HERMES_OPTIONAL_SKILLS_DIR` / `~/.hermes/skills/`).
  - Key technique: OpenAPI→SKILL.md drift-detection via `sync_from_swagger.py` (nightly CI); ≤500-line authoring rubric (short lead, endpoint tables, curl+SDK, gotchas).
  - Delta: reference implementation of the same cross-runtime pattern we use (`.claude/skills/` + `scripts/hermes/skills/`); adopt the drift-detection and authoring rubric — ignore the Venice API surface (commercial, non-OSS).

- **[intake-451] "Meta-Harness (official reference code)"** (`github.com/stanford-iris-lab/meta-harness`)
  - Relevance: runnable companion code for intake-244 that drives `meta-harness-optimization.md`. Ships ONBOARDING.md + `domain_spec.md` template + two reference experiments (text_classification, terminal_bench_2) + `claude_wrapper.py` proposer integration.
  - Key technique: agent-tasks scaffold evolution on terminal_bench_2 is the closest analog to our code-mutation search space.
  - Delta: cherry-pick — do not wholesale port. Repo explicitly disclaims "not tested beyond verifying it runs"; Tier-1/2 local implementation already exists.

- **[intake-454] "hermes-agent v2026.4.23 (v0.11.0)"** (`github.com/NousResearch/hermes-agent/releases/tag/v2026.4.23`)
  - Relevance: major release (1,556 commits / 761 PRs / 29 contributors since v0.9.0) — not a bugfix. Introduces orchestrator-role subagents with cross-agent file-state coordination, `/steer` mid-run correction, compressor anti-thrashing + language-aware + fallback chain, plugin execution-veto/result-transform hooks, transport-layer abstraction.
  - Key technique: cross-agent file-state locking for parallel subagent spawn; 5 new inference transports (Gemini CLI OAuth, NIM, ai-gateway, etc.); 12 MCP improvements including CDP raw passthrough.
  - Delta: we run a hermes-agent fork — this release is a major merge target. Individual patterns (compressor anti-thrashing, plugin hooks, /steer) map 1:1 to active handoffs (tool-output-compression, context-folding-progressive, meta-harness-optimization). MIT-licensed, no SaaS deps.

## Research Intake Update — 2026-04-26

### New Related Research

- **[intake-473] "@mariozechner/pi-agent-core — Stateful TypeScript Agent Runtime"** (`github.com/badlogic/pi-mono/tree/main/packages/agent`)
  - Relevance to this index: pi-agent-core is the closest *runtime-layer* analogue to what our outer-shell layer (Path A) does — stateful Agent class, tool execution, event streaming, no built-in tools or memory tier (those are explicitly out of scope per project README, which positions it below a coding-agent harness). Maps to hermes-outer-shell update; ripples patterns into tool-output-compression, context-folding-progressive, repl-turn-efficiency, meta-harness-optimization.
  - Key technique families lifted into child handoffs:
    - **Two-stage message pipeline** (`transformContext` + `convertToLlm` with declaration-merging custom message types) → context-folding-progressive, hermes-outer-shell.
    - **`beforeToolCall` / `afterToolCall` field-replace + throw-isolation** → tool-output-compression, meta-harness-optimization.
    - **Steering vs follow-up split with `one-at-a-time` / `all` queue modes** → repl-turn-efficiency.
    - **`streamFn` injection point + `streamProxy()` delta-only wire format** → hermes-outer-shell (drop-in candidate for Package E streaming).
  - Source credibility: 80+ contributors (Mario Zechner / badlogic primary, **Armin Ronacher top-5**), 3,805 commits since 2025-08-09, ~70 versions, formal CHANGELOG with `closes #N`, ~1:1 test/source ratio. Not an indie project. Initial intake estimate (single-author indie) was wrong.
  - Delta: no immediate cross-cutting action at the index level — concrete adoption decisions belong in each child handoff. This entry exists so a future agent landing on the index sees that pi-agent-core has cross-handoff implications and that the per-handoff lifts share a single deep-dive document (`research/deep-dives/pi-agent-core-stateful-ts-runtime.md`).

## Research Intake Update — 2026-04-30

### New Related Research

- **[intake-509] "Skills For Real Engineers — Matt Pocock's Claude Code skills collection"** (`github.com/mattpocock/skills`)
  - Index-level relevance: a second cross-runtime SKILL.md installer pattern in our intake (sibling to intake-450 veniceai/skills via the same `npx skills@latest add ...` distribution channel). Both target multiple coding-agent runtimes from one source repo. For the hermes-agent index this is a packaging-layer datapoint — it confirms that an externally-authored, single-author-curated skills bundle is the going pattern in the ecosystem, not just a one-off (veniceai). Worth tracking as we plan `scripts/hermes/skills/` packaging conventions.
  - Per-child-handoff lifts (concrete patterns harvested per child):
    - **meta-harness-optimization** → four-failure-mode taxonomy as harness-evaluation gates; `CONTEXT.md`/ADR maintenance as a search axis on the shared-language artifact (complements Flywheel intake-492's write-contract).
    - **tool-output-compression** → `/caveman` token-compression skill as a baseline-to-beat for our compressors (self-reported ~75% reduction; no methodology — anecdotal until we measure).
    - **repl-turn-efficiency** → `/caveman` and the explicit *verbosity* failure-mode framing pair with the queue-mode work (steer / follow-up).
    - **hermes-outer-shell** → SKILL.md cross-runtime installer pattern + `/setup-matt-pocock-skills` per-repo bootstrap config skill.
  - Source credibility: known TypeScript-community practitioner (Matt Pocock); MIT-licensed; no empirical claims (credibility_score null). Pattern adoption only — nothing to fork or cherry-pick.
  - Delta from prior pi-agent-core (intake-473) entry: pi-agent-core lives at the *runtime layer* (Agent class, tool execution, streaming); Pocock's collection lives at the *skill / prompt layer* upstream of that. They compose — pi-agent-core would *execute* skills shaped like Pocock's. Useful pair for outer-shell design discussions.

- **[intake-508] "DeepSeek TUI — Terminal-native coding agent for DeepSeek V4"** (`github.com/Hmbown/DeepSeek-TUI`)
  - Index-level relevance: low. Closed DeepSeek-API-only Rust TUI shell — no offline / GGUF / llama.cpp path. UX-pattern overlap only.
  - Per-child-handoff lift: **hermes-outer-shell** picks up the only meaningful overlap (Plan/Agent/YOLO three-tier approval gating + side-git snapshot rollback as a session-checkpoint reference). All other patterns (rlm_query parallel sub-agent fan-out, MCP server interop, paste-burst CRLF normalization) are already covered by Claude Code, hermes-agent v0.11.0, and pi-agent-core (intake-473) — not lifted into other child handoffs to avoid noise.
  - Delta: not a runtime candidate, not a fork target — recorded primarily to mark the URL seen and the pattern-coverage as already saturated.
