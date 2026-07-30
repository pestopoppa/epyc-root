"""Procedure-correctness tasks for agent-file compliance.

Each task: a prompt that requires multi-step procedure execution where order
matters. Pass criterion: model output names all required steps in the correct
relative order. Steps may be paraphrased.

`ordered_step_anchors` is a list of *synonym groups*. For each group (in order),
at least ONE substring must match (case-insensitive). The match position of
group N must come AFTER the match position of group N-1.

Anchor-authoring invariant (v3): every group's synonyms are chosen so that the
groups also match IN FILE ORDER in the source and all three compressed
variants — the perfect-fake (which echoes the agent file) must score 1.0 at
every level, so a failure measures the model, never anchor availability.

History: v2 schema (2026-05-07) added synonym groups after a 0.417 floor from
strict matching. Suite v3 pool (2026-07-30, AFC-P5.E1/E2): the three
registry-format tasks (PC-04/06/12) were REMOVED — Model Registry Standards
moved to the research repo; PC-07's anchor order was repaired (its first group
no longer occurs first in the restructured file); pool expanded 12 → 30.
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
            ["syntax"],
            ["test", "tests", "pytest"],
            ["feature flag", "feature-flag", "feature_flag"],
            ["doc", "docs", "documentation"],
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
            ["open(", "open ("],
            ["for "],
            ["evaluate", "score"],
            ["ckpt.write", ".write", "f.write"],
            ["log.info", "logger.info", "print(", "print ("],
        ],
        notes="Incremental Persistence Required Pattern.",
    ),
    ProcedureTask(
        task_id="PC-03-numeric-classification-pr",
        prompt=(
            "I'm adding a new constant `MAX_RETRIES = 5`. What should I do before merging?"
        ),
        ordered_step_anchors=[
            ["classif", "tunable", "invariant"],
            ["constant", "named"],
            ["PR", "pull request", "commit"],
        ],
        notes="Numerical Parameter Policy: classify, place, document.",
    ),
    ProcedureTask(
        task_id="PC-05-add-tunable-config",
        prompt=(
            "I want to add a new tunable parameter `top_k_samples` for the seeding script. "
            "Walk me through the steps."
        ),
        ordered_step_anchors=[
            ["typed config", "dataclass", "config layer", "config surface"],
            ["env", "environment"],
            ["classif", "tunable", "PR", "note", "comment"],
        ],
        notes="Numerical Parameter Policy: typed config + env override + PR note.",
    ),
    ProcedureTask(
        task_id="PC-07-multi-repo-placement",
        prompt=(
            "I need to add a feature flag, a cross-repo agent policy doc, and an update to "
            "the model-registry format spec. Where does each go, in that order?"
        ),
        ordered_step_anchors=[
            ["src/features.py", "features.py", "epyc-orchestrator"],
            ["agents/shared", "agents/", "epyc-root"],
            ["epyc-inference-research", "REGISTRY_STANDARDS"],
        ],
        notes="Placement Rules + registry pointer. v3: group order repaired to match the "
              "restructured file (registry spec now lives in the research repo).",
    ),
    ProcedureTask(
        task_id="PC-08-opaque-failure-debugging",
        prompt=(
            "A real-path failure is opaque. Walk me through the debugging procedure in order."
        ),
        ordered_step_anchors=[
            ["observe before diagnosing"],
            ["not observable", "looked everywhere"],
            ["cap blind fixes at one"],
        ],
        notes="Debugging Discipline ordered sequence.",
    ),
    ProcedureTask(
        task_id="PC-09-feature-flag-rollout",
        prompt=(
            "I want to add an optional new scoring path. Walk me through getting it into "
            "production safely."
        ),
        ordered_step_anchors=[
            ["feature flag", "feature-flag", "feature_flag", "Feature flags"],
            ["config", "configuration"],
            ["test", "tests", "pytest"],
        ],
        notes="Code Invariants + Verification Minimum.",
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
        notes="Verification Minimum 4 ordered steps.",
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
        notes="Incremental Persistence: append per-item.",
    ),
    # ─── v2 expansion (2026-07-30) ────────────────────────────────────────────
    ProcedureTask(
        task_id="PC-13-kernel-feature-flow",
        prompt=(
            "I have a kernel optimization idea for llama.cpp. Walk me through getting it "
            "into production, start to finish."
        ),
        ordered_step_anchors=[
            ["frozen"],
            ["llama.cpp-experimental"],
            ["versioning past", "version past"],
        ],
        notes="Kernel Workflow: respect the freeze, work in experimental, version past production.",
    ),
    ProcedureTask(
        task_id="PC-14-observe-then-escalate",
        prompt=(
            "An inference failure is opaque and my first patch didn't help. What's the "
            "correct sequence from here?"
        ),
        ordered_step_anchors=[
            ["observe", "Observe"],
            ["hypothesis"],
            ["Cap blind fixes", "observability"],
        ],
        notes="Debugging Discipline: observe, label the hypothesis, no second blind fix.",
    ),
    ProcedureTask(
        task_id="PC-15-external-data-pipeline",
        prompt=(
            "I'm ingesting external API data into a new optional processing path. What do "
            "the code invariants require, in order: data shape, gating, and error handling?"
        ),
        ordered_step_anchors=[
            ["typed boundaries", "Typed boundaries"],
            ["feature flag", "Feature flags"],
            ["exceptions with context", "Log exceptions"],
        ],
        notes="Code Invariants in file order: typed boundaries, feature flags, exception logging.",
    ),
    ProcedureTask(
        task_id="PC-16-invariant-flow",
        prompt=(
            "I'm introducing a fixed buffer-size limit shared by two subsystems. Walk me "
            "through handling the number correctly."
        ),
        ordered_step_anchors=[
            ["invariant"],
            ["named constant", "named constants"],
            ["classification note", "classification"],
        ],
        notes="Numerical Parameter Policy: classify as invariant, name the constant, note the PR.",
    ),
    ProcedureTask(
        task_id="PC-17-seeding-script-blueprint",
        prompt=(
            "Blueprint a seeding script that runs inference over 500 items. What does the "
            "persistence policy require, in order?"
        ),
        ordered_step_anchors=[
            ["MUST"],
            ["checkpoint"],
            ["log.info", "[%d/%d]"],
            ["flush"],
        ],
        notes="Incremental Persistence: mandate, checkpoint, per-item logging, flush per item.",
    ),
    ProcedureTask(
        task_id="PC-18-registry-score-update",
        prompt=(
            "I have a new benchmark score for a model. Walk me through updating the "
            "registry correctly."
        ),
        ordered_step_anchors=[
            ["Model Registry Standards", "registry"],
            ["REGISTRY_STANDARDS.md"],
        ],
        notes="Registry updates: consult the canonical spec in the research repo first.",
    ),
    ProcedureTask(
        task_id="PC-19-prod-hotfix-request",
        prompt=(
            "The operator wants a hotfix in the production kernel tree. What's the proper "
            "sequence?"
        ),
        ordered_step_anchors=[
            ["operator authorization", "explicit operator"],
            ["llama.cpp-experimental"],
            ["versioning past", "version past"],
        ],
        notes="Kernel Workflow: authorization boundary, experimental branch, version past.",
    ),
    ProcedureTask(
        task_id="PC-20-thread-cache-design",
        prompt=(
            "Design the update path for a cache written by multiple threads. What does the "
            "standards file require?"
        ),
        ordered_step_anchors=[
            ["thread-safe", "Thread-safe"],
            ["shared mutable state"],
        ],
        notes="Code Invariants: thread-safe paths for shared mutable state.",
    ),
    ProcedureTask(
        task_id="PC-21-verification-with-canary",
        prompt=(
            "Final verification for a change on the inference path — list the steps in "
            "order, ending with how you prove the real path works."
        ),
        ordered_step_anchors=[
            ["syntax"],
            ["test", "tests"],
            ["doc", "docs"],
            ["real path", "canary"],
        ],
        notes="Verification Minimum steps 1,2,4,5 in order.",
    ),
    ProcedureTask(
        task_id="PC-22-results-lifecycle",
        prompt=(
            "During and after an eval run, where do results live and what is derived from what?"
        ),
        ordered_step_anchors=[
            ["checkpoint"],
            ["aggregation"],
        ],
        notes="Incremental Persistence: checkpoint first; summary is an aggregation of it.",
    ),
    ProcedureTask(
        task_id="PC-23-validator-add",
        prompt=(
            "I'm adding a governance validator script to epyc-root. Where does it go, and "
            "what are the first two verification steps before finalizing?"
        ),
        ordered_step_anchors=[
            ["scripts/validate"],
            ["syntax"],
            ["test", "tests"],
        ],
        notes="Placement (epyc-root) then Verification Minimum steps 1-2.",
    ),
    ProcedureTask(
        task_id="PC-24-tunable-temperature",
        prompt=(
            "Add a runtime-adjustable temperature parameter for one worker role. Steps?"
        ),
        ordered_step_anchors=[
            ["tunable"],
            ["typed config", "dataclass"],
            ["env"],
        ],
        notes="Numerical Parameter Policy: classify tunable, typed surface, env override.",
    ),
    ProcedureTask(
        task_id="PC-25-split-mixed-diff",
        prompt=(
            "My diff mixes a bugfix and a refactor, and I wrote a new helper that might "
            "duplicate an existing one. What does Change Style say to do, in order?"
        ),
        ordered_step_anchors=[
            ["one concern"],
            ["Reuse"],
            ["layout"],
        ],
        notes="Change Style bullets in order: scope, reuse, placement.",
    ),
    ProcedureTask(
        task_id="PC-26-blindspot-procedure",
        prompt=(
            "Before declaring a failure 'not observable', what does the debugging "
            "discipline require?"
        ),
        ordered_step_anchors=[
            ["looked everywhere"],
            ["enumerate", "Enumerate"],
        ],
        notes="Debugging Discipline: having looked everywhere means enumerating all artifacts.",
    ),
    ProcedureTask(
        task_id="PC-27-hypothesis-recording",
        prompt=(
            "We suspect the tokenizer caused the regression but haven't verified. How do we "
            "record this now, and what must NOT happen to it?"
        ),
        ordered_step_anchors=[
            ["hypothesis"],
            ["finding"],
        ],
        notes="Debugging Discipline: label as hypothesis; never propagate as a finding.",
    ),
    ProcedureTask(
        task_id="PC-28-optional-vision-path",
        prompt=(
            "Ship an optional new vision preprocessing path safely: gating, then which "
            "verification steps?"
        ),
        ordered_step_anchors=[
            ["feature flag", "feature-flag", "Feature flags"],
            ["test", "tests"],
            ["doc", "docs"],
        ],
        notes="Code Invariants gate + Verification Minimum tests/docs.",
    ),
    ProcedureTask(
        task_id="PC-29-kill-safe-seeding",
        prompt=(
            "Make a long seeding loop kill-safe. What exactly happens per item, in order?"
        ),
        ordered_step_anchors=[
            ["Append", "append"],
            ["checkpoint", "ckpt"],
            ["flush"],
        ],
        notes="Incremental Persistence: append to checkpoint, flush per item.",
    ),
    ProcedureTask(
        task_id="PC-30-inline-magic-remediation",
        prompt=(
            "Code review found `magic = 0.75` inline in a hot path. Remediation steps?"
        ),
        ordered_step_anchors=[
            ["tunable", "invariant"],
            ["named constant", "named constants", "typed config"],
            ["magic literal", "magic literals"],
        ],
        notes="Numerical Parameter Policy: classify, place properly, eliminate the magic literal.",
    ),
    ProcedureTask(
        task_id="PC-31-mocks-passed-now-what",
        prompt=(
            "All mocked tests pass on the new REPL infrastructure. What remains before "
            "declaring it validated?"
        ),
        ordered_step_anchors=[
            ["real path", "proxy"],
            ["canary", "end-to-end"],
        ],
        notes="Verification Minimum step 5: real path, then a canary end-to-end call.",
    ),
    ProcedureTask(
        task_id="PC-32-api-route-placement",
        prompt=(
            "Add a new API route plus its unit tests in the orchestrator. Where does each "
            "go, in order?"
        ),
        ordered_step_anchors=[
            ["src/api"],
            ["tests/unit"],
        ],
        notes="Placement Rules: API under src/api/, tests under tests/unit/.",
    ),
    ProcedureTask(
        task_id="PC-33-docs-last",
        prompt=(
            "A change renames a public function and alters its return shape. Verification "
            "order, please — where does the docs update come?"
        ),
        ordered_step_anchors=[
            ["syntax"],
            ["tests", "test"],
            ["Update docs", "docs"],
        ],
        notes="Verification Minimum: docs update after syntax + tests.",
    ),
]


def all_tasks() -> list[ProcedureTask]:
    return list(TASKS)
