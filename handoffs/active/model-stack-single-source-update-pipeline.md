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
expansion should follow new consumer migrations. The 2026-07-06 consumer-tail
cleanup (`epyc-orchestrator` `4bf414d6`) folds the parked factual-risk degraded
fallback refactor back into main: generated stack priors remain the primary
role-tier source, and the compatibility-only fallback is isolated behind a
helper instead of a module-level live-looking role table. The follow-up
`epyc-orchestrator` `c1cbe1fe` closes the stale VL degraded-fallback gap:
present generated stack priors are now authoritative for chat-vision and
vision-stage endpoint resolution, so legacy `8086/8087` ports are used only
when the generated artifact is missing or unreadable.
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
- [x] **2026-07-06 generated artifact refresh after live-stack drift check.**
  `epyc-orchestrator` `6324af1e` refreshed
  `docs/generated/current_stack_summary.md`,
  `orchestration/derived/stack_priors.yaml`, and
  `orchestration/model_descriptors.yaml` via
  `scripts/registry/stack_change_pipeline.py update` after the canonical guard
  found stale source-artifact hashes. `stack_change_pipeline.py check`,
  `stack_change_guard.py --surface-summary-only --all-hardcoded-surfaces`, and
  the no-inference promotion-gate test target passed (`181 passed`);
  GitNexus was refreshed at the committed state. ✅ 2026-07-06
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
- [x] **2026-07-16 worker speculative-stack source-of-truth check.** The
  combined `ngram-mod,draft-mtp` worker launch had to land in the
  `epyc-inference-research` master registry before the lean orchestrator
  registry could durably compile it; a lean-only edit was overwritten by the
  startup compiler. After updating the master registry, the generated lean
  registry, descriptors, stack priors, and operator summary were refreshed, and
  live worker ports `8072/8082/8182/8282/8382` attested cleanly. ✅ 2026-07-16
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
- `src.api.routes.vision_serving`, `chat_pipeline.vision_stage`, and
  `chat_vision` now also fail closed when a generated live stack-prior artifact
  is present but lacks the requested VL role/port. Degraded legacy VL ports are
  still allowed when generated priors are missing or malformed, but present
  priors cannot be bypassed by the old `worker_vision` / `vision_escalation`
  fallback table (`epyc-orchestrator` `c1cbe1fe`; HIGH GitNexus path handled in
  the main thread).
- `src.classifiers.factual_risk` role capability tiers already derive from
  generated stack priors; the W4 simulated swap fixture now proves regenerated
  worker, vision, and long-context stack priors update factual-risk tier
  adjustment before static degraded role defaults can apply.
- `src.classifiers.factual_risk` now keeps the degraded compatibility mapping
  behind `_degraded_role_tier()` rather than a module-level `_DEGRADED_ROLE_TO_TIER`
  table. The current generated-prior path is unchanged; the cleanup reduces the
  chance that future stack work treats degraded fallback labels as authoritative
  live stack truth.
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
- 2026-07-06 DS-7 template consumer guard landed in orchestrator `464aca54`:
  `validate_template()` now treats generated live stack priors as the
  production `default` profile's serving-topology witness. Deployable default
  role ports must match generated prior ports, and logical aliases are accepted
  only when their alias target serves the generated alias ports. This closes the
  template/prior drift gap without making experimental templates rigid.

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

> **⚠ THESE SEVEN BOXES ARE STANDING CONSTRAINTS, NOT TASKS — DO NOT DISPATCH OR FLIP THEM.**
> Every open box in this section is a rule with no completion state: *"Preserve … **whenever**
> migrating"*, *"Continue … **only where**"*, *"Treat … **as** re-audited surfaces … **do not churn
> unless**"*, *"Keep production routing default-off **until** an explicit operator decision"*,
> *"Keep … **under review**"*, *"Keep completed logs out of active indices"*, *"Broaden …
> **opportunistically as** consumers create new surfaces"*. Checking one asserts that an ongoing
> constraint has been permanently satisfied, after which the constraint stops being applied.
>
> **Count corrected SIX → SEVEN, 2026-08-11 (`mainC`).** The *"Treat … as re-audited surfaces"* rule
> was a standing constraint the enumeration never counted, and it had been flipped `[x]` — the exact
> false-permit C41 predicts, *"a guard that trusts an enumeration is passed by not being
> enumerated."* The banner is the scope, so an undercount silently un-guards a real rule; the repair
> belongs here rather than in a widened predicate.
>
> Noted 2026-07-29 by `auditor`. **The heading gives no warning** — "Outstanding Work" reads like a
> task list, and three of these rows (`:320`, and the two now at `:353`/`:355`) are offered as
> dispatchable in `BACKLOG-DISPATCH-QUEUE.md`'s runner-up bench. The reliable tell is the BOX TEXT
> — a continuous imperative plus a standing condition — not the section title.


- [ ] Preserve env override precedence and explicit degraded fallbacks whenever
  migrating config, runtime, benchmark, or prompt consumers.
- [ ] Continue migrating remaining high-risk P2 consumers only where a concrete
  duplicated model/role/serving fact or duplicated stack-prior traversal still
  exists; avoid broad renderer rewrites unless there is a narrow helper seam.
- [x] Re-audit `scripts.benchmark.seeding_rewards`, `scripts.benchmark.corpus_quality_gate`
  and `scripts.autopilot.kv_compress` for duplicated live facts ✅ 2026-07-29 — each imports
  generated stack-prior helpers for normal operation; each fallback remains explicitly marked
  degraded and derives from the manifest rather than copied live model/endpoint facts.
- [ ] **STANDING — do not churn `seeding_rewards`, `corpus_quality_gate` or `kv_compress`**
  unless a concrete duplicated live fact reappears. They are re-audited surfaces that keep
  generated stack priors primary with an explicit degraded fallback.
  *(SPLIT 2026-08-11 by `mainC`, adopting `auditor`'s synthesis over my own first fix. One box
  was carrying two different things: a re-audit that genuinely COMPLETED, and a rule with no
  completion state. I had restored the whole box to `- [ ]`, which hid the finished audit; it had
  previously been `- [x]`, which retired the live rule — the same loss-mode as the consumed GEAK
  pickup box. Splitting is the only form that keeps both true. Consequence for consumers: any
  queue row marking this a CLOSED task is wrong, and the dated result now lives on its own
  checked line where a completion record belongs.)*
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
- [x] Fix promotion-gate test regressions: `_role_result` fixture missing
  `tool_chains` attribute (orchestrator `91cb03bf`), and stale ingest
  topology fixture expectation (`083e2736`). Full promotion-gate `181 passed`,
  pipeline `summary: ok`. ✅ 2026-07-07
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

---

## Follow-ups from the 2026-09-22 v10 promotion + lineup cutover

The cutover is live and serving; these are what it left owed. Each names its own
blocker rather than sitting in prose.

- [ ] **SSU-F1 — deprecate the seven `*_local` catalogue rows for the retired models, THEN delete ~544 GiB of weights.**
  The lineup change deprecated the role-holding rows and never touched the
  exact-artifact rows beneath them, so `qwen35_122b_iq2m`,
  `qwen3_next_80b_a3b_instruct_iq2m_local`, `gemma4_26b_a4b_orig_q8_local`,
  `gemma4_26b_a4b_q4km_current_local`, `gemma4_26b_a4b_orig_bf16_local`,
  `gemma4_26b_a4b_ud_iq4xs_local` and `draft_gemma4_26b_a4b_assistant_v6_f16_local`
  are all still live and non-deprecated. Three of them ALREADY point at absent
  files. Deleting before deprecating leaves seven rows naming missing artifacts.
  Clean checks already pass: no process maps them (`/proc/*/maps`), no live
  serving role references them. Use the `retire-model` skill — this is exactly
  what it refuses on. **Blocker: deletion is an operator action (destructive,
  irreversible); the deprecation half can be done now.**

- [x] **SSU-F2 — build a CPU-shape architect quality bench, then close the Flash-Next quality gap.** **DONE 2026-09-23 — and the 'gap' was the instrument.** See the cap-convergence table below.
  `architect_critic` and `qwen38_flash_next_ud_iq4xs_local` carry 2 known gaps
  each and the stack-change gate was SKIPPED to launch. `architect_bench_gpu_arm.sh`
  is GPU-shaped (pinned to cores 184-191); Flash-Next is a CPU role on 0-95.
  Until this lands, `stack_change_pipeline.py check` cannot pass strict and the
  gate stays skipped. **Blocker: none — this is buildable work.**

- [x] **SSU-F3 — explain the 2.24 GiB the capacity model does not account for on the MI210.** **RESOLVED 2026-09-23 by READING, not subtracting** — `:8083` reloaded with `LLAMA_ARG_LOG_VERBOSITY=4` at the gate's boundary; full decomposition in `artifacts/operator/vram-gap-27b-20260923.md`. The subtraction had understated the compute residual by 0.277 GiB because it could not see the DRAFT graph's own `sched_reserve` block. Two things the log confirms independently of the original argument: the kernel prints `98304 cells, 16 layers` on a 64-block model, which is the `full_attention_interval = 4` correction stated in the server's own words rather than inferred from a GGUF key; and `2 cells, 64 layers, 2 seqs 8 rs_seq` prices the MTP recurrent cache at ~0.329 GiB per unit of draft depth, so 8 -> 4 returns ~1.3 GiB. What that costs in tokens/s is STILL unmeasured and is still the input the 262144 decision needs.
  Measured 2026-09-22 under six verified load cycles: usable 63.98, steady
  63.069, so 0.91 GiB free against a predicted 3.15. The 27B holds 38.61 GiB
  against a declaration implying ~33.7. Fragmentation and transient peaks are
  BOTH ruled out by measurement (no ratchet; 0.016 GiB transient) — see
  `epyc-inference-research/data/gpu-mi210/vram-headroom-20260922/report.json`.
  Remaining candidates: the declaration understating non-KV for this artifact,
  or a fixed allocation the model does not represent. This is what makes
  `n_ctx 262144` unaffordable, so it is worth ~2 GiB of context.
  **Blocker: none — needs a per-buffer accounting of one loaded server.**

- [ ] **SSU-F4 — make the stack-change surfaces derive instead of restate.**
  The audit's structural finding (`artifacts/operator/session-friction-audit-20260922.md` §2):
  `port_map`, `role_launch_meta`, `numa_config`, the procedure enums and
  `roles.*` each independently restate `shared_with`, and nothing recomputes.
  The `stack-change` skill now enforces the discipline by hand; the durable fix
  is to derive them. **Blocker: none — design work, sizeable.**

- [x] **SSU-F5 — fix the 11 `test_stack_priors_compiler.py` failures: fixtures that RESTATE the pre-lineup ports.**
  Measured 2026-09-23: `pytest tests/unit/test_stack_priors_compiler.py` → **11 failed, 24 passed**
  (an earlier report said 16; 11 is the counted figure). The shape is `assert [8070] == [8072]`
  — fixtures hard-coding the port the worker lane answered on BEFORE the 2026-09-22 lineup
  change moved `worker_general`/`worker_explore`/`worker_math`/`toolrunner` onto frontdoor's
  `:8070` process. Failing tests: `test_stack_manifest_info_defaults_to_launcher_full_mode`,
  `..._can_compile_explicit_both_mode`, `test_alias_roles_inherit_host_full_fleet_ports`,
  `test_regenerated_worker_math_url_byte_equals_fix_a_delegated_value`,
  `test_compile_maps_model_role_server_binding`,
  `test_compile_prefers_server_mode_launch_requirement_paths`,
  `test_compile_shared_aliases_use_runtime_descriptor`,
  `test_compile_preserves_conflicts_as_gaps_when_allowed`,
  `test_compile_require_realized_mode_derives_quarter_lineup`,
  `test_compile_default_does_not_probe_realized_fleet`,
  `test_compile_projects_ctx_model_max_and_policy_hints`.
  **This is the SSU-F4 defect class one layer down** (audit §2, restated derivation): a fact that
  is a function of `server_mode.*.shared_with` copied into a test fixture as a literal, so the
  fixture asserts yesterday's topology and fails for a reason unrelated to what it tests.
  Repinning the literals fixes today and guarantees the same breakage at the next lineup change;
  deriving the expectation from the same source the compiler reads does not.
  **Blocker: none.** Owner note: a green suite here is load-bearing — `compile_stack_priors`
  refusing is what blocked the 2026-09-22 cutover for 40 minutes.

### SSU-F5 outcome and what it left (2026-09-23)

`tests/unit/test_stack_priors_compiler.py`: **11 failed / 24 passed → 35 passed**, one file changed
(+366/−95), `ruff` clean. Nine of the eleven were bucket-(1) *restated derivations* — port and role
literals copied from `port_map` / `numa_config` / `shared_with` — and are now recomputed from those
sources. One was a pin that pinned the wrong thing (`test_..._delegated_value` read the alias's own
restatement of a delegation instead of resolving the host first). One needed its fixture to stop
borrowing the production lineup: `test_compile_maps_model_role_server_binding` had **ten** assertions
the compiler resolved from the live launcher, so each fix revealed the next.

The fix is proven *derived rather than repinned*, which is the only claim worth making here. A pytest
plugin at `/mnt/raid0/llm/tmp/ssuf5/moved_lineup.py` relocates the worker lane a second time — onto
`architect_critic` (`:8074` + `:8084/:8184`), moving all five surfaces together — and **34 of 35 tests
follow the move with no edit to the test file**. The single failure is the deliberate pin failing
loudly and correctly, and it is failing at a *production* defect, not a test one. Keep that plugin: it
is a standing regression against the next lineup change.

- [ ] **SSU-F8 — `src/config/models.py::_LEGACY_SERVER_URL_FALLBACKS` still names the retired `:8072`
  worker fleet, and eleven neighbouring tests assert the same dead ports.** Found by SSU-F5 while
  reading, reported rather than fixed because it is outside one test file.
  Three rows — `worker_general`, `worker_math`, `toolrunner` — carry
  `full:http://localhost:8072,http://localhost:8082,http://localhost:8182`. Those ports have not
  existed since 2026-09-22; all three roles are aliases on frontdoor `:8070`. `_server_url_default()`
  ends in a bare subscript of this dict, so in **exactly the degraded mode the table exists to serve**
  (priors unreadable, no runtime facts, fresh checkout, bootstrap) these three roles resolve to a fleet
  with nothing listening. It reads correct today only because live runtime facts win.
  `worker_summarize` and `coder_escalation` were updated at their cutovers; the worker lane was not.
  **Do not just update the three rows.** Add `_LEGACY_SERVER_URL_FALLBACKS` as a **sixth surface** in
  `scripts/validate/check_shared_with_derivations.py` — an alias's fallback must equal its host's,
  recomputed and diffed. It is the shape that file already handles, and its absence is the whole reason
  this rotted silently while the five wired surfaces did not.
  Then clear the eleven pre-existing failures in the neighbouring suites (verified present without
  SSU-F5's change; none of them import the file it edited):
  `test_config.py` ×2 (the consumer-side twin of the defect above), `test_config_lineup_liveness.py` ×1
  (`KeyError: 'worker_general'`), `test_stack_numa_reader_agreement.py` ×2, `test_stack_numa.py` ×1,
  `test_stack_manifest_imports.py` ×4, `test_stack_change_guard.py` ×1.
  **Two of those deserve attention beyond "stale literal".** `test_stack_numa_reader_agreement`
  (`assert [8080] == [8080, 8180]`) is a reader *disagreeing about half-instance ports* — the only
  failure whose cause is not obviously a copied constant, and worth looking at independently of tests.
  And two of the four `test_stack_manifest_imports` failures are a **stale parity exception still live
  in `launch_manifest.yaml`**, whose own text says it no longer applies; while it sits there it
  pre-excuses the next real divergence. One line, a live surface, owned by whoever owns that file.
  **Blocker: none.**

- [ ] **SSU-F9 — a correctly-acquired push lock does not satisfy the pre-push guard, and the failure
  mode is silent.** Measured 2026-09-23: four consecutive failed pushes of one reviewed commit.
  Two independent defects compose, and each one alone is enough to block a push while reporting success:
  **(a) the lock directories disagree.** `serialized_push.py` with no `--lock-dir` derives ONE canonical
  directory from the git common dir (correct, and deliberate — it is what makes all five lane worktrees
  contend for one lease). The pre-push hook looks in `<repo>/coordination/push-locks/`. So `--acquire`
  reports `acquired push lock for .` and the hook then reports `the push serialization lock is NOT HELD
  — no lock file at /workspace/coordination/push-locks/push-<key>.json`. Both are telling the truth
  about different directories.
  **(b) the wrapper's own `--push` cannot satisfy its own guard across two tool calls.** The guard
  accepts a push whose process is a *descendant of the lock holder*, but `--acquire` and `--push` run as
  separate processes, so the holder pid is not an ancestor and the check falls through to
  `EPYC_PUSH_LOCK_HOLDER`/`AGENT_ID` — neither of which the wrapper exports. The push fails.
  **The silence is the real defect**: `--push` prints its full publish manifest and then
  `PUSHING as '<agent>' under the push lock ...` as its LAST line, while git's `error: failed to push
  some refs` goes to stderr and surfaces *before* the manifest. A caller reading the tail sees a
  clean-looking manifest ending in `PUSHING`, and `--release` afterwards says `(no push lock held)`,
  which reads like a normal post-push release. Nothing in that sequence says the push did not happen.
  Only `git cherry origin/main main` does — which is why the wrap-up contract requires it.
  Fix: make the guard and the wrapper agree on one lock directory; have `--push` exit non-zero and say
  `PUSH FAILED` on the last line; and have the wrapper export its own identity so its push satisfies its
  own guard. **Blocker: none.**

### SSU-F9 outcome (2026-09-23) — fixed and verified, AWAITING OPERATOR D9 ACK

Fix is complete in the `/workspace` working tree, uncommitted: `serialized_push.py`,
`pre_push_serialization_guard.sh` and their two suites, +346/−16. Both sides now resolve the lock
through **one** resolver — the guard *asks the writer* (`--print-lock-file`) rather than deriving a
second answer, and refuses if the writer's repo key disagrees with its own. The wrapper declares
`EPYC_PUSH_LOCK_HOLDER` for its own child push, asserting only what `O_EXCL` just proved. `--push`
now prints git's output *after* the manifest and ends on a verdict, and — the part that matters —
it VERIFIES rather than attempts: `git cherry` runs after the push, so a push that exits 0 without
landing is reported as `PUSH FAILED`, exit 4.

Guard strength is unchanged and that was proven, not asserted: no lock still refuses; a declared id
is still matched against the lock file rather than trusted; a mismatched id still refuses. A
mutation check re-ran the suite against the *pre-fix* guard and got exactly 4 failures, all of them
the new default-location assertions — so the new case catches the real defect and nothing regressed.
A legacy lock in the pre-fix location is honoured during transition, and two locks for one repo
refuse.

**Why 56 green assertions never saw this**: every existing shell case pinned the location with
`EPYC_PUSH_LOCK_DIR`, so not one of them exercised the default derivation. A test suite that always
supplies the value under test cannot fail on it.

- [x] **SSU-F9a — OPERATOR ACK REQUIRED (D9).** ✅ 2026-09-23 — granted and landed: commit `0f9a4ef1` (all four `scripts/coordination/**` + `scripts/hooks/**` files) carries `D9-ack: operator, 2026-09-23, in session -- authorised after the verification`, and is on origin/main. Ticked by the research-intake session on the operator's explicit ownership transfer (2026-09-23, "take ownership of all these"). All four files are under `scripts/coordination/**`
  and `scripts/hooks/**`, which D9 (ratified 2026-08-15) puts behind operator ack: the loop plane,
  where a wrong change is discovered by its consequences at 3am. The owning session cannot self-ack.
  Commit with `D9-ack: <who authorised, why>` once granted.
  **Blocker: the operator's authorisation. This is the decision, and it is genuinely theirs.**

- [x] **SSU-F9b — WITHDRAWN 2026-09-23: the premise was false, and SSU-F9 had already fixed the
  real problem.** The task claimed `epyc-orchestrator` and `epyc-inference-research` carry LFS-only
  `pre-push` hooks with no serialization guard. **They do not.** Both carry the identical chained
  hook installed 2026-08-12 — serialization guard first, `git lfs pre-push` second — byte-identical
  to epyc-root's. This was a subagent claim relayed without verification; checking it took one
  `cat`.

  **Verified by running**, in each repo, feeding the guard a real ref-update line:
  ```
  PUSH REFUSED — pre-push serialization guard
  cause: the push serialization lock is NOT HELD — no lock file at
         /mnt/raid0/llm/epyc-orchestrator/coordination/push-locks/push-2431-96371138.json
         /mnt/raid0/llm/epyc-inference-research/coordination/push-locks/push-2431-96371209.json
  ```
  Installed, functional, refusing.

  **What WAS true, and is the more interesting half.** Those paths are each repo's OWN
  `coordination/push-locks`, which is what the SSU-F9 fix produces. Before it, the guard hardcoded
  `/workspace/coordination/push-locks` while `serialized_push.py` took the lock in the repo's own
  directory — so in these two repos the guard would have reported NOT HELD for a correctly held
  lock and refused **every** push, on every attempt, forever. In epyc-root the two derivations
  coincidentally produced the same string, which is why the breakage was invisible from there.
  So SSU-F9 did not merely fix epyc-root's four failed pushes; it repaired the push path in the two
  sub-repos, where the divergence was total rather than intermittent. Today's pushes to both
  (`b14ed228`, `58b115ed`) are the demonstration — they ran through the wrapper and ended on
  `PUSH VERIFIED`.

  **Nothing to install. No operator decision required.** Filed as a decision because the premise
  said so; the premise was wrong.

- [ ] **SSU-F9c — `promote_lane.py:519` has the same defect one lease over.** It defaults
  `--lock-dir` to `serialized_push.DEFAULT_LOCK_DIR`, the `__file__`-relative fallback, which in a
  lane worktree is that lane's **private** directory — so the *promote* lease serializes nothing
  across lanes, exactly the 2026-09-01 incident that the push lease's git-common-dir derivation was
  introduced to fix. Different lease, same shape, still live. **Blocker: none.**

- [ ] **SSU-F10 — every GPU role on this host is un-auditable for VRAM between reloads, by
  default.** The per-buffer breakdown (`load_tensors:`, `llama_kv_cache:`,
  `llama_memory_recurrent:`, `sched_reserve:`) is suppressed at the launcher's default log
  verbosity, which is why SSU-F3 had to be answered by subtraction in the first place — and why the
  subtraction was wrong by 0.277 GiB. The 2026-09-23 reload settled `:8083` only, and only until it
  next restarts. Raise the model-load log verbosity permanently in the launcher so the decomposition
  is in the log of every GPU role from the moment it starts. A capacity model that cannot be checked
  against the kernel's own numbers is a model nobody can falsify. **Blocker: none.**

- [ ] **SSU-F11 — the registry's `recipe:` block is DECORATIVE: nothing reads it, and the served
  process runs a hardcoded parallel configuration.** Root-caused 2026-09-23 while chasing SSU-F7's
  two missing env knobs on `:8074`. The knobs are only the visible edge.

  **The measurement.** `architect_critic` declares, in `model_registry.yaml` under
  `recipe: {recipe_id: qwen38-flash-next-cpu-mtp}`: `threads: 48`, `cpu_shape: NUMA_FULL_T48`, and
  `env: {GGML_NOHUGEPAGE_PROCESS: '1', GGML_FA_SPLIT_KV: '0'}`. The live process (pid 2021760) runs
  `-t 96`, and its `/proc/<pid>/environ` contains `GGML_IQK=1` and the four OMP vars and **none of
  the declared knobs**. `no_mmap`, `-ctk/-ctv f16` and `--spec-draft-n-max 4` do match — but they
  match because the *launcher* and the `acceleration:` block independently say so, not because
  anything consulted `recipe:`.

  **Why: there is no reader.** `grep` for any consumer of `recipe.env` across `scripts/` and `src/`
  returns **zero hits**. `build_launch_env()` (`scripts/server/stack_env.py:258`) composes its env
  from a base copy, a canonical OMP block, and `_role_env_overrides()` — which reads
  `_ROLE_ENV_BLOCKS`, a **hardcoded dict in that file**. For `architect_critic` that dict holds
  exactly `{'GGML_NUMA_REPACK_INTERLEAVE': '0'}`, and not one of the eight role blocks mentions any
  of the three recipe knobs. `GGML_IQK=1` is live because it is a launcher default, not because the
  recipe asked for it — which is precisely why this looked like it was working.
  `cpu_shape: NUMA_FULL_T48` has no definition in `stack_numa.py`, which is why the thread count
  falls through to 96.

  **Why it matters beyond hygiene.** `GGML_NOHUGEPAGE_PROCESS=1` is **CHAMP-2, ADOPTED 2026-09-08 by
  operator ruling** (`model_registry_full.yaml:1758` says so in its own comment), it is a
  SESSION-unit knob that must be exported AT LAUNCH, and it is not being exported. An adopted,
  operator-ruled optimisation is not reaching production and nothing detects that.
  **State direction only, never a magnitude**: `qwen38_flash_next_recipe.py` sets
  `THP_SHIM["magnitude_claimed"] = False` deliberately, and the 86.4% figure in that module's tests
  is about conflating the two THP knobs discarding most of the CHAMPION, not about this shim's own
  effect. Do not quote it as the shim's value.

  **Fix shape** — the same one SSU-F8 used, and for the same reason: derive, then make disagreement
  detectable. Have `build_launch_env()` read `recipe.env` from the registry, with `_ROLE_ENV_BLOCKS`
  either removed or reduced to a documented override layer; resolve `cpu_shape` against
  `stack_numa.py` and FAIL on an undefined shape rather than silently falling through to a default;
  and add "the served process's env and thread count equal its declared recipe" as a surface in
  `scripts/validate/check_shared_with_derivations.py`, which is now the established home for exactly
  this check. A declared recipe that nothing reads is not a source of truth, it is a comment.

  **Carry this into any claim measured on `:8074`.** The architect CPU quality gate runs against
  this process, so its rows are `instrument_class: serving` AND the served configuration is not the
  recipe's — `-t 96` where the recipe measured `-t 48`, without the THP shim. The recipe's recorded
  43.281 t/s decode was measured at `t=48` WITH the shim on the champion build, so it cannot be
  expected to describe this process, and the two must never be quoted against each other.
  **Blocker: none.**

### SSU-F2 outcome — the Flash-Next "quality gap" was a measurement artifact (2026-09-23)

The CPU-shape architect quality bench exists (`architect_bench_cpu_{lib,arm,phase}.sh` +
`architect_bench_cpu_conditions.py` + `architect_bench_cpu_truncation_audit.py`), runs against live
`:8074`, and emits producer-authored belief rows. What it found closed the gap by dissolving it.

| suite | max_tokens | pooled | untruncated | truncated |
|---|---:|---:|---:|---:|
| mmlu_pro | 64 (gate) | 0.5650 | 0.7143 | 46/200 |
| mmlu_pro | 4096 | 0.7500 | 0.7590 | 5/200 |
| **mmlu_pro** | **8192** | **0.7550** | **0.7550** | **0/200** |
| gpqa | 64 (gate) | 0.5436 | 0.6176 | 25/195 |
| gpqa | 4096 | 0.6513 | 0.6492 | 4/195 |
| **gpqa** | **16384** | **0.6513** | **0.6513** | **0/195** |

**Pooled == untruncated is the definition of converged**, and it is the only state in which a pooled
accuracy is reportable. Against the retired Qwen3.5-122B's gate numbers (mmlu_pro 0.6450, gpqa
0.5692, truncated 0/200 at cap 64) Flash-Next is **ahead on both suites** — where at the gate's own
cap it appeared behind on both. The whole apparent regression was the cap: the 122B answers with a
letter, Flash-Next derives in the visible channel and was being cut off mid-derivation, scoring
~0.05 on work that was going fine.

Raising the cap was only legitimate because the truncated rows were first shown **non-degenerate**
— top repeated 60-char shingle = 1 in every sampled row, i.e. genuine long derivations that
converge, not repetition loops that no cap would ever clear. Check that before raising a cap;
otherwise "rerun until truncation hits zero" does not terminate.

Recorded in the MASTER registry (`epyc-inference-research`, `58b115ed`) under
`roles.architect_critic.performance.general_suite_quality` — **deliberately NOT in
`quality_score`**, which on this role means the CRITIC suite and stays null because that gate has
still never been run on this model. Recording general-knowledge suites there would have made the
critic-suite gap look closed. Gate policy landed in `promotion_gates.yaml` as SSU-F6.
