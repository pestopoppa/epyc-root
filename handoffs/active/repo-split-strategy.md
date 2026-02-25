# Repository Split Strategy — Comprehensive Handoff

**Created**: 2026-02-20
**Last Updated**: 2026-02-25
**Status**: PHASE 3 COMPLETE — Phase 4 next
**Priority**: High — prerequisite for FOSS release and maintainability
**Scope Note**: Includes pre-split root workload infra optimization for Claude Code/Codex governance workflows. Excludes orchestrator runtime/inference optimization changes.
**Supersedes**: `handoffs/active/open_source_orchestrator.md` (stub)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [The Three Repositories](#2-the-three-repositories)
3. [Root Orchestrator (Umbrella + Governance)](#3-root-orchestrator-umbrella--governance)
4. [Exhaustive File Migration Map](#4-exhaustive-file-migration-map)
5. [Model Registry Split](#5-model-registry-split)
6. [FOSS Readiness](#6-foss-readiness)
7. [Cross-Repo Contracts](#7-cross-repo-contracts)
8. [Per-Repo CLAUDE.md and README Rewrites](#8-per-repo-claudemd-and-readme-rewrites)
9. [Git History Strategy](#9-git-history-strategy)
10. [Pre-Split Root Workload Infra Phases](#10-pre-split-root-workload-infra-phases-claudecodex-only)
11. [Repository Split Phases](#11-repository-split-phases)
12. [Known Coupling Points and Fixes](#12-known-coupling-points-and-fixes)
13. [Verification Checklist](#13-verification-checklist)

---

## 1. Architecture Overview

The monorepo at `pestopoppa/amd-epyc-inference` currently does 4 distinct things:

| Concern | Description | Audience |
|---------|-------------|----------|
| **Orchestrator** | Multi-model hierarchical orchestration with REPL, MemRL, graph routing, tools | FOSS users, AI developers |
| **Inference Research** | AMD EPYC optimization, speculative decoding benchmarks, model quirks | Hardware optimization community |
| **llama.cpp Fork** | Custom patches (slot cache, MoE reduction, BOS fixes) | llama.cpp contributors |
| **Governance + Coordination** | Claude Code hooks, skills, CLAUDE.md matrix, handoffs, progress, logs | Internal workflow (lives in root) |

### Dependency Graph

```
              epyc-root (umbrella + governance)
               /         |         \
              /           |          \
    epyc-orchestrator     |      epyc-llama
              \           |          /
               \          |         /
            epyc-inference-research
```

Governance (hooks, skills, validation, agent files, handoffs, progress, logs) is part of the root
repo — it's inherently cross-repo coordination, not a standalone concern.

**Edges (runtime)**:
- `orchestrator` → `llama` : binary path (`llama-server`), launch commands
- `orchestrator` → `research` : model registry entries, benchmark results for routing weights
- `research` → `llama` : benchmark runner invokes `llama-server` / `llama-bench`
- `root` → all repos : hooks validate artifacts, CLAUDE.md matrix covers all repos

**Edges (development only)**:
- `research` → `orchestrator` : seeding scripts inject MemRL memories from benchmark results

---

## 2. The Three Repositories

### 2a. `epyc-orchestrator` (FOSS candidate)

**Purpose**: Production multi-model orchestration system.
**License**: MIT (already declared in pyproject.toml).

Contains:
- FastAPI API layer (`src/api/`)
- Orchestration graph (`src/graph/`)
- LLM primitives and backends (`src/llm_primitives/`, `src/backends/`)
- REPL execution environment (`src/repl_environment/`)
- MemRL memory system (`orchestration/repl_memory/`)
- Prompt builders and resolution (`src/prompt_builders/`, `orchestration/prompts/`)
- Tool system (`src/tools/`, `orchestration/tools/`, `orchestration/script_registry/`)
- Session persistence (`src/session/`)
- Config system (`src/config/`)
- Model registry (lean version — see §5)
- Services layer (`src/services/` — subset)
- Vision pipeline (`src/vision/`)
- Pipeline monitor (`src/pipeline_monitor/`)
- Classifiers (`src/classifiers/`)
- CLI entry points (`src/cli_orch.py`, `src/cli_sessions.py`)
- Docker support (`Dockerfile`, `Dockerfile.dev`, `docker-compose.yml`)
- Tests (`tests/`)
- Docs: getting-started, model-routing, system-prompt-guide, benchmarking-guide

### 2b. `epyc-inference-research` (public or private)

**Purpose**: AMD EPYC inference optimization research, benchmarking, model evaluation.

Contains:
- Benchmark infrastructure (`scripts/benchmark/`)
- Benchmark prompts and results (`benchmarks/`)
- Research docs and experiments (`research/`, `docs/experiments/`)
- Model sizing and optimization docs (`docs/chapters/`, `docs/reference/benchmarks/`, `docs/reference/models/`)
- Corpus and index building (`scripts/corpus/`, `scripts/nextplaid/`, `cache/next-plaid/`)
- Seeding and scoring scripts (`scripts/*.py` at root level)
- Model registry (full catalog version — see §5)
- Hardware chapters (01-hardware-system, EPYC-specific content)
- TOON encoder experiments (`scripts/toon/`)
- Optuna tuning (`orchestration/optimization_checkpoint.yaml`, `orchestration/optuna_study.db`)
- Voice pipeline experiments (`scripts/voice/`)
- Graph router training (`scripts/graph_router/`)

### 2c. `epyc-llama` (public fork)

**Purpose**: Custom llama.cpp fork with production patches.
**Already exists**: `pestopoppa/llama.cpp` on GitHub.

Contains:
- The llama.cpp fork (already a separate repo at `/mnt/raid0/llm/llama.cpp/`)
- Kernel patches (`kernel-dev/`)
- Build scripts (`scripts/legacy/build_llama.sh`)
- Worktree documentation (`docs/reference/LLAMA_CPP_WORKTREES.md`)

**No migration needed** — this repo already exists. Only needs:
- Move `kernel-dev/` into it
- Ensure `docs/reference/LLAMA_CPP_WORKTREES.md` lives there
- `scripts/session/verify_llama_cpp.sh` moves to root (cross-repo check)

---

## 3. Root Orchestrator (Umbrella + Governance)

Modeled after twyne-root pattern. Lives at `epyc-root/`. Governance (hooks, skills, validation,
agent files) lives here because it's inherently cross-repo coordination — not a standalone concern.

### Structure

```
epyc-root/
├── CLAUDE.md               # Cross-repo coordination rules, dependency map
├── SPEC.md                 # Operational specification (logging, hooks, permissions)
├── BEHAVIORAL.md           # AI agent behavioral standards
├── README.md               # Setup instructions, repo map
├── nightshift.yaml         # Autonomous overnight run config
├── .claude/
│   ├── settings.json       # Hooks: session-start, ripple-detection, edit-guard
│   ├── skills/             # Reusable Claude Code skills
│   ├── commands/           # Claude Code slash commands
│   ├── dependency-map.json # Directed edges between repos
│   └── maintainers.json   # Per-scope write permissions
├── agents/                 # Agent file definitions (shared/ + role overlays)
├── scripts/
│   ├── setup.sh            # Clone all repos, install deps, build agent registry
│   ├── clone-repos.sh      # Minimal: just clone the 3 child repos
│   ├── hooks/              # Claude Code pre/post tool-use hooks
│   ├── validate/           # Governance validation scripts
│   ├── session/            # Session management, health checks
│   ├── nightshift/         # Autonomous run infrastructure
│   ├── system/             # System audit scripts
│   ├── agent_log.sh        # Append-only audit logging functions
│   └── agent_log_analyze.sh # Log analysis
├── repos/                  # Child repos cloned here
│   ├── epyc-orchestrator/
│   ├── epyc-inference-research/
│   └── epyc-llama/         # or symlink to existing
├── docs/
│   ├── reference/
│   │   ├── agent-config/   # Agent file logic, CLAUDE.md matrix, debug playbook
│   │   └── constants-governance.md
│   ├── guides/
│   │   └── agent-workflows/ # Agent persona docs
│   └── recovery/           # Recovery/triage docs
├── handoffs/               # Active, blocked, archived, completed
│   ├── active/
│   ├── blocked/
│   ├── archived/
│   └── completed/
├── logs/
│   └── agent_audit.log     # Cross-repo audit trail (JSONL)
├── progress/               # Cross-repo daily progress reports
└── notes/
    └── agent-changelog.md  # CLAUDE.md change log across all repos
```

### `dependency-map.json`

```json
{
  "edges": [
    {
      "from": "epyc-orchestrator",
      "to": "epyc-llama",
      "coupling": "binary",
      "from_patterns": ["src/config/models.py", "orchestration/model_registry.yaml"],
      "to_files": ["build/bin/llama-server"],
      "notes": "Orchestrator launches llama-server via subprocess. Path from ORCHESTRATOR_PATHS_LLAMA_SERVER env var."
    },
    {
      "from": "epyc-orchestrator",
      "to": "epyc-inference-research",
      "coupling": "data",
      "from_patterns": ["orchestration/model_registry.yaml"],
      "to_files": ["benchmarks/results/**"],
      "notes": "Registry references benchmark results for routing weights. One-way data flow."
    },
    {
      "from": "epyc-inference-research",
      "to": "epyc-llama",
      "coupling": "binary",
      "from_patterns": ["scripts/benchmark/run_inference.sh"],
      "to_files": ["build/bin/llama-server", "build/bin/llama-bench"],
      "notes": "Benchmarks invoke llama.cpp binaries."
    },
    {
      "from": "epyc-root",
      "to": "epyc-orchestrator",
      "coupling": "validation",
      "from_patterns": ["scripts/hooks/*.sh", "scripts/validate/*.py"],
      "to_files": ["orchestration/task_ir.schema.json"],
      "notes": "Root governance hooks validate orchestrator artifacts. Development-time only."
    }
  ]
}
```

### `scripts/clone-repos.sh`

```bash
#!/bin/bash
set -euo pipefail

GITHUB_ORG="${GITHUB_ORG:-pestopoppa}"
REPOS_DIR="$(cd "$(dirname "$0")/.." && pwd)/repos"
mkdir -p "$REPOS_DIR"

repos=(
    epyc-orchestrator
    epyc-inference-research
    epyc-llama:llama.cpp  # remote name differs
)

for entry in "${repos[@]}"; do
    IFS=: read -r local remote <<< "$entry"
    remote="${remote:-$local}"
    dest="$REPOS_DIR/$local"
    if [ -d "$dest" ]; then
        echo "✓ $local already cloned"
    else
        echo "Cloning $remote → $dest"
        git clone "git@github.com:$GITHUB_ORG/$remote.git" "$dest"
    fi
done

echo "All repos ready in $REPOS_DIR"
```

### `scripts/setup.sh`

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# 1. Clone repos
"$SCRIPT_DIR/clone-repos.sh"

# 2. Install orchestrator
cd "$ROOT_DIR/repos/epyc-orchestrator"
if [ -f "pyproject.toml" ]; then
    pip install -e ".[dev]" 2>/dev/null || echo "Install manually: pip install -e '.[dev]'"
fi

# 3. Copy .env.example if no .env
if [ ! -f "$ROOT_DIR/repos/epyc-orchestrator/.env" ] && [ -f "$ROOT_DIR/repos/epyc-orchestrator/.env.example" ]; then
    cp "$ROOT_DIR/repos/epyc-orchestrator/.env.example" "$ROOT_DIR/repos/epyc-orchestrator/.env"
    echo "Created .env from .env.example — edit paths for your system"
fi

# 4. Verify llama.cpp build
if [ -d "$ROOT_DIR/repos/epyc-llama" ]; then
    if [ ! -f "$ROOT_DIR/repos/epyc-llama/build/bin/llama-server" ]; then
        echo "⚠ llama-server not built. Run: cd repos/epyc-llama && cmake -B build && cmake --build build -j$(nproc)"
    fi
fi

echo "Setup complete. Run 'cd repos/epyc-orchestrator && orch --help' to get started."
```

---

## 4. Exhaustive File Migration Map

Every file/directory in the current monorepo mapped to its destination.

### Legend

| Symbol | Meaning |
|--------|---------|
| **O** | `epyc-orchestrator` |
| **R** | `epyc-inference-research` |
| **L** | `epyc-llama` |
| **ROOT** | `epyc-root` (umbrella + governance) |
| **DROP** | Delete (generated, cache, backup, or obsolete) |

### Top-Level Files

| File | Dest | Notes |
|------|------|-------|
| `CLAUDE.md` | **ROOT** + rewrite per-repo | Current version is governance. Each repo gets its own. |
| `CLAUDE_GUIDE.md` | **ROOT** | Human guide for CLAUDE.md |
| `CHANGELOG.md` | **ROOT** | History stays with root; each child repo starts fresh |
| `OPENING_PROMPT.md` | **ROOT** | Session startup prompt |
| `README.md` | **O** rewrite | Current README is chaotic; rewrite for orchestrator focus |
| `Makefile` | **O** | Trim to orchestrator gates only |
| `Justfile` | **O** | Same |
| `pyproject.toml` | **O** | Strip research/governance deps |
| `requirements-dev.txt` | **O** | |
| `uv.lock` | **O** | Regenerate after dep cleanup |
| `docker-compose.yml` | **O** | |
| `Dockerfile` / `Dockerfile.dev` | **O** | |
| `.env.example` | **O** | Already well-structured for portability |
| `.mcp.json` | **ROOT** | MCP tools config for Claude Code |
| `nightshift.yaml` | **ROOT** | Autonomous run config |
| `flake.nix` | **O** | Nix build |
| `plan.md` | **DROP** | Ephemeral |
| `=0.8` / `=1.7.4` | **DROP** | pip version artifacts (ephemeral) |
| `.aider.*` | **DROP** | Aider history/config (ephemeral) |
| `.test_inference_tap.log` | **DROP** | Test log artifact (ephemeral) |
| `MagicMock` | **DROP** | Stray test artifact (ephemeral) |
| `coverage.json` / `.coverage` | **DROP** | Generated |
| `.gitignore` | **O** + adapt per-repo | |
| `.dockerignore` | **O** | |
| `.shellcheckrc` | **O** + **ROOT** | Both have shell scripts |
| `.markdownlint.json` | **O** | |
| `Twyne_V1_Whitepaper_*.json` | **DROP** | Analysis artifacts, not project code |

### `src/` → **O** (epyc-orchestrator)

The entire `src/` directory moves to **O** with these exceptions:

| Path | Dest | Notes |
|------|------|-------|
| `src/` (all) | **O** | Core orchestrator code |
| `src/hierarchical_orchestrator.egg-info/` | **DROP** | Generated |

No files from `src/` go to research or governance. The src/ tree is the orchestrator.

### `orchestration/` → Split

| Path | Dest | Notes |
|------|------|-------|
| `orchestration/model_registry.yaml` | **O** (lean) + **R** (full) | See §5 |
| `orchestration/task_ir.schema.json` | **O** | Core schema |
| `orchestration/architecture_ir.schema.json` | **O** | |
| `orchestration/formalization_ir.schema.json` | **O** | |
| `orchestration/tool_registry.schema.json` | **O** | |
| `orchestration/tool_registry.yaml` | **O** | |
| `orchestration/validate_ir.py` | **O** | |
| `orchestration/classifier_config.yaml` | **O** | |
| `orchestration/generation_monitor.yaml` | **O** | |
| `orchestration/mcp_servers.yaml` | **O** | |
| `orchestration/persona_registry.yaml` | **O** | |
| `orchestration/source_registry.yaml` | **O** | |
| `orchestration/procedure_registry.py` | **O** | |
| `orchestration/procedure_scheduler.py` | **O** | |
| `orchestration/procedure.schema.json` | **O** | |
| `orchestration/procedures/` | **O** | YAML runbooks |
| `orchestration/prompts/` | **O** | Hot-swap prompt templates |
| `orchestration/repl_memory/` | **O** | MemRL subsystem |
| `orchestration/script_registry/` | **O** | Tool manifests |
| `orchestration/tools/` | **O** | Tool implementations |
| `orchestration/examples/` | **O** | TaskIR examples |
| `orchestration/patches/` | **O** | |
| `orchestration/README.md` | **O** | |
| `orchestration/checkpoints/` | **DROP** | Runtime state |
| `orchestration/optimization_checkpoint.yaml` | **R** | Optuna state |
| `orchestration/optuna_study.db` | **R** | Optuna DB |
| `orchestration/optimization_report.md` | **R** | |
| `orchestration/orchestrator_baseline.json` | **R** | Baseline metrics |
| `orchestration/progress/` | **ROOT** | Daily progress reports |
| `orchestration/BLOCKED_TASKS.md` | **ROOT** | Task tracking |
| `orchestration/PROGRESS_TEMPLATE.md` | **ROOT** | |

### `scripts/` → Split

| Path | Dest | Notes |
|------|------|-------|
| `scripts/server/` | **O** | `orchestrator_stack.py`, `launch_production.sh`, `start_servers.sh` |
| `scripts/lib/` | **O** + **R** | Shared libs; duplicate or extract to shared package |
| `scripts/setup/` | **O** | `bootstrap.sh`, `download_models.py` |
| `scripts/skillbank/` | **O** | `seed_skills.py` |
| `scripts/benchmark/` | **R** | All benchmarking infra |
| `scripts/corpus/` | **R** | Index building |
| `scripts/nextplaid/` | **R** | Code search indexing |
| `scripts/toon/` | **R** | TOON experiments |
| `scripts/graph_router/` | **R** | Router training |
| `scripts/experiments/` | **R** | Memory viability etc. |
| `scripts/voice/` | **R** | Voice pipeline experiments |
| `scripts/document/` | **O** | OCR server launchers |
| `scripts/hooks/` | **ROOT** | Claude Code hooks |
| `scripts/validate/` | **ROOT** | Governance validation |
| `scripts/nightshift/` | **ROOT** | Autonomous run infra |
| `scripts/session/` | **ROOT** | Session management, health checks |
| `scripts/utils/agent_log.sh` | **ROOT** | Agent logging (cross-repo audit trail) |
| `scripts/utils/agent_log_analyze.sh` | **ROOT** | Log analysis |
| `scripts/utils/check_draft_compatibility.py` | **R** | Draft compat check |
| `scripts/utils/report_update_workflow.sh` | **R** | |
| `scripts/system/` | **ROOT** | System audit, reorganize |
| `scripts/legacy/` | **DROP** or **R** | Old scripts, keep if historically useful |
| `scripts/*.py` (root-level) | **R** | Seeding, scoring, migration scripts |
| `scripts/strategy_graph/` | **R** | |

### `docs/` → Split

| Path | Dest | Notes |
|------|------|-------|
| `docs/ARCHITECTURE.md` | **O** | System architecture |
| `docs/MODEL_MANIFEST.md` | **R** | Model catalog |
| `docs/SETUP.md` | **O** | |
| `docs/chapters/` | **R** | 29 chapters are research/optimization content |
| `docs/guides/getting-started.md` | **O** | |
| `docs/guides/model-routing.md` | **O** | |
| `docs/guides/model-sizing.md` | **R** | Hardware-specific |
| `docs/guides/system-prompt-guide.md` | **O** | |
| `docs/guides/benchmarking-guide.md` | **R** | |
| `docs/guides/agent-workflows/` | **ROOT** | Agent persona docs |
| `docs/diagrams/` | **O** | Topology diagram |
| `docs/experiments/` | **R** | |
| `docs/deprecated/` | **DROP** | |
| `docs/recovery/` | **ROOT** | Recovery/triage docs |
| `docs/reference/benchmarks/` | **R** | RESULTS.md, SERVER_MODE.md |
| `docs/reference/models/` | **R** | MODELS.md, QUIRKS.md |
| `docs/reference/commands/` | **O** | QUICK_REFERENCE.md |
| `docs/reference/agent-config/` | **ROOT** | Agent file logic, CLAUDE.md matrix, debug playbook |
| `docs/reference/constants-governance.md` | **ROOT** | |
| `docs/reference/LLAMA_CPP_WORKTREES.md` | **L** | |
| `docs/reference/OPEN_SOURCE_RECOMMENDATIONS.md` | **O** | |
| `docs/reference/tool-chaining-patterns.md` | **O** | |

### `tests/` → **O**

All tests move to **O**. They test orchestrator code (`src/`). Research repo gets its own test suite eventually.

### `benchmarks/` → **R**

| Path | Dest | Notes |
|------|------|-------|
| `benchmarks/` (all) | **R** | Prompts, results, baselines, evidence, images, reports |

### `research/` → **R**

| Path | Dest | Notes |
|------|------|-------|
| `research/` (all) | **R** | EAGLE, frspec, specmquant research |

### `handoffs/` → **ROOT**

| Path | Dest | Notes |
|------|------|-------|
| `handoffs/` (all) | **ROOT** | Active, blocked, archived, completed — cross-repo coordination |

### `progress/` → **ROOT**

| Path | Dest | Notes |
|------|------|-------|
| `progress/` (all) | **ROOT** | Daily progress reports — cross-repo visibility |

### `.claude/` → **ROOT** + per-repo

| Path | Dest | Notes |
|------|------|-------|
| `.claude/settings.json` | **ROOT** → adapt per child repo | Hooks reference repo-specific paths |
| `.claude/skills/` | **ROOT** | Skill definitions |
| `.claude/commands/` | **ROOT** | Command definitions |
| `.claude/plans/` | **DROP** | Ephemeral |

### Other Directories

| Path | Dest | Notes |
|------|------|-------|
| `agents/` | **ROOT** | Agent file definitions |
| `backups/` | **DROP** | Old backups |
| `cache/` | **DROP** | Runtime cache (regenerated) |
| `config/` | **DROP** | XDG config dir (desktop env artifacts, not project config) |
| `configs/` | **R** | Memory viability configs |
| `.devcontainer/` | **O** | Dev container |
| `kernel-dev/` | **L** | Kernel patches for llama.cpp |
| `logs/` | **ROOT** | Agent audit log, canvases, strategy graphs; per-repo runtime logs created at runtime |
| `patches/` | **L** or **DROP** | Check if llama.cpp patches |
| `share/` | **DROP** | XDG data dir artifacts |
| `state/` | **DROP** | Runtime state |
| `test_images/` | **O** | Vision test fixtures |
| `tmp/` | **DROP** | Temp files |
| `.venv/` | **DROP** | Virtual env (recreated) |

---

## 5. Model Registry Split

The current `orchestration/model_registry.yaml` (~3600 lines) serves two purposes:
1. **Production routing config**: ports, URLs, timeouts, role mappings
2. **Model catalog**: 30+ model entries with GGUF paths, benchmark results, quirks

### Lean Registry (epyc-orchestrator)

Keep only what the orchestrator needs at runtime:

```yaml
# orchestration/model_registry.yaml (lean — epyc-orchestrator)
version: "1.0"

paths:
  llm_root: "${ORCHESTRATOR_PATHS_LLM_ROOT}"
  model_base: "${ORCHESTRATOR_PATHS_MODEL_BASE}"
  llama_cpp_bin: "${ORCHESTRATOR_PATHS_LLAMA_CPP_BIN}"

roles:
  frontdoor:
    url: "${ORCHESTRATOR_SERVER_URLS_FRONTDOOR:-http://localhost:8080}"
    timeout: 120
  coder_escalation:
    url: "${ORCHESTRATOR_SERVER_URLS_CODER_ESCALATION:-http://localhost:8081}"
    timeout: 180
  worker:
    url: "${ORCHESTRATOR_SERVER_URLS_WORKER:-http://localhost:8082}"
    timeout: 60
  architect_general:
    url: "${ORCHESTRATOR_SERVER_URLS_ARCHITECT_GENERAL:-http://localhost:8083}"
    timeout: 600
  architect_coding:
    url: "${ORCHESTRATOR_SERVER_URLS_ARCHITECT_CODING:-http://localhost:8084}"
    timeout: 600
  # ... etc

defaults:
  temperature: 0.6
  top_p: 0.95
  context_length: 32768
```

No model GGUF paths, no benchmark results, no launch commands. Those belong to whoever operates the servers.

### Full Registry (epyc-inference-research)

The complete registry with all 30+ models, GGUF paths, compatible drafts, launch commands, benchmark results, and hardware-specific tuning. This is the research catalog.

### Migration

1. Copy current registry to research repo (full version)
2. Create lean registry for orchestrator (role→URL mapping only)
3. Update `src/registry_loader.py` to work with either format
4. The `orchestrator_stack.py` launch script needs the full registry — it moves to research or gets a `--registry` flag

---

## 6. FOSS Readiness

### 6a. Path Abstraction

**Problem**: 130+ files hardcode `/mnt/raid0/`.

**Fix**: The `.env.example` already defines `ORCHESTRATOR_PATHS_*` with proper derivation from `LLM_ROOT`. The fix is:

1. **Config module** (`src/config/__init__.py`): Already uses pydantic-settings with `ORCHESTRATOR_` prefix. All path access via `get_config().paths.*` is already portable.

2. **Scripts**: Replace all hardcoded paths with env var reads:
   ```bash
   # Before
   LLAMA_BIN=/mnt/raid0/llm/llama.cpp/build/bin/llama-server
   # After
   LLAMA_BIN="${ORCHESTRATOR_PATHS_LLAMA_SERVER:-llama-server}"
   ```

3. **model_registry.yaml**: The lean version uses `${VAR}` syntax (see §5).

4. **Bulk fix script** (run once during migration):
   ```bash
   # Find remaining hardcoded paths after config/registry cleanup
   grep -rn '/mnt/raid0' src/ orchestration/ scripts/server/ \
     --include='*.py' --include='*.sh' --include='*.yaml' \
     | grep -v '.pyc' | grep -v __pycache__
   ```

### 6b. License

Already MIT in `pyproject.toml`. Add `LICENSE` file to orchestrator repo root.

### 6c. Secrets and Credentials

Audit for:
- No API keys in code (currently clean — keys come from env vars)
- No internal hostnames (currently uses `localhost:PORT` pattern)
- No personal paths beyond `/mnt/raid0/` (already abstracted via `.env.example`)

### 6d. Documentation for External Users

Minimum docs for FOSS release:
- `README.md` — what it does, quick start, architecture diagram
- `docs/guides/getting-started.md` — installation, first run
- `docs/ARCHITECTURE.md` — component overview
- `.env.example` — all configuration knobs documented
- `CONTRIBUTING.md` — new file, standard open-source contribution guide

### 6e. Remove Internal References

Grep and remove:
- References to `Beelzebub` (internal hostname)
- References to `daniele` (username)
- AMD EPYC-specific tuning (move to research repo; orchestrator should be hardware-agnostic)
- `numactl --interleave=all` defaults (document as optional optimization, not hardcoded)

---

## 7. Cross-Repo Contracts

### 7a. Environment Variables (shared interface)

These env vars form the contract between repos:

| Variable | Set By | Used By | Purpose |
|----------|--------|---------|---------|
| `ORCHESTRATOR_PATHS_LLM_ROOT` | User/.env | O, R | Base path for all LLM files |
| `ORCHESTRATOR_PATHS_MODEL_BASE` | User/.env | O, R | GGUF model directory |
| `ORCHESTRATOR_PATHS_LLAMA_CPP_BIN` | User/.env | O, R | llama.cpp binary directory |
| `ORCHESTRATOR_PATHS_LLAMA_SERVER` | User/.env | O, R | llama-server binary path |
| `ORCHESTRATOR_SERVER_URLS_*` | User/.env | O | Per-role server URLs |
| `ORCHESTRATOR_MOCK_MODE` | User/.env | O | Skip real inference in dev |

### 7b. Binary Paths

The orchestrator needs `llama-server` on `$PATH` or via `ORCHESTRATOR_PATHS_LLAMA_SERVER`. It does NOT need to know where llama.cpp source lives.

### 7c. Optional Python Imports

Current code uses lazy imports for optional features. This pattern continues across repos:

```python
# In epyc-orchestrator — optional research integration
try:
    from epyc_research.benchmark_results import get_routing_weights
except ImportError:
    get_routing_weights = None  # Use static weights from registry
```

In practice, the orchestrator should NOT import from research. The data flow is:
- Research produces benchmark results → saved to files
- Orchestrator reads static config (registry YAML, MemRL DB)
- No runtime Python imports across repos (caveat: `scripts/benchmark/` imports from `src/` — see §12i; resolved by declaring `epyc-orchestrator` as a pip dependency in research repo)

### 7d. Data Files (shared at deployment time)

| File | Producer | Consumer | Format |
|------|----------|----------|--------|
| Model GGUF files | User/download | O (via server), R (via benchmark) | Binary |
| MemRL FAISS indices | O (runtime) | O (runtime) | `.faiss` + `.npy` |
| Benchmark results | R | O (manual copy to registry) | JSON/CSV |
| Episodic memory DB | O (runtime) | O (runtime) | SQLite |

---

## 8. Per-Repo CLAUDE.md and README Rewrites

### 8a. `epyc-orchestrator/CLAUDE.md`

```markdown
# Hierarchical Orchestrator

## What This Is
Multi-model local LLM orchestration with REPL execution, MemRL routing, and tool chaining.

## Quick Start
cp .env.example .env  # Edit paths
pip install -e ".[dev]"
orch --help

## Architecture
Request → FastAPI(:8000) → ChatPipeline → OrchestrationGraph → LLMPrimitives → [model servers]
Memory:  EpisodicStore(SQLite) → FAISSStore → ParallelEmbedder
Tools:   ToolRegistry → PluginLoader → [code, web, data, file, knowledge]

## Code Style
- Python 3.11+, ruff for linting, 100 char line length
- All paths via `get_config().paths.*` — never hardcode
- Lazy imports for optional deps (vision, knowledge, graph DB)
- Tests: `pytest tests/ -n 8` (safe default)

## Verification
make gates  # schema → shellcheck → format → lint → tests
```

### 8b. `epyc-inference-research/CLAUDE.md`

```markdown
# AMD EPYC Inference Research

## What This Is
Inference optimization research for AMD EPYC Turin (Zen 5). Speculative decoding, MoE reduction,
prompt lookup, and multi-model benchmarking.

## Hardware
AMD EPYC 9655 — 96c/192t, 1.13TB DDR5, 2x NVMe RAID0

## Key Files
- orchestration/model_registry.yaml — full model catalog
- benchmarks/results/ — raw benchmark data
- docs/reference/benchmarks/RESULTS.md — master results table
- docs/reference/models/QUIRKS.md — known model issues

## Running Benchmarks
python scripts/benchmark/run_benchmark.py --help
```

### 8c. `epyc-root/CLAUDE.md` (umbrella + governance)

```markdown
# EPYC Root — Coordination & Governance

## Purpose
Cross-repo coordination AND agent governance for the epyc project family.
All handoffs, progress reports, agent audit logs, hooks, and skills live HERE.

## Repos
| Repo | Purpose | Path |
|------|---------|------|
| epyc-orchestrator | Production orchestration system | repos/epyc-orchestrator/ |
| epyc-inference-research | Benchmarking and optimization | repos/epyc-inference-research/ |
| epyc-llama | Custom llama.cpp fork | repos/epyc-llama/ |

## Key Directories (in this repo)
- handoffs/ — active, blocked, archived, completed task handoffs
- progress/ — daily progress reports (PROGRESS_YYYY-MM-DD.md)
- logs/ — agent_audit.log (JSONL), canvases, strategy graphs
- agents/ — agent file definitions (shared/ + role overlays)
- scripts/hooks/ — Claude Code pre/post tool-use safety guards
- scripts/validate/ — governance validation scripts
- .claude/skills/ — reusable Claude Code skills

## Hooks
scripts/hooks/*.sh — pre-tool-use safety guards
- check_filesystem_path.sh — block writes outside /mnt/raid0
- check_pytest_safety.sh — block pytest -n auto
- agents_schema_guard.sh — validate agent file schema
- agents_reference_guard.sh — validate agent references

## Dependency Rules
- orchestrator → llama: binary path only (env var)
- research → llama: benchmark invocation only
- root → orchestrator: validation hooks only (dev-time)
- NO runtime Python imports across repos

## Agent Logging
source scripts/agent_log.sh
agent_session_start "Session purpose"
agent_task_start "Description" "Reasoning"
agent_task_end "Description" "success|failure"

## Cross-Repo Changes
Check .claude/dependency-map.json before modifying shared interfaces.
```

---

## 9. Git History Strategy

### `epyc-orchestrator` — Preserve history with `git-filter-repo`

The orchestrator is the most valuable code. Preserve full git history.

```bash
# 1. Fresh clone
git clone git@github.com:pestopoppa/amd-epyc-inference.git epyc-orchestrator
cd epyc-orchestrator

# 2. Filter to orchestrator files only
pip install git-filter-repo
git filter-repo \
  --path src/ \
  --path orchestration/ \
  --path tests/ \
  --path docs/ARCHITECTURE.md \
  --path docs/SETUP.md \
  --path docs/guides/getting-started.md \
  --path docs/guides/model-routing.md \
  --path docs/guides/system-prompt-guide.md \
  --path docs/reference/commands/ \
  --path docs/reference/tool-chaining-patterns.md \
  --path docs/diagrams/ \
  --path scripts/server/ \
  --path scripts/setup/ \
  --path scripts/skillbank/ \
  --path scripts/document/ \
  --path scripts/lib/ \
  --path pyproject.toml \
  --path Makefile \
  --path Justfile \
  --path Dockerfile \
  --path Dockerfile.dev \
  --path docker-compose.yml \
  --path .env.example \
  --path .gitignore \
  --path .dockerignore \
  --path .shellcheckrc \
  --path .markdownlint.json \
  --path flake.nix \
  --path test_images/

# 3. Remove research/governance artifacts from orchestration/
# (progress reports, optuna DBs, etc. — manual cleanup post-filter)

# 4. Update remote
git remote set-url origin git@github.com:pestopoppa/epyc-orchestrator.git
git push -u origin main
```

### `epyc-inference-research` — Clean start

Research content doesn't benefit from commit-level history. Most value is in the data/results, not the diffs.

```bash
mkdir epyc-inference-research && cd epyc-inference-research
git init

# Copy files from monorepo
cp -r ../amd-epyc-inference/benchmarks/ .
cp -r ../amd-epyc-inference/research/ .
cp -r ../amd-epyc-inference/scripts/benchmark/ scripts/benchmark/
cp -r ../amd-epyc-inference/scripts/corpus/ scripts/corpus/
# ... etc per migration map

git add -A
git commit -m "Initial: migrated from amd-epyc-inference monorepo"
```

### `epyc-root` — Clean start

Root + governance is coordination tooling. Clean start is fine. Copy handoffs, progress, logs,
hooks, skills, validation scripts, agent files per migration map.

### `epyc-llama` — Already exists

The fork at `pestopoppa/llama.cpp` already has its own history. Only additions:
- `kernel-dev/` directory from monorepo
- Updated docs

---

## 10. Pre-Split Root Workload Optimization — Production Configuration

### Scope Boundary (hard)

In scope: Claude Code/Codex governance (`.claude/`, hooks, skills, commands, session workflow, context/token budget controls).
Out of scope: Orchestrator runtime, model routing internals, MemRL, server topology, inference kernel/perf.

### 10.1 Confirmed Production Profile (Optuna Trial #24)

**Status**: CONFIRMED via 100-task A/B validation on 2026-02-24.
**Evidence**: `handoffs/active/pre-split-optimization-ab-test-plan.md` Section 14.3.
**Artifacts**: `benchmarks/root_workload/ab_tuning_live/confirm_20260223_233317/`

Result: **−15.2% cost, 0pp quality regression, flat latency**. Decision: **KEEP**.

#### Retained Optimizations

| ID | Name | Scale | What It Does |
|---|---|---|---|
| **0.2** | Context budget enforcement | 0.607 | Index-style CLAUDE.md, facts line cap, on-demand large artifacts |
| **10.7.4** | Admission control + budget diagnostics | 1.157 | Concurrency caps on subagent spawns, per-task budget envelopes |
| **10.7.5** | Structured context compaction | 0.842 | Compact schema blocks for repetitive artifacts (file lists, lint, failure tables) |
| **10.7.7** | Two-stage summarize/review | 0.674 | Stage A cheap summary + Stage B mid-tier verification for long inputs |
| **10.7.9** | Failure taxonomy action map | 0.787 | Deterministic failure-class → action routing (retry/escalate/stop) |
| **10.8** | Model-tier routing | 1.0 | Route tasks to Haiku/Sonnet/Opus by (task_class, difficulty_tier) |

#### Dropped Optimizations

| ID | Name | Reason |
|---|---|---|
| 0.1 | Cost policy contracts | No measurable impact in AB test; overhead not justified |
| 0.3 | Budget-aware subagent governance | Subsumed by 10.7.4 admission control |
| 0.4 | Hook governance/drift control | Already implemented as hooks; no incremental AB gain |
| 0.5 | Nightshift budget optimization | Out of scope for current test battery |
| 0.6 | Split compatibility shim | Deferred to Phase 1 of repo split |
| 10.7.1 | Correctness-gated escalation | Marginal effect; quality gate adds latency |
| 10.7.2 | THINK_HARDER one-shot | No measurable escalation avoidance |
| 10.7.3 | Priority routing override stack | Not triggered in test battery; implement if needed post-split |
| 10.7.6 | Prompt canonicalization | Requires prompt caching infrastructure not yet available |
| 10.7.8 | Delta injection on resume | No resume tasks in current test battery; revisit post-split |
| 10.7.10 | Role-normalized anomaly detection | Monitoring-only; no direct cost/quality impact |

### 10.2 Model-Tier Routing Table (10.8)

Static routing table — confirmed superior to both classifier-based and escalation-based approaches.

| Task Class | Tier 1 (easy) | Tier 2 (medium) | Tier 3 (hard) |
|---|---|---|---|
| `implementation_fix` | Haiku | Sonnet | Opus |
| `planning_synthesis` | Haiku | Sonnet | Opus |
| `long_input` | Sonnet | Sonnet | Opus |
| `read_search` | Haiku | Haiku | Sonnet |
| `resume` | Haiku | Sonnet | Opus |

Routing aggression: **moderate** (no tier bumping).

Per-model measured economics (100-task confirmation):
- **Haiku**: $0.020/task (−78% vs baseline), 94.4% quality
- **Sonnet**: $0.091/task (−2.7%), 96.2% quality
- **Opus**: $0.094/task (+1.1%), 96.7% quality

Key finding: Sonnet and Opus cost nearly the same via Claude CLI (~$0.091 vs $0.094). Savings come almost entirely from Haiku on tier-1 tasks.

#### Approaches Evaluated and Rejected

| Approach | Cost Δ | Quality Δ | Reason Rejected |
|---|---|---|---|
| Haiku classifier routing | −15.7% | −3.0pp | Same savings as static, worse quality, $0.018/call classifier overhead |
| Post-hoc Opus judging + escalation | Worse | n/a | Judge input tokens cost ~$0.08-0.09/call; overhead exceeds savings |
| Haiku-first with escalation chain | Worse | n/a | Same judge cost problem |
| Aggressive routing (more Haiku) | −15%+ | −3pp+ | Quality regression on planning_synthesis tasks |

### 10.3 Implementation Contract

The retained optimizations must be wired into `.claude/agent-cost-policy.json`:

```json
{
  "context_budget": {
    "enabled": true,
    "facts_line_cap": 150,
    "on_demand_large_artifacts": true
  },
  "admission": {
    "concurrency_limits": { "subagent_max": 4 },
    "budget_thresholds": { "per_task_usd": 0.50 }
  },
  "context_compaction": {
    "enabled": true,
    "allowed_artifact_classes": ["file_list", "lint_summary", "failure_table", "test_output"]
  },
  "long_input": {
    "two_stage_enabled": true,
    "stage_thresholds": { "cheap_summary_max_tokens": 2000 }
  },
  "failure_action_map": {
    "schema_format": "retry",
    "logic_error": "think_harder",
    "infra_timeout": "retry",
    "complexity": "escalate"
  },
  "routing": {
    "model_tier": {
      "enabled": true,
      "aggression": "moderate",
      "table": {
        "implementation_fix:1": "haiku", "implementation_fix:2": "sonnet", "implementation_fix:3": "opus",
        "planning_synthesis:1": "haiku", "planning_synthesis:2": "sonnet", "planning_synthesis:3": "opus",
        "long_input:1": "sonnet", "long_input:2": "sonnet", "long_input:3": "opus",
        "read_search:1": "haiku", "read_search:2": "haiku", "read_search:3": "sonnet",
        "resume:1": "haiku", "resume:2": "sonnet", "resume:3": "opus"
      }
    }
  }
}
```

### 10.4 Documentation Outputs (Required Before Split)

| Document | Content |
|---|---|
| `docs/root-workload/cost-policy.md` | Routing table, failure action map, budget thresholds |
| `docs/root-workload/context-budget.md` | Facts cap, compaction rules, two-stage long-input policy |
| `docs/root-workload/metrics-and-reporting.md` | Telemetry fields for all retained optimizations |

### 10.5 Future Cost Reduction Levers (Not Yet Validated)

These could push savings beyond the current −15.2%, but require infrastructure changes:

| Lever | Estimated Impact | Prerequisite |
|---|---|---|
| Prompt caching (90% input discount) | −40-50% | Multi-turn sessions or API-level caching support |
| Raw API calls (bypass CLI overhead) | Unknown | Direct Anthropic API integration; may explain Sonnet≈Opus pricing |
| Output token caps per tier | −10-15% | Per-model max_tokens policy |
| Batch API for async tasks | −8-15% | Non-latency-sensitive task identification |

### Section 10 Exit Rule

Section 10 is complete when:
1. `.claude/agent-cost-policy.json` contains the confirmed routing table and optimization config.
2. Documentation outputs (10.4) are drafted and cross-linked.
3. Section 13 verification checks pass for all retained optimizations.

---

## 11. Repository Split Phases

### Phase 1: Preparation (non-breaking, current repo) — COMPLETE

**Goal**: Make the monorepo splittable without breaking anything.
**Completed**: 2026-02-24 (commit `e2323f8`)

1. ~~Enforce env var usage~~: Replaced 42 hardcoded `/mnt/raid0/` paths across 17 files with `get_config().paths.*`
2. ~~Create lean registry prototype~~: `orchestration/model_registry_lean.yaml` with routing/timeouts/acceleration only
3. ~~Tag the monorepo~~: `git tag v0.1.0-monorepo`

### Phase 2: Create epyc-orchestrator (parallel, non-breaking) — COMPLETE

**Goal**: The orchestrator runs independently from a separate repo.
**Completed**: 2026-02-25 | **Repo**: https://github.com/pestopoppa/epyc-orchestrator

1. ~~`git filter-repo`~~: 771 commits preserved, 24 path filters applied
2. ~~Clean up~~: Removed progress reports, optimization checkpoints, Optuna DB, blocked tasks
3. ~~`LICENSE`~~: MIT (Daniele Pinna)
4. ~~Lean registry~~: Replaced full registry with lean version as default
5. ~~`pyproject.toml`~~: Renamed to `epyc-orchestrator`, removed 6 research dep groups (datasets, tuning, knowledge, retrieval, graph, ui), kept dev/toon/sandbox
6. ~~`README.md`~~: FOSS-focused with quick start, architecture, API docs
7. ~~`CLAUDE.md`~~: Orchestrator-specific (architecture, code style, testing, verification)
8. ~~`CONTRIBUTING.md`~~: Standard open-source guide
9. ~~`.env.example`~~: Generic defaults (relative paths, no `/mnt/raid0/`), lean registry mode
10. ~~Internal refs~~: Removed Beelzebub hostname, daniele username; numactl made conditional via `shutil.which()`
11. ~~Tests~~: 4602 pass, 3 pre-existing failures, 12 research test files removed
12. ~~Pushed~~: `pestopoppa/epyc-orchestrator` main branch

### Phase 3: Create epyc-inference-research (parallel) — COMPLETE

**Goal**: Research content has a home.
**Completed**: 2026-02-25 | **Repo**: https://github.com/pestopoppa/epyc-inference-research

1. ~~Fresh repo~~: `gh repo create`, copied 10,525 files per migration map (no filter-repo — fresh copy)
2. ~~Full `model_registry.yaml`~~: Complete catalog with all 30+ models, GGUF paths, drafts, quirks
3. ~~`pyproject.toml`~~: Core deps (pyyaml, requests, rich, numpy, scikit-learn) + optional groups (benchmark, tuning, knowledge, retrieval, graph, all)
4. ~~`README.md`~~: Research-focused with directory structure, key results, benchmarking workflow
5. ~~`CLAUDE.md`~~: Benchmarking workflow, model registry conventions, hardware context, critical constraints
6. ~~`LICENSE`~~: MIT (Daniele Pinna)
7. ~~`.gitignore`~~: Research patterns (*.db excepted for optuna_study.db, *.gguf, question_pool.jsonl >100MB)
8. ~~Embedded git repos~~: Removed .git dirs from research/eagle-official, frspec/FR-Spec, specmquant/SpecMQuant (committed as plain files)
9. ~~Pushed~~: `pestopoppa/epyc-inference-research` main branch

### Phase 4: Create epyc-root (umbrella + governance)

1. Fresh repo with structure from §3
2. Copy governance files per migration map (hooks, skills, validation, agents, handoffs, progress, logs)
3. Write `CLAUDE.md`, `SPEC.md`, `dependency-map.json`
4. Create `scripts/setup.sh` and `scripts/clone-repos.sh`
5. Create `.claude/settings.json` with cross-repo hooks
6. Port all finalized Phase 0.x docs and contracts into root
7. Test: `./scripts/setup.sh` from scratch clones all child repos and orchestrator runs
8. Push to `pestopoppa/epyc-root`

### Phase 5: Deprecate monorepo

1. Update `amd-epyc-inference` README: "This repo has been split. See epyc-root."
2. Archive the repo (GitHub archive feature)
3. Do NOT delete — preserve as historical reference

---

## 12. Known Coupling Points and Fixes

### 12a. `src/config/__init__.py` (895 lines) — Central config hub

**Problem**: 88 import sites depend on `get_config()`. The config bundles orchestrator settings with research-specific settings (optuna, benchmark paths).

**Fix**: Split config into orchestrator-only settings. Remove:
- `OptimizationConfig` (research)
- Benchmark-specific paths
- Any Optuna references

Keep the pydantic-settings pattern — it's the right approach.

**Files**: `src/config/__init__.py:1-895`, `src/config/models.py`, `src/config/validation.py`

### 12b. `orchestration/model_registry.yaml` — Mixed concerns

**Problem**: ~3600 lines mixing runtime config (ports, timeouts) with research catalog (model paths, benchmarks, quirks).

**Fix**: See §5. Lean registry for orchestrator, full catalog for research.

**Files**: `orchestration/model_registry.yaml`

### 12c. `src/registry_loader.py` — Loads full registry

**Problem**: Parses the full registry including model paths and launch commands. Orchestrator only needs role→URL mapping.

**Fix**: Update to handle lean registry format. If `models:` key is absent, skip model loading. The loader already uses `get()` with defaults for most fields.

**Files**: `src/registry_loader.py`

### 12d. `scripts/server/orchestrator_stack.py` — Launches servers

**Problem**: This script reads the full registry to build `llama-server` launch commands. It couples orchestrator deployment with model management.

**Fix**: This script goes to **research** repo (it's about model server management, not orchestration logic). The orchestrator assumes servers are already running and just connects via URLs.

Alternatively, keep it in orchestrator but make it read a separate `server_configs.yaml` that users provide.

**Files**: `scripts/server/orchestrator_stack.py`

### 12e. `src/graph/helpers.py` — 20+ lazy imports

**Problem**: Lazy imports from across `src.*` to avoid circular dependencies. This file is the coupling bottleneck.

**Fix**: No change needed for the split (all imports are within `src/` which stays together). But document as tech debt for future refactoring.

**Files**: `src/graph/helpers.py`

### 12f. `src/services/corpus_retrieval.py` — NextPLAID dependency

**Problem**: References NextPLAID Docker volumes and index paths.

**Fix**: Already uses `get_config().paths.*` for paths. Ensure NextPLAID is an optional feature:
```python
if not config.paths.nextplaid_index:
    return []  # No corpus retrieval without index
```

**Files**: `src/services/corpus_retrieval.py`

### 12g. `orchestration/repl_memory/` — FAISS indices and SQLite

**Problem**: Session data (`.faiss`, `.db` files) in `orchestration/repl_memory/sessions/`.

**Fix**: Runtime data should NOT be in the repo. Add `sessions/` to `.gitignore`. The path is already configurable via `ORCHESTRATOR_PATHS_SESSIONS_DIR`.

**Files**: `orchestration/repl_memory/sessions/` (gitignore), config paths

### 12h. `src/features.py` — Feature flags (38 import sites)

**Problem**: Feature flags gate functionality across the codebase.

**Fix**: Keep in orchestrator. Remove any research-specific flags (if any). The flag module itself is clean — just boolean checks.

**Files**: `src/features.py`

### 12i. Benchmark scripts importing from `src/`

**Problem**: `scripts/benchmark/*.py` imports from `src.config`, `src.llm_primitives`, etc.

**Fix**: In the research repo, declare `epyc-orchestrator` as a dependency:
```toml
[project]
dependencies = [
    "hierarchical-orchestrator",  # or pip install from git
]
```
Or extract the minimal needed interfaces (config loading, HTTP client) into a shared tiny package.

### 12j. `scripts/lib/` — Shared between orchestrator and research

**Problem**: `scripts/lib/` has utilities used by both benchmark scripts and server scripts.

**Fix**: Copy to both repos. It's small (~7 files). Or extract to a `epyc-common` package if it grows.

**Files**: `scripts/lib/env.sh`, `executor.py`, `onboard.py`, `output_parser.py`, `registry.py`, `scorer.py`, `temperature_optimizer.py`

---

## 13. Verification Checklist

### Pre-Split Root Workload Optimization (Trial #24 Profile)

- [ ] `.claude/agent-cost-policy.json` exists with confirmed routing table and optimization config (Section 10.3)
- [ ] `docs/root-workload/cost-policy.md` documents routing table, failure action map, budget thresholds
- [ ] `docs/root-workload/context-budget.md` documents facts cap, compaction rules, two-stage long-input policy
- [ ] `docs/root-workload/metrics-and-reporting.md` documents telemetry fields for retained optimizations
- [ ] Root `CLAUDE.md` references root workload docs
- [ ] Context budget enforcement (0.2): index-style CLAUDE.md, facts line cap active
- [ ] Admission control (10.7.4): subagent concurrency caps and budget envelopes enforced
- [ ] Structured context compaction (10.7.5): compact schema blocks for approved artifact classes
- [ ] Two-stage summarize/review (10.7.7): staged path active for long inputs
- [ ] Failure taxonomy action map (10.7.9): deterministic failure-class → action routing active
- [ ] Model-tier routing (10.8): static routing table wired, Haiku/Sonnet/Opus by (task_class, tier)
- [ ] 100-task confirmation reproduced: quality ≥95%, cost Δ ≥ −10% vs baseline

### Pre-Split Repository Split Prep

- [ ] Every file in the monorepo is accounted for in §4 migration map
- [ ] No file is assigned to two repos (except `scripts/lib/` intentional duplication)
- [ ] Monorepo tagged as `v0.1.0-monorepo`
- [ ] Top-20 hardcoded paths in `src/` replaced with config calls

### Post-Split: epyc-orchestrator

- [ ] `pip install -e ".[dev]"` succeeds
- [ ] `pytest tests/ -n 8` passes (all tests)
- [ ] `make gates` passes
- [ ] `orch --help` works
- [ ] No `/mnt/raid0/` in Python source (only in `.env.example` as documented default)
- [ ] No references to `Beelzebub`, `daniele`, or internal hostnames in code
- [ ] `.env.example` covers all required env vars
- [ ] `ORCHESTRATOR_MOCK_MODE=1` allows running without any model servers
- [ ] `LICENSE` file present
- [ ] `README.md` has: what it does, quick start, architecture, contributing link

### Post-Split: epyc-inference-research

- [ ] Full model registry present
- [ ] Benchmark scripts run (with `epyc-orchestrator` installed or mocked)
- [ ] `RESULTS.md` and `QUIRKS.md` present and current
- [ ] No orchestrator runtime code (no `src/api/`, no `src/graph/`)

### Post-Split: epyc-root (umbrella + governance)

- [ ] `scripts/setup.sh` clones all child repos from scratch
- [ ] `scripts/clone-repos.sh` is idempotent
- [ ] `dependency-map.json` matches actual repo dependencies
- [ ] Cross-repo hooks fire correctly (ripple detection)
- [ ] Handoffs, progress, and logs directories present and writable
- [ ] Agent logging works: `source scripts/agent_log.sh && agent_session_start "test"`
- [ ] Governance hooks validate orchestrator artifacts in `repos/epyc-orchestrator/`
- [ ] Skills and commands load in Claude Code sessions

### FOSS Readiness (epyc-orchestrator)

- [ ] A fresh user on Ubuntu 24.04 can: clone → install → run in mock mode → see API response
- [ ] No secrets, credentials, or internal references in any committed file
- [ ] All optional features degrade gracefully when deps are missing
- [ ] Docker build succeeds: `docker build -t epyc-orchestrator .`

---

## Appendix: File Count Summary

| Destination | Estimated Files | Primary Content |
|-------------|----------------|-----------------|
| **epyc-orchestrator** | ~1,670 | Python source, tests, prompts, schemas, Docker |
| **epyc-inference-research** | ~800+ | Benchmarks, scripts, research docs, model configs, benchmark images |
| **epyc-llama** | Already exists | + `kernel-dev/` (~10 files) |
| **epyc-root** | ~570 | Setup scripts, CLAUDE.md, dependency map, governance (hooks, skills, validation, agents), handoffs, progress, logs |
| **DROP** | ~50+ | Cache, backups, generated files, temp, XDG dirs |
