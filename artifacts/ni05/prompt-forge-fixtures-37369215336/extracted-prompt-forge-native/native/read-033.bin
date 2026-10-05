"""Agent-World environment synthesis — 5th autopilot species (NIB2-44).

Implements AW-1..AW-5 from `handoffs/active/agent-world-env-synthesis.md`.
Phase 1 is training-free and CPU-feasible; Phase 2 multi-env GRPO
training (AW-9) is GPU-gated.

Public surface:

  EnvSynth                 species coordinator + journal event emitter
  ETDAgent                 environment-task discovery ReAct agent
  TaskSynthesizer          generates verifiable tasks with difficulty bands
  VerifierBuilder          emits regex / exact_match / f1 verifiers
  MCPToolRegistry          persistent JSONL registry with health checks
  SolvabilityGate          reference-model solvability check (AW-4)
  EnvSynthAction           journal event dataclass
  SynthesizedTask          composed task record
"""

from scripts.autopilot.species.env_synth.etd_agent import ETDAgent
from scripts.autopilot.species.env_synth.boundary_contract import (
    HypothesisBoundaryContract,
    boundary_evidence,
)
from scripts.autopilot.species.env_synth.task_synthesizer import (
    DifficultyBand,
    SynthesizedTask,
    TaskSynthesizer,
)
from scripts.autopilot.species.env_synth.verifier_builder import (
    VerifierBuilder,
    VerifierSpec,
    VerifierType,
)
from scripts.autopilot.species.env_synth.mcp_tool_registry import (
    MCPToolEntry,
    MCPToolRegistry,
)
from scripts.autopilot.species.env_synth.species import (
    EnvSynth,
    EnvSynthAction,
    PlanExecutionGuard,
    PlanStep,
    SolvabilityGate,
)
from scripts.autopilot.species.env_synth.gap_diagnosis import (
    SuiteStagnation,
    diagnose_stagnation,
    render_arena_rollup,
)
from scripts.autopilot.species.env_synth.eval_integration import (
    T1TaskEntry,
    arena_to_t1,
    flag_human_review,
)

__all__ = [
    "EnvSynth",
    "EnvSynthAction",
    "PlanExecutionGuard",
    "PlanStep",
    "SolvabilityGate",
    "HypothesisBoundaryContract",
    "boundary_evidence",
    "ETDAgent",
    "TaskSynthesizer",
    "SynthesizedTask",
    "DifficultyBand",
    "VerifierBuilder",
    "VerifierSpec",
    "VerifierType",
    "MCPToolRegistry",
    "MCPToolEntry",
    "SuiteStagnation",
    "diagnose_stagnation",
    "render_arena_rollup",
    "T1TaskEntry",
    "arena_to_t1",
    "flag_human_review",
]
