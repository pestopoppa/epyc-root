# Hermes Agent Integration Exploration

**Status**: stub
**Created**: 2026-03-15
**Source**: intake-117 (worth_investigating)
**Repo**: https://github.com/NousResearch/hermes-agent

## Objective

Evaluate two integration paths for Hermes Agent with our orchestrator stack. Decide between adopting Hermes as an outer shell vs. cherry-picking its best ideas into our existing architecture.

## Background

Hermes Agent (Nous Research) is an open-source autonomous AI agent with persistent memory, self-improving skills, and user modeling. Deep analysis (2026-03-15) revealed:

- Memory system is simpler than advertised (2 bounded flat files + FTS5 cross-session search + context compression via auxiliary LLM)
- Skill system is mature (agentskills.io standard, hub aggregating 7 sources, security scanning pipeline)
- User modeling via Honcho (external service by Plastic Labs) is the most novel piece — dialectic LLM-to-LLM reasoning about user preferences
- Fully model-agnostic — works with any OpenAI-compatible endpoint via `base_url`

## Path A: Hermes as Outer Shell + Our Orchestrator as Backend

**How**: Point Hermes at `http://localhost:8000/v1/chat/completions`. Hermes handles memory/skills/user-modeling/multi-platform gateway. Our orchestrator handles routing, model selection, escalation, inference optimization.

**Pros**:
- Immediate access to Hermes's mature skill ecosystem (agentskills.io, 7 hub sources)
- Multi-platform gateway (Telegram, Discord, Slack, WhatsApp, Signal) for free
- User modeling via Honcho without building our own
- Our routing intelligence (MemRL, specialist routing, factual risk, difficulty signal) powers Hermes's reasoning
- Separation of concerns: agent UX (Hermes) vs. inference optimization (us)

**Cons**:
- Two-layer architecture adds latency and complexity
- Hermes's context compression may conflict with our session_log / REPL token management
- Hermes's delegation spawns child agents — unclear how these interact with our escalation chain
- Dependency on Nous Research's development direction
- Hermes's tool-calling loop may not align with our REPL execution model
- We lose fine-grained control over prompt construction (Hermes builds its own system prompts)

**Key questions**:
- Can Hermes's delegation system coexist with our escalation policy? (Hermes spawns isolated child agents; we escalate within a single conversation)
- Does Hermes respect streaming from our endpoint? (It uses OpenAI-compatible streaming)
- How does Hermes's context compression interact with our orchestrator's role-specific token budgets?
- Can we pass role hints through the API? (e.g., `model: "coder_escalation"` to force routing)

## Path B: Cherry-Pick Best Ideas into Our Stack

### B1: User Modeling (from Honcho)

**What to adopt**: Deriver/Dreamer pattern for extracting and consolidating user preferences.

**Our implementation**:
- Add a `user_profile` table to our episodic store (or a flat `USER.md` per user — Hermes proves this works at small scale)
- Use `worker_explore` (Qwen2.5-7B) as the auxiliary LLM for profile synthesis (replaces Honcho's external LLM)
- Four tools mirroring Honcho's interface: `user_profile` (fast retrieval), `user_search` (semantic search over stored facts), `user_context` (LLM-synthesized answer about user), `user_conclude` (write persistent facts)
- Background Deriver: cron job that reviews session logs and extracts preferences/corrections
- Inject user profile into system prompt alongside role prompts (same pattern as Hermes's MEMORY.md injection)

**Effort**: Medium. Core is ~200 lines for the tool interface + ~100 lines for the deriver cron. The hard part is deciding what to extract vs. what's transient.

**Gap this fills**: We currently have zero cross-session user modeling. Preferences like "use box-drawing tables", "don't run inference without asking", "always show TPS" are lost between sessions.

### B2: Context Compression (from Hermes)

**What to adopt**: Protected-zone context compression (first N + last M turns preserved, middle summarized).

**Our implementation**:
- Extend `session_log.py` to implement protected zones: first 2 + last 3 turns never compressed
- Use `worker_explore` for mid-session summarization (Hermes uses Gemini Flash for this)
- Trigger at configurable token threshold (Hermes uses 50% of context limit)
- Preserve tool-call/result pairs as atomic units during compression

**Effort**: Low-medium. Session_log already tracks turns — adding compression is ~150 lines.

**Gap this fills**: Our current session_log summary is append-only and injected every 2 turns. It doesn't compress or remove old context. Long REPL sessions accumulate redundant turn history.

### B3: Skill Hub (from agentskills.io)

**What to adopt**: The agentskills.io standard for skill storage + a hub for discovering/installing external skills.

**Our implementation**:
- Our SkillRL skillbank already stores skills with Q-values for retrieval
- Could add agentskills.io-compatible import/export (SKILL.md format)
- Hub integration is low priority — our skills are orchestration-specific, not general-purpose

**Effort**: Low value for us. Our skillbank is more sophisticated (Q-value weighted retrieval vs. flat file listing). The standard format could be useful for interop but isn't blocking.

### B4: Memory Curation Nudges — PARTIAL

**What to adopt**: Prompt the agent to periodically decide what to persist.

**Implemented (prompt-only)**:
- Added to `frontdoor.md`: "If the user states a durable preference (output format, verbosity, style, workflow pattern), acknowledge it and incorporate it for the rest of the session."
- In-session behavioral nudge only — no persistent store yet (requires B1)

**Remaining**: B1 (user modeling store) for cross-session persistence. Current nudge only affects in-session behavior.

**Effort**: Trivial — a prompt edit, same as Action 1 of reasoning compression.

## Recommendation

**Path B (cherry-pick)**, prioritized as:

1. **B1 (User Modeling)** — highest value, fills a real gap, medium effort
2. **B2 (Context Compression)** — good value, builds on existing session_log, low-medium effort
3. **B4 (Memory Nudges)** — trivial effort, depends on B1
4. **B3 (Skill Hub)** — low priority, our skillbank is already more advanced

Path A remains viable as a **parallel experiment** — point a Hermes instance at our orchestrator endpoint and test whether the two-layer architecture works in practice. This can run alongside Path B without conflict.

## Open Questions

- Does Honcho's Dreamer ("random walk exploration with surprisal") produce meaningfully better user models than a simple deriver? Or is it over-engineered?
- Hermes caps MEMORY.md at 2.2KB — is that enough? What's the right size for a user profile?
- Can we run Honcho locally instead of as an external service? (It's open-source: github.com/plastic-labs/honcho)
- How does Hermes handle multi-user scenarios? (Our orchestrator is single-user currently but could grow)
- Hermes's skill security scanning (100+ regex threat signatures) — should we adopt this for our skillbank?

## Research Intake Update — 2026-03-15

### New Related Research
- **[intake-145] "Agent Protocol"** (github.com/langchain-ai/agent-protocol)
  - Relevance: Framework-agnostic API standard for serving LLM agents — defines Runs, Threads, and Store primitives
  - Key technique: Open spec for agent interop: stateless runs, persistent multi-turn threads, namespace-scoped long-term memory store
  - Delta from current approach: We have no standardized external API for our orchestrator beyond `/chat` and `/v1/chat/completions`. Agent Protocol's Runs/Threads/Store maps to our task execution / session persistence / episodic memory. LangGraph Platform implements a superset. Could inform our API surface if we expose the orchestrator as an agent server.

- **[intake-144] "Deep Agents"** (github.com/langchain-ai/deepagents)
  - Relevance: Batteries-included agent with planning tools, sub-agent delegation, context summarization — architectural parallel to our REPL + escalation pipeline
  - Key technique: `create_deep_agent` returns compiled LangGraph graph with built-in file ops, shell access, `write_todos` planning, sub-agent contexts
  - Delta from current approach: We build our agent graph manually with pydantic_graph nodes. Deep Agents shows the "opinionated defaults" pattern — pre-tuned prompts, automatic context summarization for long conversations, file-based output storage. Our architecture is more sophisticated (multi-tier routing, MemRL, SkillBank) but less turnkey.

### Deep-Dive Findings (2026-03-15)

**Source**: `research/deep-dives/langgraph-ecosystem-comparison.md`

#### Agent Protocol Naming Alignment (Recommendation #1)

When we next touch the API surface, align with Agent Protocol's Runs/Threads/Store naming convention. Our existing primitives map cleanly:

| Agent Protocol | EPYC Equivalent |
|----------------|-----------------|
| Runs | Task execution (single `/chat` request) |
| Threads | Session persistence (`session_store.py`) |
| Store | Episodic memory (`episodic_store.py`) |

No code change needed now — architectural decision recorded. If we pursue LangGraph migration (see `handoffs/active/langgraph-migration.md`), Agent Protocol compliance comes for free via LangGraph Platform.

## Files to Create (when work begins)

- `epyc-orchestrator/src/user_modeling/` — user profile store, deriver, tools
- `epyc-orchestrator/src/context_compression.py` — protected-zone compressor
- `epyc-orchestrator/orchestration/prompts/` — memory curation nudges in role prompts
