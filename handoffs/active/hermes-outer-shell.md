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

**Status**: API-side complete. Hermes skill YAMLs written 2026-04-08 (`scripts/hermes/skills/use/`, `escalation/`, `nocode/`). Live testing with running backend pending.

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

- [x] Write Hermes skill YAML files for `/use`, `/escalation`, `/nocode` commands — ✅ 2026-04-08. Three SKILL.md files with YAML frontmatter in `scripts/hermes/skills/`. Mapping tables included.
- [ ] Validate streaming compatibility with new override params (needs inference)
- [ ] Test `x_disable_repl` end-to-end (needs inference)
- [ ] Test `x_max_escalation` with full graph (depends on LangGraph migration)

#### Skills Authoring Rubric (added 2026-04-24 from intake-450 deep-dive)

Source: [`research/deep-dives/veniceai-skills-cross-runtime-authoring.md`](../../research/deep-dives/veniceai-skills-cross-runtime-authoring.md). Three non-inference work items, mostly independent. Apply Venice's cross-runtime SKILL.md authoring discipline before our skill corpus grows.

- [ ] **A — `scripts/hermes/skills/TEMPLATE.md` + ≤500-line authoring rubric** (~30 min)
  - Codify: short lead paragraph → endpoint/override table → curl + one SDK example → explicit "Gotchas" section → ≤500 line cap
  - Reference Venice's pattern at `github.com/veniceai/skills` (any individual skill is the canonical example)
  - Write the rubric as a separate `scripts/hermes/skills/AUTHORING.md` next to the template if the template itself would be too cluttered
- [ ] **B — `scripts/hermes/skills/check_drift.py` + pre-commit hook wire** (~2 h, depends on A)
  - Parse `x_*` field declarations in `OpenAIChatRequest` (under `epyc-orchestrator/src/api/models/openai.py` per our overrides — confirm path on implementation)
  - Regex-scan all `scripts/hermes/skills/**/*.md` for documented `x_*` references
  - Two-way diff: declared-but-undocumented and documented-but-undeclared
  - Exit 1 on drift with a clear message; exit 0 on clean
  - Wire as a hook in `epyc-orchestrator/.git/hooks/pre-commit` — references `feedback_handoff_driven_tracking` discipline
  - Modeled on Venice's `sync_from_swagger.py` pattern
- [ ] **C — `scripts/hermes/skills/overview/SKILL.md` (entry-point inventory)** (~30 min, depends on A)
  - Lists every `x_*` override + what it does + which command-skill (`/use`, `/escalation`, `/nocode`) consumes it
  - Acts as the index for new readers + first thing the drift detector references

#### Phase 2+ Enhancement (added 2026-04-24 from intake-454 deep-dive)

Source: [`research/deep-dives/hermes-agent-v2026-4-23-release.md`](../../research/deep-dives/hermes-agent-v2026-4-23-release.md). Depends on Wave 1B item D (pin bump v2026.3.23 → v2026.4.23) — D lives in [`hermes-agent-index.md`](hermes-agent-index.md) P2.5.

- [ ] **F — Re-express `x_*` overrides as a namespaced Hermes plugin bundle** (4–6 h, depends on D)
  - Replace the three current SKILL.md YAMLs (`/use`, `/escalation`, `/nocode`) with a single namespaced plugin bundle using v0.11.0's new `register_command` + `pre_tool_call` veto + `transform_tool_result` hooks
  - Removes hand-maintained YAML drift surface (which B's drift detector exists to police — F + B together close the loop)
  - All code work, no inference required for the implementation. End-to-end validation rolls into G.

#### Phase 2 Validation (added 2026-04-24 from intake-454 deep-dive)

- [ ] **G — Validate subagent + single-slot llama-server interaction** (3–5 h, depends on D and F; **REQUIRES INFERENCE — Wave 2**)
  - **Resolves Question 5** above (swarm coordination)
  - Spawn 2+ parallel subagents via the new orchestrator role; each hits a single-slot llama-server independently
  - Confirm: no head-of-line blocking, correct request serialization, no shared-state corruption
  - If issues found: document the failure mode and either (i) configure spawn-depth ceiling appropriately, or (ii) move single-slot servers behind a request-broker

## Research Intake Updates

### 2026-03-15
- **[intake-145] Agent Protocol**: API standard for agent interop (Runs/Threads/Store). If we pursue Path A, Agent Protocol compliance on our `/v1/chat/completions` surface would make us pluggable into any Agent Protocol client, not just Hermes.
- **[intake-144] Deep Agents**: LangGraph-based agent with planning tools and sub-agent delegation — architectural parallel but tighter coupling than our layered approach.

### 2026-03-20
- **[intake-172/173] OpenGauss**: Production fork validates that hermes-agent can be specialized for a vertical domain while keeping the core conversation loop intact. Their multi-backend abstraction pattern shows how to cleanly add our orchestrator as a backend target.

### 2026-04-14
- **[intake-361] mcp-searxng**: MCP Server for SearXNG (635 stars, MIT, TypeScript). Exposes `searxng_web_search` and `web_url_read` tools via Model Context Protocol. When SearXNG is deployed locally (see [`searxng-search-backend.md`](/workspace/handoffs/active/searxng-search-backend.md), R&O P12), mcp-searxng could replace the cloud-dependent `web_search` tool (line 121, currently Firecrawl/Tavily, disabled) with a local, privacy-respecting alternative. Future opportunity — lower priority than orchestrator backend integration (P12 SX-1–SX-6).

## Research Intake Update — 2026-04-17

### New Related Research

- **[intake-397] "Open Agents — Vercel-Labs Reference App for Background Coding Agents"** (repo: vercel-labs/open-agents)
  - Relevance: directly analogous to hermes-outer-shell's two-layer architecture — open-agents makes the explicit design choice that the agent runs OUTSIDE the sandbox and interacts via file/search/shell tools, with a durable workflow between them. Maps cleanly to the outer-shell ↔ inner-execution separation.
  - Key technique: (1) agent-outside-sandbox control-plane separation with tool-driven sandbox interaction; (2) durable workflow execution (Vercel Workflow SDK) with persisted steps, streaming, cancellation, and reconnect-to-stream; (3) snapshot-based sandbox hibernate/resume independent from agent/model choice.
  - Delta: TS/Vercel stack is not portable to EPYC, but the three design decisions above are directly worth mining during Phase 2+ of hermes-outer-shell: stable contract between outer/inner layers, durable workflow for reconnect-on-disconnect, and snapshot-resume as analogue for session-log/episodic-store resumability.

## Research Intake Update — 2026-04-24

### New Related Research

- **[intake-450] "Venice Skills — Agent Skills for the Venice.ai API"** (`github.com/veniceai/skills`)
  - Relevance: Hermes is documented as a first-class target runtime (`$HERMES_OPTIONAL_SKILLS_DIR` / `~/.hermes/skills/`). Reference implementation of the cross-runtime SKILL.md install pattern that our `scripts/hermes/skills/` is currently bootstrapping.
  - Key technique: ≤500-line SKILL.md authoring rubric (short lead paragraph, endpoint tables, curl + one SDK example, explicit gotchas section); `sync_from_swagger.py` for OpenAPI→skill drift detection.
  - Delta: adopt the authoring rubric for our `scripts/hermes/skills/` corpus; consider the drift-detection pattern for any x_* overrides we script against internal routing APIs. Ignore the Venice API itself (commercial, non-OSS).

- **[intake-454] "hermes-agent v2026.4.23 (v0.11.0)"** (`github.com/NousResearch/hermes-agent/releases/tag/v2026.4.23`)
  - Relevance: major release with expanded plugin surface — slash-command registration, direct tool dispatch, execution veto, result-transform hooks, shell-hook lifecycle callbacks, namespaced skill bundles. All directly relevant to Phase 2+ outer-shell plugin architecture and skills validation.
  - Key technique: namespaced skill bundles + shell-hook lifecycle enables packaging our `x_*` overrides as a discrete bundle instead of patching global config.
  - Delta: evaluate the plugin-veto + result-transform hooks as an alternative to the hard-fork-and-patch pattern we've been using for routing-API overrides. Potentially removes the need for maintaining hermes-agent fork diffs if the plugin surface is expressive enough.
