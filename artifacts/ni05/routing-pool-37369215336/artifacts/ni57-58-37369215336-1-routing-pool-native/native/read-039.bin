"""EnvSynth species coordinator + journal events + solvability gate.

Wires the sub-modules (``ETDAgent`` / ``TaskSynthesizer`` / ``VerifierBuilder``
/ ``MCPToolRegistry``) into a single 5th autopilot species alongside
Seeder / NumericSwarm / PromptForge / StructuralLab.

Phase 1 scope (NIB2-44 AW-2, AW-4):

  EnvSynth.discover_and_synthesize  one discovery → tasks pipeline run
  EnvSynth.propose_actions          autopilot-visible mutation emissions
  EnvSynthAction                    journaled controller action record
  SolvabilityGate                   reference-model solvability check
                                    (AW-4 — rejects tasks a reference
                                    model cannot solve)

AW-3 (gap diagnosis rollup), AW-5 (EvalTower T1 integration), and
AW-7 (MCP tool adoption) are scaffolded in Week 2-3 of NIB2-44.
"""

from __future__ import annotations

import json
import logging
import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from scripts.autopilot.species.env_synth.boundary_contract import (
    HypothesisBoundaryContract,
    boundary_evidence,
)
from scripts.autopilot.species.env_synth.etd_agent import ETDAgent
from scripts.autopilot.species.env_synth.mcp_tool_registry import (
    MCPToolRegistry,
)
from scripts.autopilot.species.env_synth.task_synthesizer import (
    DifficultyBand,
    SynthesizedTask,
    TaskSynthesizer,
)
from scripts.autopilot.species.env_synth.verifier_builder import VerifierSpec

log = logging.getLogger("autopilot.env_synth.species")

ORCH_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_REGISTRY_PATH = ORCH_ROOT / "orchestration" / "autopilot_env_synth_registry.jsonl"
DEFAULT_ARENA_PATH = ORCH_ROOT / "orchestration" / "autopilot_env_synth_arena.jsonl"
DEFAULT_JOURNAL_PATH = ORCH_ROOT / "orchestration" / "autopilot_env_synth_journal.jsonl"


# Reference-model solvability: the gate calls this callback with
# ``(task_prompt, tool_set)`` and expects a ``(solved: bool, confidence:
# float, reason: str)`` tuple. In production this is wired to the
# architect_general worker; tests inject a mock.
ReferenceSolver = Callable[[str, list[str]], Awaitable[tuple[bool, float, str]]]
BoundaryFeedbackSink = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class PlanStep:
    """One simulated non-terminal action and its expected world state."""

    action: str
    predicted_state: Any


PlanSimulator = Callable[[SynthesizedTask], Awaitable[list[PlanStep]]]
StepExecutor = Callable[[SynthesizedTask, PlanStep], Awaitable[Any]]


@dataclass
class PlanExecutionGuard:
    """Fail closed when an induced-world plan diverges from execution.

    This is deliberately opt-in: the current Phase-1 task synthesizer has no
    environment model or action executor. A future adapter supplies both
    callbacks and an artifact directory; the guard then compares each
    predicted state to the observed state and stops at the first mismatch.
    """

    plan_simulator: PlanSimulator
    step_executor: StepExecutor
    artifact_dir: Path

    async def evaluate(self, task: SynthesizedTask) -> tuple[bool, str]:
        try:
            plan = await self.plan_simulator(task)
        except Exception as exc:  # noqa: BLE001 -- external adapter boundary
            log.warning("plan simulation raised: %s", exc)
            return False, f"plan_simulator_error: {exc}"

        for step_index, step in enumerate(plan):
            try:
                observed_state = await self.step_executor(task, step)
            except Exception as exc:  # noqa: BLE001 -- external adapter boundary
                log.warning("plan step %d execution raised: %s", step_index, exc)
                return False, f"plan_executor_error_at_step_{step_index}: {exc}"
            if observed_state != step.predicted_state:
                artifact_path = self._write_divergence_artifact(
                    task=task,
                    step_index=step_index,
                    step=step,
                    observed_state=observed_state,
                )
                return False, f"plan_executor_divergence_at_step_{step_index}: {artifact_path}"
        return True, "plan_executor_aligned"

    def _write_divergence_artifact(
        self,
        *,
        task: SynthesizedTask,
        step_index: int,
        step: PlanStep,
        observed_state: Any,
    ) -> Path:
        """Persist the first divergence for replay; never continue execution."""
        task_digest = hashlib.sha256(task.prompt.encode("utf-8")).hexdigest()[:12]
        path = self.artifact_dir / f"plan_executor_divergence_{task_digest}_step{step_index}.json"
        payload = {
            "environment_id": task.environment_id,
            "prompt": task.prompt,
            "step_index": step_index,
            "action": step.action,
            "predicted_state": step.predicted_state,
            "observed_state": observed_state,
            "reason": "plan_executor_state_mismatch",
        }
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, sort_keys=True, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        return path


@dataclass
class EnvSynthAction:
    """Journaled controller event emitted per EnvSynth cycle."""

    timestamp: str
    environment_id: str
    tool_set: list[str]
    synthesized_tasks: list[str]  # SynthesizedTask prompt hashes / ids
    rejected_task_count: int
    difficulty_band: str
    gap_descriptor: str = ""
    notes: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


@dataclass
class SolvabilityGate:
    """AW-4: reject synthesized tasks a reference model cannot solve.

    Rejection rate should stay below ``max_rejection_rate`` at steady
    state; higher rates indicate difficulty-band miscalibration and
    feed back into autopilot gap diagnosis (AW-3).

    Optional weak-reference checking calibrates the lower bound of synthetic
    task difficulty. It remains non-binding unless ``require_weak_failure`` is
    set, because synthesized tasks must not enter decision-gating evals without
    human promotion.
    """

    reference_solver: ReferenceSolver
    min_confidence: float = 0.6
    max_rejection_rate: float = 0.20
    weak_reference_solver: Optional[ReferenceSolver] = None
    require_weak_failure: bool = False
    weak_pass_confidence: float = 0.6
    plan_execution_guard: Optional[PlanExecutionGuard] = None

    async def evaluate(
        self,
        task: SynthesizedTask,
    ) -> tuple[bool, float, str]:
        try:
            solved, confidence, reason = await self.reference_solver(
                task.prompt,
                task.tool_set,
            )
        except Exception as e:
            log.warning("solvability check raised: %s", e)
            return False, 0.0, f"solver_error: {e}"
        if not solved:
            return False, confidence, reason or "reference_model_failed"
        if confidence < self.min_confidence:
            return False, confidence, "low_confidence_below_threshold"
        if self.weak_reference_solver is not None:
            try:
                weak_solved, weak_confidence, weak_reason = await self.weak_reference_solver(
                    task.prompt,
                    task.tool_set,
                )
            except Exception as e:
                log.warning("weak solvability check raised: %s", e)
                if self.require_weak_failure:
                    return False, confidence, f"weak_solver_error: {e}"
                return True, confidence, "ok_weak_solver_error_nonbinding"
            if weak_solved and weak_confidence >= self.weak_pass_confidence:
                weak_reason = weak_reason or "weak_reference_model_solved"
                if self.require_weak_failure:
                    return False, confidence, f"weak_reference_solved: {weak_reason}"
                return True, confidence, f"ok_weak_reference_solved_nonbinding: {weak_reason}"
        if self.plan_execution_guard is not None:
            aligned, guard_reason = await self.plan_execution_guard.evaluate(task)
            if not aligned:
                return False, confidence, guard_reason
        return True, confidence, "ok"


@dataclass
class EnvSynth:
    """5th autopilot species — coordinates discovery + synthesis + gating."""

    etd_agent: ETDAgent
    task_synthesizer: TaskSynthesizer
    registry: MCPToolRegistry
    solvability_gate: Optional[SolvabilityGate] = None
    arena_path: Path = field(default_factory=lambda: DEFAULT_ARENA_PATH)
    journal_path: Path = field(default_factory=lambda: DEFAULT_JOURNAL_PATH)
    boundary_feedback_sink: Optional[BoundaryFeedbackSink] = None

    def __post_init__(self) -> None:
        self.arena_path.parent.mkdir(parents=True, exist_ok=True)

    # ── public API ─────────────────────────────────────────────────

    async def discover_and_synthesize(
        self,
        theme: str,
        *,
        gap_descriptor: str = "",
        tasks_per_env: int = 3,
        band: DifficultyBand = DifficultyBand.MEDIUM,
    ) -> list[SynthesizedTask]:
        """Full pipeline: ETD → synthesis → solvability gate → arena persist.

        Returns the accepted tasks. Rejected tasks are counted in the
        journaled ``EnvSynthAction`` for gap diagnosis (AW-3).
        """
        discoveries = await self.etd_agent.discover(
            theme=theme,
            gap_descriptor=gap_descriptor,
            max_environments=3,
        )
        accepted: list[SynthesizedTask] = []
        rejected = 0

        for disc in discoveries:
            if not disc.tools:
                continue
            for _ in range(tasks_per_env):
                task = await self.task_synthesizer.synthesize(
                    disc.environment_id,
                    disc.tools,
                    band,
                )
                if task is None:
                    rejected += 1
                    continue
                if self.solvability_gate is not None:
                    ok, conf, reason = await self.solvability_gate.evaluate(task)
                    if not ok:
                        log.debug(
                            "solvability gate rejected env=%s reason=%s",
                            disc.environment_id,
                            reason,
                        )
                        rejected += 1
                        continue
                accepted.append(task)
                self._append_arena(task)

            self._journal(
                EnvSynthAction(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    environment_id=disc.environment_id,
                    tool_set=[t.tool_id for t in disc.tools],
                    synthesized_tasks=[
                        _task_id(t) for t in accepted if t.environment_id == disc.environment_id
                    ],
                    rejected_task_count=rejected,
                    difficulty_band=band.value,
                    gap_descriptor=gap_descriptor,
                )
            )

        return accepted

    def propose_actions(
        self,
        theme: str,
        band: DifficultyBand = DifficultyBand.MEDIUM,
        gap_descriptor: str = "",
    ) -> dict[str, Any]:
        """Return an autopilot-style action dict describing what this
        species would do on the next cycle. Matches the shape of
        ``{"type": "structural_experiment", ...}`` etc. so the
        controller dispatch layer can treat species uniformly.
        """
        return {
            "type": "env_synth_cycle",
            "theme": theme,
            "difficulty_band": band.value,
            "gap_descriptor": gap_descriptor,
        }

    async def synthesize_hypothesis_boundary(
        self,
        environment_id: str,
        boundary: HypothesisBoundaryContract,
        verifier: VerifierSpec,
        ground_truth_hint: str,
        *,
        band: DifficultyBand = DifficultyBand.MEDIUM,
    ) -> Optional[SynthesizedTask]:
        """Create, gate, and persist one observe-only AW-10 dynamic-T1 task."""
        tools = self.registry.by_environment(environment_id)
        task = await self.task_synthesizer.synthesize_boundary(
            environment_id,
            tools,
            band,
            boundary=boundary,
            verifier=verifier,
            ground_truth_hint=ground_truth_hint,
        )
        if task is None:
            return None
        if self.solvability_gate is not None:
            ok, _confidence, _reason = await self.solvability_gate.evaluate(task)
            if not ok:
                return None
        self._append_arena(task)
        self._journal(
            EnvSynthAction(
                timestamp=datetime.now(timezone.utc).isoformat(),
                environment_id=environment_id,
                tool_set=task.tool_set,
                synthesized_tasks=[_task_id(task)],
                rejected_task_count=0,
                difficulty_band=band.value,
                gap_descriptor=f"hypothesis_boundary:{boundary.boundary_id}",
                notes="observe_only_dynamic_t1",
            )
        )
        return task

    def emit_boundary_evidence(
        self,
        task: SynthesizedTask,
        *,
        evidence_receipt_id: str,
        hypothesis_results: dict[str, str],
    ) -> dict[str, Any]:
        """Route falsifier-resolution evidence to the owning loop's injected sink."""
        if task.boundary_contract is None:
            raise ValueError("task is not bound to a hypothesis disagreement")
        if self.boundary_feedback_sink is None:
            raise RuntimeError(
                "boundary_feedback_sink is required; local journaling is not delivery"
            )
        record = boundary_evidence(
            task.boundary_contract,
            task_id=_task_id(task),
            evidence_receipt_id=evidence_receipt_id,
            hypothesis_results=hypothesis_results,
        )
        self.boundary_feedback_sink(record)
        return record

    # ── persistence helpers ────────────────────────────────────────

    def _append_arena(self, task: SynthesizedTask) -> None:
        record = {
            "task_id": _task_id(task),
            "environment_id": task.environment_id,
            "tool_set": task.tool_set,
            "prompt": task.prompt,
            "difficulty_band": task.difficulty_band.value,
            "verifier": asdict(task.verifier),
            "ground_truth_hint": task.ground_truth_hint,
            "expected_tool_calls": list(task.expected_tool_calls),
            "metadata": task.metadata,
            "evaluation_tier": "dynamic_t1",
            "t0_eligible": False,
            "boundary_contract": (
                task.boundary_contract.to_dict() if task.boundary_contract else None
            ),
            "persisted_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.arena_path.open("a") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    def _journal(self, action: EnvSynthAction) -> None:
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        with self.journal_path.open("a") as f:
            f.write(action.to_json() + "\n")


# ── helpers ─────────────────────────────────────────────────────────


def _task_id(task: SynthesizedTask) -> str:
    """Stable identifier for a synthesized task — env + prompt hash."""
    import hashlib

    h = hashlib.sha256(f"{task.environment_id}::{task.prompt}".encode()).hexdigest()[:16]
    return f"envsynth_{h}"
