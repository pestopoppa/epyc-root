# EPYC Root — AI Assistant Guide

## Purpose

Umbrella repository for cross-repo coordination and governance. No application code lives here — orchestrator code is in `epyc-orchestrator`, research in `epyc-inference-research`, llama.cpp patches in `epyc-llama`.

## Repository Map

All repos are already cloned on this machine. Use the absolute paths below.

| Repo | Absolute Path | Purpose |
|------|---------------|---------|
| epyc-root (this) | `/mnt/raid0/llm/epyc-root` | Governance, agents, hooks, handoffs, progress |
| epyc-orchestrator | `/mnt/raid0/llm/epyc-orchestrator` | Production orchestration (`src/`, `tests/`) |
| epyc-inference-research | `/mnt/raid0/llm/epyc-inference-research` | Benchmarks, seeding, model registry, research |
| epyc-llama | `/mnt/raid0/llm/llama.cpp` | Custom llama.cpp fork |
| hermes-agent (upstream) | `/mnt/raid0/llm/hermes-agent` | Agent frontend (Nous Research, not a child repo) |

Key scripts by repo:
- **Seeding/benchmarking**: `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/` (seed_specialist_routing.py, seeding_*.py)
- **Server management**: `/mnt/raid0/llm/epyc-orchestrator/scripts/server/` (orchestrator_stack.py)
- **Model registry (full)**: `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`
- **Model registry (lean)**: `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml`
- **Hermes setup**: `/mnt/raid0/llm/epyc-root/scripts/hermes/` (setup, config, launch script)

**Single source of truth**: `/workspace/repos/<name>` is a symlink to `/mnt/raid0/llm/<name>` (or `/mnt/raid0/llm/llama.cpp` for `epyc-llama`). Both paths refer to the same physical tree — parallel agent sessions touching either path operate on the same clone, branch, and staging area. Always-good identity: `stat -c %i /workspace/repos/<name>/.git` equals `stat -c %i /mnt/raid0/llm/<name>/.git`.

For fresh setups: `scripts/clone-repos.sh` creates these symlinks (and falls back to a fresh `git clone` only if no canonical tree exists under `/mnt/raid0/llm/`). Idempotent — re-running converts any pre-existing plain-dir clone in `/workspace/repos/` into a symlink, after moving the old tree to `<name>.bak-<timestamp>`. Use `DRY_RUN=1 scripts/clone-repos.sh` to preview.

**If you see divergent commits between `/workspace/repos/<name>` and `/mnt/raid0/llm/<name>`**: the symlink was replaced by a real clone (a parallel agent ran `git clone` directly into the repos path, or `clone-repos.sh` predates the 2026-05-22 fix). Push any unique commits from both sides, then re-run `scripts/clone-repos.sh` to re-link. The script will back up the divergent clone before symlinking — verify the backup contains nothing unique before deleting.

## Dependency Map

See `.claude/dependency-map.json` for formal coupling edges between repos. Key relationships:
- **orchestrator -> llama**: Binary dependency (launches llama-server)
- **orchestrator -> research**: Data dependency (registry references benchmark results)
- **research -> llama**: Binary dependency (benchmarks invoke llama binaries)
- **root -> orchestrator**: Validation dependency (hooks validate artifacts)

## Governance Infrastructure

### Hooks (`scripts/hooks/`)
Pre/post tool-use hooks for Claude Code sessions. These enforce:
- Filesystem path safety (`check_filesystem_path.sh`)
- Agent file schema validation (`agents_schema_guard.sh`)
- Agent reference validation (`agents_reference_guard.sh`)
- Pytest memory safety (`check_pytest_safety.sh`)

### Validation (`scripts/validate/`)
Governance validators that run across repos:
- Agent structure validation
- CLAUDE.md matrix consistency
- Document drift detection
- Numeric literal auditing

### Agent Files (`agents/`)
Agent role definitions using thin-map architecture:
- `shared/` — Common standards (engineering, operating constraints, workflows)
- Role overlays — Per-agent specialization files

### Skills (`.claude/skills/`)
Reusable Claude Code skill definitions for common workflows.

### Commands (`.claude/commands/`)
Slash command definitions for Claude Code sessions.

## Handoff Workflow

Handoffs track cross-repo work items:
- `handoffs/active/` — In-progress work
- `handoffs/blocked/` — Waiting on dependencies
- `handoffs/archived/` — Historical reference

**Start here**: [`handoffs/active/master-handoff-index.md`](handoffs/active/master-handoff-index.md) — single entry point for discovering all active work. Dispatches to 5 domain-specific sub-indices.

**Current architecture review (2026-06-12)**: the `handoffs/active/fable5-findings-*` set is the standing strategic assessment — start at `fable5-findings-00-executive-summary.md`; the prioritized queue rewrite lives at `fable5-proposed-master-index-rewrite.md` until merged into the master index.

### Handoff Index Documents

When creating an index that coordinates multiple handoffs, it must be an **actionable coordination point** — not a passive navigation document. Required sections:
1. **Prioritized task list with checkboxes** — extract all outstanding tasks from linked handoffs, ordered by priority and dependency
2. **Dependency graph** — which tasks block which
3. **Cross-cutting concerns** — how changes in one subsystem affect others
4. **Reporting instructions** — what to update after task completion
5. **Key file locations** — implementation targets

An agent pointed at an index should be able to autonomously discover, prioritize, and execute outstanding work across all linked subsystems.
- `handoffs/completed/` — Done

When completing handoffs, extract findings to docs, then move to `completed/`.

## Progress Tracking

Daily progress in `progress/YYYY-MM/YYYY-MM-DD.md`. Always update after significant work.

## Agent Logging

```bash
source scripts/utils/agent_log.sh
agent_session_start "Session purpose"
agent_task_start "Description" "Reasoning"
agent_task_end "Description" "success|failure"
```

Audit trail in `logs/agent_audit.log`. Analysis: `scripts/utils/agent_log_analyze.sh --summary`.

## Measurement & Claims

`/workspace/MEASUREMENT.md` is the instrument constitution (adopted 2026-06-12). The short form:
- A decision-gating number = `(metric, protocol-id, n/reps, date, attestation ref)`. A number without a protocol citation is an **observation** — usable for hypotheses, never to gate keep/revert/deploy/promote/buy/close decisions.
- **Historical numbers**: era-label first (`epyc-orchestrator/orchestration/instrument_eras.yaml`), then apply the verb — retro-certified → use; demoted-to-prior → hypothesis only (re-measure if it must gate); retired-view → consult the era-appropriate rebuilt view. Never edit historical records to "fix" them — append.
- Benchmarks run only via the codified recipes (`bench_canonical.sh`/`canonical_recipe.py`) with operator approval; agent digest at `agents/shared/MEASUREMENT_POLICY.md`.
- The measurement trust boundary (MEASUREMENT.md, eval tower, scoring, safety gates, era registry rows) is human-amendment-only.

## Session Management

- `scripts/session/session_init.sh` — Discover models, verify llama.cpp
- `scripts/session/health_check.sh` — System health
- `scripts/session/verify_llama_cpp.sh` — Check llama.cpp branch safety
- `scripts/nightshift/` — Autonomous overnight run infrastructure

## Web Search Routing

Two web-search paths are available in this session:

1. **Built-in `WebSearch` tool** — Anthropic-hosted, opaque engine selection, US-only. Best for one-shot lookups where a single result suffices.
2. **`bash scripts/search/searx.sh '<query>'`** — self-hosted SearxNG at `localhost:8888`, returns structured JSON with `engines[]`, `score`, `unresponsive_engines[]`. Best for engine-diversity / multilingual / bulk queries.

**Prefer SearxNG when**:
- Running ≥3 web searches in one phase (literature expansion, cluster surveys).
- Querying non-English content (Chinese-lab papers, EU/JP sources).
- Engine-consensus matters (consistent hits across DDG / Brave / Wikipedia / Qwant).
- You will pipe results through `jq` / `grep` before using them.

**Stick with `WebSearch` when**:
- One-shot factual lookup; the auto-summary is fine.
- SearxNG health check fails (script exits 2).

Health-check / fallback semantics: `searx.sh` exits 2 with a fallback message if `localhost:8888` is unreachable or the endpoint returns valid JSON that is not a SearXNG payload with a `.results` array. On exit 2, switch to `WebSearch` for that query. Do not probe `localhost:8090` for `/search`; ports `8090-8095` are BGE embedding servers and return llama-server 404s for SearXNG paths.

## Historical Documentation Warning

Documents in `handoffs/archived/`, `handoffs/completed/`, `progress/`, and `CHANGELOG.md` describe historical state — they may reference `/mnt/raid0/llm/claude` (the pre-split monorepo, archived 2026-02-25) and describe code structure that has since changed. **Always verify against actual code before trusting archived descriptions.** Use the repository structure documented above for current paths.

## Code Style

- Shell: `#!/bin/bash` with `set -euo pipefail`
- Always log all actions via agent_log.sh
- Run validation after producing artifacts

## Process Management

- When asked to kill a process, **verify it is actually dead** after the kill attempt. Run `ps -p <pid>` to confirm. If SIGINT/SIGTERM fails, immediately escalate to SIGKILL. Do not report success until `ps` confirms the PID is gone.
- When running autopilot or long-lived server processes, **always check if the running process is stale** (predates recent code changes) before declaring a fix is deployed. Compare process start time (`ps -o lstart -p <pid>`) against file modification times. Restart the process if needed.

## Research Intake

- **Never dismiss a research source, model, or technique as "not applicable" or "impractical" without asking the user first.** There is often existing infrastructure context that makes things feasible. When in doubt, flag it for review rather than rejecting.

## Debugging

- When debugging performance or quality issues, **always confirm the metric direction** (higher=better vs lower=better) and ensure you are comparing the correct baselines before proposing fixes. Do not patch symptoms — identify the actual root cause first.
- If unsure about the objective or metric semantics, ask before proceeding.

## Agents & Automation

- **Do not add intake entries, handoff stubs, or other index modifications via sub-agents without explicit user approval.** All index changes must be traceable to a direct user request.

<!-- gitnexus:start -->
<!-- gitnexus:keep -->
# GitNexus — Code Intelligence

Indexed as **epyc-root** (22192 symbols, 23900 relationships, 29 execution flows). Use the `gitnexus` CLI; `gitnexus-*` skills auto-surface in the Skill tool.

**Re-index when stale:** `scripts/gitnexus-analyze.sh` — NOT bare `gitnexus analyze` (re-installs skills into a nested subdir). The wrapper takes a nonblocking per-repo lock at `/tmp/gitnexus-<repo>-analyze.lock`; exit `75` means another analyze is already running, so wait/retry rather than deleting `.gitnexus/` metadata. Interrupted incremental metadata should force GitNexus' normal rebuild path.

## Required before editing

- Run `gitnexus impact <symbol> --direction upstream`. Report blast radius + risk to the user. STOP and warn if HIGH or CRITICAL.
- Run `gitnexus status` once per session; re-analyze via wrapper if stale.

## Required for renames / refactors

- Run `gitnexus context <symbol>` to enumerate every caller/file BEFORE editing. Find-and-replace alone is unsafe.
- See the `gitnexus-refactoring` skill for the full workflow.

## Skills (invoke via Skill tool)

`gitnexus-exploring` · `gitnexus-impact-analysis` · `gitnexus-debugging` · `gitnexus-refactoring` · `gitnexus-guide` · `gitnexus-cli`

## Additional CLI

`gitnexus query <concept>` (execution flows) · `gitnexus cypher <query>` (graph) · `gitnexus wiki` (docs)
<!-- gitnexus:end -->
