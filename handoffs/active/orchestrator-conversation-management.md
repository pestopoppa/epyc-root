# Orchestrator Conversation Management — Cherry-Pick from Hermes/OpenGauss

**Status**: active
**Created**: 2026-03-20 (split from hermes-agent-index.md)
**Parent**: [hermes-agent-index.md](hermes-agent-index.md)
**Source implementations**: hermes-agent (`agent/`), OpenGauss (`agent/`, `gauss_cli/`)

## Objective

Port the best conversation management patterns from Hermes Agent and OpenGauss into our orchestrator. These fill real gaps in our stack — we have sophisticated routing and inference optimization but weak conversation-level infrastructure (no user modeling, no context compression, no session analytics).

## Work Items

### B1: User Modeling (from Honcho) — HIGH PRIORITY

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

### B2: Context Compression (from Hermes + OpenGauss) — HIGH PRIORITY

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

**Effort**: Low-medium. Session_log already tracks turns — adding compression is ~150 lines. Tool pair sanitization adds ~50 lines.

**Files to create**:
- `epyc-orchestrator/src/context_compression.py` — protected-zone compressor with tool pair sanitization

**Cross-reference**: B2 tool-pair sanitization (`_sanitize_tool_pairs()`) overlaps with `context-folding-progressive.md` Phase 1 (two-level condensation) — both modify session compaction. Coordinate sequencing: context-folding Phase 1 should land first as the structural upgrade, then B2's protected-zone logic layers on top. Alternatively, extract `_sanitize_tool_pairs()` as a standalone prerequisite for both. See `routing-and-optimization-index.md` Cross-Cutting Concern #8.

### B3: Skill Hub Interop (from agentskills.io) — LOW PRIORITY

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

### B5: Session Analytics (from OpenGauss) — MEDIUM PRIORITY

**Gap**: We have inference_tap.log and session logs but no structured analytics.

**What to adopt**: OpenGauss's `InsightsEngine` pattern — SQLite-backed analytics for token consumption, cost estimation, tool usage ranking, activity patterns.

**Implementation plan**:
- Add analytics queries to our existing session store
- Track tool usage × task success correlations (feed into MemRL reward signals)
- Generate per-session and aggregate reports

**Effort**: Low-medium. Our SQLite infrastructure exists; this is queries + formatting.

### B6: Multi-Backend Abstraction (from OpenGauss) — MEDIUM PRIORITY

**Gap**: We only support llama-server backends. No abstraction layer for alternative inference servers.

**What to adopt**: OpenGauss's `ManagedWorkflowSpec` → `ManagedContext` → `LaunchPlan` pipeline for per-backend config generation.

**Implementation plan**:
- Abstract server lifecycle into a backend interface
- Implement llama-server backend (extract from current `orchestrator_stack.py`)
- Add vLLM/TGI backends when needed
- Per-backend config generation, health checking, and capability reporting

**Effort**: Medium. Requires refactoring `orchestrator_stack.py` server management.

### B7: Prompt Injection Scanning (from OpenGauss) — LOW PRIORITY

**Gap**: We load prompts from `orchestration/prompts/*.md` without injection scanning. Currently safe (operator-controlled) but risky if we ever support user-uploaded context.

**What to adopt**: OpenGauss's 10-pattern injection scanner in `prompt_builder.py`.

**Effort**: Trivial (~30 lines). Defer until user-uploaded context is supported.

## Priority Order

1. **B1 (User Modeling)** — highest value, fills a real gap, medium effort
2. **B2 (Context Compression)** — high value, builds on existing session_log, low-medium effort
3. **B5 (Session Analytics)** — medium value, feeds MemRL, low-medium effort
4. **B6 (Multi-Backend)** — medium value, enables vLLM/TGI, medium effort
5. **B4 (Memory Nudges)** — trivial after B1
6. **B3 (Skill Hub)** — low priority
7. **B7 (Injection Scanning)** — defer

## Agent Protocol Naming Alignment

When we next touch the API surface, align with Agent Protocol's Runs/Threads/Store naming convention (recommendation from deep dive 2026-03-15):

| Agent Protocol | EPYC Equivalent |
|----------------|-----------------|
| Runs | Task execution (single `/chat` request) |
| Threads | Session persistence (`session_store.py`) |
| Store | Episodic memory (`episodic_store.py`) |

No code change needed now — architectural decision recorded. If we pursue LangGraph migration (see `handoffs/active/langgraph-migration.md`), Agent Protocol compliance comes for free via LangGraph Platform.
