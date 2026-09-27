# Model Stack Single-Source Update Pipeline — completed scope through 2026-09-27

> **Historical ledger only; current work lives in [../active/model-stack-single-source-update-pipeline.md](../active/model-stack-single-source-update-pipeline.md).**

Moved out of the active handoff at the workspace-8d wrap-up of 2026-09-27. Text is verbatim; only the
section headings introduced by this file (the `##` sections and the `###` box-group headings) are new.
Nothing here is open: every range carried zero `- [ ]` boxes when it was moved. The ticked SSU-F9 box itself
stays in the active file beside the still-open SSU-F9c.

## Superseded Status line (as of 2026-09-27)

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

## Current Baseline — detailed snapshot (compacted 2026-09-27)

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

## Closed follow-ups from the 2026-09-22 v10 promotion + lineup cutover

### SSU-F2 and SSU-F3

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

### SSU-F5

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

### SSU-F9d and SSU-F9e

- [x] **SSU-F9d — the guard's legacy-lock check compares path STRINGS, so one lock seen through two paths
  refuses as "TWO serialization locks".** `scripts/hooks/pre_push_serialization_guard.sh` (~`:431`) tests
  `[[ "$LEGACY_LOCK_FILE" != "$LOCK_FILE" && -e "$LEGACY_LOCK_FILE" ]]`. From a worktree created via
  `/mnt/raid0/llm/epyc-root`, `LOCK_FILE` is `/mnt/raid0/llm/epyc-root/coordination/push-locks/push-<key>.json`
  while the legacy path is `/workspace/coordination/push-locks/push-<key>.json` — the SAME inode, so a correctly
  held lock refuses its own push (hit live 2026-09-26, workspace-8d). Fix (one line): replace the string test with
  `[[ ! "$LEGACY_LOCK_FILE" -ef "$LOCK_FILE" && -e "$LEGACY_LOCK_FILE" ]]`, plus a shell case that takes the lock
  through one path and pushes through the other. Workaround until then: create worktrees via `/workspace`, or export
  `EPYC_PUSH_LOCK_DIR=/mnt/raid0/llm/epyc-root/coordination/push-locks`. **Blocker: operator approval** — the
  permission classifier refused the edit for a subagent (`scripts/hooks/**`, the SSU-F9a D9-ack precedent).
  Filed 2026-09-26.
  ✅ 2026-09-26 — fixed (operator-approved OP-65, root 7f4cbb42): `-ef` identity compare; tests 68/68 (the suite also stopped hard-coding /workspace's guard, 42715837). NOTE: the LIVE pre-push hook runs /workspace/scripts/hooks/pre_push_serialization_guard.sh, the shared clone's working-tree copy, so the fix takes effect only once the shared clone /workspace is updated to origin/main; until then the EPYC_PUSH_LOCK_DIR workaround still applies.
- [x] **SSU-F9e — deploy the OP-65 guard fix to the LIVE hook.** `/workspace/.git/hooks/pre-push` runs `/workspace/scripts/hooks/pre_push_serialization_guard.sh` from the shared clone's working tree, which is on a stale `main` and carries other sessions' uncommitted files. Update the shared clone to origin/main at a coordinated moment (inspect `git -C /workspace status` first; the redundant Vidya KV-quant copies there are workspace-8d's and safe to discard; `.research-session.json` and `research/intake_index.yaml` belong to other sessions), then run `bash scripts/hooks/tests/test_pre_push_serialization_guard.sh` from /workspace and expect 68/68.
  ✅ 2026-09-26 — deployed: shared clone fast-forwarded 9e2b8a46→b43ee2e9 (`merge --ff-only`, no force, no stash, no checkout/restore). The 11 ff blockers were all superseded, none unique: 8 byte-identical to a blob committed in the range (3 KV-quant files = origin/main; cli.py, ingest_sources.py, test_ingest_sources.py = 876af60b; `.research-session.json`, `research/intake_index.yaml`, `progress/2026-09/2026-09-25.md` = 304e663b), and 2 older subsets (the Vidya handoff: all 15 added lines are in origin/main; the adapters README row: origin/main is the local row plus the words "plus trial-linked exposure/reliance receipt"). They were moved aside, not discarded, into the full backup at `/mnt/raid0/llm/tmp/ssu-f9e-shared-clone-backup-20260926/` (75 files + tracked patch + sha256 manifest, verified). The other 64 dirty or untracked paths are byte-unchanged. Evidence: `git -C /workspace log -1` = b43ee2e9 = origin/main; from /workspace the guard suite reports PASS 68/68 with the guard under test at /workspace/scripts/hooks/pre_push_serialization_guard.sh; that live copy has the `-ef` compare (line 444).

### SSU-F12

- [x] **SSU-F12 — the host-only `worker` alias leaked into two consumers after the 2026-09-22 cutover.**
  ✅ 2026-09-24. `server_mode.worker` (alias_of frontdoor, listed in `shared_with`) compiles
  `deployment_status: live_stack`, so it surfaced (a) as its own scoring role in `ScoringConfig` (q_scorer
  stack-priors path; orch `42e304ac`, `_NON_SCORING_HOST_ALIASES`) and (b) in the stack-template parity check,
  where `cmd_start(validate_only=True)` HARD-FAILED with "live stack-prior role 'worker' is missing from default
  stack template" — a stack start would have refused (orch `8d7633d0`). Both now skip any live-stack role name
  that is not a canonical `Role`. 7 stale/vacuous fixtures fixed alongside (q_scorer ×3, bilinear ×2 now
  hermetic, gpu_shadow_lane ×1, stack_reload ×1).

### SSU-F14 and SSU-F15

- [x] **SSU-F14 — `orchestration/contention_matrix.yaml` is stale and blocks every `stack_manifest.py`
  commit.** ✅ 2026-09-24 — re-benched by the OP-54 stack change (orch `0a564a1f`, 18:52Z): topology
  `4893e37e`, `decision_grade: true`; `check_contention_matrix_fresh.py` → OK. Stored `topology_hash` 171f86f9 ≠ live 1c548fce; last refreshed 2026-08-23 (> 30 days).
  `scripts/validate/check_contention_matrix_fresh.py` is a pre-commit gate, so INF-41 S-11a (and any other
  `stack_manifest.py` change) cannot land until `scripts/server/contention_matrix.py` is re-run — a live
  bench sweep against production ports, i.e. an inference-session task.
- [x] **SSU-F15 — some `tests/unit` failures hit the host-wide `heavy_model` lock rather than a code defect.**
  A fix for a concurrent-import race on `inference_lock` was in flight as of 2026-09-24 (a background agent
  running the diagnosis); once landed, re-run the affected tests before attributing them to topology drift so
  SSU-F13's bucket count isn't inflated by a test-infra race.
  ✅ 2026-09-24 — resolved by orch `f42b2895`: hermetic `heavy_model` lock/gate for unit tests plus the
  `inference_lock` concurrent-import race fix. Re-run affected tests against this commit before folding any
  remaining failures into SSU-F13's bucket.
