"""Instruction-recall tasks for agent-file compliance.

Each task: a direct question about a specific clause in the agent file.
Pass criterion: model output contains a quoted-or-paraphrased correct
clause (case-insensitive substring of `acceptable_answers`).

Recall is the weakest of the three compliance signals — a model can
"remember" content from training even if the specific compressed file is
not informative. Pair with FA + PC tasks for full triangulation.

Suite v2 (2026-07-30, AFC-P5.E1/E2): the five registry-format tasks
(IR-06/08/09/10/13) were REMOVED — Model Registry Standards moved out of
ENGINEERING_STANDARDS to the research repo on 2026-07-30. Pool expanded
15 → 30 against the post-restructure source; every task keeps ≥1 anchor
present verbatim in the source AND all three compressed variants.
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
        acceptable_answers=["runtime behavior controls", "stable semantic limits", "stable limits", "runtime controls"],
    ),
    RecallTask(
        task_id="IR-03-numeric-globalfile",
        prompt="What does the engineering standards say about consolidating numeric constants into one file?",
        acceptable_answers=["Do not consolidate", "subsystem ownership", "subsystems own"],
    ),
    RecallTask(
        task_id="IR-04-pr-classification-note",
        prompt="What note must a PR include when adding numeric values?",
        acceptable_answers=["classification note", "tunable", "invariant"],
    ),
    RecallTask(
        task_id="IR-05-multi-repo-routing",
        prompt="Which repo holds feature flags, API routes, and their tests per the placement rules?",
        acceptable_answers=["epyc-orchestrator"],
    ),
    RecallTask(
        task_id="IR-07-eval-incremental",
        prompt="What's the policy for inference scripts (benchmarks, evals, seeding)?",
        acceptable_answers=["MUST persist", "incrementally", "JSONL", "checkpoint"],
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
        task_id="IR-14-feature-flag-policy",
        prompt="When should a new feature have a feature flag?",
        acceptable_answers=["optional", "gate optional features", "Gate optional features"],
    ),
    RecallTask(
        task_id="IR-15-incremental-anti-pattern",
        prompt="Why is collecting all results into a list and writing at the end an anti-pattern?",
        acceptable_answers=["killed", "lost", "partial results", "partials"],
    ),
    # ─── v2 expansion (2026-07-30) ────────────────────────────────────────────
    RecallTask(
        task_id="IR-16-kernel-frozen",
        prompt="What does the standards file say about production kernels?",
        acceptable_answers=["frozen", "do not modify, rebase, build, or commit"],
    ),
    RecallTask(
        task_id="IR-17-kernel-branch",
        prompt="Where does kernel work happen, per the standards?",
        acceptable_answers=["llama.cpp-experimental"],
    ),
    RecallTask(
        task_id="IR-18-versioning-strategy",
        prompt="How do kernel changes reach production, per the standards?",
        acceptable_answers=["versioning past production", "version past production", "versioning past"],
    ),
    RecallTask(
        task_id="IR-19-registry-spec-location",
        prompt="Where does the model-registry format spec live now?",
        acceptable_answers=["REGISTRY_STANDARDS.md"],
    ),
    RecallTask(
        task_id="IR-20-debug-first-rule",
        prompt="What's the first debugging rule when a real-path failure is opaque?",
        acceptable_answers=["Observe before diagnosing", "observe before diagnosing"],
    ),
    RecallTask(
        task_id="IR-21-blind-fix-cap",
        prompt="How many blind fixes are allowed before you must switch to observability?",
        acceptable_answers=["Cap blind fixes at one", "blind fixes at one"],
    ),
    RecallTask(
        task_id="IR-22-coherent-narrative",
        prompt="Is a coherent failure narrative sufficient evidence to close an investigation?",
        acceptable_answers=["yellow flag", "not evidence", "not reassurance"],
    ),
    RecallTask(
        task_id="IR-23-canary",
        prompt="What must you do before declaring infrastructure 'validated'?",
        acceptable_answers=["real path", "canary", "end-to-end"],
    ),
    RecallTask(
        task_id="IR-24-change-scope",
        prompt="How should each change be scoped?",
        acceptable_answers=["one concern"],
    ),
    RecallTask(
        task_id="IR-25-helper-reuse",
        prompt="Before writing a new helper, what does the file require you to do?",
        acceptable_answers=["Reuse"],
    ),
    RecallTask(
        task_id="IR-26-flag-location",
        prompt="Exactly where do feature flags live in the orchestrator repo?",
        acceptable_answers=["src/features.py"],
    ),
    RecallTask(
        task_id="IR-27-tests-location",
        prompt="Where do tests live in epyc-orchestrator?",
        acceptable_answers=["tests/unit", "tests/integration"],
    ),
    RecallTask(
        task_id="IR-28-agents-shared-purpose",
        prompt="What belongs in agents/shared/ per the placement rules?",
        acceptable_answers=["Cross-repo policy", "cross-repo policy"],
    ),
    RecallTask(
        task_id="IR-29-validation-location",
        prompt="Where does governance validation code live in epyc-root?",
        acceptable_answers=["scripts/validate"],
    ),
    RecallTask(
        task_id="IR-30-summary-role",
        prompt="What role does the final summary output play relative to the checkpoint file?",
        acceptable_answers=["aggregation"],
    ),
    RecallTask(
        task_id="IR-31-progress-log-format",
        prompt="What per-item progress-logging pattern does the file require for eval scripts?",
        acceptable_answers=["[%d/%d]", "log.info"],
    ),
    RecallTask(
        task_id="IR-32-killed-run",
        prompt="What must a killed or crashed eval run leave behind?",
        acceptable_answers=["partial results", "partials on disk", "usable partial"],
    ),
    RecallTask(
        task_id="IR-33-typed-config-home",
        prompt="Where must tunable values live?",
        acceptable_answers=["typed config", "dataclass"],
    ),
    RecallTask(
        task_id="IR-34-docs-update-trigger",
        prompt="When must docs be updated, per Verification Minimum?",
        acceptable_answers=["interfaces change", "interface change"],
    ),
    RecallTask(
        task_id="IR-35-repo-map-first",
        prompt="What should you consult before placing a new file in the multi-repo project?",
        acceptable_answers=["repository map"],
    ),
]


def all_tasks() -> list[RecallTask]:
    return list(TASKS)
