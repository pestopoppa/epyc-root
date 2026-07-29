# OpenGauss Architecture Deep Dive

**Date**: 2026-03-20
**Intake IDs**: intake-172, intake-173
**Repo**: https://github.com/math-inc/OpenGauss (170 stars, 14 forks, created 2026-03-19)
**Fork of**: nousresearch/hermes-agent
**License**: MIT

## Executive Summary

OpenGauss is a production derivative of hermes-agent specialized for Lean 4 theorem proving. It's a **CLI-first multi-agent orchestrator** that spawns managed backend sessions (Claude Code or Codex) with pre-staged Lean tooling. The architecture reveals several patterns directly applicable to our orchestrator work, particularly around session isolation, multi-backend support, and context management.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    gauss CLI (33 files)                  │
│  /prove /draft /autoprove /formalize /autoformalize     │
│  /swarm /project /handoff                               │
├──────────────┬──────────────────────────────────────────┤
│  Project     │  Backend Spawner (autoformalize.py)      │
│  Discovery   │  ├─ claude-code backend                  │
│  .gauss/     │  │  ├─ Plugin install (lean4-skills)     │
│  project.yaml│  │  ├─ MCP server config                 │
│              │  │  └─ Credential staging                 │
│              │  └─ codex backend                         │
│              │     ├─ TOML config gen                    │
│              │     ├─ Skill staging                      │
│              │     └─ Instructions gen                   │
├──────────────┴──────────────────────────────────────────┤
│                   agent/ (13 files)                      │
│  AIAgent: multi-provider, tool calling, context mgmt    │
│  ├─ prompt_builder.py (identity, skills, injection scan)│
│  ├─ context_compressor.py (protected-zone compression)  │
│  ├─ prompt_caching.py (system_and_3 Anthropic cache)    │
│  ├─ trajectory.py (ShareGPT-format JSONL export)        │
│  ├─ insights.py (SQLite session analytics)              │
│  └─ anthropic_adapter.py (native Anthropic API)         │
├─────────────────────────────────────────────────────────┤
│  gateway/ (multi-platform messaging)                    │
│  ├─ telegram, discord, slack, whatsapp, signal, email   │
│  ├─ homeassistant                                       │
│  └─ base.py (abstract platform interface)               │
├─────────────────────────────────────────────────────────┤
│  acp_adapter/ (Agent Client Protocol server)            │
│  ├─ 7 slash commands: help, model, tools, context,      │
│  │  reset, compact, version                             │
│  └─ Session CRUD, fork, cancel                          │
├─────────────────────────────────────────────────────────┤
│  skills/ (24 categories, hermes-agent skill hub)        │
│  optional-skills/                                       │
│  mini-swe-agent (submodule)                             │
│  tinker-atropos (submodule)                             │
└─────────────────────────────────────────────────────────┘
```

## Key Architectural Patterns

### 1. Terminal Handoff — Process-Level Session Isolation

**File**: `gauss_cli/handoff.py` (~350 lines)

The handoff system yields the terminal to a child process with full TTY control:

- **Two modes**: `helper` (simple subprocess) and `strict` (POSIX foreground process group transfer via `tcsetpgrp`)
- **Launcher configs**: Named launchers with custom argv, cwd, env overrides in YAML
- **Signal safety**: SIGTTOU temporarily ignored during process group transfer
- **Clean return**: Exit code and signal tracking with formatted status messages

**EPYC relevance**: Our orchestrator spawns llama-server processes but doesn't do terminal handoff. This pattern could enable `/handoff llama-server` for debugging sessions where the user gets direct llama-server access, then returns to the orchestrator.

### 2. Managed Backend Spawning — Multi-Backend Abstraction

**File**: `gauss_cli/autoformalize.py`

The autoformalize launcher handles two completely different backends through a unified interface:

- **Claude Code backend**: Installs plugins via CLI, writes MCP server JSON config, stages credentials, pre-approves tools in `.claude/settings.local.json`
- **Codex backend**: Generates TOML config, stages skill files, writes custom instructions markdown
- **Shared**: Git checkout of lean4-skills repo, tree staging, environment isolation

Key data structures:
- `ManagedWorkflowSpec` — normalizes `/prove`, `/formalize`, etc. to workflow specs
- `ManagedContext` — staged paths and metadata
- `AutoformalizeLaunchPlan` — complete launch config including HandoffRequest
- `SharedLeanBundle` — shared Lean assets across backends

**EPYC relevance**: We currently only support llama-server backends. This pattern shows how to abstract over multiple backends (e.g., llama-server vs vLLM vs TGI) with per-backend config generation and shared asset staging.

### 3. Context Compression — Protected-Zone Strategy

**File**: `agent/context_compressor.py`

Parameters:
- Trigger at 50% of context window
- Protect first 3 + last 4 turns
- Target ~2500 tokens for summaries
- Tool pair integrity: orphaned tool calls get stub results, orphaned results get removed

**EPYC relevance**: Direct parallel to our hermes-agent integration Path B2. Their implementation is more mature than what we planned — the tool pair sanitization is critical for avoiding API rejections. Our session_log.py should adopt the `_sanitize_tool_pairs()` pattern.

### 4. Prompt Injection Scanning

**File**: `agent/prompt_builder.py`

Context files (AGENTS.md, .cursorrules, SOUL.md) are scanned for 10 injection patterns before inclusion:
- "ignore previous instructions"
- "system prompt override"
- Hidden HTML divs/comments
- Credential exfiltration (`curl $TOKEN`)
- "act as if you have no restrictions"

Content truncated at 20K chars with head (70%) + tail (20%) preservation.

**EPYC relevance**: We load prompts from `orchestration/prompts/*.md` without any injection scanning. While our prompts are operator-controlled, if we ever support user-uploaded context (e.g., project files for task understanding), this pattern becomes critical.

### 5. Prompt Caching — "System and 3" Strategy

**File**: `agent/prompt_caching.py`

Uses all 4 Anthropic cache breakpoints:
1. System prompt (stable across turns)
2-4. Last 3 non-system messages (rolling window)

Claims ~75% input cost reduction on multi-turn conversations.

**EPYC relevance**: We don't use Anthropic's API directly (llama.cpp local inference), but if we ever add API-backed models as escalation targets, this caching strategy is directly applicable.

### 6. Agent Client Protocol (ACP) Server

**File**: `acp_adapter/server.py`

Exposes the agent through ACP — a standardized agent interop protocol:
- Session CRUD (create, load, resume, fork, cancel, list)
- Provider-based runtime credentials
- 7 built-in slash commands
- Tool progress, thinking, step, and message callbacks
- ThreadPoolExecutor (4 workers) for non-blocking agent execution

**EPYC relevance**: ACP is the next step beyond Agent Protocol (intake-145). Where Agent Protocol defines Runs/Threads/Store, ACP adds session forking, authentication, and structured callbacks. If we standardize our orchestrator's external API, ACP is worth evaluating alongside Agent Protocol and LangGraph Platform.

### 7. Multi-Platform Gateway

**File**: `gateway/` (7 platform integrations + base)

Platforms: Telegram, Discord, Slack, WhatsApp, Signal, Email, Home Assistant. Each implements a `base.py` interface with platform-specific message formatting and media handling.

**EPYC relevance**: We have no multi-platform story. If we pursue hermes-agent Path A (outer shell), this gateway comes for free. Low priority but validates the architecture.

### 8. Session Analytics

**File**: `agent/insights.py`

SQLite-backed analytics engine:
- Token consumption and cost estimation per model (with fuzzy pricing lookup)
- Tool usage ranking with percentages
- Activity patterns by day/hour with streak tracking
- Notable sessions (longest, most messages, highest tokens)

**EPYC relevance**: We have inference_tap.log and session logs but no structured analytics. This pattern could feed into our MemRL reward signals — e.g., correlating tool usage patterns with task success.

### 9. Trajectory Export — ShareGPT Format

**File**: `agent/trajectory.py`

Saves conversations in ShareGPT JSONL format for ML training:
- Converts `<REASONING_SCRATCHPAD>` to `<think>` tags
- Separates successful vs failed trajectories
- Detects incomplete reasoning blocks

**EPYC relevance**: If we want to fine-tune models on our orchestrator's interaction data (e.g., training a better frontdoor or specialist), ShareGPT format is the standard. Low priority but good to know the pattern exists.

### 10. Skill Discovery — OS-Aware Filtering

**File**: `agent/prompt_builder.py` (`build_skills_system_prompt`)

Skills scanned from `~/.gauss/skills/`, filtered by:
- OS platform compatibility
- Tool availability (checks if required executables exist)
- Category grouping for compact index

24 skill categories from apple ecosystem to smart home.

**EPYC relevance**: Our SkillBank uses Q-value weighted retrieval which is more sophisticated, but the OS/tool availability filtering is something we don't do — could prevent skill suggestions that require unavailable tools.

## What OpenGauss Changed From hermes-agent

Key customizations visible in the fork:

1. **Domain focus**: All workflow commands (`/prove`, `/draft`, `/formalize`, etc.) map to `lean4-skills` — the entire UX is Lean-specific
2. **Backend abstraction**: Added Codex support alongside Claude Code
3. **Project model**: `.gauss/project.yaml` with upward discovery — domain-scoped configuration
4. **ACP adapter**: Standardized agent protocol interface (not in original hermes-agent)
5. **Autoformalize launcher**: Managed session spawning with per-backend staging
6. **24 skill categories**: Expanded from hermes-agent's base skill set
7. **Submodules**: `mini-swe-agent` and `tinker-atropos` integrated

## Actionable Findings for EPYC

### High Priority
1. **Tool pair sanitization** (from context_compressor.py): Adopt `_sanitize_tool_pairs()` pattern in our session_log.py. Orphaned tool calls/results cause API rejections and can break context compression.

2. **Multi-backend abstraction** (from autoformalize.py): The `ManagedWorkflowSpec` → `ManagedContext` → `LaunchPlan` pipeline is a clean pattern for abstracting over different inference backends (llama-server, vLLM, etc.).

### Medium Priority
3. **ACP evaluation**: ACP (Agent Client Protocol) goes beyond Agent Protocol with session forking and structured callbacks. Worth evaluating for our external API surface alongside LangGraph Platform.

4. **Protected-zone context compression**: Their implementation is more mature than our B2 plan. Port the tool pair integrity logic and boundary alignment.

5. **Session analytics**: The InsightsEngine pattern (SQLite → structured analytics) could feed MemRL reward signals if we track tool usage × task success correlations.

### Low Priority
6. **Prompt injection scanning**: Add to our prompt resolver if we ever support user-uploaded context files.
7. **Trajectory export**: ShareGPT JSONL for potential fine-tuning data collection.
8. **Terminal handoff**: `/handoff` for debug sessions with direct llama-server access.

## Open Questions

1. How does the swarm coordination actually work at the process level? The CLI shows `/swarm`, `/swarm attach`, `/swarm cancel` but the implementation details weren't fully visible — likely in `gauss_cli/commands.py` or a dedicated swarm module.
2. What's the `tinker-atropos` submodule? The name suggests adversarial testing / red-teaming, which could be relevant for our benchmark suite.
3. How does `mini-swe-agent` integrate with the Lean workflow? Is it used for code editing tasks within proofs?
4. The `cron/` directory and `batch_runner.py` suggest scheduled autonomous runs — similar to our nightshift infrastructure. Worth comparing approaches.
