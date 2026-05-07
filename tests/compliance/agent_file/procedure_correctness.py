"""Procedure-correctness tasks for agent-file compliance.

Each task: a prompt that requires multi-step procedure execution where order
matters. Pass criterion: model output names all required steps in the correct
relative order. Steps may be paraphrased.

`ordered_step_anchors` is a list of *synonym groups*. For each group (in order),
at least ONE substring must match (case-insensitive). The match position of
group N must come AFTER the match position of group N-1.

This is the v2 schema (revised 2026-05-07 after Phase 3 first-pass surfaced
a 0.417 floor on this pool — see data/compliance/2026-05-06-worker30b-curve/
SUMMARY.md). The previous schema used `list[str]` with strict substring match;
many tasks failed because models used "feature flag" where the anchor was
`"feature-flag"`, or used "set deprecated to true" where the anchor was the
literal `"deprecated: true"`. Synonym groups absorb that variation.

Backward compat: the runner accepts either `str` or `list[str]` per group.
A bare `str` is treated as a one-element group.

Many tasks reference `agents/shared/ENGINEERING_STANDARDS.md` Verification
Minimum + Numerical Parameter Policy + Incremental Persistence patterns.
"""

from __future__ import annotations

from dataclasses import dataclass


# AnchorGroup: one position in the ordered procedure. Either a single substring
# (legacy) or a list of synonym substrings (any-of).
AnchorGroup = str | list[str]


@dataclass
class ProcedureTask:
    task_id: str
    prompt: str
    ordered_step_anchors: list[AnchorGroup]
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
            ["syntax"],                                       # 1. Syntax check
            ["test", "tests", "pytest"],                       # 2. Run targeted tests
            ["feature flag", "feature-flag", "feature_flag"],  # 3. Feature-flag behavior
            ["doc", "docs", "documentation"],                  # 4. Update docs
        ],
        notes="Verification Minimum: 4 ordered steps. v2: synonym groups for hyphenated 'feature-flag'.",
    ),
    ProcedureTask(
        task_id="PC-02-incremental-eval-loop",
        prompt=(
            "Show the structure of an eval loop that scores 100 prompts. Include "
            "checkpoint open, the loop body, and progress logging in the right place."
        ),
        ordered_step_anchors=[
            ["open(", "open ("],          # open checkpoint file FIRST
            ["for "],                      # then the loop
            ["evaluate", "score"],         # score per item
            ["ckpt.write", ".write", "f.write"],  # append to checkpoint
            ["log.info", "logger.info", "print(", "print ("],   # then per-item log
        ],
        notes="Incremental Persistence Required Pattern. v2: synonyms for write/log calls.",
    ),
    ProcedureTask(
        task_id="PC-03-numeric-classification-pr",
        prompt=(
            "I'm adding a new constant `MAX_RETRIES = 5`. What should I do before merging?"
        ),
        ordered_step_anchors=[
            ["classif", "tunable", "invariant"],  # classify as tunable or invariant
            ["constant", "named"],                 # since invariant: named constant
            ["PR", "pull request", "commit"],      # add classification note in PR
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
            ["deprecated"],                # the deprecated flag itself
            ["true"],                       # set to true
            ["reason", "comment", "note", "why"],  # reason / explanation
        ],
        notes="Model Entry Requirements: deprecated:true flag + reason in comments. "
              "v2: split 'deprecated: true' into two anchor groups, accept reason synonyms.",
    ),
    ProcedureTask(
        task_id="PC-05-add-tunable-config",
        prompt=(
            "I want to add a new tunable parameter `top_k_samples` for the seeding script. "
            "Walk me through the steps."
        ),
        ordered_step_anchors=[
            ["typed config", "dataclass", "config layer", "config surface"],  # typed surface
            ["env", "environment"],                                            # env override
            ["classif", "tunable", "PR", "note", "comment"],                  # PR note
        ],
        notes="Numerical Parameter Policy: typed config + env override + PR note. "
              "v2: trimmed from 5 to 3 groups; PR/classification merged into one trailing group.",
    ),
    ProcedureTask(
        task_id="PC-06-quality-score-update",
        prompt=(
            "I just got a new benchmark result: 78.3% (132/169). How do I update the quality_score field?"
        ),
        ordered_step_anchors=[
            ["pct"],
            ["raw"],
            ["inline", "map", "{"],
        ],
        notes="Scoring Fields: inline YAML map with pct + raw. v2: accept '{' as inline-map signal.",
    ),
    ProcedureTask(
        task_id="PC-07-multi-repo-placement",
        prompt=(
            "I need to add a new benchmark script + a feature flag + an agent file overlay. "
            "Where does each go and in what order?"
        ),
        ordered_step_anchors=[
            ["epyc-inference-research", "inference-research"],  # benchmark goes there
            ["src/features.py", "features.py", "epyc-orchestrator"],  # feature flag in orch
            ["agents/", "agents/shared", "epyc-root"],  # agent file in epyc-root
        ],
        notes="Placement Rules table: per-content repo routing. v2: accept repo-name synonyms.",
    ),
    ProcedureTask(
        task_id="PC-08-thread-safe-cache",
        prompt=(
            "I'm adding a shared cache that multiple threads can update. What's the procedure?"
        ),
        ordered_step_anchors=[
            ["thread-safe", "thread safe", "thread_safe"],
            ["lock", "Lock", "RLock", "mutex", "synchroniz"],
        ],
        notes="Code Invariants: use thread-safe paths. v2: synonyms for hyphenation + lock variants.",
    ),
    ProcedureTask(
        task_id="PC-09-feature-flag-rollout",
        prompt=(
            "I want to add an optional new scoring path. Walk me through getting it into "
            "production safely."
        ),
        ordered_step_anchors=[
            ["feature flag", "feature-flag", "feature_flag"],
            ["config", "configuration"],
            ["test", "tests", "pytest"],
        ],
        notes="Code Invariants + Verification Minimum. v2: hyphen synonyms.",
    ),
    ProcedureTask(
        task_id="PC-10-pre-commit-checklist",
        prompt=(
            "Pre-commit checklist for a Python change that touches a service interface. Order matters."
        ),
        ordered_step_anchors=[
            ["syntax"],
            ["test", "tests", "pytest"],
            ["feature flag", "feature-flag", "feature_flag"],
            ["doc", "docs", "documentation"],
        ],
        notes="Verification Minimum 4 ordered steps. v2: hyphen synonyms (matches PC-01 schema).",
    ),
    ProcedureTask(
        task_id="PC-11-eval-script-killed",
        prompt=(
            "An eval run got killed at item 47/100. What should the script do so partial "
            "results are usable?"
        ),
        ordered_step_anchors=[
            ["JSONL", "jsonl", "json", "csv"],
            ["append", "write"],
            ["checkpoint", "ckpt", "incremental"],
        ],
        notes="Incremental Persistence: append per-item. v2: format synonyms.",
    ),
    ProcedureTask(
        task_id="PC-12-add-vl-score",
        prompt=(
            "Add a vl_score of 92% (11/12) to a model entry. Show the YAML."
        ),
        ordered_step_anchors=[
            ["pct"],
            ["92"],
            ["raw"],
            ["11/12"],
        ],
        notes="vl_score: {pct, raw} format. (Already passes — keep as-is.)",
    ),
]


def all_tasks() -> list[ProcedureTask]:
    return list(TASKS)
