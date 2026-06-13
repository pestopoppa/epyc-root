# Stack Change Governance Pipeline

**Status**: IN PROGRESS 2026-06-13 — W1/W2 landed; W3 guardrail/scanner/procedure-enum/contract/exception checks live, strict mode blocked on descriptor and consumer gaps
**Created**: 2026-06-13
**Priority**: HIGH — prevents silent stale model constants after stack changes; no inference required for W1-W4
**Related**: [model-capability-descriptors.md](model-capability-descriptors.md), [routing-truth-restoration.md](routing-truth-restoration.md), [dynamic-stack-concurrency.md](dynamic-stack-concurrency.md), [bulk-inference-campaign.md](bulk-inference-campaign.md), [MEASUREMENT.md](../../MEASUREMENT.md)

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
- Approval-gate high-cost role classification dropped retired
  `architect_coding` in `epyc-orchestrator` `e6e10d8`; live guard warnings
  dropped from 76 to 75.
- Chat routing heuristic priors migrated to live stack-prior role filtering in
  `epyc-orchestrator` `eb4dac5`, with a non-retired degraded fallback; live
  guard warnings dropped from 75 to 74 after broader routing/pipeline tests.
- The lean registry already has competing source sections: `server_mode.*`
  reflects live launch intent, while older `roles.*.memory` and
  `process_layout.*` can lag. Consumers need declared precedence and validators.
- Known hardcoded/stale surfaces still include
  `orchestration/model_quality_signatures.yaml`, seeding/eval scripts that
  still name `architect_coding`, API/config/routing and LangGraph retired-role
  paths, and docs/tests that can preserve outdated model assumptions.

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
- [ ] **W3 — Stack drift validator** (PARTIAL in `a1e04d5` + `bfa90fa` + `f49f14d` + `69057f3`): add a CI/local validator that
  fails on retired active roles, server/role topology contradictions, stale
  hardcoded role lists, missing descriptor evidence, unindexed model ids, and
  generated-prior drift. It should print remediation paths, not silently patch.
  Current loose mode passes with warnings and validates artifact freshness plus
  hard live invariants. The hardcoded-surface scanner now exposes production
  blockers in seeding/eval defaults, API/config/routing surfaces, LangGraph
  nodes, and runtime helpers. Procedure input/schema role enums are now
  exact-generated from stack priors and fail the guard on drift. The generated
  artifact now carries a versioned structural contract, and missing required
  role/serving/prior fields fail validation. Hardcoded-surface exceptions now
  require owner/rationale/expiry metadata and remain visible as waived warnings.
  Strict mode intentionally fails until descriptor gaps are resolved and the
  remaining model-specific consumers migrate or receive explicit exception
  metadata.
- [ ] **W4 — Consumer migration** (2-3 days): migrate q_scorer, AutoPilot
  planner signatures, seeder per-role eval config, bilinear scorer model
  features, eval-tower model signatures, and launch-arg assembly to the derived
  artifact or descriptor API. Keep fallbacks for degraded scripts, but require
  tests proving fallback mode is explicit and cannot mask live drift.
  Current status: AutoPilot planner signatures (`73ed436`), q_scorer priors
  (`d5fe713`/`15d8cff`), and seeding default role/cost-tier discovery
  (`72f7dc2`) have migrated partially; bilinear model features now prefer
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
  live stack-prior roles (`eb4dac5`).
  `seeding_rewards.py` remains deferred because GitNexus marks
  `compute_comparative_rewards` CRITICAL.
- [ ] **W5 — Simulated model-swap CI gate** (1 day): implement a no-inference
  CI test that swaps one deployed role to a candidate descriptor/registry record
  and proves all derived consumers update with zero code edits. Acceptance:
  at least two simulated swaps pass, including one shared-mmap role and one
  retired-role removal.
- [ ] **W6 — Stack-change runbook and launch hook** (1 day): wire the validator
  into `orchestrator_stack.py` compile/start paths and document the operator
  command sequence. Launch should fail closed unless descriptors and derived
  priors are fresh or an explicit diagnostic override is used.

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
- `epyc-orchestrator/orchestration/repl_memory/q_scorer.py`
- `epyc-orchestrator/orchestration/repl_memory/bilinear_scorer.py`
- `epyc-orchestrator/scripts/autopilot/state_store.py`
- `epyc-orchestrator/scripts/server/orchestrator_stack.py`
- `epyc-orchestrator/orchestration/model_quality_signatures.yaml`
- `epyc-orchestrator/tests/unit/test_q_scorer.py`
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
