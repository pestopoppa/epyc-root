# Stack Change Governance Pipeline

**Status**: IN PROGRESS 2026-06-13 — W1/W2 landed; W3 guardrail/scanner/procedure-enum/contract/exception checks live through stack-prior contract v4 launch-runtime witness, simulated data-only workflow fixtures, stack-change CLI acceptance/promotion-gate output and warning summaries, machine-readable hardcoded-surface scanner rule inventory, compact surface-warning summary mode, enforced scanner-rule ownership manifest, architect/REAP quality projection, GGUF-derived model context projection, descriptor-native VL projector requirements, structured thinking-control evidence, shared-runtime alias provenance, retired-role alias normalization, legacy routing ingress alias normalization, retired architect ingress alias normalization, retired architect metadata cleanup and recurrence guard, delegation report preamble alias normalization, architect investigation prompt live-role alignment, output formalizer live-worker routing, user preference deriver live-worker routing, post-hoc grading spec/debugger prompt live-worker routing, stale role runtime-surface cleanup, launch-wrapper static-inventory recurrence guard, stack-prior-rendered AutoPilot system-card rows, read-only live process cmdline/projector attestation in stack status, manifest-derived auxiliary and generated live serving port scanning, direct/ReAct vision chat URL resolution from stack priors, API health backend probes from stack priors, summarization worker selection from stack priors, parallel burst-worker selection from stack priors, worker concurrency caps from stack priors, runtime inference lock classes from stack priors, current contention role-class pinning, proactive thinking-trigger routing to live architect, seeding throughput-prior provenance, seeding role discovery from stack priors, test-only launch-command parity witnesses from stack priors, default stack-template alias/topology alignment, and lean-registry retired architect removal; generated descriptors/priors are `status: compiled` with empty stack-prior `known_gaps`; default `stack_change_pipeline.py check` reports descriptor/stack-prior/procedure/guard/strict OK, prints `acceptance:` / `promotion_gate:` with simulated-fixture and launch-parity test targets, optional `--run-promotion-gate` executes those no-inference targets after earlier checks pass, validates scanner-rule ownership, and keeps waived production-blocker, legacy-test, and historical-doc warning categories summarized
**Created**: 2026-06-13
**Priority**: HIGH — prevents silent stale model constants after stack changes; no inference required for W1-W4
**Related**: [standardized-stack-update-pipeline-finalization.md](standardized-stack-update-pipeline-finalization.md), [model-capability-descriptors.md](model-capability-descriptors.md), [routing-truth-restoration.md](routing-truth-restoration.md), [dynamic-stack-concurrency.md](dynamic-stack-concurrency.md), [bulk-inference-campaign.md](bulk-inference-campaign.md), [MEASUREMENT.md](../../MEASUREMENT.md)

> **2026-06-13 finalization bridge**: [standardized-stack-update-pipeline-finalization.md](standardized-stack-update-pipeline-finalization.md) consolidates the older audits into the main workflow pickup plan. Use that file for the next implementation pass; continue recording commit-level progress and guard counts here.

## Why

The orchestration stack has outgrown manual update discipline. A single model or
serving-topology change now has to update registry records, descriptors,
launch args, q_scorer priors, planner signatures, seeder eval config, process
layout, tests, docs, and runtime attestation. The 2026-06-13 q_scorer fix found
severe drift: `architect_coding` was retired but still present in fallback
priors, `architect_general` and `ingest_long_context` were marked HOT in
`server_mode` while older role/process-layout metadata still implied WARM, and
`coder_escalation` shares the frontdoor model/server but old cost comments
treated it as separate memory pressure.

The target state is a fail-closed stack-change pipeline: edit model/serving
truth once, compile generated descriptors/derived priors, validate every
consumer, and refuse launch or CI if any model-specific quantity remains stale.

## Current Evidence

- `epyc-orchestrator` descriptor work is live through `545eb57`, with first
  AutoPilot signature consumer live in `73ed436`.
- q_scorer descriptor/registry priors landed in `d5fe713` and were corrected in
  `15d8cff` so HOT memory residency and retired-role absence come from live
  registry truth instead of stale constants.
- The first generated stack-priors contract landed in `epyc-orchestrator`
  `a1e04d5`: `docs/reference/stack-truth-precedence.md`,
  `src/registry/stack_priors.py`,
  `scripts/registry/compile_stack_priors.py`,
  `orchestration/derived/stack_priors.yaml`, and
  `scripts/validate/stack_change_guard.py`.
- Phase A hardcoded-surface scanning landed in `epyc-orchestrator` `bfa90fa`;
  normal guard output now reports categorized production-blocker model/stack
  constants, with `--all-hardcoded-surfaces` for docs/tests audit mode.
- Procedure role choices are now generated/guarded in `epyc-orchestrator`
  `f49f14d`: `scripts/registry/sync_procedure_role_enums.py` syncs
  `add_model_to_registry.yaml` and the procedure JSON schema from
  `stack_priors.yaml`; `stack_change_guard.py` now errors on drift.
- Stack-prior consumer contract validation landed in `epyc-orchestrator`
  `69057f3`: generated `stack_priors.yaml` embeds versioned required
  top-level/role/serving/prior fields, and `stack_change_guard.py` rejects
  artifacts missing that contract shape.
- Stack-change guard exception metadata landed in `epyc-orchestrator`
  `e162c7c`: `orchestration/stack_change_guard_exceptions.yaml` is the default
  documented exception file, invalid/expired entries are guard errors, and valid
  waived hardcoded-surface findings remain visible without becoming strict-mode
  errors.
- Chat pipeline retired-role cleanup landed in `epyc-orchestrator` `481516c`:
  `delegation_stage.py` and `proactive_stage.py` now treat only
  `architect_general` as the live architect branch trigger, dropping live guard
  warnings from 83 to 81.
- Proactive deep-reasoning trigger cleanup landed in `epyc-orchestrator`
  `53f12e0`: `/think` / `/ultrathink`-style triggers now route to live
  `architect_general` instead of the removed dedicated thinking role, stale
  comments were updated, and a unit regression covers the routing behavior.
  Validation: proactive/langgraph focused pytest -> 98 passed; `py_compile`;
  no active proactive stale thinking-role strings by `rg`;
  `stack_change_guard.py --all-hardcoded-surfaces` -> 90 known warnings only;
  `git diff --check`.
- A low-risk chat routing cleanup landed in `epyc-orchestrator` `519f710`:
  `_role_to_task_type()` dropped a redundant retired-role check and added
  current live-role mapping coverage, reducing live guard warnings from 81 to
  80. The remaining `_heuristic_role_priors()` retired-role prior is still open
  as a separate HIGH-impact routing patch.
- OpenAI-compatible model listing now derives live roles from stack priors in
  `epyc-orchestrator` `d9c053c`, preserving compatibility aliases and using a
  non-retired degraded fallback; live guard warnings dropped from 80 to 79.
- Dashboard in-flight age overrides no longer include retired
  `architect_coding` after `epyc-orchestrator` `1b9db81`; live guard warnings
  dropped from 79 to 78.
- Runtime inference lock/tap heavy-role classifications dropped retired
  `architect_coding` in `epyc-orchestrator` `6bc1f51`; live guard warnings
  dropped from 78 to 76.
- Runtime inference lock role-class derivation migrated in `epyc-orchestrator`
  `822482b`: `src/runtime/inference_lock.py` now derives live role classes from
  generated stack priors when available. Live `worker_pool` and `worker_vision`
  roles use shared locks, retired `worker_fast` is absent from live derived
  `LIGHT_ROLES`, unknown roles fail closed/exclusive, and explicit `shared=`
  overrides are unchanged. Validation: focused lock/concurrency/scheduling tests
  -> 65 passed; `py_compile`; direct derived-role assertions;
  `stack_change_guard.py --all-hardcoded-surfaces` -> same 90 known warnings;
  `git diff --check`.
- Scheduling/contention role classes were pinned to the current stack matrix in
  `epyc-orchestrator` `eed215d`: `src/scheduling/contention.py` no longer
  carries an unused fallback heavy-role constant or stale same-role vision
  comment, and real-matrix tests now assert current n-way light/heavy role
  classes, `worker_fast` absence from matrix light roles, and same-role
  `vision_escalation` ALLOW behavior. Validation: focused scheduling/admission/
  lock tests -> 78 passed; `py_compile`; `stack_change_guard.py
  --all-hardcoded-surfaces` -> same 90 known warnings; `git diff --check`.
- Legacy routing ingress alias normalization landed in `epyc-orchestrator`
  `3e4ba7c`: `/chat` and OpenAI-compatible ingress now normalize
  model-generated or legacy labels before config lookup, mapping `coder` to
  `coder_escalation` and `worker_fast` / `worker_coder` / `worker_code` to
  `worker_general`. Chat delegation parsing keeps live valid targets while
  compatibility aliases normalize old labels, and REPL `delegate` / `my_role`
  no longer advertise retired `worker_fast`, `worker_coder`, or
  `worker_explore` as live targets while still resolving them to live roles.
  The `_run_specialist_loop` return annotation/tests were updated to match the
  existing 8-value contract surfaced by the expanded verification run.
  Validation: expanded routing/chat/API suite -> 208 passed with 3 existing
  SWIG warnings; focused rerun -> 180 passed with the same warnings;
  `py_compile`; `stack_change_guard.py --all-hardcoded-surfaces` -> same 90
  known warnings; `git diff --check`.
- Delegation report role preamble normalization landed in `epyc-orchestrator`
  `6ec2686`: compact specialist report prompts now canonicalize through
  `_normalize_delegate_role`, direct preamble role sets are limited to live
  `coder_escalation` and `worker_general`, and legacy `worker_coder` /
  `worker_explore` / `worker_fast` aliases still produce live-role prompts
  without advertising retired labels. Validation: `py_compile`; focused
  delegation/architect pytest -> 87 passed; chat pipeline integration -> 28
  passed; `stack_change_guard.py` OK; `git diff --check`.
- Architect investigation prompt live-role alignment landed in
  `epyc-orchestrator` `09948db`: the active architect investigation template,
  fallback constant, and architect system example now name only
  `coder_escalation` for implementation/file-split delegation and
  `worker_general` for investigation/search. The valid role list excludes
  `worker_coder`, `worker_explore`, and `worker_fast`, with a prompt-builder
  regression asserting live roles are present and retired labels absent.
  Validation: `py_compile`; focused prompt-builder/architect/plan-review tests
  -> 11 passed; `stack_change_guard.py` OK; `git diff --check`.
- Output formalizer live-worker routing landed in `epyc-orchestrator`
  `4bf8061`: `_formalize_output` now calls live `worker_general` instead of
  the retired/legacy `worker_explore` label, and its docstring no longer embeds
  stale model speed or port assumptions. `tests/unit/test_chat_utils_coverage.py`
  now asserts the role passed to `llm_call` is `worker_general`. Validation:
  `py_compile`; focused chat-utils/stage tests -> 68 passed;
  `stack_change_guard.py` OK; `git diff --check`.
- User preference deriver live-worker routing landed in `epyc-orchestrator`
  `a9424a9`: user-modeling preference extraction now calls live
  `worker_general` instead of the retired/legacy `worker_explore` label, the
  adjacent docs were updated to avoid stale role wording, and
  `tests/unit/test_user_modeling.py` asserts the LLM-call role. Validation:
  `py_compile`; focused user-modeling tests -> 19 passed;
  `stack_change_guard.py` OK; `git diff --check`.
- Post-hoc model grading live-worker routing landed in `epyc-orchestrator`
  `a7c9ac0`: `src/pipeline_monitor/model_grader.py` now defaults grading to
  live `worker_general`; the three `orchestration/grading_specs/*.yaml` specs
  explicitly set `judge_role: worker_general`; and
  `tests/unit/test_model_grader.py` verifies fallback/default and explicit
  override behavior. Validation: `py_compile`; focused model-grader tests -> 2
  passed; YAML load check loaded 3 specs, all `worker_general`;
  `stack_change_guard.py` OK; `git diff --check`.
- Debugger prompt grading-role wording landed in `epyc-orchestrator`
  `4f9123f`: `orchestration/prompts/debugger_system.md` now documents
  `model_graded_evals` with `worker_general`, matching the model-grader
  default/spec migration.
- Default stack template alignment landed in `epyc-orchestrator` `069f8c0`:
  `src/config/stack_templates.py` supports explicit aliases and rejects
  retired deployable roles such as `architect_coding`; the default template now
  mirrors the live manifest with frontdoor/worker/ingest/vision escalation
  full-plus-quarter prewarm, aliases for shared runtime roles, one
  `architect_general`, 22 launch instances, and about 653 GB instance-counted
  RAM.
- Lean registry retired-architect cleanup landed in `epyc-orchestrator`
  `22ea541`: `model_registry_lean.yaml` no longer defines
  `architect_coding`, the coder escalation chain is `frontdoor ->
  coder_escalation`, code routing hints target `coder_escalation`, and
  registry-loader tests cover retired-role absence plus current
  `coder_escalation` acceleration `type: none`.
- Retired architect ingress compatibility landed in `epyc-orchestrator`
  `705065d`: chat pipeline ingress alias normalization now maps
  `architect_coding` to live `architect_general`, with
  `test_pipeline_routing.py` covering the legacy alias alongside delegated chat
  roundtrip validation from the main track.
- Retired architect metadata cleanup landed in `epyc-orchestrator`
  `e61e61f`: `orchestration/source_registry.yaml` no longer grants
  `architect_coding` role access, `orchestration/model_quality_signatures.yaml`
  no longer carries the retired REAP architect fallback quality signature, and
  `chat_delegation_config.py` now describes delegation re-entry against the
  live architect. `_fast_revise` was explicitly deferred because GitNexus
  impact on `_fast_revise` was HIGH and touches `generate_stream` / chat
  pipeline behavior.
- Retired architect metadata recurrence guard landed in `epyc-orchestrator`
  `828552f`: `stack_change_guard.py` now has production-blocker rules for
  `architect_coding` in `model_registry_lean.yaml`, `source_registry.yaml`, and
  `model_quality_signatures.yaml`, with regression tests in
  `tests/unit/test_stack_change_guard.py`. Main-track validation reported no
  live warnings for those three rule IDs and 28 focused guard tests passing.
- Stack-change promotion-gate output landed in `epyc-orchestrator` `079ff30`:
  `PipelineReport.acceptance_lines()` and `_print_report()` now emit
  `acceptance:` and `promotion_gate:` lines. Passing checks name the simulated
  data-only fixture target required before launch/AutoPilot promotion; failed
  checks report the strict blocker count and keep promotion blocked.
- Intentional retired-role guard surfaces were classified in `epyc-orchestrator`
  `2baaee5`: `orchestration/stack_change_guard_exceptions.yaml` now waives the
  legacy ingress alias map in `routing_decision.py` and retired-deployable
  rejection constant in `stack_templates.py` with owner/rationale/expiry
  metadata, so default `stack_change_pipeline.py check` passes while the waived
  warnings remain visible.
- Stack-change warning summaries landed in `epyc-orchestrator` `a7927c2`:
  the pipeline footer now de-duplicates warning counts and summarizes
  hardcoded-surface categories such as waived production blockers, legacy tests,
  and historical docs.
- Approval-gate high-cost role classification dropped retired
  `architect_coding` in `epyc-orchestrator` `e6e10d8`; live guard warnings
  dropped from 76 to 75.
- Chat routing heuristic priors migrated to live stack-prior role filtering in
  `epyc-orchestrator` `eb4dac5`, with a non-retired degraded fallback; live
  guard warnings dropped from 75 to 74 after broader routing/pipeline tests.
- Role docs and active graph topology no longer expose the retired architect
  coding node after `epyc-orchestrator` `0b1e5e9` and `3c7a85e`; PydanticGraph
  and LangGraph now have six active nodes, while `Role.ARCHITECT_CODING`
  direct/persisted compatibility starts on the live architect node. Live guard
  warnings dropped from 44 to 23 in the later cleanup window.
- The remaining `src/roles.py` compatibility enum line is now an explicit,
  expiring `intentional_live_exception` after `epyc-orchestrator` `fa6411c`;
  strict mode no longer promotes it as an unclassified hardcoded-surface error.
- Evidence-backed descriptor quality priors landed in `epyc-orchestrator`
  `bda46b1`: measured single-purpose suite scores now populate generated
  `priors.quality_overall` for architect, ingest, VL, and toolrunner roles;
  `762e6b0` refreshed the derived artifact metadata afterward.
- The first canonical command skeleton landed in `epyc-orchestrator`
  `e01d64d`: `scripts/registry/stack_change_pipeline.py` composes descriptor
  compile/check, stack-prior compile/check, procedure enum sync/check, and
  loose/all-surface/strict guard passes into `check` and `update` modes. Focused
  tests landed in `tests/unit/test_stack_change_pipeline.py`.
- Pipeline preview correctness was tightened in `epyc-orchestrator` `fe4b2aa`:
  guard validation now honors explicit procedure/schema paths for temp previews
  and CI fixtures, while stack-prior generation defaults to descriptor role
  bindings unless an explicit role set is requested.
- Pipeline operator output was tightened in `epyc-orchestrator` `079ff30` /
  `a7927c2`: the command now prints acceptance/promotion-gate lines and a compact
  warning-category footer. `2baaee5` classifies the two intentional retired-role
  guard surfaces so the default check path passes without `--allow-known-gaps`.
- Seeding per-role discovery migrated in `epyc-orchestrator` `2e31055`:
  `scripts/benchmark/seeding_types.py` now prefers generated stack-prior live
  roles, restores `worker_vision` and `vision_escalation` eval coverage,
  excludes shared non-default aliases, and preserves registry fallback.
- q_scorer alias-quality propagation landed in `epyc-orchestrator` `9ed177d`:
  `worker_explore` now receives stack-prior quality from live `worker_general`,
  matching existing TPS/memory alias propagation and removing the degraded
  quality fallback residue.
- Launcher parity witnesses landed in `epyc-orchestrator` `b026f7d`: the
  `tests/unit/test_build_server_command_helpers.py` assertions for
  `worker_general` MTP and VL launch commands now derive their expected launch
  requirements from `orchestration/derived/stack_priors.yaml`. This is a
  test-only follow-up to the promotion-gate work and does not alter startup
  behavior. Validation: `uv run pytest -q
  tests/unit/test_build_server_command_helpers.py` -> 37 passed; `python3 -m
  py_compile tests/unit/test_build_server_command_helpers.py`; `uv run python
  scripts/registry/stack_change_pipeline.py check` -> summary ok /
  no-inference checks passed / same warning buckets; `uv run pytest -q
  tests/unit/test_stack_change_pipeline_simulated_fixtures.py` -> 6 passed;
  `git diff --check`.
- Launch parity was promoted into the stack-change gate in `epyc-orchestrator`
  `ebd929b`: `scripts/registry/stack_change_pipeline.py` now includes both
  `tests/unit/test_stack_change_pipeline_simulated_fixtures.py` and
  `tests/unit/test_build_server_command_helpers.py` in the printed
  `promotion_gate:` command, with regression coverage in
  `tests/unit/test_stack_change_pipeline.py`. Validation: `python3 -m
  py_compile scripts/registry/stack_change_pipeline.py
  tests/unit/test_stack_change_pipeline.py`; `uv run pytest -q
  tests/unit/test_stack_change_pipeline.py
  tests/unit/test_stack_change_pipeline_simulated_fixtures.py
  tests/unit/test_build_server_command_helpers.py` -> 53 passed; `uv run
  python scripts/registry/stack_change_pipeline.py check` -> summary ok and
  `promotion_gate:` prints both targets; `git diff --check`.
- Executable stack promotion gate landed in `epyc-orchestrator` `3a20efd`:
  `scripts/registry/stack_change_pipeline.py check --run-promotion-gate`
  executes the no-inference promotion targets only after earlier stack-change
  checks pass. The default check mode still prints the targets as reference
  steps. The simulated fixture step selection was updated to use names.
  Validation: `python3 -m py_compile scripts/registry/stack_change_pipeline.py
  tests/unit/test_stack_change_pipeline.py
  tests/unit/test_stack_change_pipeline_simulated_fixtures.py`; `uv run pytest
  -q tests/unit/test_stack_change_pipeline.py` -> 11 passed; `uv run python
  scripts/registry/stack_change_pipeline.py check --run-promotion-gate` ->
  summary ok and promotion_gate ok, nested pytest 43 passed; `git diff --check`.
- Hardcoded-surface scanner rule inventory exposure landed in
  `epyc-orchestrator` `34a0407`: `scripts/validate/stack_change_guard.py`
  now exposes `hardcoded_surface_rule_inventory()` and
  `--list-hardcoded-surface-rules --surface-inventory-format yaml|json`.
  The output reports inventory `version`, `rule_count`, categories, and
  per-rule ID/category/pattern/path globs/exclude globs/comment handling/
  remediation. Direct-by-path import hygiene was also fixed so
  `python scripts/validate/stack_change_guard.py ...` works without relying on
  pipeline imports. Validation: `py_compile` passed; `ruff` passed;
  `git diff --check` passed; `uv run pytest -q
  tests/unit/test_stack_change_guard.py tests/unit/test_stack_change_pipeline.py`
  -> 41 passed; direct JSON inventory smoke passed; `uv run python
  scripts/registry/stack_change_pipeline.py check` remained summary ok with
  existing warning buckets.
- Stack guard surface summary mode landed in `epyc-orchestrator` `2cb3d6c`:
  `stack_change_guard.py` now exposes `hardcoded_surface_warning_counts()` and
  CLI `--surface-summary-only`, compacting hardcoded-surface scan warnings into
  category counts while preserving default detailed warning output. This does
  not change canonical pipeline output or guard policy. Live smoke:
  `PYTHONDONTWRITEBYTECODE=1 uv run python
  scripts/validate/stack_change_guard.py --all-hardcoded-surfaces
  --surface-summary-only` -> `WARN: 99 unique stack-prior warning(s) (99
  total)` and `surface_warnings: waived_production_blocker=2, legacy_test=72,
  historical_doc=25`. `PYTHONDONTWRITEBYTECODE=1 uv run python
  scripts/registry/stack_change_pipeline.py check` remained `summary: ok` with
  existing warning buckets and acceptance footer. Validation: `python3 -m
  py_compile scripts/validate/stack_change_guard.py
  tests/unit/test_stack_change_guard.py`; `uv run ruff check ...`; `git diff
  --check -- ...`; `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p
  no:cacheprovider tests/unit/test_stack_change_guard.py
  tests/unit/test_stack_change_pipeline.py` -> 43 passed.
- Stack surface ownership manifest landed in `epyc-orchestrator` `7815318`:
  `orchestration/stack_change_surface_manifest.yaml` is now the enforced
  ownership map for all hardcoded model/stack scanner rules. Each entry carries
  `rule_id`, category, owner, consumer scope, promotion-blocker policy, review
  cadence, evidence command, and drift response. The guard validates manifest
  presence, one-entry-per-rule coverage, duplicate or unknown rule IDs,
  category consistency with scanner rules, required text fields, and blocker
  semantics (`production_blocker` must block promotion; `legacy_test` and
  `historical_doc` do not). `--list-hardcoded-surface-rules` now enriches
  inventory output with ownership metadata and fails if the manifest is
  missing or invalid; `stack_change_pipeline.py check` passes the manifest into
  guard steps, so the canonical no-inference stack-change pipeline fails on
  scanner-rule ownership drift. Live checks: inventory JSON includes ownership
  metadata; `--all-hardcoded-surfaces --surface-summary-only` remains `99
  unique` with `waived_production_blocker=2, legacy_test=72,
  historical_doc=25`; default guard remains two waived production warnings;
  `stack_change_pipeline.py check` remains `summary: ok`; `check
  --run-promotion-gate` executed nested pytest and reported 43 passed.
  Validation: `py_compile` for guard/pipeline/tests; `ruff` on touched
  code/tests; `git diff --check`; `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q
  -p no:cacheprovider tests/unit/test_stack_change_guard.py
  tests/unit/test_stack_change_pipeline.py
  tests/unit/test_stack_change_pipeline_simulated_fixtures.py` -> 52 passed.
  Main-lane GitNexus was re-indexed after the commit: 51,900 nodes, 88,985
  edges, 300 flows. This closes the first implementation pass of the W2
  ownership-manifest lane for scanner rules; broader consumer migrations
  remain open.
- Descriptor compiler quality-key normalization landed in `epyc-orchestrator`
  `3e7efce`: generated descriptors now use stable suite-vector keys such as
  `overall`, `coder`, `agentic`, `math`, `vision_language`, and `long_context`
  instead of leaking raw registry field names like `quality_pct` and
  `coder_suite`. The remaining `check --allow-known-gaps` failure is descriptor
  regeneration drift, not stack-prior/procedure-enum drift.
- Descriptor compiler model-ID stabilization landed in `epyc-orchestrator`
  `ca9af53`: generated model IDs now match the current descriptor policy for
  every generated/live identity; only the existing REAP benchmark-only record is
  absent from compiler coverage and remains a coverage-policy drift item.
- Stack-change pipeline fail-closed protection landed in `epyc-orchestrator`
  `022a0d1`: `check` reports descriptor model removals explicitly and `update`
  skips descriptor/stack-prior/procedure writes unless
  `--allow-descriptor-model-removal` is passed after a coverage decision.
- Structured REAP descriptor coverage landed in `epyc-orchestrator` `fbef837`,
  with stack-prior metadata refreshed in `365e370`. The descriptor compiler
  preview now has no current-only or generated-only model IDs; remaining
  descriptor staleness is curated-evidence/schema drift rather than missing
  benchmark-only model coverage.
- Descriptor domain modality derivation landed in `epyc-orchestrator`
  `846c2d4`: generated descriptors retain `code`, `math`, and `long_context`
  modalities from structured model metadata instead of collapsing those models
  to text-only.
- GraphRouter training fleet discovery migrated in `epyc-orchestrator`
  `8cf0310`: offline GAT training now reads live LLMRole model nodes from
  generated stack priors, skips benchmark/candidate roles, and keeps a current
  non-retired degraded fallback.
- GraphRouter extraction/verifier action spaces migrated in `epyc-orchestrator`
  `1f16759`: a shared `scripts/graph_router/action_space.py` helper now derives
  live labels from stack priors, remaps legacy replay labels into current live
  roles, and removes fixed verifier `n_actions=8` defaults in favor of
  classifier-artifact inference.
- Shared-alias launch port drift was fixed in `epyc-orchestrator` `d4acf24`:
  `PORT_MAP` now agrees with computed launch roles for `coder_escalation`,
  `worker_summarize`, and `toolrunner`; `validate_against_registry()` now warns
  if future direct port hints diverge from `ROLE_LAUNCH_META + NUMA_CONFIG`.
- Vision ReAct serving-port selection migrated in `epyc-orchestrator`
  `06ff53c`: `src/api/routes/chat_pipeline/vision_stage.py` now reads
  `worker_vision` and `vision_escalation` ports from generated stack-prior
  serving records, with explicit degraded fallback ports for missing priors.
- Direct and ReAct vision chat URL resolution migrated in `epyc-orchestrator`
  `ee784f9`: `src/api/routes/chat_vision.py` now resolves
  `worker_vision` and `vision_escalation` backend URLs from generated
  stack-prior live `serving.endpoint` / `serving.ports` records. The degraded
  config fallback remains explicit, and `full:` URL prefixes are normalized to
  concrete endpoints before `httpx` calls.
- API health backend probes migrated in `epyc-orchestrator` `3dc21c5`:
  `src/api/routes/health.py` now derives live backend probe targets from
  generated stack-prior `deployment_status: live_stack` records, groups shared
  endpoints under slash-joined role labels, and probes each shared server once.
  Missing or malformed stack priors fall back to the old `frontdoor` plus
  `architect_general` config URL behavior.
- Chat summarization worker selection migrated in `epyc-orchestrator`
  `5b4f683`: `src/api/routes/chat_summarization.py` no longer probes retired
  `worker_fast` at port 8102 for chunk digest work. It selects the worker from
  generated stack priors, preferring live `worker_summarize`, then other live
  worker roles, with explicit degraded fallback to `worker_summarize` if the
  generated artifact is unavailable. Batch-failure fallback now retries
  sequentially through the selected live worker instead of forcing
  `worker_explore`.
- Parallel step execution burst eligibility migrated in `epyc-orchestrator`
  `cc401c0`: `src/parallel_step_executor.py` now derives same-wave burst
  worker roles from generated stack priors, accepting only live `worker_*`
  records with `serving.tier: warm`. The current live stack has no warm worker
  burst role, so execution fails closed to sequential HOT execution unless a
  future generated stack explicitly marks a live warm worker.
- Worker concurrency caps migrated in `epyc-orchestrator` `f41f956`:
  `src/runtime/concurrency.py` now derives concurrent worker caps from generated
  stack priors instead of hardcoded small-worker role tables. Only
  `deployment_status: live_stack` records whose role starts with `worker_` and
  whose `serving.tier` is `warm` are eligible; caps use `serving.slots`, default
  to 1 when absent, and fail closed to no concurrent workers if priors are
  missing or malformed. The current live stack has HOT workers only, so REPL
  parallel delegation and primitive role semaphores remain single-lane until a
  future generated stack promotes a live warm worker.
- Shared `server_mode` alias-port validation landed in `epyc-orchestrator`
  `40d46ea`: `validate_against_registry()` now checks registry rows that cover
  launch roles through `model_role` or `shared_with`, so stale shared worker
  ports warn before launch.
- AutoPilot preflight health targets migrated in `epyc-orchestrator`
  `a5aaafb`: `scripts/autopilot/preflight_audit.py` now groups live model
  server probes from generated stack-prior serving endpoints instead of a raw
  port table.
- AutoPilot program endpoint guidance migrated in `epyc-orchestrator`
  `60733c7`: `scripts/autopilot/program.md` now queries generated stack priors
  for live compaction endpoints instead of carrying stale target-port examples.
- AutoPilot program hardcoded-surface coverage landed in `epyc-orchestrator`
  `cf73ac1`: `stack_change_guard.py --all-hardcoded-surfaces` now flags stale
  static endpoint/tier guidance in `scripts/autopilot/program.md`.
- Launch-manifest semantic guard landed in `epyc-orchestrator` `312b28e`:
  generated live stack-prior serving endpoint ports, primary port membership,
  and tier are now compared against computed launch-manifest roles.
- Stack-prior launch-source freshness landed in `epyc-orchestrator`
  `a6d1200`: generated priors now hash `scripts/server/stack_manifest.py`
  and `scripts/server/stack_numa.py`, and the guard requires those source
  artifact hashes.
- Exact launch-port projection landed in `epyc-orchestrator` `dc14196`:
  generated serving records now use computed launch role port sets, preserve
  slots, and fail guard validation on missing launch ports or extra
  non-launch ports.
- Launch witness contract v2 landed in `epyc-orchestrator` `7917535`:
  generated priors now require `serving.launch.entries`, and the guard compares
  launch mode, alias status, primary role, and optional NUMA/worker/vision
  instance metadata against computed launch-manifest roles.
- Shared-runtime descriptor alias semantics landed in `epyc-orchestrator`
  `a7b72a9`: generated descriptors now merge `worker_math` and `toolrunner`
  into the primary Gemma worker runtime descriptor, remove standalone live Qwen
  math/toolrunner descriptors, retain live role bindings in stack priors, and
  record ignored non-live alias metadata as known gaps instead of role/server
  conflicts. `stack_change_pipeline.py check --allow-known-gaps` now passes
  with expected known-gap warnings.
- Shared-runtime alias provenance landed in `epyc-orchestrator` `54b7c77`:
  alias mismatch notes for `worker_general`, `worker_math`, and `toolrunner`
  are now structured provenance, not blocking gaps. Descriptor records write
  `role_bindings.alias_overrides` for ignored stale role-local model metadata;
  stack priors expose the same records under `evidence.alias_overrides`; and
  `docs/reference/stack-truth-precedence.md` documents the precedence rule.
  Generated descriptors and stack priors now have `status: compiled`, stack
  prior records have empty `known_gaps`; the temporary `ARCHITECT_CODING`
  production waiver was later closed in `03ed49f`.
- Stack-prior contract v3 launch requirements landed in `epyc-orchestrator`
  `a001017`: generated serving records now include
  `effective_context_tokens` plus `serving.launch.requirements` for worker
  model/draft paths and VL model/mmproj paths, and the guard compares those
  values against computed stack-manifest launch truth.
- Completed in `33c81ff`: contract v4 launch-runtime projection adds an
  effective runtime witness under `serving.launch.runtime`, with
  launcher/path/runtime source hashes and guard comparison.
- Completed in `fb0fd6d`: simulated data-only stack-change fixtures now cover
  frontdoor/coder shared-runtime swaps, worker-family aliases, retired-role enum
  cleanup, runtime-requirement drift, and context/KV/acceleration drift. The
  canonical pipeline now prints the fixture pytest target as a reference step.
- Completed in `837829f`: `roles.architect_general.performance.quality_score:
  "2.57/3"` is now structured, `model_descriptors.yaml` and
  `derived/stack_priors.yaml` were regenerated, and stack priors project
  `quality_overall: 0.8567` for `architect_general` and `qwen35_122b_q4km`.
  Their known gaps narrowed from quality+ctx to structured ctx only.
- Completed in `b8477b0`: GGUF header metadata was extracted from local model
  files and projected into `roles.*.model.ctx_max` for Qwen3-Next 80B,
  Qwen3.5-122B, Qwen2.5-VL 7B, Qwen3-VL 30B, and REAP-Qwen3-Coder 25B.
  `orchestration/model_descriptors.yaml` and
  `orchestration/derived/stack_priors.yaml` were regenerated; the prior
  `Missing structured ctx_max` warnings are gone, and the stack-change guard
  warning count dropped to 15 known warnings. Remaining descriptor/strict gaps
  at that point were enable_thinking evidence, REAP quality, and
  shared-runtime alias notes.
- Completed in `2ea28dd`: existing REAP-25B Claude-as-Judge raw-score evidence
  from `epyc-inference-research` was promoted into
  `roles.reap_25b_frontdoor.performance` with overall `110/183 (60%)` and
  suite totals `thinking 14/30`, `general 21/30`, `math 13/30`,
  `agentic 26/30`, `coder 18/30`, and `instruction_precision 18/33`.
  Regenerated descriptors/priors project `quality_overall: 0.6011`; REAP
  `Missing quality suite_vector evidence` and `Missing overall quality prior`
  warnings are gone. At that point REAP still had
  `Missing enable_thinking compatibility evidence`, which was cleared by
  `865b2b1`.
- Completed in `865b2b1`: descriptor acceleration now carries structured
  `thinking_control` evidence alongside legacy boolean `enable_thinking`.
  Registry evidence was added for `ingest_long_context`, `worker_vision`,
  `vision_escalation`, and `reap_25b_frontdoor`; generated descriptors and
  stack priors now preserve native/no-toggle/template-ignored behavior without
  forcing `enable_thinking` true/false. Enable-thinking compatibility gaps are
  cleared for ingest, REAP, and VL roles.
- Completed in `54b7c77`: shared-runtime alias mismatch notes for
  `worker_general`, `worker_math`, and `toolrunner` are structured provenance,
  not gaps. Generated descriptors and stack priors are now `status: compiled`;
  stack-prior role records have empty `known_gaps`.
- Completed in `03ed49f`: `Role.ARCHITECT_CODING` is now an enum alias of live
  `Role.ARCHITECT_GENERAL`, legacy `"architect_coding"` strings normalize to
  `architect_general`, and default/strict guards are clean.
- Completed in `e7fab9d`: KV adaptive compression and legacy tool permission
  lookup now normalize stale role runtime surfaces. `coder_escalation` and
  `worker_summarize` use shared frontdoor layer evidence, retired
  `architect_coding` is absent from active KV layer tables, roles without
  current layer evidence fall back to uniform compression, production port
  helpers use live role names, and `ToolRegistry` compatibility strings
  canonicalize via `Role.from_string()`.
- Completed in `603ad6b`: AutoPilot system-card generation now renders active
  `live_stack` role rows from `orchestration/derived/stack_priors.yaml`,
  including shared aliases and launch port sets. Raw registry rows are
  degraded fallback only; tests prove stale registry/candidate rows do not leak
  into the controller prompt.
- Completed in `b8a1abc`: hardcoded-surface scanner coverage now flags stale
  launch-wrapper static inventory in `scripts/server/*.sh`, including removed
  architect role/port, old model names, fixed RAM totals, and obsolete
  HOT/core wording. Focused guard tests cover both the stale and
  manifest-derived shapes.
- Completed in `0573e02`: stack status now includes an `ATTEST` column backed
  by read-only live process cmdline attestation. Concrete GGUF paths are
  checked against `/proc/<pid>/cmdline`; basename or full-path matches report
  `ok`, mismatched live GGUF paths report `model-drift` with an attestation
  warning, Docker-managed rows report `docker`, preserved or non-concrete
  model strings report `n/a`, unavailable cmdlines report `unknown`, and dead
  processes report `dead`. Changed orchestrator files:
  `scripts/server/stack_commands.py`, `scripts/server/stack_processes.py`,
  `tests/unit/test_stack_processes.py`, and
  `tests/unit/test_orchestrator_stack_reload.py`.
- Completed in `6af8b3d`: comparative seeding reward throughput priors now
  expose public provenance via `throughput_prior_provenance(cost_config=None)`
  and a shared private resolver. Provenance reports source
  (`config_override`, `legacy_config_override`, `stack_priors`,
  `degraded_fallback`, or `missing`), role list/count, stack-priors path,
  degraded-fallback flag, and missing/degraded reason. Reward math and the
  `compute_comparative_rewards` return shape are unchanged.
- Completed in `3e8121d`: descriptor compilation now projects
  `role.model.mmproj_path` into descriptor
  `serving.requirements.mmproj_path`; generated descriptors carry
  descriptor-native projector requirements for Qwen2.5-VL and Qwen3-VL roles,
  and regenerated stack priors preserve those requirements for downstream
  launch/status consumers.
- Completed in `d59029a`: stack status auxiliary port scanning now derives the
  scan set from `PORT_MAP.values()` instead of a hardcoded native aux-port set,
  and tests cover manifest-only auxiliary ports so future launch-manifest
  additions are scanned automatically.
- Completed in `6062a57`: stack status scanning now also reads generated
  `orchestration/derived/stack_priors.yaml` serving records and includes only
  integer `serving.ports` from `deployment_status: live_stack` roles. Candidate
  stack-prior ports and malformed port values are excluded, while prior-only
  live ports are included alongside manifest HOT/WARM, NUMA replica, Docker,
  and `PORT_MAP` cleanup ports.
- Completed in `53f12e0`: proactive delegation now routes `/think`,
  `/ultrathink`, and related deep-reasoning trigger phrases to live
  `architect_general` instead of the removed dedicated thinking role. Adjacent
  comments were updated and `tests/unit/test_proactive_delegator.py` carries
  the regression.
- The lean registry already has competing source sections: `server_mode.*`
  reflects live launch intent, while older `roles.*.memory` and
  `process_layout.*` can lag. Consumers need declared precedence and validators.
- Known hardcoded/stale surfaces now exclude this low-risk runtime/controller
  cleanup class. Remaining tracked surfaces are legacy-test/historical-doc
  references and other classified consumer migrations that still need
  generated-source ownership.

## Waypoints

- [x] **W1 — Stack truth precedence spec** (completed in `a1e04d5`): document a single
  precedence order for live serving facts: `server_mode` / stack manifest
  outranks `roles.*` narrative fields, descriptors compile from both but mark
  contradictions, and generated consumers must record source + precedence.
  Acceptance met by
  `epyc-orchestrator/docs/reference/stack-truth-precedence.md`, including
  `server_mode.tier=hot` vs `roles.memory.residency=warm`, shared mmap roles,
  retired roles, and benchmark/candidate roles.
- [x] **W2 — Derived stack-priors generator** (completed in `a1e04d5`): add a generator that
  compiles one machine-readable artifact from registry + descriptors, e.g.
  `orchestration/derived/stack_priors.yaml`. It must include role -> model id,
  role -> serving endpoint/server, TPS, quality priors, memory residency cost,
  acceleration/launch requirements, and source evidence. No consumer should
  re-parse free-text registry comments independently.
- [ ] **W3 — Stack drift validator** (PARTIAL in `a1e04d5` + `bfa90fa` + `f49f14d` + `69057f3` + `7917535` + `a7b72a9` + `a001017` + `33c81ff` + `fb0fd6d` + `837829f` + `b8477b0` + `2ea28dd` + `865b2b1` + `54b7c77` + `03ed49f` + `e7fab9d` + `603ad6b` + `b8a1abc` + `0573e02` + `6062a57` + `069f8c0` + `22ea541` + `705065d` + `e61e61f` + `828552f` + `079ff30` + `2baaee5` + `a7927c2` + `b026f7d` + `ebd929b` + `3a20efd` + `34a0407` + `2cb3d6c` + `7815318`): add a CI/local validator that
  fails on retired active roles, server/role topology contradictions, stale
  hardcoded role lists, missing descriptor evidence, unindexed model ids, and
  generated-prior drift. It should print remediation paths, not silently patch.
  Current loose mode passes with warnings and validates artifact freshness plus
  hard live invariants. The hardcoded-surface scanner now exposes production
  blockers in seeding/eval defaults, API/config/routing surfaces, role
  compatibility aliases, and runtime helpers. Procedure input/schema role enums are now
  exact-generated from stack priors and fail the guard on drift. The generated
  artifact now carries a versioned structural contract, contract v2 requires
  `serving.launch.entries`, contract v3 requires launch requirements and
  effective context witness fields, and missing required
  role/serving/prior/launch fields fail validation. Shared-runtime alias
  semantics now compile without role/server conflict gaps for `worker_math`
  and `toolrunner`. Contract v4 runtime witness projection landed in
  `33c81ff`; generated priors now include guarded effective runtime records.
  Simulated data-only stack-change fixtures landed in `fb0fd6d`, exercising
  shared-runtime swaps, retired-role removal, stale runtime requirements, and
  context/KV/acceleration drift without production-code edits.
  Live stack status attestation landed in `0573e02`: the status table now
  compares concrete expected GGUF paths with each live process cmdline and
  flags mismatched live GGUFs as `model-drift` instead of treating a fresh
  generated manifest as sufficient proof of deployment.
  Architect quality evidence landed in `837829f`; generated descriptors and
  stack priors now carry `quality_overall: 0.8567` for
  `architect_general`/`qwen35_122b_q4km`. GGUF header context extraction landed
  in `b8477b0`; generated descriptors and stack priors now project structured
  `ctx_max` for Qwen3-Next 80B, Qwen3.5-122B, Qwen2.5-VL 7B, Qwen3-VL 30B,
  and REAP-Qwen3-Coder 25B, clearing the `Missing structured ctx_max` warning
  class and reducing guard output to 15 known warnings. REAP quality evidence
  landed in `2ea28dd`; generated descriptors and stack priors now carry
  `quality_overall: 0.6011` from the existing Claude-as-Judge raw-score totals,
  removing REAP quality gaps. Thinking-control evidence landed in `865b2b1`;
  generated descriptors and stack priors now carry structured
  `acceleration.thinking_control` for ingest, REAP, and VL roles while leaving
  legacy `enable_thinking` unset when behavior is native/no-toggle or the
  template ignores the toggle. Enable-thinking compatibility gaps are cleared.
  Shared-runtime alias provenance landed in `54b7c77`; alias mismatch records
  now live in descriptor `role_bindings.alias_overrides` and stack-prior
  `evidence.alias_overrides`, generated descriptors/priors compile cleanly, and
  stack-prior records have empty `known_gaps`.
  Hardcoded-surface exceptions now
  require owner/rationale/expiry metadata and remain visible as waived warnings.
  The default pipeline acceptance gate now prints pass/block state (`079ff30`),
  classifies the two intentional retired-role compatibility surfaces as waived
  exceptions (`2baaee5`), and summarizes hardcoded-surface warning categories in
  the footer (`a7927c2`).
  Launch-command parity witnesses landed in `b026f7d`: test-only expected
  command fragments for `worker_general` MTP and VL launch requirements now
  come from generated stack priors instead of duplicated literals, while
  launcher/startup behavior is unchanged.
  The promotion gate was extended in `ebd929b` so the printed no-inference
  command now includes both simulated data-only stack-change fixtures and
  launcher-helper parity tests.
  Optional execution landed in `3a20efd`: `check --run-promotion-gate` runs
  those no-inference targets after the earlier stack-change checks pass, while
  default `check` remains reference-only.
  Scanner rule inventory exposure landed in `34a0407`: the guard now returns a
  machine-readable inventory through `hardcoded_surface_rule_inventory()` and
  prints YAML or JSON via `--list-hardcoded-surface-rules`, giving operators a
  stable catalog of hardcoded-surface rules without changing enforcement
  semantics.
  Surface summary mode landed in `2cb3d6c`: `--surface-summary-only` compacts
  hardcoded-surface scan warnings into category counts for operator reports,
  while default detailed warning output and canonical pipeline behavior remain
  unchanged.
  Scanner-rule ownership enforcement landed in `7815318`:
  `orchestration/stack_change_surface_manifest.yaml` gives every
  hardcoded-surface scanner rule exactly one owner/policy/review/evidence/drift
  entry, `--list-hardcoded-surface-rules` enriches rule inventory with that
  ownership metadata, and the canonical pipeline now fails if scanner-rule
  ownership drifts.
  The generated artifact source metadata was refreshed after the latest
  retired-role exception commit in `cbaceec`; descriptor-backed quality priors
  for measured roles landed in `bda46b1` with a post-commit metadata refresh in
  `762e6b0`.
  Strict mode intentionally fails until descriptor gaps are resolved and the
  remaining model-specific consumers migrate or receive explicit exception
  metadata.
- [ ] **W4 — Consumer migration** (2-3 days): migrate q_scorer, AutoPilot
  planner signatures, seeder per-role eval config, bilinear scorer model
  features, eval-tower model signatures, and launch-arg assembly to the derived
  artifact or descriptor API. Keep fallbacks for degraded scripts, but require
  tests proving fallback mode is explicit and cannot mask live drift.
  Current status: AutoPilot planner signatures (`73ed436`), q_scorer priors
  (`d5fe713`/`15d8cff` plus alias-quality propagation in `9ed177d`), and seeding default role/cost-tier discovery
  (`72f7dc2` plus live per-role discovery in `2e31055`) have migrated
  partially; bilinear model features now prefer
  stack-prior model specs (`10b3bce`); `orch status` now derives probe targets
  from stack priors (`1fe12ec`); procedure role/schema enums sync from stack
  priors (`f49f14d`); admission limits now derive from stack-prior serving
  ports/slots with a non-retired fallback (`1199f03`); retired API examples and
  delegation budgets have been cleaned up (`5e7d774`, `b1402a2`); chat pipeline
  architect branch checks now exclude retired `architect_coding` (`481516c`);
  chat routing task-type mapping no longer hardcodes the retired role
  (`519f710`); `/v1/models` reads live roles from stack priors (`d9c053c`);
  dashboard task-liveness overrides no longer include retired roles (`1b9db81`);
  inference lock/tap heavy-role classifications no longer include retired roles
  (`6bc1f51`); approval-gate high-cost classification no longer includes
  retired roles (`e6e10d8`); chat routing heuristic priors now filter through
  live stack-prior roles (`eb4dac5`); role docs and active PydanticGraph /
  LangGraph topology no longer expose a retired architect-coding node
  (`0b1e5e9`, `3c7a85e`); proactive deep-reasoning trigger routing now targets
  live `architect_general` instead of the removed thinking role (`53f12e0`).
  Seeding reward TPS/cost priors migrated to stack-prior discovery in the
  expanded CRITICAL-path pass `7ecf847`; `6af8b3d` adds explicit throughput
  prior provenance for config override, stack-prior, degraded fallback, and
  missing paths without changing comparative reward math. GraphRouter training
  fleet discovery now loads live stack-prior roles instead of a stale hardcoded
  model roster (`8cf0310`), and GraphRouter classifier/verifier extraction now
  derives live action spaces from stack priors/classifier artifacts (`1f16759`). Vision
  ReAct VL port routing now reads stack-prior serving records instead of a
  local `_VL_PORT_MAP` (`06ff53c`). Shared `server_mode` alias-port drift now
  warns through `validate_against_registry()` (`40d46ea`). AutoPilot preflight
  model-server health targets now derive from stack-prior serving records
  (`a5aaafb`), and AutoPilot human program guidance now derives compaction
  endpoints from stack priors (`60733c7`) with recurrence scanner coverage
  (`cf73ac1`). Generated live serving endpoint/primary-port/tier drift now
  fails the stack-change guard against the computed launch manifest (`312b28e`);
  exact launch port sets are generated and guarded (`dc14196`), contract v2
  launch-entry witness data is generated and guarded (`7917535`), and
  shared-runtime descriptor aliases now preserve live role coverage without
  standalone stale Qwen runtime descriptors (`a7b72a9`). Contract v3 now
  generates and guards effective launch context plus worker/VL model-path
  requirements (`a001017`). Parallel step executor burst-worker eligibility now
  derives from live warm worker records in stack priors and defaults unknown
  burst execution/error reporting to `worker_general` instead of retired
  `worker_fast` (`cc401c0`). Runtime worker concurrency caps now derive from
  the same live warm-worker stack-prior criteria and fail closed to single-lane
  execution when no live warm worker exists (`f41f956`). Runtime inference lock
  classes now derive from generated live stack-prior roles when available;
  shared worker-pool/vision roles use shared locks, missing or unknown roles fail
  closed to exclusive locks, and explicit `shared=` overrides remain authoritative
  (`822482b`). Scheduling/contention current-role assertions are now pinned to
  the real stack matrix in `eed215d`, including current n-way light/heavy
  classes, retired `worker_fast` absence from matrix light roles, and same-role
  `vision_escalation` ALLOW behavior. Legacy/model-generated routing ingress
  labels now normalize before config lookup in `3e4ba7c`: `/chat` and
  OpenAI-compatible paths map `coder` to `coder_escalation` and retired/generated
  worker aliases to `worker_general`, chat delegation keeps live targets while
  normalizing compatibility aliases, and REPL `delegate` / `my_role` no longer
  advertise retired worker aliases as live targets. Delegation report preambles
  now use the same canonicalization in `6ec2686`: compact specialist report
  prompts advertise only live `coder_escalation` / `worker_general` preambles
  while `worker_coder`, `worker_explore`, and `worker_fast` remain compatibility
  aliases that resolve to live-role prompt text. Architect investigation prompts
  now match the same live-role policy in `09948db`: active templates, fallback
  text, and system examples point implement/file-split work at
  `coder_escalation`, investigation/search work at `worker_general`, and omit
  retired worker labels from the valid role list. Output formalization now also
  routes to live `worker_general` in `4bf8061` instead of the legacy
  `worker_explore` label, and the helper docstring no longer carries stale
  speed/port assumptions. User-modeling preference extraction follows the same
  live-worker policy in `a9424a9`, with tests asserting `worker_general` as the
  `llm_call` role. Post-hoc model grading specs and defaults now also point at
  live `worker_general` in `a7c9ac0`, with fallback/default and explicit
  override behavior covered by model-grader tests; debugger prompt grading-role
  documentation follows the same `worker_general` contract in `4f9123f`.
- [ ] **W5 — Simulated model-swap CI gate** (1 day): implement a no-inference
  CI test that swaps one deployed role to a candidate descriptor/registry record
  and proves all derived consumers update with zero code edits. Acceptance:
  at least two simulated swaps pass, including one shared-mmap role and one
  retired-role removal.
- [ ] **W6 — Stack-change runbook and launch hook** (1 day): wire the validator
  into `orchestrator_stack.py` compile/start paths and document the operator
  command sequence. Launch should fail closed unless descriptors and derived
  priors are fresh or an explicit diagnostic override is used. Current status:
  command skeleton exists in `e01d64d` with preview fixes in `fe4b2aa`,
  acceptance/promotion-gate output in `079ff30`, intentional retired-role
  exception metadata in `2baaee5`, and warning category summaries in `a7927c2`,
  but
  descriptor compiler quality-key normalization in `3e7efce`, model-ID
  stabilization in `ca9af53`, and fail-closed descriptor removal protection in
  `022a0d1`; REAP coverage is structured through `fbef837`/`365e370`; domain
  modalities are generated in `846c2d4`; shared-alias `PORT_MAP` drift is fixed
  and recurrence-tested in `d4acf24`; active VL ReAct port routing now consumes
  stack-prior serving records in `06ff53c`; shared `server_mode` alias-port
  validation is covered in `40d46ea`; AutoPilot preflight health probes consume
  stack-prior endpoints in `a5aaafb`; exact launch ports are projected in
  `dc14196`; launch-entry witness contract v2 is projected in `7917535`;
  effective launch context and worker/VL model-path requirements are projected
  in `a001017`; effective runtime/binary/KV/flag witness records are projected
  and guarded in `33c81ff`; launcher parity tests now derive `worker_general`
  MTP and VL command witnesses from stack priors in `b026f7d`, the promotion
  gate includes those parity tests in `ebd929b`, and `3a20efd` can execute the
  no-inference promotion targets on request; stack status now attests expected
  concrete model
  paths against live process cmdlines in `0573e02`; descriptor-native
  Qwen2.5-VL/Qwen3-VL projector requirements landed in `3e8121d`;
  auxiliary status-scan ports now derive from `PORT_MAP` in `d59029a`;
  generated live stack-prior serving ports are included in status scanning in
  `6062a57`; API health backend probes now derive grouped live targets from
  stack priors in `3dc21c5`; summarization chunk-digest worker selection now
  reads live stack-prior workers in `5b4f683`; parallel same-wave burst worker
  selection now reads live warm worker records from stack priors and fails
  closed to sequential execution when none exist in `cc401c0`; runtime worker
  concurrency caps now read live warm-worker stack-prior slots and fail closed
  to single-lane execution in `f41f956`;
  GGUF-derived `ctx_max` projection landed in
  `b8477b0`; REAP quality projection landed in `2ea28dd`; descriptor-native
  thinking-control evidence landed in `865b2b1`; shared-runtime alias
  provenance landed in `54b7c77`. Broader stack-change work now moves to the
  temporary retired-role enum waiver, remaining hardcoded-surface cleanup, and
  consumer migrations.

## Dependency Graph

- W1 blocks W2/W3 because consumers need a declared precedence model.
- W2 blocks W4/W5 because consumers need one artifact/API to consume.
- W3 can proceed after W1 and should run before each W4 migration.
- W4 and W5 are parallel after W2/W3.
- W6 depends on W2-W5 because launch hooks must enforce the final generated
  contract, not an intermediate one.

## Cross-Cutting Concerns

- **Model descriptors**: this handoff is the governance shell around
  `model-capability-descriptors.md` W3/W4. Descriptor compilation stays the
  model-agnostic interface; this handoff ensures downstream consumers cannot
  bypass it with stale constants.
- **Routing and q_scorer**: q_scorer must not keep role/model/memory defaults
  as hidden policy. Its fallbacks are degraded-mode only and must be tested as
  such.
- **Launch truth**: `orchestrator_stack.py`, `server_mode`, and runtime
  attestation must agree. If launch args are special-cased by role name
  (`_NO_SPEC_DECODE`, ik binary paths, MTP knobs), the generated artifact must
  either own that mapping or mark it unresolved.
- **Benchmark provenance**: MEASUREMENT.md claim grammar still applies. Derived
  TPS/quality values must carry source evidence, date, protocol, and stale/gap
  markers.
- **Docs and tests**: stale docs/tests can reintroduce bad constants. The drift
  validator should scan docs/tests for retired live-role claims separately from
  production-code blockers.

## Key File Locations

- `epyc-orchestrator/orchestration/model_registry.yaml`
- `epyc-orchestrator/orchestration/model_descriptors.yaml`
- `epyc-orchestrator/scripts/registry/compile_descriptors.py`
- `epyc-orchestrator/scripts/registry/compile_stack_priors.py`
- `epyc-orchestrator/scripts/registry/sync_procedure_role_enums.py`
- `epyc-orchestrator/src/registry/model_descriptors.py`
- `epyc-orchestrator/src/registry/stack_priors.py`
- `epyc-orchestrator/docs/reference/stack-truth-precedence.md`
- `epyc-orchestrator/orchestration/derived/stack_priors.yaml`
- `epyc-orchestrator/orchestration/procedure.schema.json`
- `epyc-orchestrator/orchestration/procedures/add_model_to_registry.yaml`
- `epyc-orchestrator/scripts/validate/stack_change_guard.py`
- `epyc-orchestrator/src/api/admission.py`
- `epyc-orchestrator/src/scheduling/contention.py`
- `epyc-orchestrator/src/runtime/inference_lock.py`
- `epyc-orchestrator/orchestration/repl_memory/q_scorer.py`
- `epyc-orchestrator/scripts/benchmark/seeding_types.py`
- `epyc-orchestrator/scripts/benchmark/seeding_rewards.py`
- `epyc-orchestrator/orchestration/repl_memory/bilinear_scorer.py`
- `epyc-orchestrator/scripts/autopilot/state_store.py`
- `epyc-orchestrator/scripts/server/orchestrator_stack.py`
- `epyc-orchestrator/scripts/server/stack_commands.py`
- `epyc-orchestrator/scripts/server/stack_processes.py`
- `epyc-orchestrator/orchestration/model_quality_signatures.yaml`
- `epyc-orchestrator/tests/unit/test_scheduling_contention.py`
- `epyc-orchestrator/tests/unit/test_scheduling_contention_gate.py`
- `epyc-orchestrator/tests/unit/test_admit_set.py`
- `epyc-orchestrator/tests/unit/test_q_scorer.py`
- `epyc-orchestrator/tests/unit/test_inference_lock.py`
- `epyc-orchestrator/tests/unit/test_model_descriptor_compiler.py`
- `epyc-orchestrator/tests/unit/test_model_descriptors_schema.py`

## Proposed Validation Commands

Run after any stack/model change and before an AutoPilot restart:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
python3 -m py_compile src/registry/stack_priors.py scripts/registry/compile_stack_priors.py scripts/registry/sync_procedure_role_enums.py scripts/validate/stack_change_guard.py orchestration/repl_memory/q_scorer.py scripts/registry/compile_descriptors.py src/registry/model_descriptors.py
uv run python scripts/registry/compile_descriptors.py --dry-run --allow-incomplete
uv run python scripts/registry/compile_stack_priors.py --allow-incomplete
python3 scripts/registry/sync_procedure_role_enums.py --check
uv run python scripts/validate/stack_change_guard.py
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces
uv run --with pytest pytest -q tests/unit/test_stack_priors_compiler.py tests/unit/test_stack_change_guard.py tests/unit/test_sync_procedure_role_enums.py tests/unit/test_model_descriptors_schema.py tests/unit/test_model_descriptor_compiler.py tests/unit/test_q_scorer.py
uv run --with ruff ruff check src/registry/stack_priors.py scripts/registry/compile_stack_priors.py scripts/registry/sync_procedure_role_enums.py scripts/validate/stack_change_guard.py orchestration/repl_memory/q_scorer.py scripts/registry/compile_descriptors.py src/registry/model_descriptors.py
git diff --check
```

Future W3/W6 should replace this with a single strict command after descriptor
gaps close, e.g. `uv run python scripts/validate/stack_change_guard.py --strict`.

## Acceptance Criteria

- A stack/model change can update role -> model/serving facts in one source and
  regenerate all model-specific consumer quantities without hand-editing
  q_scorer, planner signatures, seeder config, bilinear features, or launch args.
- Retired roles such as `architect_coding` cannot remain in live priors,
  generated signatures, launch manifests, or active routing chains unless
  explicitly marked legacy/test-only.
- Shared-mmap roles such as `frontdoor` and `coder_escalation` carry one model
  identity and do not double-count memory cost.
- HOT roles such as `architect_general` and `ingest_long_context` do not receive
  WARM memory penalties because older role/process-layout fields lagged.
- CI or launch fails closed on stale generated artifacts, missing descriptor
  evidence, or contradictory live serving facts.

## Reporting

After each waypoint:

- Update this handoff with commit hashes, validator output, and any unresolved
  source-of-truth contradictions.
- Update `model-capability-descriptors.md` only when W3/W4 consumer ownership
  changes; GitNexus currently marks it HIGH blast radius.
- Update `routing-and-optimization-index.md` and `master-handoff-index.md` only
  in a deliberate doc-sync pass; GitNexus currently marks them CRITICAL/HIGH.
- Add a progress entry with exact commands and whether AutoPilot was paused or
  running.
