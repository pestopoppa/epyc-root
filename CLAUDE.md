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
