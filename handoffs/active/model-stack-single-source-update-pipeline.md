# Model Stack Single-Source Update Pipeline

**Status**: PARTIAL IMPLEMENTATION LANDED - stack-prior single-source contract,
runtime attestation, generated stack summaries, scanner-rule ownership,
production launch gate, AutoPilot preflight gate, direct benchmark runtime
enforcement, and representative frontdoor/worker/vision swap-CI coverage are
live. The `launch_maps` high-risk P2 surface is now explicitly guarded:
generated priors cover live llama launch entries, covered aliases are accepted
only when their primary role has a live prior record, and manifest-owned
auxiliary launch targets (`embedder*`, warm `worker_fast`, and launcher-only
`eval_batch_frontdoor`) are classified in the stack-change validator. Dashboard
expected-stack topology now also labels
manifest-owned warm embedder recipes (`8096/8097/8098`) by their auxiliary
roles instead of anonymous port names. WorkerPool now consumes stack-prior
primary ports and server-mode launch paths through the generated artifact, with
swap-CI proving a worker model/port replacement reaches the runtime config.
Route-local chat image/vision gating now consumes the generated vision-role
helper instead of a hardcoded legacy role set (`epyc-orchestrator` `f35448d1`).
Simulated swap-CI now also proves factual-risk role capability tiers follow
regenerated stack priors for worker, vision, and long-context swaps instead of
static degraded role defaults (`epyc-orchestrator` `cacd8c44`). Future swap-CI
expansion should follow new consumer migrations.
**Created**: 2026-06-13
**Priority**: HIGH - stale model-specific quantities can silently corrupt
routing, scoring, launch, planner prompts, replay analysis, and operator docs
after a stack change.
**History**:
[model-stack-single-source-update-pipeline-history-2026-06-15.md](../archived/model-stack-single-source-update-pipeline-history-2026-06-15.md)
and
[model-stack-single-source-update-pipeline-history-through-2026-06-19.md](../archived/model-stack-single-source-update-pipeline-history-through-2026-06-19.md)
preserve completed chronology compacted out of this active handoff.
**Related**:
[standardized-stack-update-pipeline-finalization.md](standardized-stack-update-pipeline-finalization.md),
[model-stack-update-pipeline-audit.md](model-stack-update-pipeline-audit.md),
[model-stack-change-standardization-audit.md](model-stack-change-standardization-audit.md),
[stack-change-governance-pipeline.md](stack-change-governance-pipeline.md),
[model-capability-descriptors.md](model-capability-descriptors.md)

## Objective

Make orchestration-stack changes reliable by ensuring model-specific facts are
updated once, then projected everywhere:

1. edit structured truth;
2. compile generated contracts;
3. validate all consumers and docs;
4. refuse launch, AutoPilot resume, or benchmark interpretation when generated
   truth and live/runtime facts disagree.

The concrete trigger remains the stale-quantity class of bug: shared models,
retired roles, HOT/WARM status, memory footprints, context windows, launch
ports, q_scorer costs, and prompt/operator labels must not be duplicated in
unowned local constants.

## Current Baseline

- Generated model descriptors and `orchestration/derived/stack_priors.yaml`
  are the source contract for live model, role, serving, launch, quality, and
  memory facts.
- Canonical stack-change checks are live for descriptor/stack-prior freshness,
  stack-manifest registry drift, q_scorer provenance, runtime attestation,
  production launch, AutoPilot preflight, and direct benchmark preflight.
- Current hardcoded-surface inventory is owned by
  `orchestration/stack_change_surface_manifest.yaml` with
  `consumer_surface_count=13` and `rule_count=27`; the previous active-code
  warning baseline is clean.
- Shared stack-prior helpers now cover the main config/admission, OpenAI
  model-list ordering, health, status, preflight, routing/action,
  prompt/delegation, benchmark/eval, and runtime-policy consumers. Completed
  details through 2026-06-19 are compacted in
  [model-stack-single-source-update-pipeline-history-through-2026-06-19.md](../archived/model-stack-single-source-update-pipeline-history-through-2026-06-19.md).
- `src.runtime.inference_tap` safe-mode stream policy now resolves its
  generated-prior or manifest-derived non-stream role set dynamically instead
  of freezing `SAFE_NON_STREAM_ROLES` at import time; the legacy module
  attribute remains available for compatibility.
- `src.runtime.inference_lock` exclusive/shared role policy now resolves its
  generated-prior or manifest-derived lock role sets dynamically instead of
  freezing `HEAVY_ROLES` / `LIGHT_ROLES` at import time; legacy module
  attributes remain available for compatibility.
- `src.api.routes.chat_routing` heuristic prior roles now keep generated stack
  priors as primary and derive degraded fallback candidates from the computed
  stack manifest instead of a four-role static tuple; embedding services are
  excluded and aliases are canonicalized.
- `src.api.admission` now keeps generated stack-prior slot limits as primary
  and derives degraded fallback URL/slot limits from the computed stack
  manifest at controller construction time instead of preserving an import-time
  static URL table; embedding services remain excluded from admission gating.
- `orchestration.repl_memory.bilinear_scorer` cold-start model features now
  keep generated stack priors as primary and derive degraded fallback specs
  from compiled model descriptors instead of a hand-maintained role/model
  feature table.
- `scripts.graph_router.train_graph_router` model-fleet training nodes now
  keep generated stack priors as primary and derive degraded fallback fleet
  records from compiled model descriptors instead of a static model-fleet table.
- `scripts.benchmark.seeding_rewards` throughput priors now keep generated
  stack priors as primary and derive explicit degraded fallback throughput from
  compiled model descriptors before falling back to the legacy static table.
- `scripts.benchmark.seeding_types` benchmark topology constants still keep
  generated stack priors as primary, but degraded fallback role/port/heavy-port
  discovery now derives from the lean registry `server_mode` records instead
  of preserving a separate current-stack role/port table.
- 2026-07-04 follow-up removed the remaining local YAML traversal from
  `scripts.benchmark.seeding_types._load_live_stack_prior_roles`; the seeding
  topology/default-role reader now uses the shared
  `src.registry.stack_priors.live_stack_role_records()` helper while preserving
  registry degraded fallback semantics. GitNexus impact for the loader was LOW
  (`impactedCount=21`), but it feeds benchmark seeding and AutoPilot seeder role
  refresh, so the migration was handled on the main thread.
- `scripts.registry.render_stack_summary` still keeps generated stack priors
  and compiled descriptors as the normal sources for operator/system-card role
  rows, while the last-resort raw-registry fallback now canonicalizes generic
  chain aliases and refuses retired or arbitrary server-mode aliases.
- AutoPilot controller system-card rendering now fails closed when the live
  generator is unavailable instead of falling back to checked-in
  `scripts/autopilot/system_card.md`; degraded controller guidance explicitly
  says live role/port/tier/throughput facts are unavailable and forbids using
  historical docs, memories, or old logs as authoritative stack truth.
- `scripts.autopilot.preflight_audit` was re-audited after the generated-prior
  migrations: live model-server targets already come from stack-prior serving
  URLs, while the remaining degraded fallback intentionally reads
  stack-manifest HOT/WARM auxiliary metadata and launch-mode filtering. Do not
  churn this surface unless a concrete duplicated role/port fact reappears.
- `src.api.routes.openai_compat` now uses the shared stack-prior primary-port
  helper for `/v1/models` ordering instead of keeping a route-local port
  resolver; explicit endpoint precedence and compatibility aliases are
  preserved.
- `src.services.worker_pool` now uses the shared stack-prior primary-port
  helper and generated launch requirements for worker model paths. The compiler
  and stack-change guard both treat explicit `server_mode.model_path`,
  `draft_model_path`, and `mmproj_path` as launch-requirement overrides on top
  of stack-manifest defaults, so a data-only worker swap updates the generated
  artifact before WorkerPool consumes it.
- `orchestration.repl_memory.routing_classifier` now canonicalizes saved and
  loaded classifier label maps through the GraphRouter action-space helper, so
  seeded frontdoor actions and legacy role aliases normalize to current routing
  targets instead of relying on a route-local `Role.from_string()` path.
- `src.api.routes.chat_pipeline.routing_decision.resolve_timeout` now resolves
  live request timeouts through the current config helper instead of the
  compatibility `ROLE_TIMEOUTS` import-time snapshot; `RoutingResult` uses the
  same current-config helper for escalation timeout lookups while preserving
  the legacy dict export for older importers.
- `src.services.escalation_prewarmer` now derives the architect prewarm
  endpoint and chat-template model hint from generated stack priors; legacy
  `ARCHITECT_PORTS` and `ARCHITECT_PORT_MODEL_HINT` imports remain as explicit
  degraded fallback compatibility only. This was a main-thread CRITICAL-risk
  migration because the prewarm path feeds live graph escalation.
- `src.api.routes.vision_serving` now derives the live vision role set from
  generated stack-prior launch metadata, and both chat-vision endpoint
  resolution paths consume that helper instead of a route-local static role
  set. Legacy `VISION_ROLES` and degraded VL ports remain compatibility exports
  only; a valid generated artifact with no vision launch roles no longer
  silently resurrects legacy vision roles. This was a main-thread HIGH-risk
  migration because it touches multimodal request routing.
- `src.classifiers.factual_risk` role capability tiers already derive from
  generated stack priors; the W4 simulated swap fixture now proves regenerated
  worker, vision, and long-context stack priors update factual-risk tier
  adjustment before static degraded role defaults can apply.
- X-MAS has an evidence-backed true function-axis 5x5 winner table and a
  default-off guarded enforce path. The 2026-06-21 quiet constrained-policy
  A/B carried `xmas_policy=incumbent_constrained_v1` and returned
  `decision.status=hold` (`score_delta=-0.25`, latency ratio `0.714`), but
  orchestrator `f517902d` repaired the same-cheap-role failure mode and
  `b108f865` versioned the repaired policy as
  `incumbent_constrained_cheapfirst_v2`. The 2026-07-03 repaired-policy
  quiet-window A/B (`benchmarks/results/runs/xmas_live_ab/20260703T213541Z-constrained-policy-v2`)
  returned `decision.status=promote_candidate` with no blockers
  (`score_delta=+0.10`, latency ratio `0.938`, lift domain `reasoning`,
  regression domains none). Production enforce remains default-off pending an
  explicit operator enablement/reload/attestation decision, not another held-out
  repaired-policy A/B.
- The 2026-06-20 read-only manifest audit found P1 closed and all named
  P2/HIGH surfaces either migrated, generated, or re-audited. The follow-up
  `launch_maps` audit verified that generated stack priors carry launch entries
  for live llama roles (`frontdoor`, `worker_general`, `architect_general`,
  `worker_vision`, `vision_escalation`) and the hardcoded-surface inventory is
  still `consumer_surface_count=13`, `rule_count=27`.
- The 2026-06-28 no-inference currentness recheck again found no active
  P2/HIGH migration tail: all-hardcoded-surface guard OK, canonical pipeline
  `summary: ok`, strict guard OK, runtime attestation OK, no active production
  waivers, inventory still `consumer_surface_count=13` / `rule_count=27`, and
  promotion-gate pytest passed `176` tests. Future work should be triggered by
  a concrete new duplicated model/role/port fact or a new migrated consumer that
  deserves swap-CI coverage.
- 2026-07-03 follow-up repaired planner/operator-facing stack truth after the
  CPU embedded-NEXTN `-md` fix: generated stack summaries and system cards now
  render same-file Qwen NEXTN draft requirements as `embedded_nextn=...` rather
  than `draft=...`, while Gemma's separate assistant-head path remains
  `draft=...`. The canonical stack-change update also refreshed descriptor and
  stack-prior source hashes to the current launcher commit. Validation:
  `stack_change_pipeline.py check` returned `summary: ok`, the hardcoded-surface
  guard passed, and the no-inference promotion-gate slice passed `179` tests.
- 2026-07-03 follow-up `8524096b` classifies launcher-only
  `eval_batch_frontdoor` as a manifest-owned warm auxiliary using `mode=default`
  without adding it to active-role registry compilation. The canonical
  stack-change update refreshed descriptor/stack-prior source hashes and
  `current_stack_summary.md`; `stack_change_pipeline.py check --run-promotion-gate`
  returned `summary: ok` with `181` promotion-gate tests passing.
- 2026-07-04 source-freshness repair refreshed generated descriptors,
  stack priors, and `current_stack_summary.md` after the committed
  `orchestrator_stack.py` launcher hash drifted ahead of the generated
  `source_artifacts.orchestrator_stack` fingerprint. The diff is metadata-only
  (compiled timestamp, source commit/hash fingerprints, generated summary
  hashes). Validation: `stack_change_pipeline.py check --run-promotion-gate`
  returned `summary: ok` with `181` promotion-gate tests passing; focused
  `test_stack_priors_compiler.py` + `test_stack_change_guard.py` passed
  `80` tests.

### 2026-06-27 Config Catalog Re-Audit

The `config_model_catalog` surface is HIGH blast-radius but not currently an
open consumer-migration tail. GitNexus impact reported `ServerURLsConfig`,
`TimeoutsConfig`, and `LLMConfig` as HIGH because they sit on the broad
`src.config` import path. Main-thread audit confirmed:

- `ServerURLsConfig` derives live role URLs from generated stack priors, with
  manifest-derived service/warm compatibility fallbacks.
- `TimeoutsConfig` reads role/server/service timeouts from registry
  `runtime_defaults.timeouts`, while retaining explicit compatibility aliases.
- `LLMConfig.depth_role_overrides` and `depth_override_max_depth` read registry
  runtime defaults.
- Public singleton coverage exists for `get_config()` stack-prior behavior and
  env override layering.

Validation:

- `tests/unit/test_config.py tests/unit/test_session_models.py tests/unit/test_registry_loader.py` -> `93 passed`.
- `tests/unit/test_config_consolidation.py tests/unit/test_api_imports.py` -> `113 passed`.

Conclusion: keep `config_model_catalog` in the guarded surface inventory, but do
not treat it as a parked W4 migration unless a future concrete duplicated fact
appears.
- 2026-07-04 follow-up rechecked the `src.config.models` compatibility-alias
  surface after a sidecar flagged `ServerURLsConfig` / `TimeoutsConfig` as
  HIGH blast-radius. GitNexus confirmed the broad config import blast radius
  (`impactedCount=190`), so the main thread audited rather than delegated it:
  `worker_explore` URL/timeout defaults canonicalize to `worker_general`,
  `worker_fast` remains the explicit manifest-owned warm auxiliary, and
  `worker_coder` resolves to the same warm compatibility port/timeout as
  current tests expect. `stack_change_guard.py --all-hardcoded-surfaces` and
  `stack_change_pipeline.py check` are clean; focused config compatibility
  tests passed. Keep this as guarded compatibility, not an open migration,
  unless a future stack change introduces a concrete stale role/port fact.
- Orchestrator `471a4d2` closes the `launch_maps` auxiliary-role tail with an
  explicit validator classification rather than widening generated prior role
  semantics. `validate_launch_manifest_serving_alignment()` now rejects
  unclassified launch targets without generated live priors, allows covered
  aliases only when their primary role has a live prior record, allows
  embedding-mode launch targets as manifest-owned auxiliaries, and allows only
  the explicit warm `worker_fast` legacy worker-pool candidate outside the live
  prior map. The full no-inference promotion gate passed (`174 passed`) and
  `stack_change_pipeline.py check --run-promotion-gate` returned
  `summary: ok`.

## Completed Scope

| Through | Historical ledger |
|---------|-------------------|
| 2026-06-15 | [model-stack-single-source-update-pipeline-history-2026-06-15.md](../archived/model-stack-single-source-update-pipeline-history-2026-06-15.md) |
| 2026-06-19 | [model-stack-single-source-update-pipeline-history-through-2026-06-19.md](../archived/model-stack-single-source-update-pipeline-history-through-2026-06-19.md) |

## Required Contract

Any future stack update should be accepted only when these hold:

- generated descriptors, stack priors, procedure enums, and operator summaries
  are fresh;
- model-specific consumer surfaces are either generated from stack priors or
  explicitly owned degraded fallbacks;
- q_scorer/reward/routing/admission/launch/status/prompt consumers do not hide
  stale local model facts;
- live runtime flags, model paths, mmproj paths, context/KV/spec flags, and
  known-stack listeners agree with generated launch truth;
- scanner rules and consumer surfaces have manifest ownership metadata.

## Outstanding Work

- [ ] Preserve env override precedence and explicit degraded fallbacks whenever
  migrating config, runtime, benchmark, or prompt consumers.
- [ ] Continue migrating remaining high-risk P2 consumers only where a concrete
  duplicated model/role/serving fact or duplicated stack-prior traversal still
  exists; avoid broad renderer rewrites unless there is a narrow helper seam.
- [ ] Treat `scripts.benchmark.seeding_rewards`,
  `scripts.benchmark.corpus_quality_gate`, and `scripts.autopilot.kv_compress`
  as re-audited surfaces: the current implementations already keep generated
  stack priors primary with explicit degraded fallback. Do not churn them unless
  a concrete duplicated live fact reappears.
- [ ] Broaden W4 swap-CI opportunistically as migrated consumers create new
  witness surfaces; do not add abstract fixture coverage without a migrated
  consumer to prove. Latest re-audits: the simulated vision swap already covers
  the migrated vision serving consumers (`stack_prior_vl_ports`,
  `_vl_port_for_role`, `_vl_url_for_role`, and `_vl_url_for_port`) against the
  generated stack-prior artifact, and the simulated worker swap now covers
  WorkerPool primary-port/model-path consumption plus factual-risk role-tier
  consumption after a generated worker swap. The simulated vision and
  long-context swaps also prove factual-risk role-tier consumption for their
  role classes.
- [x] Deploy/reload the repaired X-MAS constrained policy and rerun the
  held-out quiet-window A/B with required policy
  `incumbent_constrained_cheapfirst_v2`; the 2026-07-03 artifact is
  `promote_candidate` with no blockers.
- [ ] Keep production routing default-off until an explicit operator
  enablement/reload/attestation decision accepts the repaired-policy evidence.
- [ ] Keep `scripts/autopilot/short_term_memory.md` under review as live run
  state; do not prune it during active AutoPilot execution.
- [ ] Keep completed implementation logs out of active indices; record future
  closures in `progress/` and compact/archive at wrap-up.

## Validation

Default no-inference acceptance:

```bash
uv run python scripts/registry/stack_change_pipeline.py check
```

Promotion/launch-boundary acceptance:

```bash
uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate
```

Surface inventory checks:

```bash
uv run python scripts/validate/stack_change_guard.py --surface-summary-only --all-hardcoded-surfaces
uv run python scripts/validate/stack_change_guard.py --list-hardcoded-surface-rules --surface-inventory-format json > /tmp/stack-change-inventory.json
```
