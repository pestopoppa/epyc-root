"""Procedure-correctness tasks for agent-file compliance.

Each task: a prompt that requires multi-step procedure execution where order
matters. Pass criterion: model output names all required steps in the correct
relative order. Steps may be paraphrased; the order check uses a stable-anchor
substring per step.

Many of these reference `agents/shared/ENGINEERING_STANDARDS.md` Verification
Minimum + Numerical Parameter Policy + Incremental Persistence patterns.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProcedureTask:
    task_id: str
    prompt: str
    ordered_step_anchors: list[str]  # list of substrings, must appear in this order
    relevant_agent_file: str = "agents/shared/ENGINEERING_STANDARDS.md"
    notes: str = ""


TASKS: list[ProcedureTask] = [
    ProcedureTask(
        task_id="PC-01-verification-minimum",
        prompt=(
            "I'm about to finalize a Python change that adds a new feature flag and "
            "modifies a service interface. Walk me through the verification steps in order."
        ),
        ordered_step_anchors=[
            "syntax",       # 1. Syntax check
            "test",         # 2. Run targeted tests
            "feature-flag",  # 3. Confirm feature-flag behavior
            "doc",          # 4. Update docs
        ],
        notes="Verification Minimum: 4 ordered steps.",
    ),
    ProcedureTask(
        task_id="PC-02-incremental-eval-loop",
        prompt=(
            "Show the structure of an eval loop that scores 100 prompts. Include "
            "checkpoint open, the loop body, and progress logging in the right place."
        ),
        ordered_step_anchors=[
            "open(",        # open checkpoint file FIRST
            "for ",         # then the loop
            "evaluate",     # score per item
            "ckpt.write",   # append to checkpoint
            "log.info",     # then per-item log
        ],
        notes="Incremental Persistence Required Pattern.",
    ),
    ProcedureTask(
        task_id="PC-03-numeric-classification-pr",
        prompt=(
            "I'm adding a new constant `MAX_RETRIES = 5`. What should I do before merging?"
        ),
        ordered_step_anchors=[
            "classif",       # classify as tunable or invariant
            "constant",      # since invariant: named constant
            "PR",            # add classification note in PR
        ],
        notes="Numerical Parameter Policy: classify, place, document.",
    ),
    ProcedureTask(
        task_id="PC-04-deprecate-model",
        prompt=(
            "We need to deprecate the qwen2.5-32B entry in the model registry. "
            "Walk me through it step by step."
        ),
        ordered_step_anchors=[
            "deprecated: true",
            "reason",
            "comment",
        ],
        notes="Model Entry Requirements: deprecated:true flag + reason in comments.",
    ),
    ProcedureTask(
        task_id="PC-05-add-tunable-config",
        prompt=(
            "I want to add a new tunable parameter `top_k_samples` for the seeding script. "
            "Walk me through the steps."
        ),
        ordered_step_anchors=[
            "typed config",
            "dataclass",
            "env override",
            "PR",
            "classification",
        ],
        notes="Numerical Parameter Policy: typed config + env override + PR note.",
    ),
    ProcedureTask(
        task_id="PC-06-quality-score-update",
        prompt=(
            "I just got a new benchmark result: 78.3% (132/169). How do I update the quality_score field?"
        ),
        ordered_step_anchors=[
            "pct",
            "raw",
            "inline",
        ],
        notes="Scoring Fields: inline YAML map with pct + raw.",
    ),
    ProcedureTask(
        task_id="PC-07-multi-repo-placement",
        prompt=(
            "I need to add a new benchmark script + a feature flag + an agent file overlay. "
            "Where does each go and in what order?"
        ),
        ordered_step_anchors=[
            "epyc-inference-research",   # benchmark goes there
            "src/features.py",            # feature flag in orchestrator
            "agents/",                    # agent file in epyc-root
        ],
        notes="Placement Rules table: per-content repo routing.",
    ),
    ProcedureTask(
        task_id="PC-08-thread-safe-cache",
        prompt=(
            "I'm adding a shared cache that multiple threads can update. What's the procedure?"
        ),
        ordered_step_anchors=[
            "thread-safe",
            "lock",
        ],
        notes="Code Invariants: use thread-safe paths.",
    ),
    ProcedureTask(
        task_id="PC-09-feature-flag-rollout",
        prompt=(
            "I want to add an optional new scoring path. Walk me through getting it into "
            "production safely."
        ),
        ordered_step_anchors=[
            "feature flag",
            "config",
            "test",
        ],
        notes="Code Invariants + Verification Minimum.",
    ),
    ProcedureTask(
        task_id="PC-10-pre-commit-checklist",
        prompt=(
            "Pre-commit checklist for a Python change that touches a service interface. Order matters."
        ),
        ordered_step_anchors=[
            "syntax",
            "tests",
            "feature-flag",
            "docs",
        ],
        notes="Verification Minimum 4 ordered steps.",
    ),
    ProcedureTask(
        task_id="PC-11-eval-script-killed",
        prompt=(
            "An eval run got killed at item 47/100. What should the script do so partial "
            "results are usable?"
        ),
        ordered_step_anchors=[
            "JSONL",
            "append",
            "checkpoint",
        ],
        notes="Incremental Persistence: append per-item.",
    ),
    ProcedureTask(
        task_id="PC-12-add-vl-score",
        prompt=(
            "Add a vl_score of 92% (11/12) to a model entry. Show the YAML."
        ),
        ordered_step_anchors=[
            "pct",
            "92",
            "raw",
            "11/12",
        ],
        notes="vl_score: {pct, raw} format.",
    ),
]


def all_tasks() -> list[ProcedureTask]:
    return list(TASKS)
