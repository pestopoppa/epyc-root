# Standardized Stack Update Pipeline Finalization

**Status**: PARTIAL IMPLEMENTATION LANDED - canonical stack-change command and
promotion gates are live. Generated-contract and guard checks are clean.
Runtime-attestation checks can still stop during intentionally isolated
clean-window measurements that bind stack ports; the latest frontdoor G11
measurement window caused such a stop while active, then exited without a
claim-grade aggregate. A rerun after that exit returned `summary: ok`.
Remaining work is high-risk consumer migrations and opportunistic W4 swap-CI.
**Lifecycle**: superseded — consolidated into the authoritative pair [`model-stack-single-source-update-pipeline.md`](model-stack-single-source-update-pipeline.md) (consumer-SSoT) + [`stack-change-governance-pipeline.md`](stack-change-governance-pipeline.md) (command/gates). Remaining work (W4 swap-CI, high-risk consumer migrations) is co-tracked there — no unique one-time work here. Per [`stale-open-audit-2026-07-18.md`](stale-open-audit-2026-07-18.md) finding #5. Hard-archive to `completed/` pending operator OK.
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
- 2026-06-21 A9 follow-up `3693f6c7` restored that clean baseline after the
  offline reward verifier tests intentionally added historical
  `architect_coding:delegated` remap fixtures. The fixtures now carry exact
  `stack-change-guard: allow` markers, `guard_all_surfaces: ok` is restored,
  `stack_change_pipeline.py check --run-promotion-gate` passed, and the
  executable promotion gate reported `174 passed`.
- 2026-06-28 currentness recheck: `stack_change_guard.py
  --all-hardcoded-surfaces` returned OK; `stack_change_pipeline.py check`
  returned `summary: ok` with `guard_all_surfaces: ok`, `guard_strict: ok`,
  `runtime_attestation: ok`, and `acceptance: no-inference checks passed`;
  surface inventory remained `consumer_surface_count=13`, `rule_count=27`;
  `orchestration/stack_change_guard_exceptions.yaml` remained
  `exceptions: []`; and the no-inference promotion gate passed `176` tests.
  This found no live N11 consumer-migration gap to patch while AutoPilot is
  accruing W6 evidence.
- 2026-07-04 currentness repair: `stack_change_guard.py
  --all-hardcoded-surfaces` caught stale generated stack-prior source metadata
  for `scripts/server/orchestrator_stack.py` (`source_artifacts` expected the
  previous launcher hash). Regenerating through the canonical
  `stack_change_pipeline.py update` path refreshed descriptors, stack priors,
  procedure enums, and the generated operator summary without semantic role
  diffs. The follow-up `stack_change_pipeline.py check --run-promotion-gate`
  returned `summary: ok` and the promotion gate passed `181` tests.
- 2026-07-05 source-fingerprint repair: after Orchestrator `01d14301`
  changed the launcher NUMA default, `stack_change_guard.py
  --all-hardcoded-surfaces` again caught stale `source_artifacts` metadata for
  `scripts/server/orchestrator_stack.py`. Orchestrator `a0377110` regenerated
  descriptors, stack priors, and the generated operator summary through the
  canonical pipeline. The diff was metadata-only: compiled timestamps, source
  commits, source hashes, and summary fingerprints; no role rows, ports, tiers,
  launch requirements, or procedure enums changed. The follow-up
  `stack_change_pipeline.py check --run-promotion-gate` returned `summary: ok`,
  `guard_all_surfaces: ok`, `guard_strict: ok`, `runtime_attestation: ok`, and
  promotion gate `181` tests passed.
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
- 2026-06-20 WorkerPool follow-through landed in Orchestrator `1a8cb729` and
  `b0150e1c`: runtime worker-pool config now uses shared stack-prior
  primary-port selection and generated launch requirements for worker model
  paths. The stack-prior compiler and guard both honor explicit
  `server_mode` launch-path overrides on top of stack-manifest defaults, and
  the simulated worker swap fixture proves a data-only worker model/port swap
  reaches WorkerPool. `stack_change_pipeline.py check` returned `summary: ok`
  and the executable promotion target passed 174 no-inference tests.
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
  promotion-gate execution move together for `ingest_long_context`. Orchestrator
  `cacd8c44` broadens the same simulated swap fixture to factual-risk role
  capability tiers, proving worker, vision, and long-context swaps update
  `src.classifiers.factual_risk` through regenerated stack priors instead of
  static degraded role defaults.
- 2026-07-06 consumer-tail integration: Orchestrator `4bf414d6` folds the
  parked factual-risk degraded fallback cleanup back into the main stack SSoT
  line. The live/generated role-tier path remains primary; the explicit degraded
  role-tier compatibility table is now isolated behind `_degraded_role_tier()`
  rather than a module-level mapping that can be mistaken for live stack truth.
  Validation passed with `test_factual_risk.py` (`51 passed`), focused
  `py_compile`/`ruff`, and the canonical `stack_change_pipeline.py check
  --run-promotion-gate` (`summary: ok`, promotion gate `181 passed`).
- 2026-07-06 DS-7 guard integration: Orchestrator `464aca54` makes
  `stack_templates/default.yaml` fail validation when deployable role ports
  drift from generated live stack-prior serving ports. Logical aliases remain
  valid only when the alias target serves the generated alias ports; experimental
  templates are not forced to mirror production priors. Validation passed with
  `test_dynamic_stack.py` + `test_stack_templates_v2.py` (`47 passed`),
  `orchestrator_stack.py start --stack-profile default --validate-only`,
  `stack_change_guard.py --surface-summary-only --all-hardcoded-surfaces`, and
  `stack_change_pipeline.py check --run-promotion-gate` (`181 passed`).

## Outstanding Work

- [ ] **SS-BENCH-GATE — a stack reload must check for a running CPU bench, not just autopilot.**
      **Incident 2026-07-27**: an operator-authorized `orchestrator_stack.py reload orchestrator`
      killed the Laguna Q4 CPU bench **1h09m into a decision-gating run**. The reload spawned an
      accelerated sidecar (PID `1202069`, 15:51:42) on cores the bench had pinned, and the bench's
      *campaign continuity gate* invalidated the run:
      `campaign continuity gate failed: production stack continuity invalid: accelerated sidecar
      1202069 overlaps CPU bench cores: [0, 1, 2, ...]`.
      The precondition that was checked — "autopilot is down" — is **not the relevant gate**; the
      gate keys on **core overlap** with a pinned bench. Two things to land:
  - [x] SS-BENCH-GATE-a — **LANDED** ✅ 2026-07-27 (orchestrator `237f16f0`).
        `orchestrator_stack.py` start/stop/reload now call `guard_against_running_bench()`, which
        detects a live bench driver (`*_bench_runner.py`, `v7_quality_gate_runner.py`, `llama-bench`,
        `run_e8_quality_baseline_reseed.py`), prints the incident context, and exits 2 unless
        `--allow-during-bench` is passed. `earlyoom` is excluded — it merely names `llama-bench` in
        its arguments. **Verified live on first run**: it caught the E8 quality baseline reseed
        (PID 1485364) and the v7 quality gate.
  - [ ] SS-BENCH-GATE-b — Pin the orchestrator fleet (including transient sidecars) off the CPU
        bench core range so a reload cannot trip the gate at all. This is the durable fix; (a) is the
        guard rail.


- [x] Keep the `waived_production_blocker` mechanism empty by default and
  fail-closed: any future waiver must be intentional, owned, expiring, and
  removed as soon as compatibility no longer needs it. Current guard state has
  no active waivers (`orchestration/stack_change_guard_exceptions.yaml`
  contains `exceptions: []`) and `stack_change_pipeline.py check` reports
  `guard_strict: ok`. Orchestrator `5bfab0a7` hardens this from convention to
  enforcement: documented `production_blocker` surface waivers now fail closed
  unless `stack_change_guard.py` / `stack_change_pipeline.py` is run with
  `--allow-production-blocker-waivers`, leaving any accepted emergency waiver
  visible as `hardcoded_surface.waived.production_blocker`.
- [ ] Continue high-risk consumer migrations only after focused GitNexus impact
  checks. Use the stack-change surface manifest to pick the next consumer.
  Latest completed slices: Orchestrator `95a23aa` canonicalized the
  generated-stack-docs raw-registry degraded fallback, `523cb02` made AutoPilot
  system-card generation fail closed instead of reusing checked-in stale
  guidance, and `3007610` moved admission degraded fallback URL/slot limits to
  computed stack-manifest truth; `93722b1` moved seeding degraded benchmark
  topology fallback to registry-derived truth. Remaining slices should continue
  to distinguish de-duplication from deliberate precedence changes. As of the
  2026-06-28 currentness recheck, this is opportunistic-on-new-finding rather
  than an already-identified open code migration.
- [ ] Finish W4 swap-CI so representative stack changes prove generated
  descriptors, stack priors, q_scorer priors, operator summary, promotion-gate
  execution, and selected consumer witnesses move together. The simulated
  frontdoor swap fixture now also exercises promotion-gate execution in the
  same swapped state, and representative worker, vision, and long-context ingest
  swaps now cover distinct live role classes. The worker swap also covers the
  migrated text-side primary-port consumers after `6c9ac6b`, the seeding
  descriptor degraded fallback after `7a90924`, and factual-risk role-tier
  consumption after `cacd8c44`; `4bf414d6` keeps that factual-risk degraded
  fallback compatibility explicit. The remaining gap is opportunistic expansion
  as new high-risk consumers are migrated rather than a missing end-to-end
  happy-path proof.
- [x] Fix promotion-gate test failures: `test_seed_specialist_routing_main_and_retry.py`
  had 4 failures — `_role_result` fixture missing `tool_chains` attribute that
  `seed_specialist_routing.py:447` / `seed_specialist_routing_v2.py:423` access.
  Orchestrator `91cb03bf` adds `tool_chains=[]` to the fixture. Combined with
  the prior `083e2736` (stale ingest topology fixture expectation), full
  promotion-gate is now `181 passed`, pipeline `summary: ok`. ✅ 2026-07-07
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
