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

Suite v3 pool extension (2026-11-10, flash-tools): 30 → 150. The original 30
tasks are unchanged; 120 new tasks (PC-34..PC-153) were added, spread roughly
evenly over the ordered procedures in ENGINEERING_STANDARDS.md (Code
Invariants, Numerical Parameter Policy, Change Style, Placement Rules,
Kernel Workflow, Incremental Persistence, Model Registry Standards,
Debugging Discipline, Verification Minimum). Each is a distinct scenario.
New anchors are verbatim-present, in scorer order, in the source file AND all
three compressed variants (checked by script; perfect-fake passes 150/150 at
every level). Anchors avoid wrapped phrases ("explicit operator authorization"
breaks across lines in two variants) and the `{pct, raw}` map absent from the
aggressive variant.
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
    # ─── v3 expansion (2026-11-10): 30 → 150, ~evenly across ENGINEERING_STANDARDS procedures ──
    ProcedureTask(
        task_id="PC-34-webhook-payload-parsing",
        prompt=(
            "A third-party billing webhook posts JSON to our service. Order the code-invariant rules I should apply: parsing, status strings, gating the handler, and what to do when parsing blows up."
        ),
        ordered_step_anchors=[
            ["typed boundaries"],
            ["enums"],
            ["feature flag"],
            ["log exceptions"],
        ],
        notes="Code Invariants: typed boundaries, enums, feature flag, exception logging.",
    ),
    ProcedureTask(
        task_id="PC-35-order-status-strings",
        prompt=(
            "My handler compares `status == \"in_progress\"` in six places. Which invariants apply, and in what order do I tackle them?"
        ),
        ordered_step_anchors=[
            ["typed boundaries"],
            ["enums"],
        ],
        notes="Code Invariants: typed boundaries then enums/constants.",
    ),
    ProcedureTask(
        task_id="PC-36-experimental-reranker-gating",
        prompt=(
            "We want to land an experimental reranker behind a switch, and it calls out to a flaky service. Which two invariants matter, in file order?"
        ),
        ordered_step_anchors=[
            ["feature flag"],
            ["log exceptions"],
        ],
        notes="Code Invariants: flag then exception logging.",
    ),
    ProcedureTask(
        task_id="PC-37-silent-except-cleanup",
        prompt=(
            "I found `except: pass` around a cache refresh in a worker. After fixing that, what other invariant applies to the same cache if multiple threads refresh it?"
        ),
        ordered_step_anchors=[
            ["log exceptions"],
            ["thread-safe"],
        ],
        notes="Code Invariants: log exceptions then thread-safe paths.",
    ),
    ProcedureTask(
        task_id="PC-38-config-loader-from-yaml",
        prompt=(
            "I'm reading a YAML file written by another team into the app. Give me the invariant order from the data boundary down to failures."
        ),
        ordered_step_anchors=[
            ["typed boundaries"],
            ["enums"],
            ["log exceptions"],
        ],
        notes="Code Invariants: boundary typing, enums, exception context.",
    ),
    ProcedureTask(
        task_id="PC-39-shared-counter-metrics",
        prompt=(
            "Two request threads update a shared metrics dict. What do the invariants require, ending with the state update path?"
        ),
        ordered_step_anchors=[
            ["log exceptions"],
            ["thread-safe"],
        ],
        notes="Code Invariants: exception logging, thread-safe updates.",
    ),
    ProcedureTask(
        task_id="PC-40-role-name-literals",
        prompt=(
            "Role names are typed as raw strings across the router. Walk through what the invariants want, starting from data typing and ending at gating a new optional route."
        ),
        ordered_step_anchors=[
            ["typed boundaries"],
            ["enums"],
            ["feature flag"],
        ],
        notes="Code Invariants: typed boundaries, enums, feature flag.",
    ),
    ProcedureTask(
        task_id="PC-41-scraper-new-optional-path",
        prompt=(
            "A new optional scraper path reads HTML-derived records, can raise on malformed rows, and shares a dedup set across threads. List all five invariants in order."
        ),
        ordered_step_anchors=[
            ["typed boundaries"],
            ["enums"],
            ["feature flag"],
            ["log exceptions"],
            ["thread-safe"],
        ],
        notes="Code Invariants: all five in order.",
    ),
    ProcedureTask(
        task_id="PC-42-typed-boundary-only",
        prompt=(
            "What is the first code invariant for data entering from outside the process, and which one follows it?"
        ),
        ordered_step_anchors=[
            ["typed boundaries"],
            ["enums"],
        ],
        notes="Code Invariants: first two.",
    ),
    ProcedureTask(
        task_id="PC-43-gate-then-log",
        prompt=(
            "I added an optional telemetry exporter. How should it be gated, and how should its failures be handled?"
        ),
        ordered_step_anchors=[
            ["feature flag"],
            ["log exceptions"],
        ],
        notes="Code Invariants: flag then exceptions.",
    ),
    ProcedureTask(
        task_id="PC-44-thread-pool-registry",
        prompt=(
            "A thread pool mutates a shared model-state table while a monitor reads it. Where do exceptions go and how should the table be updated?"
        ),
        ordered_step_anchors=[
            ["log exceptions"],
            ["thread-safe"],
        ],
        notes="Code Invariants: exceptions with context, thread-safe.",
    ),
    ProcedureTask(
        task_id="PC-45-string-keys-to-enums",
        prompt=(
            "Our JSON handler switches on ad hoc strings and enabling it should be optional. Order: type the input, replace the strings, gate it."
        ),
        ordered_step_anchors=[
            ["typed boundaries"],
            ["enums"],
            ["feature flag"],
        ],
        notes="Code Invariants: boundaries, enums, flag.",
    ),
    ProcedureTask(
        task_id="PC-46-socket-reader-thread",
        prompt=(
            "A background socket reader thread appends to a shared buffer and sometimes swallows decode errors. What do the invariants say about the swallowing and the buffer, in order?"
        ),
        ordered_step_anchors=[
            ["log exceptions"],
            ["thread-safe"],
        ],
        notes="Code Invariants: exception logging then thread-safe.",
    ),
    ProcedureTask(
        task_id="PC-47-optional-ingest-flag-first",
        prompt=(
            "Before I write an optional CSV ingestor, tell me which invariants cover external data, string constants, feature gating, and error logging, in order."
        ),
        ordered_step_anchors=[
            ["typed boundaries"],
            ["enums"],
            ["feature flag"],
            ["log exceptions"],
        ],
        notes="Code Invariants: first four.",
    ),
    ProcedureTask(
        task_id="PC-48-flag-error-thread",
        prompt=(
            "For an optional background sync that fails sometimes and touches shared state, give the gating, failure handling, and concurrency invariants in order."
        ),
        ordered_step_anchors=[
            ["feature flag"],
            ["log exceptions"],
            ["thread-safe"],
        ],
        notes="Code Invariants: last three.",
    ),
    ProcedureTask(
        task_id="PC-49-beam-width-classify",
        prompt=(
            "I'm adding `BEAM_WIDTH = 8` for a decoding experiment we will sweep. Walk through the numerical policy: class, home, override."
        ),
        ordered_step_anchors=[
            ["tunable"],
            ["typed config"],
            ["env override"],
        ],
        notes="Numerical: tunable, typed config, env override.",
    ),
    ProcedureTask(
        task_id="PC-50-header-length-limit",
        prompt=(
            "The wire format caps a header at 4096 bytes in both client and server. How should this number be treated?"
        ),
        ordered_step_anchors=[
            ["invariant"],
            ["named constants"],
            ["magic literals"],
        ],
        notes="Numerical: invariant, named constants, no magic literals.",
    ),
    ProcedureTask(
        task_id="PC-51-global-constants-file",
        prompt=(
            "Someone proposes one `constants.py` to hold every number in the repo. What does the policy say, and what should replace it?"
        ),
        ordered_step_anchors=[
            ["tunable"],
            ["global file"],
        ],
        notes="Numerical: tunable, do not consolidate to a global file.",
    ),
    ProcedureTask(
        task_id="PC-52-pr-description-numeric",
        prompt=(
            "My PR adds two numeric knobs. What must the PR description include, after I've classified them?"
        ),
        ordered_step_anchors=[
            ["tunable"],
            ["invariant"],
            ["classification note"],
        ],
        notes="Numerical: classify then classification note.",
    ),
    ProcedureTask(
        task_id="PC-53-timeout-ops-override",
        prompt=(
            "Request timeout will be bumped by ops during incidents. Where does it live and how do ops change it?"
        ),
        ordered_step_anchors=[
            ["tunable"],
            ["typed config"],
            ["env override"],
        ],
        notes="Numerical: tunable, typed config, env override.",
    ),
    ProcedureTask(
        task_id="PC-54-page-size-invariant",
        prompt=(
            "Pagination page size is fixed at 100 by an upstream API contract. Classify and place it."
        ),
        ordered_step_anchors=[
            ["invariant"],
            ["named constants"],
        ],
        notes="Numerical: invariant then named constant.",
    ),
    ProcedureTask(
        task_id="PC-55-retry-backoff-sweeps",
        prompt=(
            "We'll sweep retry backoff 0.5 to 4 seconds during evaluation. What class, what surface, and what operational hook?"
        ),
        ordered_step_anchors=[
            ["tunable"],
            ["typed config"],
            ["env override"],
        ],
        notes="Numerical: tunable.",
    ),
    ProcedureTask(
        task_id="PC-56-magic-literal-in-loop",
        prompt=(
            "Review spotted `if score > 0.62:` in a ranking loop where 0.62 is a mandated semantic threshold. Remediate in order."
        ),
        ordered_step_anchors=[
            ["invariant"],
            ["named constants"],
            ["magic literals"],
        ],
        notes="Numerical: invariant, named constants, magic literals.",
    ),
    ProcedureTask(
        task_id="PC-57-per-subsystem-ownership",
        prompt=(
            "Cache and scheduler each have their own tunable limits. Should I move both into a shared numbers module?"
        ),
        ordered_step_anchors=[
            ["tunable"],
            ["global file"],
        ],
        notes="Numerical: do not consolidate; subsystem owns.",
    ),
    ProcedureTask(
        task_id="PC-58-pr-note-for-invariant",
        prompt=(
            "I only added one invariant constant in this PR. Do I still owe the reviewer a note, and what goes in it?"
        ),
        ordered_step_anchors=[
            ["invariant"],
            ["classification note"],
        ],
        notes="Numerical: classification note for invariants too.",
    ),
    ProcedureTask(
        task_id="PC-59-sampling-top-p",
        prompt=(
            "Add `top_p` to a role's sampling config used in experiments. Walk through steps from classification to docs for ops."
        ),
        ordered_step_anchors=[
            ["tunable"],
            ["typed config"],
            ["env override"],
            ["classification note"],
        ],
        notes="Numerical: full tunable path to PR note.",
    ),
    ProcedureTask(
        task_id="PC-60-max-context-hard-limit",
        prompt=(
            "The model's context window of 32768 is a hard boundary shared by the tokenizer and the scheduler. Handle it."
        ),
        ordered_step_anchors=[
            ["invariant"],
            ["named constants"],
            ["magic literals"],
            ["classification note"],
        ],
        notes="Numerical: invariant path to note.",
    ),
    ProcedureTask(
        task_id="PC-61-replace-hardcoded-weights",
        prompt=(
            "A scoring function hardcodes 0.3/0.7 blend weights we tune per suite. Remediate: classify, place, avoid magic."
        ),
        ordered_step_anchors=[
            ["tunable"],
            ["typed config"],
            ["magic literals"],
            ["classification note"],
        ],
        notes="Numerical: tunable, typed config, magic literals, note.",
    ),
    ProcedureTask(
        task_id="PC-62-slot-count-dataclass",
        prompt=(
            "`n_slots` changes per host and we benchmark it. Where should the value live, and should an env override exist?"
        ),
        ordered_step_anchors=[
            ["tunable"],
            ["typed config"],
            ["env override"],
        ],
        notes="Numerical: tunable.",
    ),
    ProcedureTask(
        task_id="PC-63-shared-boundary-name",
        prompt=(
            "Two subsystems share a max payload length of 1 MiB. Name it, classify it, and say why a literal is wrong."
        ),
        ordered_step_anchors=[
            ["invariant"],
            ["named constants"],
            ["magic literals"],
        ],
        notes="Numerical: invariant.",
    ),
    ProcedureTask(
        task_id="PC-64-numbers-in-one-file-plan",
        prompt=(
            "A refactor plan moves all thresholds into `core/numbers.py`. Critique against the policy and say what to do with tunables vs invariants."
        ),
        ordered_step_anchors=[
            ["tunable"],
            ["invariant"],
            ["global file"],
        ],
        notes="Numerical: tunable, invariant, global file.",
    ),
    ProcedureTask(
        task_id="PC-65-review-checklist-numerics",
        prompt=(
            "Give me a reviewer's checklist for a PR that adds numerics: both classes, tunable home, invariant home, and what the PR text carries."
        ),
        ordered_step_anchors=[
            ["tunable"],
            ["invariant"],
            ["typed config"],
            ["named constants"],
            ["classification note"],
        ],
        notes="Numerical: class defs through note.",
    ),
    ProcedureTask(
        task_id="PC-66-env-override-when-relevant",
        prompt=(
            "Not every tunable needs an environment override. When does the policy want one, and where does the tunable itself live?"
        ),
        ordered_step_anchors=[
            ["tunable"],
            ["typed config"],
            ["env override"],
        ],
        notes="Numerical: tunable, typed config, env override when operationally relevant.",
    ),
    ProcedureTask(
        task_id="PC-67-thresholds-ablation-study",
        prompt=(
            "For an ablation over three confidence thresholds I need to tidy the code. Placement, then the PR note?"
        ),
        ordered_step_anchors=[
            ["tunable"],
            ["typed config"],
            ["classification note"],
        ],
        notes="Numerical: tunable, typed config, note.",
    ),
    ProcedureTask(
        task_id="PC-68-full-numeric-audit",
        prompt=(
            "Audit a module with mixed numbers end to end: define the two classes, fix homes, remove literals, avoid a global dump, then write the PR note."
        ),
        ordered_step_anchors=[
            ["tunable"],
            ["invariant"],
            ["typed config"],
            ["env override"],
            ["named constants"],
            ["magic literals"],
            ["global file"],
            ["classification note"],
        ],
        notes="Numerical: full ordered policy.",
    ),
    ProcedureTask(
        task_id="PC-69-bugfix-plus-rename",
        prompt=(
            "My branch fixes a parser bug and also renames twelve variables for taste. How should the change be shaped?"
        ),
        ordered_step_anchors=[
            ["one concern"],
        ],
        notes="Change Style: one concern.",
    ),
    ProcedureTask(
        task_id="PC-70-helper-duplicate-check",
        prompt=(
            "I'm about to write `parse_duration()`. Before that, and then for where the file goes, what does Change Style say?"
        ),
        ordered_step_anchors=[
            ["reuse"],
            ["layout"],
        ],
        notes="Change Style: reuse then layout.",
    ),
    ProcedureTask(
        task_id="PC-71-new-module-location",
        prompt=(
            "I created `utils2.py` at the repo root for a new helper. Which Change Style rules does that break, in order?"
        ),
        ordered_step_anchors=[
            ["reuse"],
            ["layout"],
        ],
        notes="Change Style: reuse, layout.",
    ),
    ProcedureTask(
        task_id="PC-72-three-rules-pr-review",
        prompt=(
            "Review a PR that adds a feature, reformats three unrelated files, writes its own retry helper, and drops a new file in a random folder. Go rule by rule."
        ),
        ordered_step_anchors=[
            ["one concern"],
            ["reuse"],
            ["layout"],
        ],
        notes="Change Style: all three.",
    ),
    ProcedureTask(
        task_id="PC-73-split-pr-feature-and-lint",
        prompt=(
            "Lint fixes and a new endpoint are in one commit. What should I do and what comes next once I add helpers?"
        ),
        ordered_step_anchors=[
            ["one concern"],
            ["reuse"],
        ],
        notes="Change Style: scope then reuse.",
    ),
    ProcedureTask(
        task_id="PC-74-adding-new-dataset-loader",
        prompt=(
            "Adding a dataset loader: scope the change, check for existing loaders, and decide the file location."
        ),
        ordered_step_anchors=[
            ["one concern"],
            ["reuse"],
            ["layout"],
        ],
        notes="Change Style: all three.",
    ),
    ProcedureTask(
        task_id="PC-75-one-concern-only",
        prompt=(
            "What is the first rule of Change Style and how does it affect a mixed refactor-plus-feature diff?"
        ),
        ordered_step_anchors=[
            ["one concern"],
        ],
        notes="Change Style: one concern.",
    ),
    ProcedureTask(
        task_id="PC-76-reuse-then-place",
        prompt=(
            "I need a string-normalizing function and a new test fixture file. Which existing code do I look at first, and how do I decide where the fixture goes?"
        ),
        ordered_step_anchors=[
            ["reuse"],
            ["layout"],
        ],
        notes="Change Style: reuse, layout.",
    ),
    ProcedureTask(
        task_id="PC-77-flag-then-api-route",
        prompt=(
            "I'm adding a gated experiment route in the orchestrator. In order: where do I check the repository map, where does the flag go, and where does the route live?"
        ),
        ordered_step_anchors=[
            ["repository map"],
            ["src/features.py"],
            ["src/api/"],
        ],
        notes="Placement orchestrator: map, features.py, api.",
    ),
    ProcedureTask(
        task_id="PC-78-roles-and-tests",
        prompt=(
            "New role metadata plus its unit test in the orchestrator. Where does each go?"
        ),
        ordered_step_anchors=[
            ["src/roles.py"],
            ["tests/unit/"],
        ],
        notes="Placement orchestrator: roles.py, tests/unit.",
    ),
    ProcedureTask(
        task_id="PC-79-map-first-then-flag",
        prompt=(
            "Before placing a file at all, what do I consult, and where do the orchestrator feature flags live?"
        ),
        ordered_step_anchors=[
            ["repository map"],
            ["src/features.py"],
        ],
        notes="Placement: map then features.py.",
    ),
    ProcedureTask(
        task_id="PC-80-routing-metadata-update",
        prompt=(
            "A change adds a role and its routing metadata and an API service for it. Order the destinations."
        ),
        ordered_step_anchors=[
            ["src/roles.py"],
            ["src/api/"],
        ],
        notes="Placement orchestrator: roles then api.",
    ),
    ProcedureTask(
        task_id="PC-81-integration-test-placement",
        prompt=(
            "Where does an integration test for a new API endpoint go, relative to its unit test?"
        ),
        ordered_step_anchors=[
            ["src/api/"],
            ["tests/unit/"],
            ["tests/integration/"],
        ],
        notes="Placement orchestrator: api, unit, integration.",
    ),
    ProcedureTask(
        task_id="PC-82-flag-roles-api-tests",
        prompt=(
            "Feature flag, a routing entry, a state service, a unit test, an integration test: where does each of these five things go in the orchestrator, in file order?"
        ),
        ordered_step_anchors=[
            ["src/features.py"],
            ["src/roles.py"],
            ["src/api/"],
            ["tests/unit/"],
            ["tests/integration/"],
        ],
        notes="Placement orchestrator: all five.",
    ),
    ProcedureTask(
        task_id="PC-83-api-models-state",
        prompt=(
            "Add request/response models and shared state for a new route. Which directory?"
        ),
        ordered_step_anchors=[
            ["src/api/"],
        ],
        notes="Placement orchestrator: src/api.",
    ),
    ProcedureTask(
        task_id="PC-84-flag-and-integration",
        prompt=(
            "A new optional behavior needs its flag and an end-to-end integration test. Locations?"
        ),
        ordered_step_anchors=[
            ["src/features.py"],
            ["tests/integration/"],
        ],
        notes="Placement orchestrator: features.py then integration.",
    ),
    ProcedureTask(
        task_id="PC-85-roles-service-unit-tests",
        prompt=(
            "Registering a role, writing its service, then covering it with unit tests: give the directories in order."
        ),
        ordered_step_anchors=[
            ["src/roles.py"],
            ["src/api/"],
            ["tests/unit/"],
        ],
        notes="Placement orchestrator: roles, api, unit.",
    ),
    ProcedureTask(
        task_id="PC-86-map-then-api-then-integration",
        prompt=(
            "I'm placing a new API service and its integration test and I haven't looked at the repo map. What's the order?"
        ),
        ordered_step_anchors=[
            ["repository map"],
            ["src/api/"],
            ["tests/integration/"],
        ],
        notes="Placement orchestrator: map, api, integration.",
    ),
    ProcedureTask(
        task_id="PC-87-new-agent-definition",
        prompt=(
            "I'm authoring a new role definition file in epyc-root. Where does it go, and where does a policy doc shared across repos go?"
        ),
        ordered_step_anchors=[
            ["agents/"],
            ["agents/shared/"],
        ],
        notes="Placement root: agents/, agents/shared/.",
    ),
    ProcedureTask(
        task_id="PC-88-validator-and-rationale",
        prompt=(
            "A new governance validator and a design-rationale write-up in epyc-root: where does each go?"
        ),
        ordered_step_anchors=[
            ["scripts/validate/"],
            ["docs/"],
        ],
        notes="Placement root: scripts/validate, docs.",
    ),
    ProcedureTask(
        task_id="PC-89-agent-policy-validator",
        prompt=(
            "Agent definition, a cross-repo policy, and a validator for it. List directories in order."
        ),
        ordered_step_anchors=[
            ["agents/"],
            ["agents/shared/"],
            ["scripts/validate/"],
        ],
        notes="Placement root: agents, shared, validate.",
    ),
    ProcedureTask(
        task_id="PC-90-all-four-root",
        prompt=(
            "Place these four artifacts in epyc-root in file order: an agent definition, a cross-repo rule, a lint script for governance, and an architecture note."
        ),
        ordered_step_anchors=[
            ["agents/"],
            ["agents/shared/"],
            ["scripts/validate/"],
            ["docs/"],
        ],
        notes="Placement root: all four.",
    ),
    ProcedureTask(
        task_id="PC-91-shared-policy-docs",
        prompt=(
            "Cross-repo policy plus the design explanation for why it exists. Where do both go?"
        ),
        ordered_step_anchors=[
            ["agents/shared/"],
            ["docs/"],
        ],
        notes="Placement root: shared then docs.",
    ),
    ProcedureTask(
        task_id="PC-92-agent-def-and-docs",
        prompt=(
            "Where does a new agent overlay go and where does its architecture rationale go?"
        ),
        ordered_step_anchors=[
            ["agents/"],
            ["docs/"],
        ],
        notes="Placement root: agents then docs.",
    ),
    ProcedureTask(
        task_id="PC-93-validation-script-first",
        prompt=(
            "Governance validation script, then its architecture rationale. Directories?"
        ),
        ordered_step_anchors=[
            ["scripts/validate/"],
            ["docs/"],
        ],
        notes="Placement root: validate then docs.",
    ),
    ProcedureTask(
        task_id="PC-94-map-then-shared",
        prompt=(
            "What's the first thing to consult before placing a cross-repo policy, and what directory does the policy go into?"
        ),
        ordered_step_anchors=[
            ["repository map"],
            ["agents/shared/"],
        ],
        notes="Placement: map then shared.",
    ),
    ProcedureTask(
        task_id="PC-95-flag-and-validator-cross-repo",
        prompt=(
            "A flag in the orchestrator and a validator in epyc-root that checks it exist in the same task. Which paths, orchestrator first?"
        ),
        ordered_step_anchors=[
            ["src/features.py"],
            ["scripts/validate/"],
        ],
        notes="Placement: orchestrator then root.",
    ),
    ProcedureTask(
        task_id="PC-96-api-route-and-agent-def",
        prompt=(
            "New route in the orchestrator and a matching agent definition in epyc-root: directories in order."
        ),
        ordered_step_anchors=[
            ["src/api/"],
            ["agents/"],
        ],
        notes="Placement: orchestrator then root.",
    ),
    ProcedureTask(
        task_id="PC-97-prod-patch-request",
        prompt=(
            "Someone asks me to patch a bug directly in the production llama.cpp tree. What does the kernel workflow say about the tree, what is required, and where does the work happen?"
        ),
        ordered_step_anchors=[
            ["frozen"],
            ["authorization"],
            ["llama.cpp-experimental"],
        ],
        notes="Kernel: frozen, authorization, experimental.",
    ),
    ProcedureTask(
        task_id="PC-98-new-quant-kernel",
        prompt=(
            "I've written a faster dequant kernel. Take me from the state of production to how it ships."
        ),
        ordered_step_anchors=[
            ["frozen"],
            ["llama.cpp-experimental"],
            ["versioning past", "version past"],
        ],
        notes="Kernel: frozen, experimental, version past.",
    ),
    ProcedureTask(
        task_id="PC-99-rebase-prod-branch",
        prompt=(
            "I want to rebase the production branch onto upstream. Is that allowed, and what is the alternative?"
        ),
        ordered_step_anchors=[
            ["frozen"],
            ["rebase"],
            ["authorization"],
            ["llama.cpp-experimental"],
            ["versioning past", "version past"],
        ],
        notes="Kernel: frozen, rebase, authorization, experimental, versioning.",
    ),
    ProcedureTask(
        task_id="PC-100-modify-build-commit",
        prompt=(
            "Which three actions on production kernels need explicit authorization, and what do I do instead?"
        ),
        ordered_step_anchors=[
            ["frozen"],
            ["modify"],
            ["rebase"],
            ["authorization"],
            ["llama.cpp-experimental"],
        ],
        notes="Kernel: modify, rebase, authorization, experimental.",
    ),
    ProcedureTask(
        task_id="PC-101-where-is-the-motivation",
        prompt=(
            "Where is the full kernel workflow and its motivating failure documented, and what is the shipping rule?"
        ),
        ordered_step_anchors=[
            ["llama.cpp-experimental"],
            ["versioning past", "version past"],
            ["CLAUDE.md"],
        ],
        notes="Kernel: experimental, version past, CLAUDE.md.",
    ),
    ProcedureTask(
        task_id="PC-102-hip-graph-experiment",
        prompt=(
            "A HIP-graph capture experiment needs a new branch. Which branch convention, and how does it eventually reach production?"
        ),
        ordered_step_anchors=[
            ["llama.cpp-experimental"],
            ["versioning past", "version past"],
        ],
        notes="Kernel: experimental then version past.",
    ),
    ProcedureTask(
        task_id="PC-103-authorization-boundary",
        prompt=(
            "The user told me earlier to be quick, then asked for a prod-tree commit. Does that satisfy the authorization rule? Give the sequence of rules."
        ),
        ordered_step_anchors=[
            ["frozen"],
            ["authorization"],
            ["llama.cpp-experimental"],
        ],
        notes="Kernel: frozen, authorization, experimental.",
    ),
    ProcedureTask(
        task_id="PC-104-full-sequence-pointer",
        prompt=(
            "Give the entire kernel-workflow chain from the freeze through where I can read the canonical text."
        ),
        ordered_step_anchors=[
            ["frozen"],
            ["modify"],
            ["authorization"],
            ["llama.cpp-experimental"],
            ["versioning past", "version past"],
            ["CLAUDE.md"],
        ],
        notes="Kernel: all in order.",
    ),
    ProcedureTask(
        task_id="PC-105-benchmark-sweep-design",
        prompt=(
            "Design a throughput benchmark script that runs 200 prompts. Order the persistence rules: the mandate, writing results, checkpoint format, and the summary's role."
        ),
        ordered_step_anchors=[
            ["persist"],
            ["append"],
            ["jsonl"],
            ["checkpoint"],
            ["aggregation"],
        ],
        notes="Persistence: mandate, append, JSONL, checkpoint, aggregation.",
    ),
    ProcedureTask(
        task_id="PC-106-batch-at-end-fix",
        prompt=(
            "My script collects results in a list and dumps at the end. What is wrong, and what do I change first?"
        ),
        ordered_step_anchors=[
            ["immediately"],
            ["batch"],
        ],
        notes="Persistence: immediately, not batch.",
    ),
    ProcedureTask(
        task_id="PC-107-crash-leaves-partials",
        prompt=(
            "The node rebooted mid-run. What is the final summary relative to the checkpoint, and what must a crashed run still have left on disk?"
        ),
        ordered_step_anchors=[
            ["aggregation"],
            ["partial"],
        ],
        notes="Persistence: summary is an aggregation; crash leaves partial results.",
    ),
    ProcedureTask(
        task_id="PC-108-progress-logging-line",
        prompt=(
            "What per-item log line does the policy ask for in eval scripts?"
        ),
        ordered_step_anchors=[
            ["log.info"],
        ],
        notes="Persistence: log.info progress.",
    ),
    ProcedureTask(
        task_id="PC-109-anti-pattern-walkthrough",
        prompt=(
            "Walk me through the anti-pattern and why the required pattern fixes it, in the order they appear."
        ),
        ordered_step_anchors=[
            ["anti-pattern"],
            ["results.append"],
            ["json.dump"],
            ["required pattern"],
        ],
        notes="Persistence: anti-pattern then required.",
    ),
    ProcedureTask(
        task_id="PC-110-required-pattern-body",
        prompt=(
            "Write out the required pattern's per-item steps: open, work, write, flush, log."
        ),
        ordered_step_anchors=[
            ["open(checkpoint"],
            ["ckpt.write"],
            ["ckpt.flush"],
            ["log.info"],
        ],
        notes="Persistence: open, write, flush, log.",
    ),
    ProcedureTask(
        task_id="PC-111-seeding-script-bullets",
        prompt=(
            "A seeding script talks to the model 1000 times. List all four persistence bullets in order."
        ),
        ordered_step_anchors=[
            ["append"],
            ["checkpoint"],
            ["aggregation"],
            ["partial"],
            ["log.info"],
        ],
        notes="Persistence: four bullets.",
    ),
    ProcedureTask(
        task_id="PC-112-csv-vs-jsonl",
        prompt=(
            "Can I use CSV instead of JSONL for the checkpoint? And when exactly do I write each row?"
        ),
        ordered_step_anchors=[
            ["append"],
            ["jsonl"],
            ["checkpoint"],
            ["immediately"],
        ],
        notes="Persistence: append, JSONL/CSV, checkpoint, immediately.",
    ),
    ProcedureTask(
        task_id="PC-113-summary-is-derivative",
        prompt=(
            "The final summary JSON is the thing dashboards read. What does the policy say about it?"
        ),
        ordered_step_anchors=[
            ["checkpoint"],
            ["aggregation"],
        ],
        notes="Persistence: summary is aggregation of checkpoint.",
    ),
    ProcedureTask(
        task_id="PC-114-kill-safe-eval-order",
        prompt=(
            "A long eval gets SIGTERM at item 47. Which persistence behaviors make it safe, in order?"
        ),
        ordered_step_anchors=[
            ["immediately"],
            ["partial"],
            ["log.info"],
        ],
        notes="Persistence: immediately, partial, log.",
    ),
    ProcedureTask(
        task_id="PC-115-flush-per-item",
        prompt=(
            "After writing a record to the checkpoint, what call comes next, and then what log?"
        ),
        ordered_step_anchors=[
            ["ckpt.write"],
            ["ckpt.flush"],
            ["log.info"],
        ],
        notes="Persistence: write, flush, log.",
    ),
    ProcedureTask(
        task_id="PC-116-benchmark-mandate-scope",
        prompt=(
            "Does the persistence mandate apply to a one-off llama-bench wrapper? Cite the rule's scope and the first requirement."
        ),
        ordered_step_anchors=[
            ["persist"],
            ["append"],
        ],
        notes="Persistence: persist, append.",
    ),
    ProcedureTask(
        task_id="PC-117-progress-visible",
        prompt=(
            "Operators can't see how far my seeding run got. Which rule fixes this, and where in the loop does it go relative to flush?"
        ),
        ordered_step_anchors=[
            ["ckpt.flush"],
            ["log.info"],
        ],
        notes="Persistence: flush then log.info.",
    ),
    ProcedureTask(
        task_id="PC-118-anti-pattern-appending-list",
        prompt=(
            "Explain what `results.append(evaluate(item))` loses and what the final dump does."
        ),
        ordered_step_anchors=[
            ["anti-pattern"],
            ["results.append"],
            ["json.dump"],
        ],
        notes="Persistence: anti-pattern.",
    ),
    ProcedureTask(
        task_id="PC-119-checkpoint-open-mode",
        prompt=(
            "How should the checkpoint be opened and what is written inside the loop, in order?"
        ),
        ordered_step_anchors=[
            ["required pattern"],
            ["open(checkpoint"],
            ["ckpt.write"],
        ],
        notes="Persistence: required pattern, open, write.",
    ),
    ProcedureTask(
        task_id="PC-120-score-then-append",
        prompt=(
            "When exactly is a result appended: before scoring, after scoring, or at the end? And then what?"
        ),
        ordered_step_anchors=[
            ["append"],
            ["immediately"],
            ["batch"],
            ["aggregation"],
        ],
        notes="Persistence: append, immediately, not batch, aggregation.",
    ),
    ProcedureTask(
        task_id="PC-121-full-persistence-walkthrough",
        prompt=(
            "Take a new eval harness from mandate to the final per-item log line: all bullets, then both patterns."
        ),
        ordered_step_anchors=[
            ["persist"],
            ["append"],
            ["checkpoint"],
            ["aggregation"],
            ["partial"],
            ["log.info"],
            ["anti-pattern"],
            ["required pattern"],
            ["ckpt.write"],
            ["ckpt.flush"],
        ],
        notes="Persistence: full ordered.",
    ),
    ProcedureTask(
        task_id="PC-122-jsonl-checkpoint-partials",
        prompt=(
            "Where does usable partial data live after a crash and what format is it?"
        ),
        ordered_step_anchors=[
            ["append"],
            ["jsonl"],
            ["partial"],
        ],
        notes="Persistence: append, JSONL, partial.",
    ),
    ProcedureTask(
        task_id="PC-123-add-new-model-entry",
        prompt=(
            "I'm adding an entry for a new model to the registry. Where is the canonical spec, and which repo owns it?"
        ),
        ordered_step_anchors=[
            ["model registry standards"],
            ["epyc-inference-research"],
            ["registry_standards.md"],
        ],
        notes="Registry: section, repo, spec file.",
    ),
    ProcedureTask(
        task_id="PC-124-scoring-field-format",
        prompt=(
            "What's the scoring-field format for registry entries, and where is it defined?"
        ),
        ordered_step_anchors=[
            ["model registry standards"],
            ["registry_standards.md"],
        ],
        notes="Registry: standards then spec file.",
    ),
    ProcedureTask(
        task_id="PC-125-registry-spec-owner",
        prompt=(
            "Is the registry format spec cross-repo engineering policy? Which repo has it?"
        ),
        ordered_step_anchors=[
            ["model registry standards"],
            ["epyc-inference-research"],
        ],
        notes="Registry: epyc-inference-research.",
    ),
    ProcedureTask(
        task_id="PC-126-registry-entry-requirements",
        prompt=(
            "I need to know the entry requirements for a registry row. Which document do I open?"
        ),
        ordered_step_anchors=[
            ["epyc-inference-research"],
            ["registry_standards.md"],
        ],
        notes="Registry: repo then file.",
    ),
    ProcedureTask(
        task_id="PC-127-garbled-output-first-move",
        prompt=(
            "A model returns garbled output on the real path and nobody knows why. What is the first move, and how should my guess be labeled?"
        ),
        ordered_step_anchors=[
            ["observe before diagnosing"],
            ["hypothesis"],
        ],
        notes="Debug: observe, hypothesis.",
    ),
    ProcedureTask(
        task_id="PC-128-root-cause-in-handoff",
        prompt=(
            "I want to write 'KV cache corruption' as the cause in the handoff but haven't confirmed. What rules apply?"
        ),
        ordered_step_anchors=[
            ["observe before diagnosing"],
            ["hypothesis"],
            ["finding"],
        ],
        notes="Debug: observe, hypothesis, finding.",
    ),
    ProcedureTask(
        task_id="PC-129-blind-spot-claim",
        prompt=(
            "Logs show nothing. Before I say the failure is not observable, what must I do?"
        ),
        ordered_step_anchors=[
            ["not observable"],
            ["enumerate"],
        ],
        notes="Debug: not observable, enumerate.",
    ),
    ProcedureTask(
        task_id="PC-130-second-patch-temptation",
        prompt=(
            "My fix for a hang didn't work, and I have a second idea. What now?"
        ),
        ordered_step_anchors=[
            ["cap blind fixes at one"],
            ["observability"],
        ],
        notes="Debug: cap blind fixes, observability.",
    ),
    ProcedureTask(
        task_id="PC-131-full-debug-order",
        prompt=(
            "Give the full opaque-failure procedure in file order: evidence, label the guess, blind-spot claims, the fix cap, the narrative caveat."
        ),
        ordered_step_anchors=[
            ["observe before diagnosing"],
            ["hypothesis"],
            ["not observable"],
            ["cap blind fixes at one"],
            ["coherent failure narrative"],
        ],
        notes="Debug: five bullets.",
    ),
    ProcedureTask(
        task_id="PC-132-tidy-story-warning",
        prompt=(
            "My incident write-up reads very coherently and I'm confident. What does the discipline say about that?"
        ),
        ordered_step_anchors=[
            ["coherent failure narrative"],
            ["yellow flag"],
        ],
        notes="Debug: coherent narrative, yellow flag.",
    ),
    ProcedureTask(
        task_id="PC-133-trace-flag",
        prompt=(
            "What is the cheapest debug move for opaque inference failures?"
        ),
        ordered_step_anchors=[
            ["not observable"],
            ["enumerate"],
        ],
        notes="Debug: not observable requires, enumerate.",
    ),
    ProcedureTask(
        task_id="PC-134-hypothesis-propagation",
        prompt=(
            "Can I put an unverified mechanism in the progress log? Under what label and what must never happen?"
        ),
        ordered_step_anchors=[
            ["observe before diagnosing"],
            ["hypothesis"],
            ["finding"],
        ],
        notes="Debug: label hypothesis, never as finding.",
    ),
    ProcedureTask(
        task_id="PC-135-hostquiet-cost",
        prompt=(
            "Each patch on inference-gated work costs a host-quiet window. How does that shape the sequence after a failed fix?"
        ),
        ordered_step_anchors=[
            ["cap blind fixes at one"],
            ["observability"],
            ["coherent failure narrative"],
        ],
        notes="Debug: cap blind fixes, observability, coherence.",
    ),
    ProcedureTask(
        task_id="PC-136-enumerate-artifacts",
        prompt=(
            "What artifacts do I look for with find/ls before calling something unobservable, and what follows if a hypothesis-driven fix then fails?"
        ),
        ordered_step_anchors=[
            ["not observable"],
            ["enumerate"],
            ["cap blind fixes at one"],
            ["observability"],
        ],
        notes="Debug: not observable, enumerate, cap, observability.",
    ),
    ProcedureTask(
        task_id="PC-137-observe-then-cap",
        prompt=(
            "Order: capture primitive datum, then what after one failed patch?"
        ),
        ordered_step_anchors=[
            ["observe before diagnosing"],
            ["cap blind fixes at one"],
            ["observability"],
        ],
        notes="Debug: observe, cap, observability.",
    ),
    ProcedureTask(
        task_id="PC-138-narrative-after-fix",
        prompt=(
            "After my second theory also failed, the story hangs together nicely. Which warnings apply, in order?"
        ),
        ordered_step_anchors=[
            ["cap blind fixes at one"],
            ["observability"],
            ["coherent failure narrative"],
            ["yellow flag"],
        ],
        notes="Debug: cap, observability, coherence, yellow flag.",
    ),
    ProcedureTask(
        task_id="PC-139-syntax-first",
        prompt=(
            "What's the very first check before finalizing modified Python, and the next one?"
        ),
        ordered_step_anchors=[
            ["syntax"],
            ["targeted tests"],
        ],
        notes="Verify: syntax then targeted tests.",
    ),
    ProcedureTask(
        task_id="PC-140-flag-then-docs",
        prompt=(
            "My change adds a flag and alters an interface. After tests, which two steps?"
        ),
        ordered_step_anchors=[
            ["targeted tests"],
            ["feature-flag behavior"],
            ["update docs"],
        ],
        notes="Verify: tests, flag behavior, docs.",
    ),
    ProcedureTask(
        task_id="PC-141-renamed-public-api",
        prompt=(
            "I renamed a public method. Order the verification steps through to docs."
        ),
        ordered_step_anchors=[
            ["syntax"],
            ["targeted tests"],
            ["update docs"],
        ],
        notes="Verify: syntax, tests, docs.",
    ),
    ProcedureTask(
        task_id="PC-142-full-five-steps",
        prompt=(
            "List the five steps of the verification minimum in order, finishing with the real-path check."
        ),
        ordered_step_anchors=[
            ["syntax"],
            ["targeted tests"],
            ["feature-flag behavior"],
            ["update docs"],
            ["real path"],
        ],
        notes="Verify: five.",
    ),
    ProcedureTask(
        task_id="PC-143-stub-passes-claim",
        prompt=(
            "My stubbed REPL test passes. Which step says that's not enough, and what do I run?"
        ),
        ordered_step_anchors=[
            ["real path"],
            ["proxy"],
            ["canary"],
        ],
        notes="Verify: real path, proxy, canary.",
    ),
    ProcedureTask(
        task_id="PC-144-dry-run-ready",
        prompt=(
            "A dry-run says the service is ready. What must I do before saying 'validated'?"
        ),
        ordered_step_anchors=[
            ["proxy"],
            ["canary"],
        ],
        notes="Verify: proxy, canary.",
    ),
    ProcedureTask(
        task_id="PC-145-gated-feature-verification",
        prompt=(
            "A gated feature is merged. Verification order: syntax, tests, what about the flag, and finally?"
        ),
        ordered_step_anchors=[
            ["syntax"],
            ["targeted tests"],
            ["feature-flag behavior"],
            ["real path"],
        ],
        notes="Verify: syntax, tests, flag, real path.",
    ),
    ProcedureTask(
        task_id="PC-146-docs-after-flag",
        prompt=(
            "Which verification step covers the flag and which follows it?"
        ),
        ordered_step_anchors=[
            ["feature-flag behavior"],
            ["update docs"],
        ],
        notes="Verify: flag, docs.",
    ),
    ProcedureTask(
        task_id="PC-147-pre-merge-script-change",
        prompt=(
            "I only touched one Python script. Give the first two required checks and the final canary requirement."
        ),
        ordered_step_anchors=[
            ["syntax"],
            ["targeted tests"],
            ["canary"],
        ],
        notes="Verify: syntax, tests, canary.",
    ),
    ProcedureTask(
        task_id="PC-148-infra-ready-declaration",
        prompt=(
            "Before declaring REPL infrastructure ready: what are the tests step and the real-path step, in order?"
        ),
        ordered_step_anchors=[
            ["targeted tests"],
            ["real path"],
            ["canary"],
        ],
        notes="Verify: tests then real path then canary.",
    ),
    ProcedureTask(
        task_id="PC-149-interface-change-docs",
        prompt=(
            "An interface changed. When do docs get updated relative to the tests, and what is last?"
        ),
        ordered_step_anchors=[
            ["targeted tests"],
            ["update docs"],
            ["real path"],
        ],
        notes="Verify: tests, docs, real path.",
    ),
    ProcedureTask(
        task_id="PC-150-four-before-canary",
        prompt=(
            "Steps 1 through 4, then the canary: write the sequence for a change adding an optional parameter."
        ),
        ordered_step_anchors=[
            ["syntax"],
            ["targeted tests"],
            ["feature-flag behavior"],
            ["update docs"],
            ["canary"],
        ],
        notes="Verify: 1-4 then canary.",
    ),
    ProcedureTask(
        task_id="PC-151-proxy-trap",
        prompt=(
            "Explain why a mock that bypasses IO proves nothing and what to run instead, after the standard four checks."
        ),
        ordered_step_anchors=[
            ["update docs"],
            ["real path"],
            ["proxy"],
            ["canary"],
        ],
        notes="Verify: docs, real path, proxy, canary.",
    ),
    ProcedureTask(
        task_id="PC-152-syntax-and-flag",
        prompt=(
            "Steps one and three of the verification minimum for a modified Python file with a new flag?"
        ),
        ordered_step_anchors=[
            ["syntax"],
            ["feature-flag behavior"],
        ],
        notes="Verify: syntax, flag behavior.",
    ),
    ProcedureTask(
        task_id="PC-153-tests-docs-real",
        prompt=(
            "After syntax, I plan tests, docs, and the real-path validation. Is that the right order?"
        ),
        ordered_step_anchors=[
            ["syntax"],
            ["targeted tests"],
            ["update docs"],
            ["real path"],
        ],
        notes="Verify: syntax, tests, docs, real path.",
    ),
]


def all_tasks() -> list[ProcedureTask]:
    return list(TASKS)
