# Stack Change Governance Pipeline

**Status**: IN PROGRESS - canonical stack-change command, generated
stack-prior contract, guard/scanner ownership, runtime attestation, launch and
preflight gates, promotion-gate execution, and representative swap-CI witnesses
are live. Remaining work is high-risk consumer migration and waiver hygiene;
completed governance history through 2026-06-19 is compacted under
`Completed Scope`.
**Created**: 2026-06-13
**Updated**: 2026-07-26
**Priority**: HIGH — prevents silent stale model constants after stack changes; no inference required for W1-W4
**Related**: [standardized-stack-update-pipeline-finalization.md](standardized-stack-update-pipeline-finalization.md), [model-capability-descriptors.md](model-capability-descriptors.md), [routing-truth-restoration.md](routing-truth-restoration.md), [dynamic-stack-concurrency.md](dynamic-stack-concurrency.md), [bulk-inference-campaign.md](bulk-inference-campaign.md), [MEASUREMENT.md](../../MEASUREMENT.md)

> **2026-06-13 finalization bridge**: [standardized-stack-update-pipeline-finalization.md](standardized-stack-update-pipeline-finalization.md) consolidates the older audits into the main workflow pickup plan. Use that file for the next implementation pass; continue recording commit-level progress and guard counts here.

## 2026-07-26 Staleness Review

W4 remains active in the [routing and optimization
index](routing-and-optimization-index.md) and
[design-backlog triage](design-backlog-triage-2026-07-23.md). The v8
registration repair (`epyc-orchestrator` `e923a40b`) is current evidence that
generated priors and consumer probes must stay aligned; it does not complete
the remaining high-risk consumer migration or waiver-hygiene work.

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

## Current Baseline

- Canonical check: `uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate` in `epyc-orchestrator`.
- Generated descriptors and stack priors are compiled with empty stack-prior
  `known_gaps` for live roles.
- Guard ownership is machine-readable through
  `orchestration/stack_change_surface_manifest.yaml`; hardcoded-surface rule
  inventory and compact summary output are available for operator review.
- Runtime attestation checks model/mmproj paths, known-stack listeners, state
  gaps, concrete launch flags, context/KV/spec flags, binary path, and related
  llama-server runtime evidence.
- Promotion-gate execution includes the simulated stack-change fixtures and
  launch-parity witnesses; swap-CI has representative q_scorer/operator
  summary/system-card/health/dashboard/routing/API/long-context/vision coverage.
- Completed details are in the dated ledgers listed below and in daily
  `progress/` logs, not in this active handoff.

## Completed Scope

| Through | Historical ledger |
|---------|-------------------|
| 2026-06-15 | [standardized-stack-update-pipeline-finalization-history-2026-06-15.md](../archived/standardized-stack-update-pipeline-finalization-history-2026-06-15.md) and related active-handoff histories |
| 2026-06-19 | [stack-change-governance-pipeline-history-through-2026-06-19.md](../archived/stack-change-governance-pipeline-history-through-2026-06-19.md) |

## Waypoints

- [x] **W1 - Stack truth precedence spec**: live serving facts have documented precedence, shared-runtime alias handling, retired-role handling, and generated-consumer source evidence.
- [x] **W2 - Derived stack-priors generator**: descriptors compile the machine-readable stack-prior artifact consumed by validators and migrated consumers.
- [x] **W3 - Stack drift validator foundation**: freshness, structural contract, scanner ownership, exception metadata, runtime witness, surface summary, and promotion-gate reporting are live. Strict/future hardening continues through owned consumer surfaces rather than a new guard system.
- [ ] **W4 - Consumer migration**: continue migrating remaining stack-sensitive consumers to generated stack priors or explicit degraded fallbacks. Use the N11/N11a handoffs and `stack_change_surface_manifest.yaml` for prioritization.
  **2026-08-11 (`mainB`) — sized, and the reason it has stayed open is structural: THE MANIFEST
  RECORDS NO MIGRATION STATE.** `consumer_surfaces` carries 13 entries whose fields are
  `classification / consumer_scope / source_of_truth / promotion_blocker / review_cadence /
  drift_response / implementation_refs / owner / validation_command` — and **no** migration or
  status field. So "remaining consumers" is not a queryable set; every session that picks this row
  up must re-derive it from scratch, which is why it never closes.
  A mechanical screen over `implementation_refs` (does the file read generated priors / does it
  contain port literals) gives **5 clean, 8 mixed, 0 with no priors read at all**. **That is a
  SCREEN, not a verdict, and must not be quoted as "8 remaining"**: W4's own wording permits
  *"or explicit degraded fallbacks"*, and a regex cannot distinguish a **declared** fallback
  (compliant) from a **hardcoded copy** (not). Reporting the screen as a count would be the same
  category error as comparing a joint verdict to a single-axis threshold — see SEQ-A.
  **The unblocking step is therefore not migration work, it is a `migration_status` field on each
  `consumer_surfaces` entry** (`migrated` | `explicit_fallback` | `unmigrated`, with the evidence
  ref), so the set becomes queryable and the promotion gate can assert on it. That is a schema
  change to a governance artifact owned by `stack-change-governance`, so it is **proposed, not
  applied** — not something to land unattended overnight against a file with a promotion-blocker
  contract.
  Screen output for whoever takes it: clean = `routing_prior_consumers`, `admission_policy`,
  `lock_tap_policy`, `procedure_role_enums`, `generated_stack_docs`; needs a human read =
  `q_scorer_priors`, `seeding_reward_priors`, `config_model_catalog`, `health_preflight_probes`,
  `launch_maps`, `dashboard_status_system_cards`, `planner_prompt_guidance`, `runtime_attestation`.
- [x] **W5 - Simulated model-swap CI gate**: representative data-only stack swaps execute in the promotion gate and cover generated artifacts plus selected consumers.
- [x] **W6 - Stack-change runbook and launch hook**: production launch, AutoPilot preflight, and benchmark preflight use the canonical gate; bypasses are explicit diagnostics only.

## Dependency Graph

- W1 blocks W2/W3 because consumers need a declared precedence model.
- W2 blocks W4/W5 because consumers need one artifact/API to consume.
- W3 can proceed after W1 and should run before each W4 migration.
- W4 and W5 are parallel after W2/W3.
- W6 depended on W2-W5 because launch hooks needed to enforce the generated
  contract. The production launch hook and runbook are now live; future
  consumer migrations should extend the same promotion gate instead of adding
  separate launch checks.

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
