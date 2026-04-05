# Orchestrator Conversation Management — Cherry-Pick from Hermes/OpenGauss

**Status**: active (B1/B2/B3/B5/B6/B7 code complete 2026-04-05, awaiting integration validation)
**Created**: 2026-03-20 (split from hermes-agent-index.md)
**Updated**: 2026-04-05
**Parent**: [hermes-agent-index.md](hermes-agent-index.md)
**Source implementations**: hermes-agent (`agent/`), OpenGauss (`agent/`, `gauss_cli/`)

## Objective

Port the best conversation management patterns from Hermes Agent and OpenGauss into our orchestrator. These fill real gaps in our stack — we have sophisticated routing and inference optimization but weak conversation-level infrastructure (no user modeling, no context compression, no session analytics).

## Work Items

### B1: User Modeling (from Honcho) — ✅ CODE COMPLETE 2026-04-05

**Implementation**: `src/user_modeling/` package (3 modules, ~300 lines, 18 tests).
- `profile_store.py`: SQLite-backed store with bounded entries (§ delimiter, 4KB cap), injection scanning on writes, frozen snapshot for prefix cache stability, LRU eviction.
- `deriver.py`: Background preference extraction via `PREF [category] text` format. Accepts `llm_call` for worker_explore integration.
- `tools.py`: 4 tool functions (`user_profile`, `user_search`, `user_context`, `user_conclude`). Module-level singleton store.
- Feature flag: `ORCHESTRATOR_USER_MODELING=1` (requires `injection_scanning`).

**Gap**: We have zero cross-session user modeling. Preferences like "use box-drawing tables", "don't run inference without asking", "always show TPS" are lost between sessions.

**What to adopt**: Deriver/Dreamer pattern for extracting and consolidating user preferences.

**Implementation plan**:
- Add a `user_profile` table to our episodic store (or a flat `USER.md` per user — Hermes proves this works at small scale)
- Use `worker_explore` (Qwen2.5-7B) as the auxiliary LLM for profile synthesis (replaces Honcho's external LLM)
- Four tools mirroring Honcho's interface: `user_profile` (fast retrieval), `user_search` (semantic search over stored facts), `user_context` (LLM-synthesized answer about user), `user_conclude` (write persistent facts)
- Background Deriver: cron job that reviews session logs and extracts preferences/corrections
- Inject user profile into system prompt alongside role prompts (same pattern as Hermes's MEMORY.md injection)

**Effort**: Medium. Core is ~200 lines for the tool interface + ~100 lines for the deriver cron. The hard part is deciding what to extract vs. what's transient.

**Files to create**:
- `epyc-orchestrator/src/user_modeling/` — user profile store, deriver, tools

**Open questions**:
- Does Honcho's Dreamer ("random walk exploration with surprisal") produce meaningfully better user models than a simple deriver? Or is it over-engineered?
- Hermes caps MEMORY.md at 2.2KB — is that enough? What's the right size for a user profile?
- Can we run Honcho locally instead of as an external service? (It's open-source: github.com/plastic-labs/honcho)
- How does Hermes handle multi-user scenarios? (Our orchestrator is single-user currently but could grow)

### B2: Context Compression (from Hermes + OpenGauss) — ✅ CODE COMPLETE 2026-04-05

**Implementation**: `src/context_compression.py` (~280 lines, 22 tests).
- `ContextCompressor` class with protected zones (first 3 + last 5 turns).
- `sanitize_tool_pairs()`: fixes orphaned tool_call/result pairs (adds stubs, removes orphans).
- `align_boundary_forward()`: prevents splitting on orphaned tool results.
- Type-aware tool output summarization: `classify_tool_output()` → error/file_read/repl/other; errors kept verbatim, file reads stubbed, REPL outputs summarized.
- Configurable via `CompressorConfig` (trigger ratio, protect counts, output age threshold).
- Feature flag: `ORCHESTRATOR_CONTEXT_COMPRESSION=1`.

**Gap**: Our current session_log summary is append-only and injected every 2 turns. It doesn't compress or remove old context. Long REPL sessions accumulate redundant turn history.

**What to adopt**: Protected-zone context compression (first N + last M turns preserved, middle summarized).

**Implementation plan**:
- Extend `session_log.py` to implement protected zones: first 2 + last 3 turns never compressed
- Use `worker_explore` for mid-session summarization (Hermes uses Gemini Flash for this)
- Trigger at configurable token threshold (Hermes uses 50% of context limit)
- Preserve tool-call/result pairs as atomic units during compression

**Port from OpenGauss** (deep dive 2026-03-20):
- `_sanitize_tool_pairs()` — fixes orphaned tool call/result pairs before compression. Orphaned pairs cause API rejections. Critical.
- `_align_boundary_forward/backward()` — prevents splitting tool groups during compression. Prevents subtle breakage.

**NEW (from Goose/Clido deep dive, 2026-04-04)**: Add tool-output-specific summarization. After 8+ tool calls, use `worker_explore` to summarize older tool outputs in-place while keeping last 3 verbatim. Selective by type: REPL outputs always summarize, file reads replace with stub, error outputs keep verbatim. Goose does this uniformly after 10+ calls; our version should be type-aware.

**Effort**: Low-medium. Session_log already tracks turns — adding compression is ~150 lines. Tool pair sanitization adds ~50 lines. Tool output summarization adds ~80 lines.

**Files to create**:
- `epyc-orchestrator/src/context_compression.py` — protected-zone compressor with tool pair sanitization

**Cross-reference**: B2 tool-pair sanitization (`_sanitize_tool_pairs()`) overlaps with `context-folding-progressive.md` Phase 1 (two-level condensation) — both modify session compaction. Coordinate sequencing: context-folding Phase 1 should land first as the structural upgrade, then B2's protected-zone logic layers on top. Alternatively, extract `_sanitize_tool_pairs()` as a standalone prerequisite for both. See `routing-and-optimization-index.md` Cross-Cutting Concern #8.

### B3: Skill Hub Interop (from agentskills.io) — ✅ CODE COMPLETE 2026-04-05

**Implementation**: `src/skill_hub_interop.py` (~100 lines, 13 tests).
- `parse_skill_md()` / `export_skill_md()`: YAML frontmatter SKILL.md format (agentskills.io compatible).
- `scan_skill()`: 6 threat patterns (eval/exec, subprocess shell, os.system, credential access, network exfil, file overwrite).
- `load_skills_from_directory()`: Batch loader for `*/SKILL.md` pattern.
- Extends existing `skillbank` flag — no new feature flag.

**Gap**: None critical. Our SkillRL skillbank is more sophisticated (Q-value weighted retrieval vs. flat file listing).

**What to adopt**: The agentskills.io standard for skill storage format (SKILL.md).

**Implementation plan**:
- Add agentskills.io-compatible import/export to our skillbank
- Hub integration is low priority — our skills are orchestration-specific, not general-purpose
- Hermes's skill security scanning (100+ regex threat signatures) — consider adopting for our skillbank

**Effort**: Low value. Standard format useful for interop but not blocking.

### B4: Memory Curation Nudges — PARTIAL (depends on B1)

**Gap**: No persistent cross-session preference storage.

**What to adopt**: Prompt the agent to periodically decide what to persist.

**Implemented (prompt-only)**:
- Added to `frontdoor.md`: "If the user states a durable preference (output format, verbosity, style, workflow pattern), acknowledge it and incorporate it for the rest of the session."
- In-session behavioral nudge only — no persistent store yet (requires B1)

**Remaining**: B1 (user modeling store) for cross-session persistence.

**Effort**: Trivial beyond B1.

### B5: Session Analytics + Token Budgeting (from OpenGauss + Clido) — ✅ CODE COMPLETE 2026-04-05

**Implementation**: `src/session_analytics.py` (~200 lines, 12 tests).
- `SessionTokenBudget`: tracks cumulative input+output tokens per session. `ORCHESTRATOR_MAX_SESSION_TOKENS` env var. Compaction trigger at 70%, hard-stop at 100%.
- `compute_analytics()`: aggregates TurnRecord lists into tool usage ranking, role distribution, outcome breakdown, error/escalation counts.
- `format_analytics()`: human-readable report string.
- Feature flag: `ORCHESTRATOR_SESSION_TOKEN_BUDGET=1`.

**Gap**: We have inference_tap.log and session logs but no structured analytics. No per-session token budget to prevent runaway sessions.

**What to adopt**: OpenGauss's `InsightsEngine` pattern — SQLite-backed analytics for token consumption, cost estimation, tool usage ranking, activity patterns. Plus Clido's `--max-budget-usd` adapted as per-session token budgeting.

**Implementation plan**:
- Add analytics queries to our existing session store
- Track tool usage x task success correlations (feed into MemRL reward signals)
- Generate per-session and aggregate reports
- **NEW (from Goose/Clido deep dive, 2026-04-04)**: Add `ORCHESTRATOR_MAX_SESSION_TOKENS` env var for per-session token budget. Track cumulative input+output tokens in session_log. Trigger compaction at 70% of budget, hard-stop at 100% with work summary. Even with local inference, runaway sessions waste GPU time.

**Effort**: Low-medium. Our SQLite infrastructure exists; this is queries + formatting + token counting.

### B6: Multi-Backend Abstraction (from OpenGauss) — ✅ CODE COMPLETE 2026-04-05

**Implementation**: `src/backends/server_lifecycle.py` (~250 lines, 18 tests).
- `ServerLifecycle` Protocol: `build_launch_command()`, `health_check()`, `get_status()`.
- `LlamaServerLifecycle`: Full implementation with NUMA affinity, KV config, extra args, health/status via /health and /slots endpoints.
- `VLLMLifecycle`, `TGILifecycle`: Stub implementations with correct command structure.
- `ServerConfig`, `ServerCapabilities`, `ServerStatus` dataclasses.
- `get_lifecycle()` factory function. Does NOT modify `orchestrator_stack.py`.

**Gap**: We only support llama-server backends. No abstraction layer for alternative inference servers.

**What to adopt**: OpenGauss's `ManagedWorkflowSpec` → `ManagedContext` → `LaunchPlan` pipeline for per-backend config generation.

**Implementation plan**:
- Abstract server lifecycle into a backend interface
- Implement llama-server backend (extract from current `orchestrator_stack.py`)
- Add vLLM/TGI backends when needed
- Per-backend config generation, health checking, and capability reporting

**Effort**: Medium. Requires refactoring `orchestrator_stack.py` server management.

### B7: Prompt Injection Scanning (from OpenGauss) — ✅ CODE COMPLETE 2026-04-05

**Implementation**: `src/security/injection_scanner.py` (~80 lines, 16 tests).
- `scan_content()`: 10 regex threat patterns + invisible unicode detection (10 codepoints).
- Categories: prompt_injection, role_hijack, deception, instruction_override, instruction_disregard, restriction_bypass, html_injection, exfil_curl, exfil_cat_env, ssh_backdoor, invisible_unicode.
- Frozen `ScanResult` dataclass. Length-gated (20 chars–200KB).
- Feature flag: `ORCHESTRATOR_INJECTION_SCANNING=1` (on by default in production).

**Gap**: We load prompts from `orchestration/prompts/*.md` without injection scanning. Currently safe (operator-controlled) but risky if we ever support user-uploaded context.

**What to adopt**: OpenGauss's 10-pattern injection scanner in `prompt_builder.py`.

**Effort**: Trivial (~30 lines). Defer until user-uploaded context is supported.

## Priority Order

1. ~~**B1 (User Modeling)**~~ ✅ 2026-04-05. 18 tests.
2. ~~**B2 (Context Compression)**~~ ✅ 2026-04-05. 22 tests.
3. ~~**B5 (Session Analytics)**~~ ✅ 2026-04-05. 12 tests.
4. ~~**B6 (Multi-Backend)**~~ ✅ 2026-04-05. 18 tests.
5. **B4 (Memory Nudges)** — trivial: wire B1 tools into frontdoor prompt for cross-session persistence
6. ~~**B3 (Skill Hub)**~~ ✅ 2026-04-05. 13 tests.
7. ~~**B7 (Injection Scanning)**~~ ✅ 2026-04-05. 16 tests. Foundation for B1 write safety.

**Next steps**: Wire B1-B7 into the orchestrator pipeline (register tools, call compressor from helpers.py, inject profile into system prompt). Feature flags added to `src/features.py` — enable via env vars for validation.

## Agent Protocol Naming Alignment

When we next touch the API surface, align with Agent Protocol's Runs/Threads/Store naming convention (recommendation from deep dive 2026-03-15):

| Agent Protocol | EPYC Equivalent |
|----------------|-----------------|
| Runs | Task execution (single `/chat` request) |
| Threads | Session persistence (`session_store.py`) |
| Store | Episodic memory (`episodic_store.py`) |

No code change needed now — architectural decision recorded. If we pursue LangGraph migration (see `handoffs/active/langgraph-migration.md`), Agent Protocol compliance comes for free via LangGraph Platform.

## Research Intake Update — 2026-04-01

### New Related Research
- **[intake-249] "Claude Code Repo Leak Analysis — Harness Architecture Deep Dive"**
  - Pattern: **Tool-level behavior constraints**. CC distributes behavioral instructions INTO each tool definition (e.g., Edit tool requires prior Read, Bash tool pushes toward dedicated tools first, Agent tool teaches delegation anti-patterns). Our tool definitions in `model_registry.yaml` are structural (name, permissions) with zero behavioral guidance per tool — all behavior lives in the system prompt.
  - Delta from current approach: Moving tool-specific behavior from the system prompt into the tool definition reduces system prompt size and places constraints at the exact surface where mistakes happen. CC's approach: "The harness does not rely on one master prompt. They distribute behavior constraints across the exact surfaces where mistakes happen."
  - Concrete adoption: For each tool in our registry, add a `behavioral_guidance` field with 2-3 sentences of tool-specific instructions. Priority tools: `code_execution` (should describe REPL discipline), `web_research` (should describe when to use vs simple search), `escalation` (should describe when NOT to escalate).
  - Effort: Low. ~1 line per tool in registry + resolver change to inject tool guidance into tool definitions sent to the model.

- **[intake-254] "Goose — Open Source Autonomous AI Coding Agent"** (github.com/block/goose)
  - Pattern: **Tool output summarization**. Goose summarizes older tool call outputs after 10+ calls while keeping recent calls verbatim. Our B2 context compression should add type-aware tool output summarization (REPL=summarize, file reads=stub, errors=keep).
  - Pattern: **Auto-compaction at 80% token limit**. Our planned 50% threshold is more aggressive; Goose's 80% is a useful data point. Their fallback chain (summarize -> truncate -> clear -> prompt) is more graceful than a hard stop.
  - Delta: Goose's lead/worker multi-model routing is a turn-count heuristic (first 3 turns = lead, rest = worker). Simpler than our SkillRL routing but their failure-threshold fallback (worker errors -> temporary lead takeover) is a clean pattern.

- **[intake-255] "Clido — Multi-Provider CLI Coding Agent"** (github.com/clido-ai/clido-cli)
  - Pattern: **Per-session token budgeting**. `--max-budget-usd` caps spending per session. Adapted for local inference: `ORCHESTRATOR_MAX_SESSION_TOKENS` to prevent runaway GPU time. Maps to B5 scope.
  - Pattern: **"Fast" sub-profile**. Clido allows a lightweight model for utility tasks alongside the main model. This validates our frontdoor/worker/explore role split architecture.
  - Delta: Clido's 16-provider multi-backend is about cloud API switching, not local server management. Not transferable to our llama.cpp stack.

- **[intake-249] "Claude Code Repo Leak Analysis — Forked Subagents for Context Hygiene"**
  - Pattern: CC has two subagent modes — **fresh** (new prompt + restricted tools, like our escalation to higher tier) and **forked** (inherited parent context, optimized for prompt cache reuse). Forked agents offload noisy intermediate work while sharing the parent's cached prompt prefix.
  - Delta: Our escalation pipeline sends full context anew to the higher-tier model. No prompt cache reuse between tiers. No "fork for context hygiene" pattern — noisy tool outputs stay in the main context until compaction.
  - Concrete adoption: When escalating, structure the prompt so the stable prefix (system prompt + role + task description) is identical between tiers → enables KV cache prefix sharing if we ever route through an API with prompt caching. For local llama.cpp: investigate whether llama_kv_cache_seq_cp could enable a similar "fork" operation.
  - Effort: Medium. Requires prompt restructuring for escalation + investigation of llama.cpp KV cache sharing primitives.
