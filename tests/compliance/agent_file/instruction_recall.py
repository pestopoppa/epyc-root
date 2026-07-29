"""Instruction-recall tasks for agent-file compliance.

Each task: a direct question about a specific clause in the agent file.
Pass criterion: model output contains a quoted-or-paraphrased correct
clause (case-insensitive substring of `acceptable_answers`).

Recall is the weakest of the three compliance signals — a model can
"remember" content from training even if the specific compressed file is
not informative. Pair with FA + PC tasks for full triangulation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RecallTask:
    task_id: str
    prompt: str
    acceptable_answers: list[str]  # any substring match passes
    relevant_agent_file: str = "agents/shared/ENGINEERING_STANDARDS.md"
    notes: str = ""


TASKS: list[RecallTask] = [
    RecallTask(
        task_id="IR-01-silent-except",
        prompt="What does the engineering standards file say about silent exception handling?",
        acceptable_answers=["do not use silent", "except: pass", "silent `except"],
    ),
    RecallTask(
        task_id="IR-02-tunable-vs-invariant",
        prompt="Define `tunable` vs `invariant` per the engineering standards.",
        acceptable_answers=["runtime behavior controls", "stable semantic limits", "hard boundaries"],
    ),
    RecallTask(
        task_id="IR-03-numeric-globalfile",
        prompt="What does the engineering standards say about consolidating numeric constants into one file?",
        acceptable_answers=["Do not consolidate", "subsystem ownership"],
    ),
    RecallTask(
        task_id="IR-04-pr-classification-note",
        prompt="What note must a PR include when adding numeric values?",
        acceptable_answers=["one-line classification note", "tunable", "invariant"],
    ),
    RecallTask(
        task_id="IR-05-multi-repo-routing",
        prompt="Which repo holds orchestrator code (src/, tests/, orchestration/)?",
        acceptable_answers=["epyc-orchestrator"],
    ),
    RecallTask(
        task_id="IR-06-multi-repo-routing-research",
        prompt="Which repo holds benchmarks, research, and the model registry?",
        acceptable_answers=["epyc-inference-research"],
    ),
    RecallTask(
        task_id="IR-07-eval-incremental",
        prompt="What's the policy for inference scripts (benchmarks, evals, seeding)?",
        acceptable_answers=["MUST persist", "incrementally", "JSONL", "checkpoint"],
    ),
    RecallTask(
        task_id="IR-08-quality-score-format",
        prompt="What's the canonical format for `quality_score` in the model registry?",
        acceptable_answers=["pct", "raw", "inline YAML map"],
    ),
    RecallTask(
        task_id="IR-09-paths-must-be",
        prompt="What's required of paths in model registry entries?",
        acceptable_answers=["must be absolute", "absolute"],
    ),
    RecallTask(
        task_id="IR-10-deprecated-handling",
        prompt="How should deprecated models be handled in the registry?",
        acceptable_answers=["deprecated: true", "retain", "reason"],
    ),
    RecallTask(
        task_id="IR-11-thread-safe",
        prompt="What does the engineering standards say about shared mutable state?",
        acceptable_answers=["thread-safe"],
    ),
    RecallTask(
        task_id="IR-12-verification-minimum",
        prompt="List the steps in 'Verification Minimum' before finalizing.",
        acceptable_answers=["syntax", "tests", "feature", "docs"],
    ),
    RecallTask(
        task_id="IR-13-research-vs-orchestrator-registry",
        prompt="What's the difference between the research and orchestrator registries?",
        acceptable_answers=["comprehensive", "active stack", "lean"],
    ),
    RecallTask(
        task_id="IR-14-feature-flag-policy",
        prompt="When should a new feature have a feature flag?",
        acceptable_answers=["optional", "Gate optional features"],
    ),
    RecallTask(
        task_id="IR-15-incremental-anti-pattern",
        prompt="Why is collecting all results into a list and writing at the end an anti-pattern?",
        acceptable_answers=["killed", "lost", "partial results"],
    ),
]


def all_tasks() -> list[RecallTask]:
    return list(TASKS)
