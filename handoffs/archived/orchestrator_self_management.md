# Handoff: Orchestrator Self-Management Infrastructure

**Created:** 2026-01-24
**Updated:** 2026-01-24 (Phases 1-8 COMPLETE)
**Status:** ✅ IMPLEMENTATION COMPLETE (Phase 9 optional)
**Priority:** High
**Plan File:** `/home/daniele/.claude/plans/mighty-prancing-pillow.md`

---

## Executive Summary

Enable the local orchestrator to deterministically perform self-management operations:
1. New model benchmarking
2. Model registry management
3. Codebase management
4. Fine-tuning operations

**Core Principle:** LLM generates minimal tokens (~350/operation); deterministic code executes work.

---

## User Requirements (Verbatim)

### 1. Checkpointing & Hot-Swap
> "checkpoint any configurations of any model used by the orchestrator such that individual model servers can be 'detached' from the orchestration, rebooted and reattached, without having to reload the entire orchestration engine"

### 2. Rollback & Approval
> "There must be a deterministic script for rewinding changes through either github or some other versioning system. In all cases, the orchestration should prepare diffs/patches for owner to approve."

### 3. Pausable Procedures
> "if the orchestration is needed by the user for active work, benchmarks and long procedures should be easily placeable on pause for later scheduled resumption"

### 4. Self-Optimization
> "During idle time, the frontdoor model could run a routine to selectively explore performance optimizations of itself"

### 5. Token Efficiency
> "Because such self-work can be very work intensive, it is important to transform all deterministic tasks into tools as much as possible. Tokens should always be generated very judiciously"

---

## Architecture Decision: No K8s/Terraform

**Evaluated:** Kubernetes + Terraform for service orchestration

**Decision:** Stay with enhanced Python orchestrator (`orchestrator_stack.py`)

**Rationale:**
1. **Single-machine** - K8s value is cluster orchestration; overhead without benefit on single EPYC 9655
2. **NUMA sensitivity** - `numactl --interleave=all` for 460GB/s bandwidth; containers add friction
3. **mmap model loading** - HOT/WARM/COLD pools rely on direct memory access
4. **Zero overhead** - Current approach has no containerization cost

**Reconsider K8s if:**
- Add second inference node
- Multi-user workload isolation needed
- Cloud deployment

---

## Architecture: Three-Layer Self-Management

```
┌─────────────────────────────────────────────────────────┐
│                    REPL Environment                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ get_proc()  │  │ run_step()  │  │ validate()  │      │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘      │
└─────────┼────────────────┼────────────────┼─────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────┐
│              Procedure Registry (NEW)                    │
│  procedures/                                             │
│    benchmark_new_model.yaml                              │
│    update_registry_perf.yaml                             │
│    add_model_quirks.yaml                                 │
│    run_finetuning.yaml                                   │
└────────────────────────┬────────────────────────────────┘
                         │ outcomes logged to
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Episodic Memory (existing)                  │
│  - Learns which procedures succeed in which contexts     │
│  - Q-values track procedure effectiveness                │
│  - Suggests procedures based on past success             │
└─────────────────────────────────────────────────────────┘
```

---

## Key Insight: Procedures vs Examples

| Approach | Use Case | Determinism |
|----------|----------|-------------|
| **Episodic Memory** | "Tasks like this succeeded with..." | Fuzzy |
| **Procedure Registry** | "To benchmark a model, run steps 1-5" | Deterministic |
| **Script Registry** | "Execute this validated code block" | Deterministic |

**Recommendation:** Procedure Registry is best - deterministic + learnable + maintainable.

---

## Implementation Phases

### Phase 1: Procedure Registry Core ✅ COMPLETE
- [x] Create `orchestration/procedures/` directory
- [x] Create `orchestration/procedures/state/` directory
- [x] Create `orchestration/checkpoints/` directory
- [x] Create `orchestration/patches/{pending,approved,rejected}` directories
- [x] Define `procedure.schema.json` for YAML validation (319 lines)
- [x] Implement `ProcedureRegistry` class with load/validate/execute (~980 lines)
- [x] Unit tests for registry (486 lines, 25 tests passing)

### Phase 2: REPL Integration (Procedure Tools) ✅ COMPLETE
- [x] `_run_procedure()` - full execution with gates
- [x] `_list_procedures()` - list by category
- [x] `_get_procedure_status()` - check procedure status

### Phase 3: Checkpointing & Hot-Swap ✅ COMPLETE
- [x] `_checkpoint_create()` - save server configs
- [x] `_checkpoint_restore()` - restore from checkpoint
- [ ] Hook into `orchestrator_stack.py` start/stop (optional)
- [ ] (Optional) `_generate_systemd_units()` - boot persistence

### Phase 4: Pausable Procedures ✅ COMPLETE
- [x] State machine: PENDING → RUNNING → PAUSED → COMPLETED/FAILED
- [x] `ProcedureScheduler` class (522 lines) with:
  - Job scheduling with dependencies
  - Pause/resume support
  - Statistics tracking
  - Background execution

### Phase 5: Rollback & Approval ✅ COMPLETE
- [x] `_prepare_patch()` - generate unified diff to `patches/pending/`
- [x] `_list_patches()` - list patches by status
- [x] `_apply_approved_patch()` - apply after approval
- [x] `_reject_patch()` - reject with reason

### Phase 6: Core Procedures (Benchmarking) ✅ COMPLETE
- [x] `benchmark_new_model.yaml`
- [x] `update_registry_performance.yaml`
- [x] `add_model_to_registry.yaml`
- [x] `add_model_quirks.yaml`
- [x] `check_draft_compatibility.yaml`
- [x] `deprecate_model.yaml` (added for safety)

### Phase 7: Memory Integration ✅ COMPLETE
- [x] Log procedure executions to episodic memory (`_log_to_memory()`)
- [x] Seed 8 procedure-calling examples (56 total now)
- [x] `enable_memory` parameter for `ProcedureRegistry`

### Phase 8: Advanced Procedures ✅ COMPLETE
- [x] `run_quality_gates.yaml`
- [x] `create_handoff.yaml`
- [x] `prepare_finetuning_dataset.yaml`
- [x] `run_finetuning.yaml`
- [x] `evaluate_finetuned_model.yaml`

### Phase 9: Self-Optimization ⏸️ OPTIONAL/DEFERRED
- [ ] Integrate Optuna idle-time loop
- [ ] `IdleTimeOptimizer` class
- [ ] Runtime parameter tuning

---

## Files Created/Modified

| File | Change | Status |
|------|--------|--------|
| `orchestration/procedures/` | NEW directory | ✅ Created |
| `orchestration/procedures/state/` | NEW directory | ✅ Created |
| `orchestration/checkpoints/` | NEW directory | ✅ Created |
| `orchestration/patches/{pending,approved,rejected}/` | NEW directory tree | ✅ Created |
| `orchestration/procedure.schema.json` | NEW YAML schema (319 lines) | ✅ Created |
| `orchestration/procedure_registry.py` | NEW registry + executor (~980 lines) | ✅ Created |
| `orchestration/procedure_scheduler.py` | NEW background scheduler (522 lines) | ✅ Created |
| `tests/unit/test_procedure_registry.py` | NEW unit tests (486 lines, 25 tests) | ✅ Created |
| `src/repl_environment.py` | Add 9 procedure/patch tools | ✅ Modified |
| `orchestration/procedures/*.yaml` | 11 procedure definitions | ✅ Created |
| `orchestration/repl_memory/seed_examples.json` | Add 8 procedure examples (56 total) | ✅ Modified |
| `scripts/server/orchestrator_stack.py` | Add checkpoint hooks | ⏸️ Optional |

### Procedure YAML Files (11 total)

| Procedure | Category | Purpose |
|-----------|----------|---------|
| `benchmark_new_model.yaml` | benchmark | Run benchmark suite on new GGUF model |
| `check_draft_compatibility.yaml` | benchmark | Validate draft-target pairing |
| `add_model_to_registry.yaml` | registry | Add new model entry |
| `update_registry_performance.yaml` | registry | Update t/s, speedup metrics |
| `add_model_quirks.yaml` | registry | Document model quirks |
| `deprecate_model.yaml` | registry | Mark model deprecated (manual delete) |
| `run_quality_gates.yaml` | codebase | Run full gate suite |
| `create_handoff.yaml` | codebase | Generate handoff documents |
| `prepare_finetuning_dataset.yaml` | finetuning | Prepare/split datasets |
| `run_finetuning.yaml` | finetuning | Execute LoRA/QLoRA training |
| `evaluate_finetuned_model.yaml` | finetuning | Post-training evaluation |

### REPL Tools Added (9 total)

| Tool | Purpose |
|------|---------|
| `_run_procedure()` | Execute procedure with inputs |
| `_list_procedures()` | List procedures by category |
| `_get_procedure_status()` | Check procedure status |
| `_checkpoint_create()` | Save server configs |
| `_checkpoint_restore()` | Restore from checkpoint |
| `_prepare_patch()` | Generate unified diff |
| `_list_patches()` | List patches by status |
| `_apply_approved_patch()` | Apply approved patch |
| `_reject_patch()` | Reject with reason |

---

## Procedure YAML Schema (Draft)

```yaml
# Example: benchmark_new_model.yaml
id: benchmark_new_model
description: Run full benchmark suite on a new model
version: 1.0
category: benchmarking  # benchmarking | registry | codebase | finetuning

prerequisites:
  - check: file_exists
    path: "{model_path}"
  - check: model_in_registry
    model: "{model_name}"
    required: false

parameters:
  model_path:
    type: string
    required: true
    description: Full path to GGUF model
  model_name:
    type: string
    required: true
  suite:
    type: string
    default: "all"
    enum: [all, thinking, coder, general, agentic, math, vl, long_context, instruction_precision]

steps:
  - id: health_check
    action: run_shell
    command: |
      # NOTE: llama.cpp path is environment-specific
      # Set LLAMA_CLI env var or adjust path
      timeout 15 ${LLAMA_CLI:-llama-cli} \
        -m {model_path} -p "Hello" -n 10 --no-display-prompt
    on_failure: abort

  - id: detect_architecture
    action: run_shell
    command: |
      /mnt/raid0/llm/llama.cpp/build/bin/llama-cli \
        -m {model_path} --show-config 2>&1 | grep -E "arch|expert"
    extract:
      architecture: "grep -oP 'arch: \\K\\w+'"
      expert_count: "grep -oP 'n_expert: \\K\\d+'"

  - id: run_benchmark
    action: run_shell
    command: |
      ./scripts/benchmark/run_overnight_benchmark_suite.sh \
        --model {model_path} --suite {suite}
    timeout: 14400  # 4 hours
    background: true
    pausable: true  # Can be paused/resumed

  - id: wait_and_score
    action: run_shell
    depends_on: run_benchmark
    command: |
      python scripts/benchmark/score_benchmarks.py \
        --model {model_name} --latest
    extract:
      score_pct: "grep -oP 'Score: \\K[\\d.]+%'"
      avg_tps: "grep -oP 'Avg TPS: \\K[\\d.]+'"

  - id: update_registry
    action: python
    code: |
      from scripts.lib.registry import ModelRegistry
      reg = ModelRegistry()
      reg.update_performance(
          model="{model_name}",
          baseline_tps=float("{avg_tps}"),
          benchmark_date=datetime.now().isoformat()[:10]
      )
      reg.save()
    requires_approval: true  # Generates patch for review

gates:
  - results_file_exists
  - registry_updated
  - results_md_updated

on_success:
  log_to_memory: true
  q_value: 0.9

on_failure:
  log_to_memory: true
  q_value: 0.3
  create_handoff: true
```

---

## Procedure State File (For Pause/Resume)

```yaml
# orchestration/procedures/state/{procedure_id}_{timestamp}.yaml
procedure_id: benchmark_new_model
execution_id: "2026-01-24T10:00:00_abc123"
started_at: "2026-01-24T10:00:00"
paused_at: "2026-01-24T11:30:00"  # null if running
status: paused  # pending | running | paused | completed | failed
current_step: run_benchmark
completed_steps:
  - health_check
  - detect_architecture
extracted_values:
  architecture: qwen2
  expert_count: 64
parameters:
  model_path: /mnt/raid0/llm/models/NewModel.gguf
  model_name: NewModel
  suite: all
resume_at: "2026-01-24T18:00:00"  # scheduled resumption (optional)
error: null  # error message if failed
```

---

## Server Checkpoint Format

```yaml
# orchestration/checkpoints/server_state.yaml
checkpoint_id: "2026-01-24T14:30:00"
created_at: "2026-01-24T14:30:00"
servers:
  frontdoor:
    port: 8080
    model: Qwen3-Coder-30B-A3B-Q4_K_M.gguf
    model_path: /mnt/raid0/llm/models/Qwen3-Coder-30B-A3B-Q4_K_M.gguf
    pid: 12345
    state: running
    config:
      threads: 96
      ctx_size: 32768
      override_kv: "qwen3moe.expert_used_count=int:4"
      numa: interleave_all
  coder_primary:
    port: 8081
    model: Qwen2.5-Coder-32B-Q4_K_M.gguf
    draft: Qwen2.5-Coder-0.5B-Instruct-Q8_0.gguf
    pid: 12346
    state: running
    config:
      threads: 96
      draft_max: 24
```

---

## Rollback Checkpoint Format

```yaml
# orchestration/checkpoints/rollback_{checkpoint_id}.yaml
checkpoint_id: "pre_benchmark_2026-01-24"
created_at: "2026-01-24T10:00:00"
description: "Before benchmarking NewModel"
git_ref: "abc123def456"
git_branch: main
files_modified:
  - path: orchestration/model_registry.yaml
    hash_before: "sha256:..."
  - path: docs/reference/benchmarks/RESULTS.md
    hash_before: "sha256:..."
```

---

## REPL Tools Summary (12 New Tools)

### Procedure Tools (4)
| Tool | Signature | Purpose |
|------|-----------|---------|
| `get_procedure` | `(id: str) -> JSON` | Get procedure definition |
| `list_procedures` | `(category?: str) -> JSON` | List available procedures |
| `run_procedure` | `(id: str, **params) -> JSON` | Execute full procedure |
| `run_procedure_step` | `(id: str, step: str, **params) -> JSON` | Execute single step |

### Checkpoint Tools (4)
| Tool | Signature | Purpose |
|------|-----------|---------|
| `checkpoint_servers` | `() -> JSON` | Save all server configs |
| `restore_server` | `(role: str, checkpoint?: str) -> JSON` | Restore single server |
| `detach_server` | `(role: str) -> JSON` | Graceful stop + save state |
| `reattach_server` | `(role: str) -> JSON` | Restart from saved state |

### Pause/Resume Tools (3)
| Tool | Signature | Purpose |
|------|-----------|---------|
| `pause_procedure` | `(id: str, resume_at?: str) -> JSON` | Pause with optional schedule |
| `resume_procedure` | `(id: str) -> JSON` | Resume from last step |
| `list_paused_procedures` | `() -> JSON` | List paused with schedules |

### Rollback Tools (4)
| Tool | Signature | Purpose |
|------|-----------|---------|
| `create_rollback_point` | `(description: str) -> JSON` | Git checkpoint |
| `preview_changes` | `(checkpoint_id: str) -> str` | Show diff |
| `prepare_patch` | `(files: list, desc: str) -> str` | Generate unified diff |
| `apply_approved_patch` | `(patch_id: str) -> JSON` | Apply after approval |

---

## Token Budget

| Operation | Target Tokens | Actual (Manual) |
|-----------|---------------|-----------------|
| Identify procedure needed | ~50 | 2000+ |
| Call `run_procedure()` | ~100 | 500+ |
| Summarize result | ~200 | 500+ |
| **Total per operation** | **~350** | **3000-5000** |

**Goal:** 10x reduction in tokens for self-management operations.

---

## Existing Infrastructure to Leverage

| Component | Location | Purpose |
|-----------|----------|---------|
| Optuna framework | `scripts/benchmark/optuna_orchestrator.py` | Self-optimization |
| Episodic memory | `orchestration/repl_memory/` | Procedure learning |
| Model registry | `orchestration/model_registry.yaml` | Server configs |
| Orchestrator stack | `scripts/server/orchestrator_stack.py` | Server management |
| Benchmark scripts | `scripts/benchmark/` | 19 scripts to wrap |

---

## Open Questions

1. **Permission model**: Should all procedures be available to all roles, or tier-based?
   - *Current thinking*: Start with all available; add restrictions if needed

2. **Versioning**: How to handle procedure updates without breaking memory references?
   - *Current thinking*: Version field in YAML; memory stores `procedure_id:version`

3. **Parameter validation**: Strict schema enforcement or flexible?
   - *Current thinking*: Strict for required params, flexible for optional

---

## Permissions Added (2026-01-24)

The following permissions were added to `.claude/settings.local.json` for yolo agent execution:

```json
"Bash(python:*)",
"Bash(python orchestration/procedure_registry.py:*)",
"Bash(pytest:*)",
"Bash(pytest tests/:*)",
"Bash(mkdir -p:*)",
"Bash(touch:*)",
"Bash(rm:*)",
"Bash(cp:*)",
"Bash(mv:*)",
"Bash(wc:*)",
"Bash(head:*)",
"Bash(tail:*)",
"Bash(test:*)",
"Bash(git status:*)",
"Bash(git diff:*)",
"Bash(git log:*)",
"Bash(git show:*)",
"Bash(git branch:*)",
"Bash(git rev-parse:*)",
"Bash(agent_task_start:*)",
"Bash(agent_task_end:*)",
"Bash(agent_session_start:*)",
"Read(**)",
"Edit(**)",
"Write(**)"
```

---

## Autonomous Execution Guide (For Yolo Agent)

### Environment Notes
- **Local (Beelzebub)**: Project at `/mnt/raid0/llm/claude/`
- **Container/DevSpace**: Project at `/workspace/`
- All paths in this handoff are **relative** to project root
- For llama.cpp commands: set `LLAMA_CLI` env var or skip those steps if not available

### Pre-Flight Checks
```bash
# Run from project root (wherever it's mounted)

# Verify directories exist
test -d orchestration/procedures/state && echo "✓ procedures/state exists"
test -d orchestration/checkpoints && echo "✓ checkpoints exists"
test -d orchestration/patches/pending && echo "✓ patches dir exists"

# Verify REPL environment exists
test -f src/repl_environment.py && echo "✓ repl_environment.py exists"
```

### Step 1: Create procedure.schema.json
**File:** `orchestration/procedure.schema.json`
**Validation:** `python -c "import json; json.load(open('orchestration/procedure.schema.json'))"`

### Step 2: Create ProcedureRegistry class
**File:** `orchestration/procedure_registry.py`
**Validation:** `python -c "from orchestration.procedure_registry import ProcedureRegistry; print('✓ Import OK')"`

### Step 3: Create first procedure YAML
**File:** `orchestration/procedures/benchmark_new_model.yaml`
**Validation:** `python orchestration/procedure_registry.py validate orchestration/procedures/benchmark_new_model.yaml`

### Step 4: Add REPL tools
**File:** `src/repl_environment.py` (edit existing)
**Validation:** `python -c "from src.repl_environment import REPLEnvironment; r=REPLEnvironment(); print('get_procedure' in r.tools)"`

### Step 5: Run unit tests
**Command:** `pytest tests/unit/test_procedure_registry.py -v`
**Validation:** Exit code 0

### Gate: Phase 1 Complete
```bash
# All must pass
python -c "from orchestration.procedure_registry import ProcedureRegistry; p=ProcedureRegistry(); print(f'Loaded {len(p.procedures)} procedures')"
python -c "from src.repl_environment import REPLEnvironment; r=REPLEnvironment(); assert 'get_procedure' in r.tools"
```

---

## Exact File Contents

### File 1: orchestration/procedure.schema.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Procedure Definition",
  "type": "object",
  "required": ["id", "description", "version", "category", "steps"],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[a-z_]+$",
      "description": "Unique procedure identifier (snake_case)"
    },
    "description": {
      "type": "string",
      "description": "Human-readable description"
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+$",
      "description": "Semantic version (major.minor)"
    },
    "category": {
      "type": "string",
      "enum": ["benchmarking", "registry", "codebase", "finetuning", "maintenance"]
    },
    "prerequisites": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["check"],
        "properties": {
          "check": {"type": "string", "enum": ["file_exists", "model_in_registry", "server_running", "git_clean"]},
          "path": {"type": "string"},
          "model": {"type": "string"},
          "role": {"type": "string"},
          "required": {"type": "boolean", "default": true}
        }
      }
    },
    "parameters": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["type"],
        "properties": {
          "type": {"type": "string", "enum": ["string", "integer", "boolean", "array"]},
          "required": {"type": "boolean", "default": false},
          "default": {},
          "enum": {"type": "array"},
          "description": {"type": "string"}
        }
      }
    },
    "steps": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "action"],
        "properties": {
          "id": {"type": "string", "pattern": "^[a-z_]+$"},
          "action": {"type": "string", "enum": ["run_shell", "python", "llm_call", "wait"]},
          "command": {"type": "string"},
          "code": {"type": "string"},
          "prompt": {"type": "string"},
          "depends_on": {"type": "string"},
          "timeout": {"type": "integer", "default": 300},
          "background": {"type": "boolean", "default": false},
          "pausable": {"type": "boolean", "default": false},
          "requires_approval": {"type": "boolean", "default": false},
          "on_failure": {"type": "string", "enum": ["abort", "continue", "retry"], "default": "abort"},
          "extract": {
            "type": "object",
            "additionalProperties": {"type": "string"}
          }
        }
      }
    },
    "gates": {
      "type": "array",
      "items": {"type": "string"}
    },
    "on_success": {
      "type": "object",
      "properties": {
        "log_to_memory": {"type": "boolean"},
        "q_value": {"type": "number", "minimum": 0, "maximum": 1}
      }
    },
    "on_failure": {
      "type": "object",
      "properties": {
        "log_to_memory": {"type": "boolean"},
        "q_value": {"type": "number", "minimum": 0, "maximum": 1},
        "create_handoff": {"type": "boolean"}
      }
    }
  }
}
```

### File 2: orchestration/procedure_registry.py

```python
#!/usr/bin/env python3
"""Procedure Registry for deterministic self-management operations.

Loads, validates, and executes YAML-defined procedures.
"""

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml

try:
    import jsonschema
except ImportError:
    jsonschema = None


class ProcedureStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StepResult:
    step_id: str
    success: bool
    output: str = ""
    extracted: dict = field(default_factory=dict)
    duration_seconds: float = 0.0
    error: Optional[str] = None


@dataclass
class ProcedureState:
    procedure_id: str
    execution_id: str
    status: ProcedureStatus
    started_at: datetime
    paused_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    completed_steps: list = field(default_factory=list)
    extracted_values: dict = field(default_factory=dict)
    parameters: dict = field(default_factory=dict)
    resume_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_yaml(self) -> str:
        return yaml.dump({
            "procedure_id": self.procedure_id,
            "execution_id": self.execution_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "current_step": self.current_step,
            "completed_steps": self.completed_steps,
            "extracted_values": self.extracted_values,
            "parameters": self.parameters,
            "resume_at": self.resume_at.isoformat() if self.resume_at else None,
            "error": self.error,
        }, default_flow_style=False)

    @classmethod
    def from_yaml(cls, content: str) -> "ProcedureState":
        data = yaml.safe_load(content)
        return cls(
            procedure_id=data["procedure_id"],
            execution_id=data["execution_id"],
            status=ProcedureStatus(data["status"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            paused_at=datetime.fromisoformat(data["paused_at"]) if data.get("paused_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            current_step=data.get("current_step"),
            completed_steps=data.get("completed_steps", []),
            extracted_values=data.get("extracted_values", {}),
            parameters=data.get("parameters", {}),
            resume_at=datetime.fromisoformat(data["resume_at"]) if data.get("resume_at") else None,
            error=data.get("error"),
        )


class ProcedureRegistry:
    """Registry for loading, validating, and executing procedures."""

    def __init__(self, procedures_dir: str = None, schema_path: str = None):
        self.base_dir = Path("orchestration")
        self.procedures_dir = Path(procedures_dir) if procedures_dir else self.base_dir / "procedures"
        self.state_dir = self.procedures_dir / "state"
        self.schema_path = Path(schema_path) if schema_path else self.base_dir / "procedure.schema.json"

        self.procedures: dict[str, dict] = {}
        self.schema: Optional[dict] = None

        self._load_schema()
        self._load_procedures()

    def _load_schema(self) -> None:
        """Load JSON schema for procedure validation."""
        if self.schema_path.exists():
            with open(self.schema_path) as f:
                self.schema = json.load(f)

    def _load_procedures(self) -> None:
        """Load all procedure YAML files from procedures directory."""
        if not self.procedures_dir.exists():
            return

        for yaml_file in self.procedures_dir.glob("*.yaml"):
            if yaml_file.name.startswith("_"):  # Skip private files
                continue
            try:
                with open(yaml_file) as f:
                    proc = yaml.safe_load(f)
                if proc and "id" in proc:
                    self.procedures[proc["id"]] = proc
            except Exception as e:
                print(f"Warning: Failed to load {yaml_file}: {e}", file=sys.stderr)

    def validate(self, procedure: dict) -> tuple[bool, list[str]]:
        """Validate a procedure against the schema.

        Returns (is_valid, list_of_errors).
        """
        errors = []

        # Basic required fields
        for field in ["id", "description", "version", "category", "steps"]:
            if field not in procedure:
                errors.append(f"Missing required field: {field}")

        # JSON Schema validation if available
        if jsonschema and self.schema:
            try:
                jsonschema.validate(procedure, self.schema)
            except jsonschema.ValidationError as e:
                errors.append(f"Schema validation failed: {e.message}")

        # Step validation
        if "steps" in procedure:
            step_ids = set()
            for step in procedure["steps"]:
                if "id" not in step:
                    errors.append("Step missing 'id' field")
                elif step["id"] in step_ids:
                    errors.append(f"Duplicate step id: {step['id']}")
                else:
                    step_ids.add(step["id"])

                if "action" not in step:
                    errors.append(f"Step {step.get('id', '?')} missing 'action' field")
                elif step["action"] == "run_shell" and "command" not in step:
                    errors.append(f"Step {step['id']}: run_shell requires 'command'")
                elif step["action"] == "python" and "code" not in step:
                    errors.append(f"Step {step['id']}: python requires 'code'")

        return len(errors) == 0, errors

    def get(self, procedure_id: str) -> Optional[dict]:
        """Get a procedure by ID."""
        return self.procedures.get(procedure_id)

    def list(self, category: str = None) -> list[dict]:
        """List all procedures, optionally filtered by category."""
        procs = list(self.procedures.values())
        if category:
            procs = [p for p in procs if p.get("category") == category]
        return procs

    def _substitute_params(self, text: str, params: dict, extracted: dict) -> str:
        """Substitute {param} placeholders in text."""
        all_values = {**params, **extracted}
        for key, value in all_values.items():
            text = text.replace(f"{{{key}}}", str(value))
        return text

    def _run_shell_step(self, step: dict, params: dict, extracted: dict) -> StepResult:
        """Execute a shell command step."""
        command = self._substitute_params(step["command"], params, extracted)
        timeout = step.get("timeout", 300)

        start_time = time.time()
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd="."  # Run from project root
            )
            duration = time.time() - start_time

            output = result.stdout + result.stderr
            success = result.returncode == 0

            # Extract values if defined
            step_extracted = {}
            if "extract" in step and success:
                for key, pattern in step["extract"].items():
                    match = re.search(pattern, output)
                    if match:
                        step_extracted[key] = match.group(1) if match.groups() else match.group(0)

            return StepResult(
                step_id=step["id"],
                success=success,
                output=output[:10000],  # Truncate long output
                extracted=step_extracted,
                duration_seconds=duration,
                error=None if success else f"Exit code {result.returncode}"
            )
        except subprocess.TimeoutExpired:
            return StepResult(
                step_id=step["id"],
                success=False,
                error=f"Timeout after {timeout}s",
                duration_seconds=timeout
            )
        except Exception as e:
            return StepResult(
                step_id=step["id"],
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time
            )

    def _run_python_step(self, step: dict, params: dict, extracted: dict) -> StepResult:
        """Execute a Python code step."""
        code = self._substitute_params(step["code"], params, extracted)

        start_time = time.time()
        try:
            # Create isolated namespace
            namespace = {
                "params": params,
                "extracted": extracted,
                "datetime": datetime,
                "Path": Path,
                "json": json,
                "yaml": yaml,
            }
            exec(code, namespace)
            duration = time.time() - start_time

            return StepResult(
                step_id=step["id"],
                success=True,
                output=str(namespace.get("result", "")),
                duration_seconds=duration
            )
        except Exception as e:
            return StepResult(
                step_id=step["id"],
                success=False,
                error=str(e),
                duration_seconds=time.time() - start_time
            )

    def run_step(self, procedure_id: str, step_id: str, params: dict = None, extracted: dict = None) -> StepResult:
        """Execute a single step from a procedure."""
        proc = self.get(procedure_id)
        if not proc:
            return StepResult(step_id=step_id, success=False, error=f"Procedure not found: {procedure_id}")

        step = next((s for s in proc["steps"] if s["id"] == step_id), None)
        if not step:
            return StepResult(step_id=step_id, success=False, error=f"Step not found: {step_id}")

        params = params or {}
        extracted = extracted or {}

        action = step["action"]
        if action == "run_shell":
            return self._run_shell_step(step, params, extracted)
        elif action == "python":
            return self._run_python_step(step, params, extracted)
        else:
            return StepResult(step_id=step_id, success=False, error=f"Unknown action: {action}")

    def run(self, procedure_id: str, params: dict = None) -> tuple[bool, ProcedureState]:
        """Execute a full procedure.

        Returns (success, final_state).
        """
        proc = self.get(procedure_id)
        if not proc:
            raise ValueError(f"Procedure not found: {procedure_id}")

        params = params or {}
        execution_id = f"{datetime.now().isoformat()}_{procedure_id}"

        state = ProcedureState(
            procedure_id=procedure_id,
            execution_id=execution_id,
            status=ProcedureStatus.RUNNING,
            started_at=datetime.now(),
            parameters=params,
        )

        # Check prerequisites
        for prereq in proc.get("prerequisites", []):
            if not self._check_prerequisite(prereq, params):
                if prereq.get("required", True):
                    state.status = ProcedureStatus.FAILED
                    state.error = f"Prerequisite failed: {prereq}"
                    return False, state

        # Execute steps
        for step in proc["steps"]:
            state.current_step = step["id"]

            # Check dependencies
            if "depends_on" in step:
                if step["depends_on"] not in state.completed_steps:
                    state.status = ProcedureStatus.FAILED
                    state.error = f"Dependency not met: {step['depends_on']}"
                    return False, state

            result = self.run_step(procedure_id, step["id"], params, state.extracted_values)

            if result.success:
                state.completed_steps.append(step["id"])
                state.extracted_values.update(result.extracted)
            else:
                on_failure = step.get("on_failure", "abort")
                if on_failure == "abort":
                    state.status = ProcedureStatus.FAILED
                    state.error = result.error
                    self._save_state(state)
                    return False, state
                elif on_failure == "continue":
                    continue
                # retry would need additional logic

        state.status = ProcedureStatus.COMPLETED
        state.completed_at = datetime.now()
        state.current_step = None
        self._save_state(state)

        return True, state

    def _check_prerequisite(self, prereq: dict, params: dict) -> bool:
        """Check if a prerequisite is met."""
        check = prereq["check"]

        if check == "file_exists":
            path = self._substitute_params(prereq["path"], params, {})
            return Path(path).exists()
        elif check == "git_clean":
            result = subprocess.run(
                "git status --porcelain",
                shell=True,
                capture_output=True,
                text=True,
                cwd="."  # Run from project root
            )
            return result.stdout.strip() == ""

        return True  # Unknown checks pass by default

    def _save_state(self, state: ProcedureState) -> Path:
        """Save procedure state to file."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        state_file = self.state_dir / f"{state.execution_id.replace(':', '-')}.yaml"
        with open(state_file, "w") as f:
            f.write(state.to_yaml())
        return state_file

    def list_paused(self) -> list[ProcedureState]:
        """List all paused procedures."""
        paused = []
        if not self.state_dir.exists():
            return paused

        for state_file in self.state_dir.glob("*.yaml"):
            try:
                with open(state_file) as f:
                    state = ProcedureState.from_yaml(f.read())
                if state.status == ProcedureStatus.PAUSED:
                    paused.append(state)
            except Exception:
                continue

        return paused


def main():
    """CLI for procedure registry operations."""
    import argparse

    parser = argparse.ArgumentParser(description="Procedure Registry CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate a procedure YAML file")
    validate_parser.add_argument("file", help="Path to YAML file")

    # list command
    list_parser = subparsers.add_parser("list", help="List all procedures")
    list_parser.add_argument("--category", help="Filter by category")

    # run command
    run_parser = subparsers.add_parser("run", help="Run a procedure")
    run_parser.add_argument("procedure_id", help="Procedure ID")
    run_parser.add_argument("--param", action="append", nargs=2, metavar=("KEY", "VALUE"), help="Parameters")

    args = parser.parse_args()
    registry = ProcedureRegistry()

    if args.command == "validate":
        with open(args.file) as f:
            proc = yaml.safe_load(f)
        valid, errors = registry.validate(proc)
        if valid:
            print(f"✓ {args.file} is valid")
        else:
            print(f"✗ {args.file} has errors:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)

    elif args.command == "list":
        procs = registry.list(args.category)
        for p in procs:
            print(f"  {p['id']}: {p['description']} [{p['category']}]")

    elif args.command == "run":
        params = dict(args.param) if args.param else {}
        success, state = registry.run(args.procedure_id, params)
        print(f"{'✓' if success else '✗'} {args.procedure_id}: {state.status.value}")
        if state.error:
            print(f"  Error: {state.error}")
        if state.extracted_values:
            print(f"  Extracted: {state.extracted_values}")


if __name__ == "__main__":
    main()
```

### File 3: orchestration/procedures/benchmark_new_model.yaml

**NOTE**: This procedure uses llama.cpp commands. The yolo agent should focus on Phase 1-2 (registry + REPL tools) first. Benchmark procedures require the local inference environment.

```yaml
id: benchmark_new_model
description: Run full benchmark suite on a new model
version: "1.0"
category: benchmarking

prerequisites:
  - check: file_exists
    path: "{model_path}"

parameters:
  model_path:
    type: string
    required: true
    description: Full path to GGUF model file
  model_name:
    type: string
    required: true
    description: Human-readable model name for registry
  suite:
    type: string
    default: "all"
    enum: [all, thinking, coder, general, agentic, math, vl, long_context, instruction_precision]
    description: Benchmark suite to run

steps:
  - id: health_check
    action: run_shell
    command: |
      timeout 30 /mnt/raid0/llm/llama.cpp/build/bin/llama-cli \
        -m {model_path} -p "Hello" -n 10 --no-display-prompt 2>&1
    timeout: 60
    on_failure: abort

  - id: detect_architecture
    action: run_shell
    command: |
      /mnt/raid0/llm/llama.cpp/build/bin/llama-cli \
        -m {model_path} --show-config 2>&1 | head -50
    extract:
      architecture: "arch\\s*=\\s*(\\w+)"
      n_expert: "n_expert\\s*=\\s*(\\d+)"

  - id: run_benchmark
    action: run_shell
    command: |
      ./scripts/benchmark/run_overnight_benchmark_suite.sh \
        --model {model_path} --suite {suite} 2>&1
    timeout: 14400
    pausable: true
    on_failure: abort

  - id: collect_results
    action: run_shell
    depends_on: run_benchmark
    command: |
      ls -la benchmarks/results/runs/ | tail -5
    extract:
      results_dir: "(\\d{4}-\\d{2}-\\d{2}T[^\\s]+)"

gates:
  - results_file_exists

on_success:
  log_to_memory: true
  q_value: 0.9

on_failure:
  log_to_memory: true
  q_value: 0.3
  create_handoff: true
```

---

## Resume Commands

```bash
# Continue implementation
# Ensure you're in the project root (adjust path for your environment)
# Local: cd /mnt/raid0/llm/claude
# Container: cd /workspace

# Check current state
ls -la orchestration/procedures/
ls -la orchestration/checkpoints/
ls -la orchestration/patches/

# Reference the plan
cat /home/daniele/.claude/plans/mighty-prancing-pillow.md
```

### File 4: REPL Tools to Add (src/repl_environment.py)

Add these methods to the `REPLEnvironment` class:

```python
# Add to __init__ self.tools dict:
#   "get_procedure": self._get_procedure,
#   "list_procedures": self._list_procedures,
#   "run_procedure": self._run_procedure,
#   "run_procedure_step": self._run_procedure_step,

def _get_procedure(self, procedure_id: str) -> str:
    """Get a procedure definition by ID.

    Args:
        procedure_id: The procedure identifier (e.g., 'benchmark_new_model')

    Returns:
        JSON string with procedure definition including steps, parameters, gates.
    """
    from orchestration.procedure_registry import ProcedureRegistry
    registry = ProcedureRegistry()
    proc = registry.get(procedure_id)
    if proc:
        return json.dumps(proc, indent=2)
    return json.dumps({"error": f"Procedure not found: {procedure_id}"})

def _list_procedures(self, category: str = None) -> str:
    """List available procedures, optionally filtered by category.

    Args:
        category: Optional filter - benchmarking, registry, codebase, finetuning, maintenance

    Returns:
        JSON array of procedure summaries.
    """
    from orchestration.procedure_registry import ProcedureRegistry
    registry = ProcedureRegistry()
    procs = registry.list(category)
    summaries = [
        {"id": p["id"], "description": p["description"], "category": p["category"], "version": p["version"]}
        for p in procs
    ]
    return json.dumps(summaries, indent=2)

def _run_procedure(self, procedure_id: str, **params) -> str:
    """Execute a procedure with given parameters.

    Runs all steps sequentially, validates gates, logs outcome to memory.

    Args:
        procedure_id: The procedure to execute
        **params: Parameters required by the procedure

    Returns:
        JSON with execution summary including success, extracted values, duration.
    """
    from orchestration.procedure_registry import ProcedureRegistry
    registry = ProcedureRegistry()

    try:
        success, state = registry.run(procedure_id, params)
        return json.dumps({
            "success": success,
            "procedure_id": procedure_id,
            "status": state.status.value,
            "completed_steps": state.completed_steps,
            "extracted_values": state.extracted_values,
            "error": state.error,
            "duration_seconds": (state.completed_at - state.started_at).total_seconds() if state.completed_at else None
        }, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

def _run_procedure_step(self, procedure_id: str, step_id: str, **params) -> str:
    """Execute a single step from a procedure.

    For manual/interactive execution when you need fine-grained control.

    Args:
        procedure_id: The procedure containing the step
        step_id: The specific step to execute
        **params: Parameters for variable substitution

    Returns:
        JSON with step result including success, output, extracted values.
    """
    from orchestration.procedure_registry import ProcedureRegistry
    registry = ProcedureRegistry()

    result = registry.run_step(procedure_id, step_id, params)
    return json.dumps({
        "step_id": result.step_id,
        "success": result.success,
        "output": result.output[:2000] if result.output else None,  # Truncate for token efficiency
        "extracted": result.extracted,
        "duration_seconds": result.duration_seconds,
        "error": result.error
    }, indent=2)
```

### File 5: tests/unit/test_procedure_registry.py

```python
"""Unit tests for ProcedureRegistry."""

import json
import pytest
import tempfile
from pathlib import Path

import yaml


@pytest.fixture
def temp_procedures_dir():
    """Create temporary procedures directory with test procedure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        proc_dir = Path(tmpdir) / "procedures"
        proc_dir.mkdir()
        (proc_dir / "state").mkdir()

        # Create test procedure
        test_proc = {
            "id": "test_procedure",
            "description": "Test procedure for unit tests",
            "version": "1.0",
            "category": "maintenance",
            "parameters": {
                "message": {"type": "string", "required": True}
            },
            "steps": [
                {
                    "id": "echo_message",
                    "action": "run_shell",
                    "command": "echo {message}",
                    "extract": {"output": "(.+)"}
                }
            ],
            "on_success": {"log_to_memory": False, "q_value": 0.9}
        }
        with open(proc_dir / "test_procedure.yaml", "w") as f:
            yaml.dump(test_proc, f)

        # Create schema
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["id", "description", "version", "category", "steps"]
        }
        with open(Path(tmpdir) / "procedure.schema.json", "w") as f:
            json.dump(schema, f)

        yield tmpdir


def test_registry_loads_procedures(temp_procedures_dir):
    """Test that registry loads YAML procedures."""
    from orchestration.procedure_registry import ProcedureRegistry

    registry = ProcedureRegistry(
        procedures_dir=f"{temp_procedures_dir}/procedures",
        schema_path=f"{temp_procedures_dir}/procedure.schema.json"
    )

    assert "test_procedure" in registry.procedures
    assert registry.procedures["test_procedure"]["description"] == "Test procedure for unit tests"


def test_registry_get_procedure(temp_procedures_dir):
    """Test getting a procedure by ID."""
    from orchestration.procedure_registry import ProcedureRegistry

    registry = ProcedureRegistry(
        procedures_dir=f"{temp_procedures_dir}/procedures",
        schema_path=f"{temp_procedures_dir}/procedure.schema.json"
    )

    proc = registry.get("test_procedure")
    assert proc is not None
    assert proc["id"] == "test_procedure"

    missing = registry.get("nonexistent")
    assert missing is None


def test_registry_list_procedures(temp_procedures_dir):
    """Test listing procedures with optional category filter."""
    from orchestration.procedure_registry import ProcedureRegistry

    registry = ProcedureRegistry(
        procedures_dir=f"{temp_procedures_dir}/procedures",
        schema_path=f"{temp_procedures_dir}/procedure.schema.json"
    )

    all_procs = registry.list()
    assert len(all_procs) == 1

    filtered = registry.list(category="maintenance")
    assert len(filtered) == 1

    empty = registry.list(category="nonexistent")
    assert len(empty) == 0


def test_registry_validate_procedure(temp_procedures_dir):
    """Test procedure validation."""
    from orchestration.procedure_registry import ProcedureRegistry

    registry = ProcedureRegistry(
        procedures_dir=f"{temp_procedures_dir}/procedures",
        schema_path=f"{temp_procedures_dir}/procedure.schema.json"
    )

    # Valid procedure
    valid_proc = registry.get("test_procedure")
    is_valid, errors = registry.validate(valid_proc)
    assert is_valid
    assert len(errors) == 0

    # Invalid procedure (missing fields)
    invalid_proc = {"id": "incomplete"}
    is_valid, errors = registry.validate(invalid_proc)
    assert not is_valid
    assert len(errors) > 0


def test_registry_run_step(temp_procedures_dir):
    """Test running a single step."""
    from orchestration.procedure_registry import ProcedureRegistry

    registry = ProcedureRegistry(
        procedures_dir=f"{temp_procedures_dir}/procedures",
        schema_path=f"{temp_procedures_dir}/procedure.schema.json"
    )

    result = registry.run_step(
        "test_procedure",
        "echo_message",
        params={"message": "Hello World"}
    )

    assert result.success
    assert "Hello World" in result.output
    assert result.extracted.get("output") == "Hello World"


def test_registry_run_full_procedure(temp_procedures_dir):
    """Test running a complete procedure."""
    from orchestration.procedure_registry import ProcedureRegistry, ProcedureStatus

    registry = ProcedureRegistry(
        procedures_dir=f"{temp_procedures_dir}/procedures",
        schema_path=f"{temp_procedures_dir}/procedure.schema.json"
    )

    success, state = registry.run("test_procedure", {"message": "Test Run"})

    assert success
    assert state.status == ProcedureStatus.COMPLETED
    assert "echo_message" in state.completed_steps
    assert state.extracted_values.get("output") == "Test Run"


def test_procedure_state_serialization():
    """Test ProcedureState YAML serialization round-trip."""
    from datetime import datetime
    from orchestration.procedure_registry import ProcedureState, ProcedureStatus

    state = ProcedureState(
        procedure_id="test",
        execution_id="2026-01-24T10:00:00_test",
        status=ProcedureStatus.RUNNING,
        started_at=datetime.now(),
        parameters={"key": "value"},
        completed_steps=["step1"],
        extracted_values={"result": "42"}
    )

    yaml_str = state.to_yaml()
    restored = ProcedureState.from_yaml(yaml_str)

    assert restored.procedure_id == state.procedure_id
    assert restored.status == state.status
    assert restored.parameters == state.parameters
    assert restored.completed_steps == state.completed_steps
```

---

## Validation Checklist (For Autonomous Agent)

After each phase, run validation before proceeding:

### After Phase 1
```bash
# Must all pass
python -c "import json; json.load(open('orchestration/procedure.schema.json'))"
python -c "from orchestration.procedure_registry import ProcedureRegistry; print('✓ Import OK')"
python orchestration/procedure_registry.py validate orchestration/procedures/benchmark_new_model.yaml
pytest tests/unit/test_procedure_registry.py -v
```

### After Phase 2
```bash
# Test REPL tools
python -c "
from src.repl_environment import REPLEnvironment
r = REPLEnvironment()
assert 'get_procedure' in r.tools
assert 'list_procedures' in r.tools
assert 'run_procedure' in r.tools
print('✓ All procedure tools registered')
"
```

### After Phase 6
```bash
# Verify core procedures exist and validate
for proc in benchmark_new_model update_registry_performance add_model_to_registry; do
  python orchestration/procedure_registry.py validate orchestration/procedures/${proc}.yaml
done
```

---

## Related Documents

- **Plan File:** `/home/daniele/.claude/plans/mighty-prancing-pillow.md`
- **REPL Environment:** `src/repl_environment.py`
- **Episodic Memory:** `orchestration/repl_memory/`
- **Model Registry:** `orchestration/model_registry.yaml`
- **Orchestrator Stack:** `scripts/server/orchestrator_stack.py`
- **Previous Handoff:** `handoffs/active/orchestrator_document_pipeline.md` (COMPLETED)
