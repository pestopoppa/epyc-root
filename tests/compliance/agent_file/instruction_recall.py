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

Suite v3 (2026-11-10): pool expanded 30 -> 150 (IR-36..IR-155, 120 new tasks,
~5 per ENGINEERING_STANDARDS directive across 24 directive groups). The
existing 30 are unchanged. Every new task has >=1 anchor present verbatim
(case-insensitive) in the source AND all three compressed variants.
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
    # ─── v3 expansion (2026-11-10): +120 tasks, ~5 per directive ─────────────────
    # v3 group: typed-enums
    RecallTask(
        task_id="IR-36-boundary-type",
        prompt='How should data that crosses a system boundary from an external source be handled according to the standards?',
        acceptable_answers=['typed boundaries'],
    ),
    RecallTask(
        task_id="IR-37-boundary-scope",
        prompt="Which kind of data does the 'typed boundaries' rule apply to?",
        acceptable_answers=['external data'],
    ),
    RecallTask(
        task_id="IR-38-enum-vs-string",
        prompt="A colleague compares a status against the literal string 'done' in six places. What do the standards want instead?",
        acceptable_answers=['enums'],
    ),
    RecallTask(
        task_id="IR-39-adhoc-strings",
        prompt='What does the file say about ad hoc strings?',
        acceptable_answers=['ad hoc strings'],
    ),
    RecallTask(
        task_id="IR-40-constants-use",
        prompt='Besides enums, what else should replace repeated literal strings per the Code Invariants section?',
        acceptable_answers=['constants'],
    ),
    # v3 group: flags
    RecallTask(
        task_id="IR-41-flag-gate-what",
        prompt='What kind of functionality must be gated behind a feature flag?',
        acceptable_answers=['optional features'],
    ),
    RecallTask(
        task_id="IR-42-flag-gate-where",
        prompt='In which layer should a feature flag be defined for a given repo?',
        acceptable_answers=['feature flags'],
    ),
    RecallTask(
        task_id="IR-43-flag-file-orch",
        prompt='A developer adds a toggle for an experimental orchestrator feature. Which file should declare it?',
        acceptable_answers=['src/features.py'],
    ),
    RecallTask(
        task_id="IR-44-flag-verify-step",
        prompt='Which Verification Minimum step concerns feature flags?',
        acceptable_answers=['feature-flag behavior'],
    ),
    RecallTask(
        task_id="IR-45-flag-unconditional",
        prompt='Is it acceptable to ship an optional feature always-on with no switch? What do the invariants require?',
        acceptable_answers=['feature flags', 'gate'],
    ),
    # v3 group: exceptions
    RecallTask(
        task_id="IR-46-exc-forbidden-idiom",
        prompt='Which exact exception-handling idiom is explicitly forbidden?',
        acceptable_answers=['except: pass'],
    ),
    RecallTask(
        task_id="IR-47-exc-log-what",
        prompt='When you catch an exception, what must accompany the log message?',
        acceptable_answers=['with context'],
    ),
    RecallTask(
        task_id="IR-48-exc-swallow-review",
        prompt='In code review you see a bare except that discards the error. Which Code Invariants bullet does it violate?',
        acceptable_answers=['silent'],
    ),
    RecallTask(
        task_id="IR-49-exc-log-verb",
        prompt='What should you do with exceptions you handle, instead of swallowing them?',
        acceptable_answers=['log exceptions'],
    ),
    RecallTask(
        task_id="IR-50-exc-debug-impact",
        prompt='Why might silent exception handling hurt the debugging approach described elsewhere in the file?',
        acceptable_answers=['silent', 'context'],
    ),
    # v3 group: threads
    RecallTask(
        task_id="IR-51-thr-what",
        prompt='What kind of state requires thread-safe update paths?',
        acceptable_answers=['shared mutable'],
    ),
    RecallTask(
        task_id="IR-52-thr-adj",
        prompt='Which adjective describes the update paths required for shared mutable state?',
        acceptable_answers=['thread-safe'],
    ),
    RecallTask(
        task_id="IR-53-thr-counter",
        prompt='Two worker threads increment a module-level counter. Which standard applies?',
        acceptable_answers=['thread-safe'],
    ),
    RecallTask(
        task_id="IR-54-thr-cache",
        prompt='A global dict cache is written by request handlers concurrently. What does the Code Invariants section require?',
        acceptable_answers=['shared mutable'],
    ),
    RecallTask(
        task_id="IR-55-thr-section",
        prompt='Under which section heading does the thread-safety rule appear?',
        acceptable_answers=['Code Invariants'],
    ),
    # v3 group: tunable
    RecallTask(
        task_id="IR-56-tun-home",
        prompt='Where must `tunable` numeric values live?',
        acceptable_answers=['typed config'],
    ),
    RecallTask(
        task_id="IR-57-tun-dataclass",
        prompt='Name the Python construct, besides generic typed config, that holds tunable values.',
        acceptable_answers=['dataclass'],
    ),
    RecallTask(
        task_id="IR-58-tun-env",
        prompt='What override mechanism may tunables have when operationally relevant?',
        acceptable_answers=['env override'],
    ),
    RecallTask(
        task_id="IR-59-tun-batchsize",
        prompt='You add a new timeout that operators will tune during evaluation. How is it classified and where does it go?',
        acceptable_answers=['tunable', 'typed config'],
    ),
    RecallTask(
        task_id="IR-60-tun-meaning",
        prompt='Describe in a phrase what kind of numbers count as tunable.',
        acceptable_answers=['runtime'],
    ),
    # v3 group: invariant
    RecallTask(
        task_id="IR-61-inv-form",
        prompt='In what form must `invariant` values be written?',
        acceptable_answers=['named constants'],
    ),
    RecallTask(
        task_id="IR-62-inv-forbidden",
        prompt='What must invariant values never be written as?',
        acceptable_answers=['magic literals'],
    ),
    RecallTask(
        task_id="IR-63-inv-def",
        prompt='Which kind of numbers does the file classify as invariant?',
        acceptable_answers=['stable'],
    ),
    RecallTask(
        task_id="IR-64-inv-scope",
        prompt='May a named invariant constant be subsystem-local, or must it be global?',
        acceptable_answers=['named constants'],
    ),
    RecallTask(
        task_id="IR-65-inv-example",
        prompt='A 4096-byte protocol header limit appears as a bare number in three files. What do the standards require?',
        acceptable_answers=['named constants', 'magic literals'],
    ),
    # v3 group: global-file
    RecallTask(
        task_id="IR-66-glob-forbid",
        prompt='Does the numerical policy permit a single central file for all numbers?',
        acceptable_answers=['global file'],
    ),
    RecallTask(
        task_id="IR-67-glob-owner",
        prompt='Who owns tunables under the policy, the whole project or each subsystem?',
        acceptable_answers=['subsystem'],
    ),
    RecallTask(
        task_id="IR-68-glob-verb",
        prompt='What are you told NOT to do with numeric values, regarding a single file?',
        acceptable_answers=['do not consolidate'],
    ),
    RecallTask(
        task_id="IR-69-glob-plan",
        prompt='Someone proposes a constants.py with every threshold in the repo. Respond per the standards.',
        acceptable_answers=['global file', 'tunables'],
    ),
    RecallTask(
        task_id="IR-70-glob-which",
        prompt="Which category of numbers is the 'don't consolidate' rule specifically protecting?",
        acceptable_answers=['tunables'],
    ),
    # v3 group: pr-note
    RecallTask(
        task_id="IR-71-pr-what",
        prompt='What must PRs that add numerics include?',
        acceptable_answers=['classification note'],
    ),
    RecallTask(
        task_id="IR-72-pr-size",
        prompt='How is the PR classification note described in terms of length?',
        acceptable_answers=['classification note'],
    ),
    RecallTask(
        task_id="IR-73-pr-values",
        prompt='What two labels can the PR classification note choose between?',
        acceptable_answers=['tunable', 'invariant'],
    ),
    RecallTask(
        task_id="IR-74-pr-trigger",
        prompt='Which kind of PR triggers the classification-note requirement?',
        acceptable_answers=['PRs adding numerics'],
    ),
    RecallTask(
        task_id="IR-75-pr-twoclasses",
        prompt='Numeric values fall into how many classes under the Numerical Parameter Policy?',
        acceptable_answers=['two classes'],
    ),
    # v3 group: one-concern
    RecallTask(
        task_id="IR-76-con-scope",
        prompt='How should each change be scoped?',
        acceptable_answers=['one concern'],
    ),
    RecallTask(
        task_id="IR-77-con-refactor",
        prompt='A PR fixes a bug and also reformats unrelated modules. Which Change Style rule is violated?',
        acceptable_answers=['one concern'],
    ),
    RecallTask(
        task_id="IR-78-con-section",
        prompt='Under which heading does the scoping rule appear?',
        acceptable_answers=['Change Style'],
    ),
    RecallTask(
        task_id="IR-79-con-count",
        prompt='How many concerns may a single change address?',
        acceptable_answers=['one concern'],
    ),
    RecallTask(
        task_id="IR-80-con-bundle",
        prompt='May a feature addition and an unrelated cleanup ship together in one change?',
        acceptable_answers=['concern'],
    ),
    # v3 group: reuse-layout
    RecallTask(
        task_id="IR-81-reu-before",
        prompt='What should you do with existing code before adding new helpers?',
        acceptable_answers=['reuse'],
    ),
    RecallTask(
        task_id="IR-82-reu-where-new",
        prompt='Where should new files be placed?',
        acceptable_answers=['layout'],
    ),
    RecallTask(
        task_id="IR-83-reu-dup",
        prompt='You are about to write a string-normalising function. What first?',
        acceptable_answers=['reuse'],
    ),
    RecallTask(
        task_id="IR-84-reu-style-section",
        prompt='Which section holds both the reuse rule and the file-placement rule?',
        acceptable_answers=['Change Style'],
    ),
    RecallTask(
        task_id="IR-85-reu-layout-which",
        prompt='A new module does not clearly fit anywhere. Which layout should guide its placement?',
        acceptable_answers=['layout'],
    ),
    # v3 group: repo-map
    RecallTask(
        task_id="IR-86-map-name",
        prompt='What canonical document must be consulted before placing a file?',
        acceptable_answers=['repository map'],
    ),
    RecallTask(
        task_id="IR-87-map-when",
        prompt='At what moment should you consult the repository map?',
        acceptable_answers=['repository map'],
    ),
    RecallTask(
        task_id="IR-88-map-where",
        prompt='Which file hosts the repository map that the placement rules link to?',
        acceptable_answers=['CLAUDE.md'],
    ),
    RecallTask(
        task_id="IR-89-map-multi",
        prompt="Why does the placement section's title mention 'Multi-Repo'?",
        acceptable_answers=['repository map'],
    ),
    RecallTask(
        task_id="IR-90-map-first",
        prompt='Which step comes first when deciding where a new file lives in the multi-repo project?',
        acceptable_answers=['repository map'],
    ),
    # v3 group: orch-placement
    RecallTask(
        task_id="IR-91-orch-roles",
        prompt='Where do roles and routing metadata live in epyc-orchestrator?',
        acceptable_answers=['src/roles.py'],
    ),
    RecallTask(
        task_id="IR-92-orch-api",
        prompt='Which directory holds API routes, models, services and state?',
        acceptable_answers=['src/api/'],
    ),
    RecallTask(
        task_id="IR-93-orch-unit",
        prompt='Where do unit tests for the orchestrator go?',
        acceptable_answers=['tests/unit/'],
    ),
    RecallTask(
        task_id="IR-94-orch-integ",
        prompt='Where do integration tests for the orchestrator go?',
        acceptable_answers=['tests/integration/'],
    ),
    RecallTask(
        task_id="IR-95-orch-registry",
        prompt='Besides src/roles.py, what else holds roles/routing metadata in the orchestrator?',
        acceptable_answers=['model registry'],
    ),
    # v3 group: root-placement
    RecallTask(
        task_id="IR-96-root-agents",
        prompt='Where do agent definitions live in epyc-root?',
        acceptable_answers=['agents/'],
    ),
    RecallTask(
        task_id="IR-97-root-shared",
        prompt='Which directory in epyc-root holds cross-repo policy documents?',
        acceptable_answers=['agents/shared/'],
    ),
    RecallTask(
        task_id="IR-98-root-validate",
        prompt='A new governance lint script belongs in which epyc-root directory?',
        acceptable_answers=['scripts/validate/'],
    ),
    RecallTask(
        task_id="IR-99-root-docs",
        prompt='Where does architecture and design rationale go in epyc-root?',
        acceptable_answers=['docs/'],
    ),
    RecallTask(
        task_id="IR-100-root-repo-name",
        prompt="Which repo do the 'agents/', 'scripts/validate/' and 'docs/' placement rules belong to?",
        acceptable_answers=['epyc-root'],
    ),
    # v3 group: kernel-frozen
    RecallTask(
        task_id="IR-101-kf-state",
        prompt='What is the status of production kernels?',
        acceptable_answers=['frozen'],
    ),
    RecallTask(
        task_id="IR-102-kf-verbs",
        prompt='List the actions forbidden on a production kernel.',
        acceptable_answers=['modify, rebase, build, or commit'],
    ),
    RecallTask(
        task_id="IR-103-kf-exception",
        prompt='Under what condition may a frozen production kernel be touched?',
        acceptable_answers=['authorization'],
    ),
    RecallTask(
        task_id="IR-104-kf-who",
        prompt='Who must authorize changes to a production kernel?',
        acceptable_answers=['operator'],
    ),
    RecallTask(
        task_id="IR-105-kf-rebuild",
        prompt='Is rebuilding the production kernel tree in place permitted without sign-off?',
        acceptable_answers=['build', 'authorization'],
    ),
    # v3 group: kernel-branch
    RecallTask(
        task_id="IR-106-kb-branch",
        prompt='Which branch name is used for kernel work?',
        acceptable_answers=['llama.cpp-experimental'],
    ),
    RecallTask(
        task_id="IR-107-kb-fresh",
        prompt='How fresh must the kernel work branch be, relative to production?',
        acceptable_answers=['fresh'],
    ),
    RecallTask(
        task_id="IR-108-kb-ship",
        prompt='How does kernel work ship to production?',
        acceptable_answers=['past production'],
    ),
    RecallTask(
        task_id="IR-109-kb-canon",
        prompt='Where is the full kernel workflow documented canonically?',
        acceptable_answers=['CLAUDE.md'],
    ),
    RecallTask(
        task_id="IR-110-kb-patch",
        prompt='May you patch the production kernel in place to land a quick fix?',
        acceptable_answers=['past production', 'frozen'],
    ),
    # v3 group: persistence
    RecallTask(
        task_id="IR-111-per-formats",
        prompt='Which two file formats are named for incremental checkpoints?',
        acceptable_answers=['JSONL/CSV'],
    ),
    RecallTask(
        task_id="IR-112-per-when",
        prompt='When must each result be appended to the checkpoint?',
        acceptable_answers=['immediately'],
    ),
    RecallTask(
        task_id="IR-113-per-scope",
        prompt='Which category of scripts does the Incremental Persistence rule cover?',
        acceptable_answers=['inference'],
    ),
    RecallTask(
        task_id="IR-114-per-must",
        prompt='Which RFC-2119 strength marker governs incremental persistence?',
        acceptable_answers=['MUST'],
    ),
    RecallTask(
        task_id="IR-115-per-batch",
        prompt='Is it acceptable to buffer results and write them in one batch once the run finishes?',
        acceptable_answers=['batch'],
    ),
    # v3 group: summary-partial
    RecallTask(
        task_id="IR-116-sp-summary-role",
        prompt='Is the final summary the primary data store?',
        acceptable_answers=['primary'],
    ),
    RecallTask(
        task_id="IR-117-sp-checkpoint-source",
        prompt='What is the summary an aggregation of?',
        acceptable_answers=['checkpoint'],
    ),
    RecallTask(
        task_id="IR-118-sp-crash",
        prompt='What must exist on disk after a run is killed?',
        acceptable_answers=['partial'],
    ),
    RecallTask(
        task_id="IR-119-sp-where",
        prompt='Where must the partial results of a crashed run be left?',
        acceptable_answers=['on disk'],
    ),
    RecallTask(
        task_id="IR-120-sp-oom",
        prompt='An eval is OOM-killed at item 400 of 1000. What state should the run have left?',
        acceptable_answers=['killed', 'partial'],
    ),
    # v3 group: progress-patterns
    RecallTask(
        task_id="IR-121-pp-logcall",
        prompt='Which logging call is used for per-item progress?',
        acceptable_answers=['log.info'],
    ),
    RecallTask(
        task_id="IR-122-pp-format",
        prompt='What counter format string appears in the progress log pattern?',
        acceptable_answers=['[%d/%d]'],
    ),
    RecallTask(
        task_id="IR-123-pp-flush",
        prompt='Which call in the required pattern forces the checkpoint write to disk?',
        acceptable_answers=['ckpt.flush()'],
    ),
    RecallTask(
        task_id="IR-124-pp-mode",
        prompt='In what file mode is the checkpoint opened in the required pattern?',
        acceptable_answers=['open(checkpoint'],
    ),
    RecallTask(
        task_id="IR-125-pp-anti",
        prompt='What comment marks the data-loss risk in the anti-pattern snippet?',
        acceptable_answers=['lost if killed'],
    ),
    # v3 group: registry
    RecallTask(
        task_id="IR-126-reg-file",
        prompt='Which file now holds the model-registry format specification?',
        acceptable_answers=['REGISTRY_STANDARDS.md'],
    ),
    RecallTask(
        task_id="IR-127-reg-repo",
        prompt='Which repository hosts the registry format spec?',
        acceptable_answers=['epyc-inference-research'],
    ),
    RecallTask(
        task_id="IR-128-reg-heading",
        prompt='What is the heading of the section that points to the registry spec?',
        acceptable_answers=['Model Registry Standards'],
    ),
    RecallTask(
        task_id="IR-129-reg-moved",
        prompt='Is the registry format spec still defined inline in the standards file?',
        acceptable_answers=['REGISTRY_STANDARDS'],
    ),
    RecallTask(
        task_id="IR-130-reg-path",
        prompt='In which docs path under that repo does the registry spec live?',
        acceptable_answers=['docs/reference/models'],
    ),
    # v3 group: observe
    RecallTask(
        task_id="IR-131-obs-datum",
        prompt='What must you have seen before stating a root cause?',
        acceptable_answers=['primitive datum'],
    ),
    RecallTask(
        task_id="IR-132-obs-hyp",
        prompt='How should an unverified mechanism be labelled?',
        acceptable_answers=['hypothesis'],
    ),
    RecallTask(
        task_id="IR-133-obs-propagate",
        prompt='What may you never do with an unverified mechanism in handoffs or logs?',
        acceptable_answers=['propagate'],
    ),
    RecallTask(
        task_id="IR-134-obs-heading",
        prompt="What is the full name of the debugging discipline's first rule?",
        acceptable_answers=['Observe before diagnosing'],
    ),
    RecallTask(
        task_id="IR-135-obs-rootcause",
        prompt='A teammate writes a guessed root cause into a progress log as fact. What rule is broken?',
        acceptable_answers=['root cause', 'hypothesis'],
    ),
    # v3 group: not-observable
    RecallTask(
        task_id="IR-136-no-claim",
        prompt="What does declaring something 'not observable' require?",
        acceptable_answers=['looked everywhere'],
    ),
    RecallTask(
        task_id="IR-137-no-enum",
        prompt='What must you do with artifacts before declaring a blind spot?',
        acceptable_answers=['enumerate'],
    ),
    RecallTask(
        task_id="IR-138-no-artifacts",
        prompt='What do you enumerate before concluding there is no evidence?',
        acceptable_answers=['artifacts'],
    ),
    RecallTask(
        task_id="IR-139-no-onelog",
        prompt='Is checking the single log you already know enough to call something unobservable?',
        acceptable_answers=['looked everywhere'],
    ),
    RecallTask(
        task_id="IR-140-no-rule-name",
        prompt='What is the quoted phrase of the rule that demands exhaustive searching for evidence?',
        acceptable_answers=['Not observable'],
    ),
    # v3 group: blind-fixes
    RecallTask(
        task_id="IR-141-bf-cap",
        prompt='What is the cap on blind fixes?',
        acceptable_answers=['blind fixes at one'],
    ),
    RecallTask(
        task_id="IR-142-bf-next",
        prompt='After a hypothesis-driven fix fails, what should the next action be?',
        acceptable_answers=['observability'],
    ),
    RecallTask(
        task_id="IR-143-bf-second",
        prompt='May you try a second speculative patch right after the first failed?',
        acceptable_answers=['another fix'],
    ),
    RecallTask(
        task_id="IR-144-bf-name",
        prompt='Give the exact bolded name of the rule limiting speculative fixes.',
        acceptable_answers=['Cap blind fixes'],
    ),
    RecallTask(
        task_id="IR-145-bf-hypothesis",
        prompt='What kind of fix is limited to one attempt before observability?',
        acceptable_answers=['hypothesis'],
    ),
    # v3 group: yellow-flag
    RecallTask(
        task_id="IR-146-yf-term",
        prompt='What colour of flag is a coherent failure narrative?',
        acceptable_answers=['yellow flag'],
    ),
    RecallTask(
        task_id="IR-147-yf-notwhat",
        prompt='A coherent failure narrative is not what, according to the file?',
        acceptable_answers=['reassurance'],
    ),
    RecallTask(
        task_id="IR-148-yf-subject",
        prompt='Which kind of narrative should raise suspicion rather than comfort?',
        acceptable_answers=['coherent failure narrative'],
    ),
    RecallTask(
        task_id="IR-149-yf-story",
        prompt='Your investigation produced a neat story that explains every symptom. What does the file say about trusting it?',
        acceptable_answers=['yellow flag'],
    ),
    RecallTask(
        task_id="IR-150-yf-evidence",
        prompt='Does a plausible story count as evidence for closing a debugging session?',
        acceptable_answers=['not reassurance'],
    ),
    # v3 group: verification
    RecallTask(
        task_id="IR-151-ver-syntax",
        prompt='What is the first Verification Minimum step?',
        acceptable_answers=['syntax check'],
    ),
    RecallTask(
        task_id="IR-152-ver-tests",
        prompt='Which kind of tests should be run before finalizing?',
        acceptable_answers=['targeted tests'],
    ),
    RecallTask(
        task_id="IR-153-ver-docs",
        prompt='What does Verification Minimum say about documentation?',
        acceptable_answers=['docs'],
    ),
    RecallTask(
        task_id="IR-154-ver-proxy",
        prompt='What does step 5 say about validating a stub or proxy?',
        acceptable_answers=['real path'],
    ),
    RecallTask(
        task_id="IR-155-ver-ready",
        prompt="What must you exercise before declaring infrastructure 'ready'?",
        acceptable_answers=['canary'],
    ),
]


def all_tasks() -> list[RecallTask]:
    return list(TASKS)
