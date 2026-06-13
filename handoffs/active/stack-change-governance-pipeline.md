# Stack Change Governance Pipeline

**Status**: IN PROGRESS 2026-06-13 — W1/W2 landed; W3 guardrail/scanner/procedure-enum/contract/exception checks live through stack-prior contract v4 launch-runtime witness, simulated data-only workflow fixtures, architect/REAP quality projection, GGUF-derived model context projection, structured thinking-control evidence, shared-runtime alias provenance, retired-role alias normalization, stale role runtime-surface cleanup, launch-wrapper static-inventory recurrence guard, stack-prior-rendered AutoPilot system-card rows, read-only live process cmdline attestation in stack status, and seeding throughput-prior provenance; generated descriptors/priors are `status: compiled` with empty stack-prior `known_gaps`; `stack_change_pipeline.py check --allow-known-gaps` reports descriptor/stack-prior/procedure/guard/strict OK, while `--all-hardcoded-surfaces` now reports only legacy-test/historical-doc classes for this cleanup track
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
- [ ] **W3 — Stack drift validator** (PARTIAL in `a1e04d5` + `bfa90fa` + `f49f14d` + `69057f3` + `7917535` + `a7b72a9` + `a001017` + `33c81ff` + `fb0fd6d` + `837829f` + `b8477b0` + `2ea28dd` + `865b2b1` + `54b7c77` + `03ed49f` + `e7fab9d` + `603ad6b` + `b8a1abc` + `0573e02`): add a CI/local validator that
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
  live stack-prior roles (`eb4dac5`); role docs and active PydanticGraph /
  LangGraph topology no longer expose a retired architect-coding node
  (`0b1e5e9`, `3c7a85e`).
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
  requirements (`a001017`).
- [ ] **W5 — Simulated model-swap CI gate** (1 day): implement a no-inference
  CI test that swaps one deployed role to a candidate descriptor/registry record
  and proves all derived consumers update with zero code edits. Acceptance:
  at least two simulated swaps pass, including one shared-mmap role and one
  retired-role removal.
- [ ] **W6 — Stack-change runbook and launch hook** (1 day): wire the validator
  into `orchestrator_stack.py` compile/start paths and document the operator
  command sequence. Launch should fail closed unless descriptors and derived
  priors are fresh or an explicit diagnostic override is used. Current status:
  command skeleton exists in `e01d64d` with preview fixes in `fe4b2aa`, but
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
  and guarded in `33c81ff`; stack status now attests expected concrete model
  paths against live process cmdlines in `0573e02`; GGUF-derived `ctx_max`
  projection landed in
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
- `epyc-orchestrator/orchestration/repl_memory/q_scorer.py`
- `epyc-orchestrator/scripts/benchmark/seeding_rewards.py`
- `epyc-orchestrator/orchestration/repl_memory/bilinear_scorer.py`
- `epyc-orchestrator/scripts/autopilot/state_store.py`
- `epyc-orchestrator/scripts/server/orchestrator_stack.py`
- `epyc-orchestrator/scripts/server/stack_commands.py`
- `epyc-orchestrator/scripts/server/stack_processes.py`
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
