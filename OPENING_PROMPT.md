# Claude Code Opening Prompt — EPYC Multi-Repo Project

Copy and paste this as your first message when starting Claude Code.

> **Path history note**: Progress logs and handoffs dated before 2026-02-25 reference
> `/mnt/raid0/llm/claude` (the pre-split monorepo). Those paths are no longer valid.
> Use the repository structure documented below.

---

## OPENING PROMPT (FULL)

```
# 1. Source logging (MANDATORY for all actions)
source scripts/utils/agent_log.sh
agent_session_start "LLM optimization session"

# 2. Load project context
cat CLAUDE.md

# 3. Discover all available models
bash scripts/session/session_init.sh

# 4. Load research results summary (in epyc-inference-research)
head -100 repos/epyc-inference-research/docs/reference/benchmarks/RESULTS.md

# 5. Check model registry for routing (in epyc-inference-research)
head -80 repos/epyc-inference-research/orchestration/model_registry.yaml

PRODUCTION STATUS (December 2025):
===================================
Orchestration: Hierarchical agent system with TaskIR/ArchitectureIR
Best: Prompt Lookup 12.7x, Spec Decode 11x, MoE reduction +87%
Deprecated: EAGLE, CAS-Spec (0% acceptance)

MULTI-REPO STRUCTURE:
=====================
epyc-root (this repo)        — Governance, agents, hooks, skills, handoffs
repos/epyc-orchestrator/     — Production orchestration (src/, tests/)
repos/epyc-inference-research/ — Benchmarks, model registry, research
repos/epyc-llama/            — Custom llama.cpp fork

ORCHESTRATION WORKFLOW:
1. Front Door emits TaskIR -> orchestration/last_task_ir.json
2. Validate: python3 orchestration/validate_ir.py task orchestration/last_task_ir.json
3. Route to specialist/workers per model_registry.yaml
4. Run gates: make gates (in the relevant repo)
5. On failure: return to producer once, then escalate

CRITICAL RULES:
1. ALL files on /mnt/raid0/ ONLY
2. Log ALL actions via agent_log.sh
3. Run `make gates` after producing artifacts
4. Max 3 retries on failures, then STOP
5. NEVER use speculation with SSM models (Qwen3-Next)

Execute session_init.sh and confirm you see the model inventory.
```

---

## ALTERNATIVE: Quick Start

```
source scripts/utils/agent_log.sh && agent_session_start "Quick session"
bash scripts/session/session_init.sh
cat CLAUDE.md | head -150

# Production speedups achieved:
# - Prompt Lookup: 12.7x on summarization
# - Speculative Decoding: 11x on code generation
# - Expert Reduction: +87% on 235B MoE

ALL files on /mnt/raid0/ ONLY — NEVER write to /, /home/, /tmp/, /var/
```

---

## SESSION-SPECIFIC PROMPTS

### Production Inference Session

```
Today's goal: Run optimized inference with best configurations

Best configurations from benchmarks:
- Code generation: Qwen2.5-Coder-32B + 0.5B draft, K=24 -> 33 t/s (11x)
- Summarization: Any model + prompt lookup -> 95.18 t/s (12.7x)
- MoE models: Expert reduction to 4 -> +48-132%
- SSM models: Expert reduction ONLY (no speculation!)

Commands:
# Code generation (11x)
OMP_NUM_THREADS=1 numactl --interleave=all \
  llama-speculative -m Qwen2.5-Coder-32B-Q4_K_M.gguf \
  -md Qwen2.5-Coder-0.5B-Instruct-Q8_0.gguf --draft-max 24 -t 96

# Summarization (12.7x)
llama-cli -m MODEL.gguf --lookup-ngram-min 3 -f doc_with_source.txt -t 96

# MoE expert reduction (+87%)
llama-cli -m Qwen3-235B-A22B-Q4_K_M.gguf \
  --override-kv qwen3moe.expert_used_count=int:4 -t 96
```

### Orchestration Development Session

```
Today's goal: Work on the orchestration layer

Work in: repos/epyc-orchestrator/

Key files:
- orchestration/task_ir.schema.json     # TaskIR JSON Schema
- orchestration/architecture_ir.schema.json  # ArchitectureIR Schema
- orchestration/model_registry.yaml     # Model -> Role mapping (lean version)
- orchestration/validate_ir.py          # IR validator

Workflow:
1. Front Door emits TaskIR for each request
2. Save to orchestration/last_task_ir.json
3. Validate: python3 orchestration/validate_ir.py task orchestration/last_task_ir.json
4. Route per model_registry.yaml routing_hints
5. Workers produce artifacts
6. Run gates: make gates
7. On failure: return to producer, escalate on second failure

Gates (in order): schema -> shellcheck -> format -> lint -> unit -> integration
```

### Benchmarking Session

```
Today's goal: Run benchmarks and record results

Work in: repos/epyc-inference-research/

CRITICAL FLAGS (prevent hangs):
--no-display-prompt --simple-io --no-warmup --temp 0

Baseline benchmark:
OMP_NUM_THREADS=1 numactl --interleave=all \
  ./llama-bench -m MODEL.gguf -t 96 -p 512 -n 128

Speculative decoding benchmark:
OMP_NUM_THREADS=1 numactl --interleave=all \
  llama-speculative -m TARGET.gguf -md DRAFT.gguf \
  --draft-max K -t 96 -n 512 --no-display-prompt

After benchmarking:
1. Record in docs/reference/benchmarks/RESULTS.md
2. Update research summary if significant
3. Run: make gates
```

### Model Testing Session

```
Today's goal: Test new/untested models

Work in: repos/epyc-inference-research/

For each model:
1. Determine architecture (dense/MoE/SSM)
2. Run baseline: ./llama-bench -m MODEL.gguf -t 96 -p 512 -n 128
3. If MoE: Test expert reduction --override-kv ARCH.expert_used_count=int:4
4. If dense: Test with compatible draft model
5. If SSM (Qwen3-Next): NO speculation, expert reduction only
6. Record results in docs/reference/benchmarks/RESULTS.md

Model compatibility rules:
- Qwen2.5 family: Use Qwen2.5-0.5B or Qwen2.5-Coder-0.5B draft
- Qwen3 MoE: Use expert reduction, NOT speculation
- Qwen3-Next (SSM): Expert reduction ONLY
- Qwen3-Coder-480B: Expert reduction ONLY (BOS mismatch)
```

---

## ORCHESTRATION QUICK REFERENCE

### TaskIR Required Fields

```json
{
  "task_id": "string (UUID)",
  "task_type": "chat|doc|code|ingest|manage",
  "priority": "interactive|batch",
  "objective": "string",
  "inputs": [{"type": "path|url|text", "value": "..."}],
  "constraints": ["..."],
  "assumptions": ["..."],
  "agents": [{"tier": "A|B|C|D", "role": "..."}],
  "plan": {"steps": [{"id": "S1", "actor": "...", "action": "...", "outputs": ["..."]}]},
  "gates": ["schema", "format", "lint", "typecheck", "unit"],
  "definition_of_done": ["..."],
  "escalation": {"max_level": "B3", "on_second_failure": true}
}
```

### Model Registry Roles

| Role | Tier | Model | Acceleration |
|------|------|-------|--------------|
| frontdoor | A | Qwen3-Coder-30B-A3B | Expert reduction (4) |
| coder_primary | B | Qwen2.5-Coder-32B | Speculative K=24 |
| ingest_long_context | B | Qwen3-Next-80B-A3B | Expert reduction (2) NO SPEC |
| architect_general | B | Qwen3-235B-A22B | Expert reduction (4) |
| worker_general | C | Meta-Llama-3-8B | Prompt lookup |
| worker_math | C | Qwen2.5-Math-7B | Speculative K=8 |
| draft_qwen25_coder | D | Qwen2.5-Coder-0.5B | -- (85 t/s raw) |

### Gate Chain

```bash
make gates  # Runs: schema -> shellcheck -> format -> lint
```

Individual gates:
```bash
make schema      # Validate IR files
make shellcheck  # Lint .sh scripts
make format      # Format shell + markdown
make lint        # shellcheck + markdownlint
```

---

## CRITICAL CONSTRAINTS

### SSM Models (Qwen3-Next family)
```
NEVER use with:
- --draft / --draft-max (speculative decoding)
- --lookup-ngram-min (prompt lookup)
- Any speculation-based method

ONLY use:
- Expert reduction: --override-kv qwen3next.expert_used_count=int:2
```

### Qwen3-Coder-480B
```
NEVER use speculative decoding (BOS token mismatch)
Use expert reduction: --override-kv qwen3moe.expert_used_count=int:2
```

### All Models
```
NEVER write to /, /home/, /tmp/, /var/
ALL files on /mnt/raid0/ ONLY
```

---

## FAILURE HANDLING

### Gate Failures
1. First failure -> return gate report to producing agent
2. Second failure -> escalate one tier (C->B, B->B3)
3. Third failure -> escalate to B3 Architect with IR/contract fix

### Inference Hangs
1. Check for interactive mode (missing --simple-io)
2. Verify timeout: `timeout 300 llama-cli ...`
3. Kill: `pkill -f llama-cli`
4. Log the failure: `agent_task_end "benchmark" "failure:hang"`

### Loop Detection
```bash
scripts/utils/agent_log_analyze.sh --loops
```

Max 3 retries, then STOP and document blocker.

---

## DIRECTORY STRUCTURE

```
/mnt/raid0/llm/epyc-root/           # This repo — governance umbrella
├── CLAUDE.md                        # Main project guide
├── OPENING_PROMPT.md                # This file
├── agents/                          # Agent role definitions
├── handoffs/                        # active/, blocked/, archived/, completed/
├── progress/                        # Daily progress logs
├── logs/                            # Runtime logs, agent_audit.log
├── scripts/
│   ├── hooks/                       # Claude Code pre/post hooks
│   ├── session/                     # Session management
│   ├── nightshift/                  # Autonomous overnight runs
│   ├── system/                      # System utilities
│   └── utils/                       # agent_log.sh, analysis
└── repos/                           # Child repositories
    ├── epyc-orchestrator/           # Production orchestration
    │   ├── src/                     # Application code
    │   ├── tests/                   # Test suite
    │   └── orchestration/           # Registry, prompts, schemas
    ├── epyc-inference-research/     # Research & benchmarks
    │   ├── benchmarks/              # prompts/, results/
    │   ├── docs/                    # chapters/, reference/
    │   ├── orchestration/           # Full model registry
    │   └── scripts/                 # Benchmark scripts
    └── epyc-llama/                  # Custom llama.cpp fork
```

---

## VERIFYING AGENT BEHAVIOR

```bash
# Summary of activity
scripts/utils/agent_log_analyze.sh --summary

# Detect loops
scripts/utils/agent_log_analyze.sh --loops

# Show errors
scripts/utils/agent_log_analyze.sh --errors

# Get rollback commands
scripts/utils/agent_log_analyze.sh --rollbacks
```

---

## CONTEXT WINDOW COMPACTION PROTOCOL

**When the agent needs to compact context, it MUST first:**

```bash
# 1. Log session state
agent_task_start "Pre-compaction save" "Preserving state"
agent_observe "completed_tasks" "List what was done"
agent_observe "current_task" "What's in progress"
agent_observe "pending_tasks" "What remains"

# 2. Update research report with any new findings

# 3. Create summary for retention
echo "=== COMPACTION SUMMARY ==="
echo "Session: $AGENT_SESSION_ID"
echo "Progress: [describe]"
echo "Next steps: [describe]"
echo "Active models: [list paths]"

agent_task_end "Pre-compaction save" "ready"
```
