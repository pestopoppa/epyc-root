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

Key scripts by repo:
- **Seeding/benchmarking**: `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/` (seed_specialist_routing.py, seeding_*.py)
- **Server management**: `/mnt/raid0/llm/epyc-orchestrator/scripts/server/` (orchestrator_stack.py)
- **Model registry (full)**: `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`
- **Model registry (lean)**: `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml`

For fresh setups: `scripts/clone-repos.sh` clones into `repos/` with symlinks.

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

## Session Management

- `scripts/session/session_init.sh` — Discover models, verify llama.cpp
- `scripts/session/health_check.sh` — System health
- `scripts/session/verify_llama_cpp.sh` — Check llama.cpp branch safety
- `scripts/nightshift/` — Autonomous overnight run infrastructure

## Historical Documentation Warning

Documents in `handoffs/archived/`, `handoffs/completed/`, `progress/`, and `CHANGELOG.md` describe historical state — they may reference `/mnt/raid0/llm/claude` (the pre-split monorepo, archived 2026-02-25) and describe code structure that has since changed. **Always verify against actual code before trusting archived descriptions.** Use the repository structure documented above for current paths.

## Code Style

- Shell: `#!/bin/bash` with `set -euo pipefail`
- Always log all actions via agent_log.sh
- Run validation after producing artifacts

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **epyc-root** (381 symbols, 431 relationships, 5 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/epyc-root/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/epyc-root/context` | Codebase overview, check index freshness |
| `gitnexus://repo/epyc-root/clusters` | All functional areas |
| `gitnexus://repo/epyc-root/processes` | All execution flows |
| `gitnexus://repo/epyc-root/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## CLI

- Re-index: `npx gitnexus analyze`
- Check freshness: `npx gitnexus status`
- Generate docs: `npx gitnexus wiki`

<!-- gitnexus:end -->
