# Hermes/OpenGauss as Outer Shell

**Status**: in-progress (Phase 1 complete, Phase 2 routing API done, skills + validation pending)
**Created**: 2026-03-20 (split from hermes-agent-index.md)
**Updated**: 2026-04-05
**Parent**: [hermes-agent-index.md](hermes-agent-index.md)
**Repos**: https://github.com/NousResearch/hermes-agent, https://github.com/math-inc/OpenGauss
**Decision**: Vanilla Hermes (not OpenGauss) — OpenGauss is Lean 4-specific; Hermes has first-class custom endpoint support

## Objective

Evaluate running Hermes Agent (or its OpenGauss fork) as a user-facing frontend on top of our orchestrator. Hermes handles conversation UX, memory, skills, multi-platform gateway. Our orchestrator handles routing, model selection, escalation, inference optimization underneath via `/v1/chat/completions`.

## How It Works

```
User (Telegram/Discord/CLI/etc.)
  └─→ Hermes/OpenGauss (conversation mgmt, memory, skills, gateway)
        └─→ POST localhost:8000/v1/chat/completions
              └─→ EPYC Orchestrator (frontdoor → routing → specialist → escalation)
                    └─→ llama-server (inference)
```

## Pros

- Immediate access to Hermes's mature skill ecosystem (agentskills.io, 7 hub sources)
- Multi-platform gateway (Telegram, Discord, Slack, WhatsApp, Signal, Email, Home Assistant) for free
- User modeling via Honcho without building our own
- Our routing intelligence (MemRL, specialist routing, factual risk, difficulty signal) powers Hermes's reasoning
- Separation of concerns: agent UX (Hermes) vs. inference optimization (us)
- OpenGauss proves this architecture works in production (170 stars, Lean 4 vertical)

## Cons

- Two-layer architecture adds latency and complexity
- Hermes's context compression may conflict with our session_log / REPL token management
- Hermes's delegation spawns child agents — unclear how these interact with our escalation chain
- Dependency on Nous Research's development direction (mitigated: OpenGauss is MIT-licensed fork)
- Hermes's tool-calling loop may not align with our REPL execution model
- We lose fine-grained control over prompt construction (Hermes builds its own system prompts)

## Two-Layer Memory Architecture

In this model, Hermes and the orchestrator each maintain their own memory at different abstraction levels. They don't overlap — Hermes never sees our episodic store, and our orchestrator doesn't know the user's name or style preferences.

| | Hermes/OpenGauss (outer) | EPYC Orchestrator (inner) |
|---|---|---|
| **What it remembers** | User preferences, conversation style, past topics, personality | Task strategies, routing outcomes, skill Q-values, model performance |
| **Memory system** | MEMORY.md (flat file, 2.2KB cap) + Honcho user modeling | Episodic store (SQLite + FAISS) + MemRL reward history + SkillBank |
| **Scope** | Cross-session user relationship | Cross-task optimization decisions |
| **Example** | "User prefers box-drawing tables, hates verbose summaries" | "Q4_K_M Qwen2.5-72B solves math better than Q8_0 32B for difficulty > 0.7" |

### Cross-Layer Preference Problem

User preferences expressed to Hermes (e.g., "always use the biggest model") can only reach the orchestrator as text in the prompt. The orchestrator's frontdoor may or may not pick up on it — there's no formal contract for passing preferences across the boundary.

**Solution: Deterministic Override Flags**

Expose reduced orchestrator subgraphs that the outer shell can activate deterministically via API parameters — analogous to Claude Code's `/model` command, which bypasses model selection rather than hoping the prompt influences it.

Design:
- Hermes slash commands (e.g., `/use architect`, `/use biggest`, `/escalation off`) map to API parameters on the `/v1/chat/completions` call
- The orchestrator exposes these as optional fields in the request body (e.g., `"routing_override": "architect_qwen2_5_72b"`, `"max_escalation": "B1"`, `"force_model": "..."`)
- When present, these bypass the frontdoor classification and routing graph — deterministic, no prompt interpretation needed
- When absent, normal MemRL-driven routing applies

This keeps the clean separation: Hermes handles the user-facing command UX, the orchestrator handles the graph shortcut. The contract between them is a typed API schema, not prompt text.

Examples:
```
# User tells Hermes: "use the big model for this"
# Hermes sends: POST /v1/chat/completions {"routing_override": "architect_qwen2_5_72b", ...}

# User tells Hermes: "don't escalate, keep it simple"
# Hermes sends: POST /v1/chat/completions {"max_escalation": "B1", ...}

# Normal request — Hermes has no routing opinion
# Hermes sends: POST /v1/chat/completions {... no override fields ...}
# → Full frontdoor → MemRL → specialist → escalation graph applies
```

## Key Questions to Resolve

1. **Delegation vs escalation**: Can Hermes's child agent spawning coexist with our escalation policy? (Hermes spawns isolated child agents; we escalate within a single conversation)
2. **Streaming compatibility**: Does Hermes respect streaming from our endpoint? (It uses OpenAI-compatible streaming — likely yes)
3. **Context budget conflicts**: How does Hermes's context compression (50% threshold, protected first 3 + last 4 turns) interact with our role-specific token budgets?
4. **Override API surface**: What's the minimal set of routing overrides to expose? Candidates: `routing_override` (force specific role), `max_escalation` (cap escalation tier), `force_model` (bypass routing entirely), `disable_repl` (skip code execution)
5. **Swarm coordination**: OpenGauss's `/swarm` spawns parallel agents — each would hit our orchestrator independently. Does our inference lock handle concurrent requests correctly?

## Validation Plan

1. Stand up a Hermes instance pointed at `localhost:8000/v1/chat/completions`
2. Test basic conversation flow — does routing work transparently?
3. Test multi-turn context — does Hermes's compression interact badly with our session_log?
4. Test tool calling — does Hermes's tool loop trigger our REPL execution correctly?
5. Test escalation — submit a task that requires B2→B3 escalation, verify Hermes doesn't interfere
6. Measure added latency from the two-layer architecture

## OpenGauss-Specific Considerations

If using OpenGauss (the fork) rather than vanilla Hermes:

- **ACP adapter**: Could expose our orchestrator through the Agent Client Protocol standard, enabling third-party agent clients
- **Multi-backend**: OpenGauss already abstracts over Claude Code and Codex backends — adding "EPYC orchestrator" as a third backend type would be clean
- **Project model**: `.gauss/project.yaml` could scope orchestrator behavior per-project (e.g., different routing rules for different repos)

## Phase 1 Implementation (2026-03-25)

### Decision: Hermes over OpenGauss

Use vanilla Hermes Agent. OpenGauss is heavily specialized for Lean 4 (CLI commands, project model, backend spawner all Lean-specific). Hermes is general-purpose with first-class custom OpenAI-compatible endpoint support. OpenGauss patterns (ACP, session analytics, context compression) documented in `research/deep-dives/opengauss-architecture-analysis.md` can be ported independently (Path B).

### Source Audit Findings

- **No litellm** — uses OpenAI SDK directly (`openai.OpenAI`). Clean, no supply-chain risk from litellm.
- **Auto-detect model**: Queries `/v1/models` — perfect for llama-server (serves exactly 1 model)
- **Tool calling**: Assumes OpenAI-native format (`tool_calls` in response). llama-server `--jinja` flag required.
- **Memory**: Simple flat files (`~/.hermes/memories/MEMORY.md`, `USER.md`), no database
- **Auxiliary models**: All side tasks (compression, vision, web_extract) configurable to use same local endpoint via `provider: "main"`
- **30+ tools available**: Local-safe subset: terminal, file, code_execution, todo, memory, skills, session_search, cronjob, delegate_task
- **Cloud-dependent tools** (disabled in our config): vision_analyze (OpenRouter), image_generate (FAL), browser (Browserbase), web_search (Firecrawl/Tavily), honcho (cloud), mixture_of_agents (OpenRouter)
- **Entry point**: `python cli.py` or `hermes` wrapper after install

### Architecture (Phase 1)

```
User (CLI)
  └── Hermes Agent (conversation, memory, tools, skills)
        └── POST http://localhost:8099/v1/chat/completions
              └── llama-server (Qwen3-Coder-30B-A3B, --jinja, Q4_K_M, ~39 t/s)
```

### Files Created

| File | Purpose |
|------|---------|
| `scripts/hermes/hermes-config.yaml` | Config for `~/.hermes/config.yaml` (symlinked) |
| `scripts/hermes/launch_hermes_backend.sh` | llama-server on :8099 with --jinja, no-think template |
| `scripts/hermes/setup_hermes.sh` | One-time symlink: config + HERMES.md + .env |
| `scripts/hermes/chat-template-no-think.jinja` | Qwen3 chat template with thinking disabled via `<\|im_sep\|>` |
| `scripts/hermes/HERMES.md` | Custom system prompt context (workstation info, paths, conventions) |

### Setup Steps

```bash
# 1. Clone + install (already done)
cd /mnt/raid0/llm/hermes-agent && ./scripts/install.sh

# 2. Symlink config + create .env
/mnt/raid0/llm/epyc-root/scripts/hermes/setup_hermes.sh

# 3. Start backend (deferred — not while benchmarks running)
/mnt/raid0/llm/epyc-root/scripts/hermes/launch_hermes_backend.sh

# 4. Start Hermes
hermes  # or: cd /mnt/raid0/llm/hermes-agent && python cli.py
```

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Qwen3 tool calling format not auto-detected by llama-server | Check `Chat format:` in server logs; provide `--chat-template-file` if needed |
| Auxiliary model calls expect cloud API features | All auxiliary pointed at same local endpoint |
| Context overflow with long tool outputs | `max_turns: 30`, compression enabled (50% threshold) |
| Compression model empty string not resolved | May need explicit model name; test during validation |
| Tool calling loop doesn't terminate | Conservative `max_turns`, monitor with `/usage` |

### Remaining Work (no inference needed)

- [ ] Think token mitigation: Prepare `--chat-template-file` with thinking disabled for simple turns, or system prompt hint (`/think` only when needed)
- [x] Context mismatch investigation: **FIXED** — `-np 2` splits total context across slots (32K/2=16K per slot). `/v1/props` reports per-slot value. Fix: `-np 1` (single-user CLI) + explicit `context_length: 32768` in config
- [ ] Hermes skill authoring: Write EPYC-specific skills (e.g., `/bench` to trigger benchmarks, `/stack` to manage orchestrator) — deferred to Phase 2
- [x] Custom system prompt: Created `HERMES.md` (symlinked to hermes-agent dir) — loaded as context file on startup. Contains workstation info, key paths, conventions, style prefs.
- [x] Compression model config: Verified — `provider: "main"` maps to custom endpoint, empty `summary_model` uses auto-detected model from `/v1/models`. Works with single-model llama-server.

### Deferred: Inference Validation (requires running llama-server)

**Smoke test results (2026-03-25)**:
- Basic conversation: **PASS** (slow, ~24s first response from think tokens)
- Tool execution: **PASS** (terminal `ls` dispatches and returns)

**Remaining tests**:
- [ ] Multi-turn context (references prior answer)
- [ ] Code execution (write + run Python)
- [ ] Memory persistence (MEMORY.md across sessions)
- [ ] Latency measurement (first-token, total)
- [ ] Compression trigger (long conversation, verify compaction works with local model)
- [ ] Delegation (subagent spawns, uses same local endpoint)

**Known issues to fix during validation**:
1. Think token overhead: burns context + wall-clock on trivial turns
2. Context burns fast: 7.6K/16K (47%) after one exchange
3. Context mismatch: `-c 32768` in script but Hermes sees 16K
4. Effective throughput much lower than raw 39 t/s

## Phase 2 Implementation (2026-04-05)

### Routing API Override Parameters — DONE

Added 3 new extension fields to `OpenAIChatRequest` (`src/api/models/openai.py`):
- `x_max_escalation`: Cap escalation tier (`A`, `B1`, `B2`, `C`)
- `x_force_model`: Force specific model by registry name, bypassing all routing
- `x_disable_repl`: Skip REPL code execution, force direct text response

Wiring in `openai_compat.py`:
- `x_force_model` takes precedence over `x_orchestrator_role` (which already exists)
- `x_disable_repl` bypasses REPL loop in both streaming and non-streaming paths
- `x_max_escalation` passed through to routing metadata (full graph enforcement pending LangGraph migration)
- All override fields appear in `x_orchestrator_metadata` when `x_show_routing=true`

**Hermes slash command → API parameter mapping**:
| Hermes Command | API Parameter | Value |
|---------------|---------------|-------|
| `/use architect` | `x_orchestrator_role` | `architect` |
| `/use biggest` | `x_force_model` | `architect_qwen2_5_72b` |
| `/escalation off` | `x_max_escalation` | `A` |
| `/escalation B1` | `x_max_escalation` | `B1` |
| `/nocode` | `x_disable_repl` | `true` |
| (default) | (none) | Normal MemRL routing |

**Status**: API-side complete. Hermes-side skill authoring (to map slash commands to API params) deferred — requires Hermes skill YAML files + testing with running backend.

### Config Parameter Mapping

| Hermes Config Key | Orchestrator Behavior | Effective? |
|-------------------|----------------------|-----------|
| `base_url` | Points Hermes at llama-server or orchestrator endpoint | YES |
| `compression.enabled` | Hermes-side context compression (independent of orchestrator) | YES |
| `compression.threshold` | Token ratio trigger (0.5 = compress at 50% context used) | YES |
| `compression.protected_turns` | Turns never compressed (first/last) | YES |
| `delegation.max_iterations` | Hermes child agent turn cap | YES (Hermes-internal) |
| `memory.max_chars` | MEMORY.md size limit | YES |
| `toolsets.*` | Which Hermes tools are available | YES |
| `temperature` | Passed to llama-server | YES |
| `max_tokens` | Passed to llama-server | YES |
| `vision_model` | N/A when pointing at text-only endpoint | NO-OP |
| `web_search_model` | N/A (cloud tool disabled) | NO-OP |

### Auth Flow Design — DEFERRED

Single-user only for now. No auth on any endpoint. When multi-user is needed, add API key auth to `/v1/chat/completions` (bearer token checked against config file). Not implementing until there's a concrete multi-user use case.

### Remaining Phase 2 Work

- [ ] Write Hermes skill YAML files for `/use`, `/escalation`, `/nocode` commands (needs hermes-agent skill format investigation)
- [ ] Validate streaming compatibility with new override params (needs inference)
- [ ] Test `x_disable_repl` end-to-end (needs inference)
- [ ] Test `x_max_escalation` with full graph (depends on LangGraph migration)

## Research Intake Updates

### 2026-03-15
- **[intake-145] Agent Protocol**: API standard for agent interop (Runs/Threads/Store). If we pursue Path A, Agent Protocol compliance on our `/v1/chat/completions` surface would make us pluggable into any Agent Protocol client, not just Hermes.
- **[intake-144] Deep Agents**: LangGraph-based agent with planning tools and sub-agent delegation — architectural parallel but tighter coupling than our layered approach.

### 2026-03-20
- **[intake-172/173] OpenGauss**: Production fork validates that hermes-agent can be specialized for a vertical domain while keeping the core conversation loop intact. Their multi-backend abstraction pattern shows how to cleanly add our orchestrator as a backend target.
