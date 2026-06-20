# Standardized Stack Update Pipeline Finalization

**Status**: PARTIAL IMPLEMENTATION LANDED - canonical stack-change command and
promotion gates are live. Generated-contract and guard checks are clean.
Runtime-attestation checks can still stop during intentionally isolated
clean-window measurements that bind stack ports; the latest frontdoor G11
measurement window caused such a stop while active, then exited without a
claim-grade aggregate. A rerun after that exit returned `summary: ok`.
Remaining work is high-risk consumer migrations and opportunistic W4 swap-CI.
**Created**: 2026-06-13
**Priority**: HIGH - stale model-specific constants can corrupt scoring,
routing, launch, planner context, and benchmark interpretation after stack
changes.
**History**:
[standardized-stack-update-pipeline-finalization-history-2026-06-15.md](../archived/standardized-stack-update-pipeline-finalization-history-2026-06-15.md)
preserves the completed chronology compacted out of this active handoff.
**Related**:
[model-stack-single-source-update-pipeline.md](model-stack-single-source-update-pipeline.md),
[stack-change-governance-pipeline.md](stack-change-governance-pipeline.md),
[model-stack-update-pipeline-audit.md](model-stack-update-pipeline-audit.md),
[model-stack-change-standardization-audit.md](model-stack-change-standardization-audit.md),
[model-capability-descriptors.md](model-capability-descriptors.md),
[routing-truth-restoration.md](routing-truth-restoration.md),
[fable5-findings-01-measurement-and-integrity.md](../completed/fable5-findings-01-measurement-and-integrity.md)

## Purpose

Finish the standardized pipeline that makes orchestration model/serving changes
safe:

1. structured stack truth changes first;
2. generated descriptors, stack priors, and operator summaries refreshed from
   that truth;
3. all known model-specific consumers validated;
4. production launch, AutoPilot resume, and benchmark preflight blocked when
   live model facts drift from generated truth.

Do not create a second registry or guard system. Extend the current
descriptor -> stack-prior -> guard -> consumer-migration path.

## Current Baseline

- Canonical command:
  `uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate`
  in `epyc-orchestrator`.
- Default check after Orchestrator `9dcfbf5` was green:
  `stack_manifest_registry: ok`, `runtime_attestation: ok`,
  `q_scorer_priors: ok`, and descriptors/stack priors fresh. The 2026-06-20
  N11a migration checks that failed runtime attestation did so only while the
  isolated K-MEM Tulving listener owned port `8080`; that listener is now gone,
  so future full-pipeline checks should expect runtime attestation to run again.
- Generated descriptors and stack priors are `status: compiled`; stack-prior
  role `known_gaps` are empty.
- Current all-surface warning baseline: clean. Orchestrator `d459f46` labeled
  the last retired-role launch test as intentional legacy coverage, and
  `stack_change_pipeline.py check --run-promotion-gate` now reports
  `guard_all_surfaces: ok`.
- 2026-06-19 descriptor drift from the research registry hash was repaired
  through the canonical `stack_change_pipeline.py update` path. The generated
  diff was limited to `model_descriptors.yaml` / `stack_priors.yaml`
  source-artifact metadata and `check --run-promotion-gate` returned
  `summary: ok` with 172 tests passing.
- 2026-06-19 recheck after the X-MAS reporting and KB-RAG manifest-prune
  commits again returned `summary: ok`: descriptor/stack-prior/procedure/operator
  artifacts fresh, `guard_all_surfaces: ok`, `runtime_attestation: ok`, and the
  executable promotion gate passed 172 no-inference tests. No pipeline code
  changes were needed for N11 in this pass.
- 2026-06-19 high-risk N11a consumer migration landed in Orchestrator `911b880`:
  stack-prior primary-port selection is centralized in
  `stack_prior_primary_port()` and direct endpoint-first fallback consumers
  (`orch status`, corpus gate model discovery, GraphRouter fleet discovery, and
  AutoPilot preflight target grouping) now share that helper. Consumers with
  intentionally different precedence, such as worker-pool port-first binding and
  stack-summary rendering, were left unchanged.
- 2026-06-19 W4 swap-CI expansion landed in Orchestrator `6c9ac6b`: the
  simulated worker swap fixture now proves the text-side primary-port consumers
  migrated in `911b880` (`orch status`, corpus quality gate discovery,
  GraphRouter fleet loading, and AutoPilot preflight health grouping) all read
  the same generated `stack_priors.yaml` primary port after a data-only stack
  change.
- 2026-06-19 follow-up migrations after `6c9ac6b` removed or constrained
  several remaining stack-prior consumers: OpenAI `/v1/models` helper ordering,
  chat-completions degraded fallback role order, stack-monitoring and
  slot-query consumers, dashboard service hints, and seeding reward descriptor
  fallback. A read-only `health_preflight_probes` audit found no further
  duplicate role/port table to migrate in AutoPilot preflight.
- 2026-06-19 W4 swap-CI follow-up landed in Orchestrator `7a90924`: the
  simulated worker swap fixture now also proves seeding reward degraded
  fallback reads swapped model descriptor throughput before the legacy static
  table.
- 2026-06-19 high-risk generated-stack-docs cleanup landed in Orchestrator
  `95a23aa`: the final raw-registry degraded fallback in
  `render_stack_summary.py:registry_role_rows` now emits only canonical current
  roles or generic chain aliases resolved to canonical roles, and skips retired
  serialized aliases or arbitrary auxiliary server names.
- 2026-06-19 AutoPilot system-card fail-closed cleanup landed in Orchestrator
  `523cb02`: `_render_system_card()` no longer falls back to checked-in
  `system_card.md` when live generation breaks. The degraded card blocks stale
  planner/operator stack truth by explicitly marking live role, port, tier,
  throughput, baseline, and trust-boundary facts unavailable until
  `gen_system_card.py --check` passes again.
- 2026-06-19 admission degraded-fallback cleanup landed in Orchestrator
  `3007610`: `src.api.admission` still uses generated stack-prior slot limits
  as primary truth, but empty/bad priors now fall back to computed stack-manifest
  launch records at controller construction time instead of an import-time
  static URL table. Embedding services are skipped so they do not become
  request-admission gates.
- 2026-06-19 benchmark seeding topology fallback cleanup landed in Orchestrator
  `93722b1`: `scripts.benchmark.seeding_types` still uses generated stack
  priors for default roles, role ports, heavy ports, and model ports, but the
  degraded fallback now derives topology from lean-registry `server_mode`
  records instead of preserving a separate static current-stack role/port table.
- 2026-06-20 high-risk vision-serving consumer migration landed in Orchestrator
  `c9d499f`: `src.api.routes.vision_serving` now derives the live vision role
  set from generated stack-prior launch metadata, and `chat_vision` plus
  `chat_pipeline.vision_stage` consume that helper for VL endpoint/role
  resolution. Legacy `VISION_ROLES`/VL port constants remain degraded fallback
  compatibility only; valid generated priors with no vision launch roles do not
  silently re-enable legacy vision roles.
- Guard inventory currently reports `consumer_surface_count=13` and
  `rule_count=27`.
- Active operator topology docs were refreshed in `8221971`, `d94954a` marked
  remaining retired-role doc mentions as historical notes, and `7ad5965` moved
  legacy seed fixtures to exact inline allowances.
- W4 promotion-gate execution/failure coverage landed in Orchestrator
  `d9fd1eb`; system-card swap visibility landed in `4aed83d`;
  health/dashboard stack-prior witnesses landed in `8beaf79`; representative
  routing/API role-surface witnesses landed in `edd20f7`; stack-manifest vs
  registry drift gating landed in `3c18a17`; swap-CI can still be broadened as
  new high-risk consumers are migrated. Long-context ingest swap-CI coverage
  landed in `63b8612`, proving generated descriptors, stack priors, operator
  summary, system card, health/dashboard endpoint hints, q_scorer priors, and
  promotion-gate execution move together for `ingest_long_context`.

## Outstanding Work

- [ ] Keep the two `waived_production_blocker` surfaces intentional, owned, and
  expiring; remove them if compatibility no longer needs them.
- [ ] Continue high-risk consumer migrations only after focused GitNexus impact
  checks. Use the stack-change surface manifest to pick the next consumer.
  Latest completed slices: Orchestrator `95a23aa` canonicalized the
  generated-stack-docs raw-registry degraded fallback, `523cb02` made AutoPilot
  system-card generation fail closed instead of reusing checked-in stale
  guidance, and `3007610` moved admission degraded fallback URL/slot limits to
  computed stack-manifest truth; `93722b1` moved seeding degraded benchmark
  topology fallback to registry-derived truth. Remaining slices should continue
  to distinguish de-duplication from deliberate precedence changes.
- [ ] Finish W4 swap-CI so representative stack changes prove generated
  descriptors, stack priors, q_scorer priors, operator summary, promotion-gate
  execution, and selected consumer witnesses move together. The simulated
  frontdoor swap fixture now also exercises promotion-gate execution in the
  same swapped state, and representative worker, vision, and long-context ingest
  swaps now cover distinct live role classes. The worker swap also covers the
  migrated text-side primary-port consumers after `6c9ac6b` and the seeding
  descriptor degraded fallback after `7a90924`. The remaining gap is
  opportunistic expansion as new high-risk consumers are migrated rather than a
  missing end-to-end happy-path proof.
- [ ] Keep direct benchmark, production launch, and AutoPilot preflight wired to
  the canonical gate; no new bypasses.

## Operating Rules

- Before editing root or orchestrator files, run `gitnexus status`; re-index
  through the repo wrapper if stale.
- Before code or high-impact doc changes, run `gitnexus impact ... --direction
  upstream` and keep the patch scoped to the blast radius.
- Active indices should stay dispatch-oriented. Completed chronology belongs in
  `progress/`, completed/archived handoffs, and commit history.
- No inference is required for this handoff unless a future consumer migration
  explicitly needs live runtime validation.

## Validation

For no-inference stack-change work in `epyc-orchestrator`:

```bash
uv run python scripts/validate/stack_change_guard.py --surface-summary-only --all-hardcoded-surfaces
uv run pytest -q tests/unit/test_stack_change_guard.py
uv run python scripts/registry/stack_change_pipeline.py check
```

For promotion-gate or launch-boundary changes:

```bash
uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate
```
