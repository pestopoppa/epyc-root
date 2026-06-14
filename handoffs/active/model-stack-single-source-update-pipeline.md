# Model Stack Single-Source Update Pipeline

**Status**: PARTIAL IMPLEMENTATION LANDED - 2026-06-14 follow-up `epyc-orchestrator` `1148ff6` closes live q_scorer prior-source promotion gating and the no-inference data-only fixture gaps for the stale frontdoor/coder and context/KV/acceleration cases. Follow-up `e31ebe1` wires the canonical no-inference promotion gate into production `orchestrator_stack.py start` before host prereqs/model launch, with dev/validate-only/migration dry-run skips and explicit emergency bypass. Follow-up `e02930f` wires the same canonical promotion gate into AutoPilot preflight before model/web/inference checks. Follow-up `dbcae29` lands generated current-stack operator summaries from stack priors (`docs/generated/current_stack_summary.md`, `scripts/registry/render_stack_summary.py`, stack pipeline and system-card integration). Follow-up `6474204` expands the executable promotion gate to include benchmark/seeding preflight suites. Follow-up `1457e58` adds the first `runtime_attestation` promotion step for concrete live model/mmproj drift. Follow-up `3065b8b` extends that gate to unmanaged known-stack listeners/state gaps and concrete live runtime flag drift. Follow-up `d3643eb` lands the first enforced P2 model-specific consumer-surface ownership manifest. Follow-up `0cdc15e` migrates the tap safe-streaming non-stream role table to stack-prior-derived truth. Follow-up `f41b1f3` migrates `config_model_catalog` defaults to generated stack-prior server URL truth while preserving environment overrides and explicit degraded fallbacks. Follow-up `c7928cf` migrates dashboard/status port labels to generated stack-prior launch-entry truth while preserving explicit service-only fallbacks. Remaining work is broader static lock/tap policy cleanup, other high-risk consumer migrations, and direct benchmark runtime enforcement where needed.
**Created**: 2026-06-13
**Priority**: HIGH - prevents stale model-specific quantities from silently corrupting routing, scoring, launch, planner prompts, replay analysis, and operator docs after a stack change
**Scope**: Documentation handoff only. No application code, inference, AutoPilot, server restarts, or seeding were performed. This sidecar updated root handoff/index/progress docs only; root GitNexus was refreshed before editing.
**Related**: [standardized-stack-update-pipeline-finalization.md](standardized-stack-update-pipeline-finalization.md), [model-stack-update-pipeline-audit.md](model-stack-update-pipeline-audit.md), [model-stack-change-standardization-audit.md](model-stack-change-standardization-audit.md), [stack-change-governance-pipeline.md](stack-change-governance-pipeline.md), [model-capability-descriptors.md](model-capability-descriptors.md)

## Objective

Make orchestration-stack changes reliable by turning model-specific updates into a single-source pipeline:

1. edit structured truth;
2. compile generated contracts;
3. validate all consumers and docs;
4. refuse launch, AutoPilot resume, or benchmark interpretation when live model facts are stale.

The immediate trigger was stale q_scorer/model-stack quantities: `frontdoor` and `coder_escalation` share the same live model/server, `architect_general` and `ingest_long_context` are HOT, and `architect_coding` is retired as a distinct live role. Those facts must not depend on somebody remembering to update local constants.

This handoff is a concise pickup contract. The long historical audit lives in `model-stack-update-pipeline-audit.md`; implementation should extend the existing descriptor -> stack-prior -> guard -> consumer-migration path instead of inventing a parallel registry.

## Start Here - 2026-06-14 Update

Current implementation result:

- `epyc-orchestrator` `1148ff6` added `validate_live_q_scorer_prior_sources()` in `orchestration/repl_memory/q_scorer.py`.
- `scripts/registry/stack_change_pipeline.py check --run-promotion-gate` now reports `q_scorer_priors: ok/failed` and blocks promotion when any live q_scorer role uses degraded fallback provenance while stack priors are valid.
- The simulated data-only `frontdoor`/`coder_escalation` swap fixture now verifies q_scorer source provenance, and the context/KV/acceleration fixture is complete with `architect_general` quality data.
- Validation reported by the main orchestrator track: py_compile on touched files; ruff on touched files; `pytest -q tests/unit/test_q_scorer.py tests/unit/test_stack_change_pipeline.py tests/unit/test_stack_change_pipeline_simulated_fixtures.py` -> 82 passed; `stack_change_pipeline.py check --run-promotion-gate` -> `q_scorer_priors: ok`, promotion gate 48 passed; hardcoded-surface summary unchanged (`waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`).
- `epyc-orchestrator` `e31ebe1` wires production `scripts/server/orchestrator_stack.py start` to run `uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate` before host prereqs/model launch. Dev starts, `--validate-only`, and migration dry-run skip the gate; emergency diagnostics can bypass with `--skip-stack-change-gate` or `ORCHESTRATOR_SKIP_STACK_CHANGE_GATE=1`.
- The same update refreshed descriptor/stack-prior source hashes in the canonical pipeline artifacts. Validation reported by the main orchestrator track: py_compile on touched launcher/test files; focused pytest `tests/unit/test_orchestrator_stack_reload.py tests/unit/test_stack_change_pipeline.py` -> 27 passed; expanded pytest `tests/unit/test_orchestrator_stack_reload.py tests/unit/test_stack_change_pipeline.py tests/unit/test_build_server_command_helpers.py` -> 69 passed; parser smoke found `--skip-stack-change-gate`; `stack_change_pipeline.py check --run-promotion-gate` passed with promotion gate 48 tests and known warnings only.
- `epyc-orchestrator` `e02930f` adds `audit_stack_change_gate()` to `scripts/autopilot/preflight_audit.py` and runs it as preflight step 0, before model-server, web-search, web-fetch, inference, blacklist, archive-authority, and recent-trial checks. The AutoPilot gate executes `uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate` from the orchestrator repo, fails closed on nonzero exit, OSError, or a 180s timeout, and reports compact `summary:` / `acceptance:` output on success. Unit coverage landed in `tests/unit/test_autopilot_preflight_audit.py` for canonical command shape, failure, and timeout.
- `epyc-orchestrator` `dbcae29` lands P3 generated-current-stack operator summaries. The patch adds generated `docs/generated/current_stack_summary.md`, reusable `scripts/registry/render_stack_summary.py`, stack-change pipeline `operator_summary` check/update integration, and system-card helper reuse so operator/planner rows come from stack-prior truth instead of copied constants. The committed generated summary has 10 live HOT roles and no deployable `architect_coding` row. During review, stale staging of the generated summary was caught, and `tests/unit/test_stack_change_pipeline.py` now asserts the written summary equals `render_current_stack_summary(...)` instead of merely checking that the file exists.
- Validation reported for `dbcae29`: `uv run ruff check scripts/registry/render_stack_summary.py scripts/autopilot/gen_system_card.py scripts/registry/stack_change_pipeline.py tests/unit/test_stack_change_pipeline.py tests/unit/test_autopilot_system_card.py`; `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider tests/unit/test_autopilot_system_card.py tests/unit/test_stack_change_pipeline.py` -> 17 passed; `uv run python scripts/registry/render_stack_summary.py --check`; `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate` -> `operator_summary: ok`, `q_scorer_priors: ok`, `promotion_gate: ok` / 48 passed with known warning classes unchanged (`waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`); `git diff --cached --check`.
- `epyc-orchestrator` `6474204` expands `scripts/registry/stack_change_pipeline.py` `PROMOTION_GATE_TARGETS` to include benchmark/seeding preflight suites: `tests/unit/test_seeding_infra.py`, `tests/unit/test_seeding_infra_additional.py`, `tests/unit/test_seeding_infra_branching.py`, and `tests/unit/test_seed_specialist_routing_main_and_retry.py`. It also repairs stale benchmark test fixtures by using `_MOD.MODEL_PORTS[0]` instead of retired port `8080`, adds current debugger diagnostic fields (`difficulty_score`, `difficulty_band`, `factual_risk_score`, `factual_risk_band`) to the retry helper, and fixes simulated-fixture self-contamination by routing fixture updates through a temp `operator_summary` with a regression proving they do not mutate real `docs/generated/current_stack_summary.md`.
- Validation reported for `6474204`: ruff on touched files passed; `render_stack_summary.py --check` passed; simulated fixtures 7 passed; expanded focused target 128 passed; full `stack_change_pipeline.py check --run-promotion-gate` passed. The executable promotion gate now runs 163 tests, with warning buckets unchanged (`waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`).
- `epyc-orchestrator` `1457e58` factors the existing status attestation warning text in `scripts/server/stack_commands.py` into `runtime_attestation_warnings()` and keeps `cmd_status` output behavior aligned with the previous status warning semantics.
- The same patch adds a `runtime_attestation` step to `scripts/registry/stack_change_pipeline.py` after `q_scorer_priors` and before `promotion_gate`. It fails promotion on concrete live model/mmproj drift and skips the executable pytest gate when earlier checks fail.
- Current live check reported `runtime_attestation: ok`; no concrete live model/mmproj drift was detected.
- Validation reported for `1457e58`: ruff on touched files passed with legacy launcher `F401` ignored; focused pytest `tests/unit/test_orchestrator_stack_reload.py tests/unit/test_stack_change_pipeline.py tests/unit/test_stack_change_pipeline_simulated_fixtures.py` -> 38 passed; broader adjacent pytest `tests/unit/test_orchestrator_stack_reload.py tests/unit/test_stack_processes.py tests/unit/test_stack_runtime.py tests/unit/test_build_server_command_helpers.py tests/unit/test_stack_change_pipeline.py tests/unit/test_stack_change_pipeline_simulated_fixtures.py tests/unit/test_autopilot_preflight_audit.py` -> 111 passed; `stack_change_pipeline.py check --run-promotion-gate` passed with `runtime_attestation: ok`, promotion gate 163 passed, and warning buckets unchanged (`waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`).
- `epyc-orchestrator` `3065b8b` extends `runtime_attestation_warnings()` and the `runtime_attestation` promotion step beyond model/mmproj drift. The gate now reports unmanaged known-stack listeners/state gaps and concrete live runtime flag drift: binary path, `-m`, `-md`, `--mmproj`, `-c`, `-np`, `-ub`, `-ctk`/`-ctv`, `--no-mmap`/`--mlock`, `--slot-save-path`, `--flash-attn`, `--jinja`, `--reasoning`, `--override-kv`, and MTP/spec flags.
- Validation reported for `3065b8b`: ruff passed on `scripts/server/stack_commands.py`, `scripts/registry/stack_change_pipeline.py`, and `tests/unit/test_orchestrator_stack_reload.py`; live `runtime_attestation_warnings()` returned `warnings=0`; focused pytest `tests/unit/test_orchestrator_stack_reload.py` -> 19 passed; broader adjacent suite -> 114 passed; `stack_change_pipeline.py check --run-promotion-gate` passed with `runtime_attestation: ok`, detail `no concrete live process drift detected`, promotion gate 163 passed, and warning buckets unchanged (`waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`).
- Scope note: `3065b8b` closes the P5 runtime-attestation target set for the current stack. Future stack-prior/runtime-contract expansion should add any new launch/runtime flags to this same attestation surface and promotion-gate tests.
- `epyc-orchestrator` `d3643eb` adds enforced model-specific `consumer_surfaces` to `orchestration/stack_change_surface_manifest.yaml` and validates them in `scripts/validate/stack_change_guard.py`.
- Required consumer surface IDs are now: `q_scorer_priors`, `seeding_reward_priors`, `routing_prior_consumers`, `admission_policy`, `lock_tap_policy`, `config_model_catalog`, `health_preflight_probes`, `launch_maps`, `dashboard_status_system_cards`, `planner_prompt_guidance`, `procedure_role_enums`, `generated_stack_docs`, and `runtime_attestation`.
- Validation reported for `d3643eb`: ruff passed for `scripts/validate/stack_change_guard.py` and `tests/unit/test_stack_change_guard.py`; `tests/unit/test_stack_change_guard.py` -> 39 passed; `stack_change_guard.py --list-hardcoded-surface-rules --surface-inventory-format json` reports `consumer_surface_count: 13`; default `stack_change_pipeline.py check` passed; `stack_change_pipeline.py check --run-promotion-gate` passed with `runtime_attestation: ok`, promotion gate 163 passed, and warning buckets unchanged.
- `epyc-orchestrator` `0cdc15e` migrates the `lock_tap_policy` safe-streaming role table in `src/runtime/inference_tap.py`: safe-mode non-stream roles now derive from generated stack-prior `model.mem_gb`, with fallback to the prior architect-only behavior when stack priors are missing or malformed.
- Current live derived policy preserves behavior: `SAFE_NON_STREAM_ROLES ['architect_general']`.
- Validation reported for `0cdc15e`: ruff passed for `src/runtime/inference_tap.py` and `tests/unit/test_inference_tap.py`; `tests/unit/test_inference_tap.py` -> 32 passed; manifest lock/tap validation command `tests/unit/test_inference_lock.py tests/unit/test_inference_tap.py` -> 43 passed; default `stack_change_pipeline.py check` passed; `stack_change_pipeline.py check --run-promotion-gate` passed with promotion gate 163 and unchanged warning buckets.
- `epyc-orchestrator` `f41b1f3` migrates the P2 `config_model_catalog` surface: `ServerURLsConfig` and Pydantic `ServerURLsSettings` defaults now derive from generated stack priors, environment overrides remain authoritative, and explicit degraded fallback values stay aligned with current stack-manifest aliases.
- Validation reported for `f41b1f3`: ruff passed on touched files; config/registry pytest set -> 167 passed; topology/health/vision/lock/tap/admission set -> 91 passed; stack governance set -> 113 passed; API/chat set -> 83 passed, 2 skipped; extra chat-template/concurrency set -> 26 passed; default `stack_change_pipeline.py check` passed; `stack_change_pipeline.py check --run-promotion-gate` passed with promotion gate 163 passed and warning buckets unchanged (`waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`).
- `epyc-orchestrator` `c7928cf` migrates the P2 `dashboard_status_system_cards` / generated status surface: dashboard model-serving port labels now project from generated stack-prior launch entries instead of static hand-maintained port-range hints. Alias and candidate records do not overwrite primary physical roles, service-only ports retain explicit fallback labels, and `/dashboard/api/node/{port}` uses the same `_port_hint` helper as topology discovery.
- Validation reported for `c7928cf`: ruff passed on dashboard files; `uv run pytest -q tests/unit/test_dashboard_helpers.py tests/unit/test_dashboard_route_html.py tests/unit/test_autopilot_system_card.py` -> 75 passed; `stack_change_pipeline.py check --run-promotion-gate` passed with `runtime_attestation: ok`, promotion gate 163 passed, and warning buckets unchanged.
- Benchmark/seeding preflight suites are now included in the canonical launch/AutoPilot promotion gate. Direct edits to benchmark `scripts/benchmark/seeding_infra.py:run_preflight` were intentionally avoided because GitNexus reported HIGH upstream blast radius across benchmark entrypoints; if future acceptance requires direct benchmark runtime enforcement rather than promotion-gate coverage, keep that as a focused follow-up.
- AutoPilot clean window before this patch produced trial `805` as frontier and trial `806` as dominated/healthy. The main agent is separately repairing the archive-authority tail and refreshing orchestrator GitNexus; this sidecar did not run AutoPilot, inference, seeding, or orchestrator code.

Prior lightweight audit result:

- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/registry/stack_change_pipeline.py check` passed in `epyc-orchestrator`: descriptors fresh, stack priors fresh, procedure enums checked, loose/all-surface/strict guard stages non-blocking, `summary: ok`, and the acceptance block printed the promotion-gate command plus surface-inventory command.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces --surface-summary-only` reported `WARN: 99 unique stack-prior warning(s) (99 total)` with `surface_warnings: waived_production_blocker=2, legacy_test=72, historical_doc=25`.
- The live generated contract has the flagged facts correct: `frontdoor` and `coder_escalation` both use `qwen3.6-35b-a3b-q8_0`, port `8070`, HOT tier, shared mmap, and `memory_cost: 1.0`; `architect_general` and `ingest_long_context` are HOT with `memory_cost: 1.0`; `architect_coding` is absent from live stack-prior roles.
- The risk is no longer "q_scorer is definitely wrong by default", "production launch can skip the canonical stack-change gate by default", "AutoPilot preflight can reach model/web/inference checks before the canonical stack-change gate", "the primary current-stack operator summary is hand-copied", "benchmark/seeding preflight regressions are outside the executable promotion-gate target set", "concrete live model/mmproj drift can pass promotion unnoticed", "known-stack listeners/state gaps and concrete binary/runtime flag drift can pass promotion unnoticed", "model-specific consumer surfaces have no enforced ownership inventory", "tap safe-streaming non-stream roles are a static role-name table", "`config_model_catalog` server URL defaults are hand-copied from the stack", or "dashboard model-serving port labels come from static port-range hints". q_scorer now prefers stack priors, the promotion gate checks live prior-source provenance, production start runs that gate before launch, AutoPilot preflight runs the same gate first, `dbcae29` makes the current operator stack summary generated and checked by the stack pipeline, `6474204` brings benchmark/seeding preflight suites into the gate, `1457e58` gates promotion on concrete live model/mmproj drift, `3065b8b` gates promotion on the current runtime flag/listener/state target set, `d3643eb` enforces the 13-surface consumer ownership inventory, `0cdc15e` derives tap safe-mode non-stream roles from stack-prior `model.mem_gb`, `f41b1f3` derives config model catalog server URL defaults from generated stack priors while preserving env overrides and degraded fallbacks, and `c7928cf` derives dashboard/status model-serving port labels from stack-prior launch entries. The remaining risk is that direct benchmark runtime paths, broader static lock/tap policy, and other high-risk consumer implementations can still bypass or outlive generated truth until the remaining P0/P2 migration work is finished.

Use this as the follow-up implementation order:

- [ ] **P0 - Promote the canonical preflight to launch/AutoPilot/benchmark gates.** Production `orchestrator_stack.py start` now runs `stack_change_pipeline.py check --run-promotion-gate` before host prereqs/model launch as of `e31ebe1`, with dev/validate-only/migration dry-run skips and explicit emergency bypass. AutoPilot preflight now runs the same gate first as of `e02930f`, before model/web/inference checks. `6474204` expands the gate target set to benchmark/seeding preflight suites, so launch/AutoPilot promotion now executes those regressions. Runtime attestation is inside that canonical gate as of `1457e58`/`3065b8b`. Keep this waypoint open only for direct benchmark runtime enforcement if required, because GitNexus flagged benchmark `scripts/benchmark/seeding_infra.py:run_preflight` as HIGH upstream blast radius.
- [x] **P1 - Close live-looking q_scorer fallback residue.** `1148ff6` keeps degraded/offline fallbacks but blocks promotion when valid stack priors exist and any live q_scorer role resolves TPS, quality, or memory priors from degraded fallback provenance. Tests now assert source provenance for the flagged roles.
- [ ] **P2 - Expand surface ownership from scanner rules to consumer surfaces.** `d3643eb` lands the first enforced model-specific consumer-surface manifest pass: the guard now requires 13 `consumer_surfaces` (`q_scorer_priors`, `seeding_reward_priors`, `routing_prior_consumers`, `admission_policy`, `lock_tap_policy`, `config_model_catalog`, `health_preflight_probes`, `launch_maps`, `dashboard_status_system_cards`, `planner_prompt_guidance`, `procedure_role_enums`, `generated_stack_docs`, `runtime_attestation`) and reports `consumer_surface_count: 13` in JSON inventory output. `0cdc15e` lands the first `lock_tap_policy` migration by deriving tap safe-mode non-stream roles from stack-prior `model.mem_gb`, currently preserving `SAFE_NON_STREAM_ROLES ['architect_general']`. `f41b1f3` lands the first `config_model_catalog` migration by deriving `ServerURLsConfig` and Pydantic `ServerURLsSettings` defaults from stack-prior server URL aliases, while retaining env override precedence and explicit degraded fallback values. `c7928cf` lands the first `dashboard_status_system_cards` migration by deriving dashboard/status model-serving port labels from stack-prior launch entries while preserving service-only fallback labels and primary physical role precedence. Keep P2 open for broader static lock/tap policy cleanup, other high-risk consumer migrations, and follow-through validation inside those surfaces.
- [x] **P3 - Generate current operator/planner stack summaries or mark them historical.** `dbcae29` adds generated `docs/generated/current_stack_summary.md`, `scripts/registry/render_stack_summary.py`, stack pipeline `operator_summary` check/update support, and system-card helper reuse. The primary current operator summary is now generated from stack priors and validated by `stack_change_pipeline.py check --run-promotion-gate`; the committed summary has 10 live HOT roles and no deployable `architect_coding` row. Any residual doc surfaces found by later scanner work should be handled under P2 consumer ownership / historical-label cleanup, not by reopening this primary-summary waypoint.
- [x] **P4 - Prove data-only swaps for the exact stale cases.** Simulated fixtures now cover the stale shared-server, retired-role, runtime/context/KV/acceleration, q_scorer-provenance, and launch/VL fixture targets without production source edits. `1148ff6` specifically added q_scorer provenance assertions to the `frontdoor`/`coder_escalation` data-only swap and completed the context/KV/acceleration fixture with `architect_general` quality data.
- [x] **P5 - Wire runtime attestation into promotion.** `1457e58` adds the first promotion-time `runtime_attestation` step and closes the concrete live model/mmproj drift acceptance gate; `3065b8b` extends it to unmanaged known-stack listeners/state gaps and concrete live runtime flag drift (`binary_path`, `-m`, `-md`, `--mmproj`, `-c`, `-np`, `-ub`, `-ctk`/`-ctv`, `--no-mmap`/`--mlock`, `--slot-save-path`, `--flash-attn`, `--jinja`, `--reasoning`, `--override-kv`, and MTP/spec flags). Current live check reported `runtime_attestation: ok`, detail `no concrete live process drift detected`, and live `runtime_attestation_warnings()` returned `warnings=0`.

Dependency graph:

```text
Structured truth
  -> descriptor compile/check
  -> stack-prior compile/check
  -> procedure enum sync/check
  -> guard + surface manifest
  -> typed consumers and generated summaries
  -> process/runtime attestation
  -> launch / AutoPilot preflight / benchmark interpretation

P0 production-launch enforcement depends on the existing pipeline and no-inference promotion tests, including the `1148ff6` `q_scorer_priors` stage, and is wired in `e31ebe1`.
P0 AutoPilot preflight enforcement uses the same executable promotion gate and is wired in `e02930f` before model/web/inference checks.
P0 benchmark/seeding preflight test coverage is included in the executable promotion gate as of `6474204`; direct benchmark `scripts/benchmark/seeding_infra.py:run_preflight` runtime enforcement remains a focused follow-up if the benchmark path must fail closed outside launch/AutoPilot promotion.
P2 consumer-surface ownership metadata is enforced as of `d3643eb` and depends on stack-prior contract v4 staying fresh; the tap safe-streaming role table migration landed in `0cdc15e`, `config_model_catalog` server URL default derivation landed in `f41b1f3`, and dashboard/status port-label derivation landed in `c7928cf`, while broader static lock/tap policy and other high-risk consumer migrations remain separate implementation work. Runtime attestation is now a promotion-gate regression target for the current stack-prior runtime contract.
P3 primary-summary generation is closed by `dbcae29`; any remaining doc-surface classification rides P2 ownership or explicit historical-label cleanup.
P1 and P4 are closed for the current stale q_scorer/data-only fixture cases but should remain regression targets in the promotion gate.
AutoPilot promotion is covered by `e02930f`; benchmark/seeding preflight regression coverage is covered by `6474204`; concrete live model/mmproj drift promotion gating is covered by `1457e58`; full current runtime flag/listener/state attestation is covered by `3065b8b`; first-pass consumer-surface ownership enforcement is covered by `d3643eb`; tap safe-streaming non-stream role derivation is covered by `0cdc15e`; config catalog server URL default derivation is covered by `f41b1f3`; dashboard/status port-label derivation is covered by `c7928cf`; direct benchmark runtime enforcement still depends on the remaining P0 nuance plus actual high-risk P2 consumer migrations. Operator current-stack summary evidence is generated and checked as of `dbcae29`.
```

Stale/hardcoded examples found in this audit:

- `epyc-orchestrator/orchestration/repl_memory/q_scorer.py` still contains degraded TPS/quality/memory fallbacks for offline/degraded operation, but `1148ff6` added `validate_live_q_scorer_prior_sources()` so live-role promotion fails if valid stack priors are bypassed for degraded fallback provenance.
- `epyc-orchestrator/orchestration/repl_memory/q_scorer.py` loads generated stack-prior live priors first and records source provenance; tests now assert that live roles use stack-prior sources when the artifact is valid.
- `epyc-orchestrator/orchestration/derived/stack_priors.yaml:207` and `:326` show `coder_escalation` and `frontdoor` sharing model identity, port `8070`, HOT tier, and `memory_cost: 1.0`; `:469` shows `ingest_long_context` HOT with `memory_cost: 1.0`.
- `epyc-orchestrator/scripts/server/stack_manifest.py:129` is the launcher tier/alias source; `:132` documents `coder_escalation`/`worker_summarize` sharing frontdoor, `:157`/`:158` classify `architect_general` and `ingest_long_context` as HOT, and `:177` documents `architect_coding` removal.
- `epyc-orchestrator/scripts/registry/stack_change_pipeline.py:121` emits the acceptance/warning/promotion/surface-inventory block, while `:588` keeps executable promotion-gate mode behind `--run-promotion-gate`.
- `epyc-orchestrator/scripts/server/orchestrator_stack.py start` runs the executable promotion gate before production host prereqs/model launch as of `e31ebe1`. Dev launches, validate-only, and migration dry-run skip it; bypass must be explicit through `--skip-stack-change-gate` or `ORCHESTRATOR_SKIP_STACK_CHANGE_GATE=1`.
- `epyc-orchestrator/scripts/autopilot/preflight_audit.py` runs the executable promotion gate first as of `e02930f`, before model-server, web-search, web-fetch, inference, blacklist, archive-authority, and recent-trial checks.
- `epyc-orchestrator/scripts/registry/stack_change_pipeline.py` includes benchmark/seeding preflight suites in `PROMOTION_GATE_TARGETS` as of `6474204`, lifting the promotion gate from 48 tests to 163 tests.
- `epyc-orchestrator/scripts/server/stack_commands.py` exposes `runtime_attestation_warnings()` as of `1457e58`, factoring the status warning text while preserving `cmd_status` output behavior; as of `3065b8b`, that helper also checks unmanaged known-stack listeners/state gaps and concrete live binary/runtime flag drift against generated launch contracts.
- `epyc-orchestrator/scripts/registry/stack_change_pipeline.py` runs `runtime_attestation` after `q_scorer_priors` and before `promotion_gate` as of `1457e58`; it fails on concrete live model/mmproj drift, and as of `3065b8b` also fails on unmanaged known-stack listeners/state gaps and concrete live runtime flag drift before running the pytest promotion gate.
- `epyc-orchestrator/scripts/validate/stack_change_guard.py:1240` enforces HOT live roles have `memory_cost: 1.0`; `:1273` promotes unwaived warnings to strict errors; `:1328`/`:1339` expose rule inventory and summary modes.

## Current Evidence

- `epyc-orchestrator/docs/reference/stack-truth-precedence.md` already defines the precedence rule: live serving topology first, model descriptors second, role metadata third, historical/benchmark records last.
- `epyc-orchestrator/orchestration/derived/stack_priors.yaml` is the generated consumer contract. Current contract version is `4`, with required role, serving, launch, runtime, and prior fields.
- `epyc-orchestrator/scripts/registry/stack_change_pipeline.py` already composes descriptor check/update, stack-prior check/update, procedure enum sync/check, loose guard, all-surface guard, strict guard, and simulated fixture references.
- `epyc-orchestrator/scripts/validate/stack_change_guard.py` now exposes a machine-readable hardcoded-surface rule inventory in `34a0407`: `hardcoded_surface_rule_inventory()` plus `--list-hardcoded-surface-rules --surface-inventory-format yaml|json`. The inventory reports `version`, `rule_count`, `categories`, and per-rule `rule_id`, category, pattern, path/exclude globs, comment-line handling, and remediation. The same commit fixed direct-by-path CLI import hygiene so `python scripts/validate/stack_change_guard.py ...` works outside pipeline imports.
- `epyc-orchestrator/scripts/registry/stack_change_pipeline.py check` now prints `surface_inventory: run uv run python scripts/validate/stack_change_guard.py --list-hardcoded-surface-rules` in the passing acceptance block as of `b82ae3d`, so the canonical stack-change preflight points operators at the machine-readable scanner-rule catalog. No enforcement semantics changed.
- `epyc-orchestrator/scripts/validate/stack_change_guard.py` now exposes `hardcoded_surface_warning_counts()` and `--surface-summary-only` as of `2cb3d6c`, letting operators compact hardcoded-surface scan warnings into category counts such as waived production blockers, legacy tests, and historical docs while preserving the default detailed warning output. This is reporting hygiene only; canonical pipeline output and guard policy are unchanged.
- `epyc-orchestrator/orchestration/stack_change_surface_manifest.yaml` landed in `7815318` as the first enforced W2 ownership manifest for hardcoded model/stack scanner rules. Each rule now has exactly one manifest entry with rule ID, category, owner, consumer scope, promotion-blocker policy, review cadence, evidence command, and drift response. The guard validates manifest presence, coverage, duplicate or unknown rule IDs, category consistency, required text fields, and promotion-blocker policy, and `stack_change_pipeline.py check` now fails if scanner-rule ownership drifts.
- `epyc-orchestrator` `d3643eb` extends `orchestration/stack_change_surface_manifest.yaml` with enforced model-specific `consumer_surfaces` and teaches `scripts/validate/stack_change_guard.py` to validate required surface IDs and expose `consumer_surface_count: 13` in the JSON rule inventory. This is the first P2 consumer-surface ownership enforcement pass; it does not by itself migrate every high-risk consumer to typed/generated truth.
- `epyc-orchestrator` `0cdc15e` migrates `src/runtime/inference_tap.py` safe-mode non-stream role selection from a static architect-role table to stack-prior-derived `model.mem_gb`, with malformed/missing-prior fallback to prior behavior. The live derived policy remains `SAFE_NON_STREAM_ROLES ['architect_general']`; broader static lock/tap policy remains open under P2.
- `epyc-orchestrator` `f41b1f3` migrates `src/config/config_model_catalog.py` server URL defaults from hand-copied aliases to generated stack-prior aliases. It derives `ServerURLsConfig` and Pydantic `ServerURLsSettings` defaults from stack-prior truth, preserves environment override precedence, and keeps explicit degraded fallback values aligned with the current stack manifest.
- `epyc-orchestrator` `c7928cf` migrates dashboard/status model-serving port labels from static port-range hints to generated stack-prior launch entries. Alias and candidate records cannot overwrite primary physical-role labels, service-only ports keep explicit fallback labels, and `/dashboard/api/node/{port}` shares `_port_hint` with topology discovery.
- `epyc-orchestrator/orchestration/repl_memory/q_scorer.py` now loads live TPS, quality, and memory priors from stack priors first and labels local constants as degraded fallback.
- Generated/system-card and launch-wrapper work has started: AutoPilot live-stack rows and production launch summaries are derived from stack priors or stack manifest instead of hand-written inventory.
- Production launch gating has started: `orchestrator_stack.py start` now runs the canonical no-inference promotion gate before host prereqs/model launch for production starts.
- AutoPilot preflight gating has started: `preflight_audit.py` now runs the same canonical promotion gate before model/web/inference checks.
- Benchmark/seeding promotion-gate coverage has started: `stack_change_pipeline.py check --run-promotion-gate` now executes the seeding infrastructure and specialist-routing preflight unit suites before accepting the stack.
- Runtime attestation promotion coverage now covers the current concrete runtime target set: `stack_change_pipeline.py check --run-promotion-gate` runs `runtime_attestation` before the executable pytest gate and fails on concrete live model/mmproj drift, unmanaged known-stack listeners/state gaps, and concrete live runtime flag drift. The current live check reported `runtime_attestation: ok`, detail `no concrete live process drift detected`.
- Root GitNexus was refreshed and current before the `3065b8b` documentation edit. The docs target was not represented as a code symbol; the relevant orchestrator helper impact check for `runtime_attestation_warnings()` was LOW before the implementation lane edited it.

## Single-Source Contract

Every model-stack change must classify and update these quantities through structured sources:

| Quantity | Canonical source | Generated surface / consumer |
|---|---|---|
| Live role -> endpoint, port, slots, tier, shared-server binding | `epyc-orchestrator/orchestration/model_registry.yaml` `server_mode.*`, reconciled with `scripts/server/stack_manifest.py` | `orchestration/derived/stack_priors.yaml` `roles.*.serving` |
| Physical model identity, modality, context, quant, evidence | `orchestration/model_descriptors.yaml` and descriptor compiler inputs | `stack_priors.yaml` `model`, `evidence`, `priors`, `acceleration` |
| Benchmark/candidate history | `epyc-inference-research/orchestration/model_registry.yaml` and benchmark artifacts | imported into descriptors only with provenance/status; never live truth by itself |
| q_scorer, seeding, replay, reward cost/TPS/quality | `stack_priors.yaml` `roles.*.priors` | typed loaders or explicit degraded fallback provenance |
| Procedure role enums and executor permissions | live roles from `stack_priors.yaml` | `sync_procedure_role_enums.py` generated/check mode |
| Launch runtime, binary, context, KV/cache, spec/MTP, mmproj | stack manifest/runtime witnesses projected into stack priors | stack-change guard and launch/status consumers |
| Runtime policy tables: admission, locks, tap streaming, high-cost roles | stack-prior tier/slots/model class plus explicit policy hints | generated policy projection or clearly named degraded fallback |
| Operator docs, planner prompts, dashboards, system cards | generated stack summary plus runtime attestation | no manual current-stack tables unless labelled historical |
| Config model catalog server URLs | stack-prior serving aliases with env override precedence | `ServerURLsConfig`, `ServerURLsSettings`, explicit degraded fallback |
| Dashboard/status model-serving port labels | stack-prior launch entries, primary physical role first | topology discovery, `/dashboard/api/node/{port}`, service-only fallback labels |

Rules:

- Production consumers should use typed helpers around `src/registry/stack_priors.py` where possible.
- Direct YAML parsing is acceptable for scripts that cannot import runtime code, but it must preserve degraded-mode warnings and source provenance.
- Fallback constants must be named `FALLBACK_*` or `DEGRADED_*`, must exclude retired live roles unless testing historical compatibility, and must not silently satisfy live decisions while fresh stack priors exist.
- Historical docs and replay data may retain retired roles only with era/legacy classification; they are not live role truth.

## Required Operator Workflow

The target operator workflow should be one canonical no-inference command family:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/registry/stack_change_pipeline.py check
uv run python scripts/registry/stack_change_pipeline.py update
uv run python scripts/registry/stack_change_pipeline.py check --strict
```

`check` must be read-only and fail when generated artifacts are stale, procedure enums drift, stack-prior contracts are invalid, source hashes changed, live known gaps block decision-grade consumers, or production hardcoded surfaces are unwaived.

`update` must write only generated artifacts from structured truth: descriptors, stack priors, procedure role enums, and generated stack summaries once those exist. It must never invent missing measurements, classify hardcoded surfaces by default, or edit historical records.

Before production launch, AutoPilot resume, or benchmark interpretation, require:

- descriptor check/update clean;
- stack-prior check/update clean;
- procedure enum check clean;
- stack-change guard loose/all-surface/strict result summarized;
- simulated data-only stack-change fixtures passing;
- current process/port/runtime attestation compared against generated priors; as of `1457e58`, concrete live model/mmproj drift is gated, and as of `3065b8b`, unmanaged known-stack listeners/state gaps plus concrete live binary/runtime flag drift are gated for the current runtime-contract target set;
- doc/planner/operator summaries generated or explicitly marked historical.

As of `e31ebe1`, production `orchestrator_stack.py start` enforces the canonical no-inference promotion gate before host prereqs/model launch. As of `e02930f`, AutoPilot preflight enforces the same gate before model/web/inference checks. As of `1457e58`, the gate includes concrete live model/mmproj drift attestation. As of `3065b8b`, the gate also includes unmanaged known-stack listeners/state gaps and concrete live binary/runtime flag drift. As of `d3643eb`, P2 has enforced ownership metadata for the required consumer surfaces. As of `0cdc15e`, the tap safe-mode non-stream role table is derived from stack priors. As of `f41b1f3`, config model catalog server URL defaults are derived from stack-prior aliases with env overrides preserved. As of `c7928cf`, dashboard/status model-serving port labels are derived from stack-prior launch entries. This leaves benchmark interpretation/direct runtime enforcement, broader static lock/tap policy, and other high-risk consumer migrations as the remaining model-stack hardening work.

## Implementation Work Packages

### W1 - Finish The Canonical Pipeline Command

Goal: one operator command replaces scattered manual steps.

Tasks:

- Extend `scripts/registry/stack_change_pipeline.py` output with an acceptance summary: descriptor freshness, stack-prior freshness, source hashes, loose/all-surface/strict guard counts, stale surface categories, simulated fixture target, and exact remediation commands.
- Keep the `b82ae3d` `surface_inventory:` acceptance hint in the passing `check` output so operators can discover the scanner-rule catalog before launch or AutoPilot resume review.
- Add a "promotion gate" mode for launch/AutoPilot decisions that refuses on production hardcoded surfaces, missing decision-grade priors, stale generated summaries, or unattested live processes.
- Keep production launch enforcement wired through `orchestrator_stack.py start` and AutoPilot preflight enforcement wired through `preflight_audit.py`; with runtime attestation now in the canonical gate, extend equivalent enforcement to benchmark-interpretation paths only if direct benchmark runtime enforcement is required beyond promotion-gate coverage.
- Ensure update mode writes generated summaries only after structured artifacts are fresh.

Likely targets:

- `scripts/registry/stack_change_pipeline.py`
- `scripts/validate/stack_change_guard.py`
- `src/registry/stack_priors.py`
- `tests/unit/test_stack_change_pipeline.py`
- `tests/unit/test_stack_change_pipeline_simulated_fixtures.py`

### W2 - Add A Complete Model-Specific Surface Inventory

Goal: every live model-specific quantity has an owner and validator.

Current increment: `34a0407` exposes the existing hardcoded-surface scanner rules as a machine-readable inventory through `hardcoded_surface_rule_inventory()` and the `stack_change_guard.py --list-hardcoded-surface-rules` CLI. `7815318` adds `orchestration/stack_change_surface_manifest.yaml` as the first enforced ownership map for those scanner rules, and the guard/pipeline now fail if the scanner-rule ownership manifest is missing, incomplete, duplicated, category-inconsistent, or promotion-policy inconsistent. `d3643eb` adds the first enforced model-specific `consumer_surfaces` inventory to the same manifest and validates 13 required surface IDs in `stack_change_guard.py`; JSON inventory now reports `consumer_surface_count: 13`. `0cdc15e` lands the first `lock_tap_policy` migration by deriving tap safe-mode non-stream roles from stack-prior `model.mem_gb` while preserving current live behavior. `f41b1f3` lands the first `config_model_catalog` migration by deriving server URL defaults from stack-prior aliases while preserving env overrides and degraded fallback values. `c7928cf` lands the first `dashboard_status_system_cards` migration by deriving model-serving port labels from stack-prior launch entries while preserving service-only fallback labels. This closes the first W2/P2 enforcement pass for consumer-surface ownership plus three concrete consumer migrations; actual high-risk consumer migrations and broader static lock/tap policy remain open.

Tasks:

- Maintain the enforced `d3643eb` consumer-surface manifest for all required model-specific surfaces: q_scorer, seeding reward priors, routing prior consumers, admission, lock/tap policy, config model catalog, health/preflight probes, launch maps, dashboards/system cards, planner prompt guidance, procedure role enums, generated stack docs, and runtime attestation.
- Keep the distinction clear between "consumer surface owned" and "consumer migrated"; the current manifest identifies and governs every required surface, and `0cdc15e` / `f41b1f3` / `c7928cf` migrate tap safe-streaming, config catalog server URL defaults, and dashboard/status port labels, but other high-risk consumers still need typed/generated-truth migration follow-through.
- Continue the `lock_tap_policy` migration beyond tap safe-streaming non-stream roles wherever remaining static lock/tap policy still exists.
- Classify each surface as generated, typed consumer, explicit degraded fallback, legacy test, historical doc, or open production blocker.
- Teach the guard to report unclassified model-specific surfaces as actionable drift.

Likely targets:

- `orchestration/stack_change_guard_exceptions.yaml`
- `orchestration/stack_change_surface_manifest.yaml`
- `scripts/validate/stack_change_guard.py`
- `tests/unit/test_stack_change_guard.py`
- root handoff/wiki docs after implementation lands

### W3 - Centralize Typed Consumer APIs

Goal: production code stops hand-parsing stack facts.

Tasks:

- Add or extend stack-prior helpers for live roles, retired roles, serving records, scorer priors, policy hints, launch requirements, modality/projector requirements, and generated summary rows.
- Migrate remaining local policy tables where model identity, tier, port, cost, or residency is the underlying reason.
- Keep non-live compatibility aliases as explicit compatibility API, not live role discovery.

Likely targets:

- `src/registry/stack_priors.py`
- `src/config/models.py`
- `src/runtime/inference_lock.py`
- `src/runtime/inference_tap.py`
- `src/api/admission.py`
- dashboard/status/health routes
- q_scorer and seeding/replay consumers

### W4 - Generate Current Docs And Planner Context

Goal: operator-facing text cannot become hidden source truth.

Tasks:

- Generate current stack summaries from stack priors and runtime attestation for system cards, status pages, and runbooks.
- Add guard coverage for static current-stack tables in prompts/docs/scripts.
- Label historical docs explicitly when they preserve old role/model names.
- Use documentation sidecars during implementation so docs are updated in parallel with code changes, but do not let sidecars edit shared indices unless the main workflow approves.

Likely targets:

- `scripts/autopilot/gen_system_card.py`
- `scripts/server/launch_production.sh`
- dashboard/status routes
- root `handoffs/active/*` and `wiki/*` summaries
- docs build/rewrite validation where applicable

### W5 - Prove Data-Only Stack Changes

Goal: model swaps and role retirements are data updates, not source edits.

Tasks:

- Extend simulated fixtures for:
  - shared-server model swaps like `frontdoor` / `coder_escalation`;
  - role retirement like `architect_coding`;
  - HOT/WARM tier changes;
  - context/KV/spec/MTP changes;
  - VL model/mmproj swaps;
  - research-only candidate additions.
- Acceptance: generated descriptors/priors/enums/summaries change, production code does not.
- Fail if live consumers read stale fallback tables while valid stack priors exist.

Likely targets:

- `tests/unit/test_stack_change_pipeline_simulated_fixtures.py`
- stack-prior compiler fixtures
- guard fixtures for stale surface recurrence

## Validation Checklist

Run this no-inference validation set after implementation changes:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/registry/stack_change_pipeline.py check
uv run python scripts/registry/stack_change_pipeline.py check --allow-known-gaps
uv run python scripts/registry/stack_change_pipeline.py update
uv run python scripts/validate/stack_change_guard.py
uv run python scripts/validate/stack_change_guard.py --list-hardcoded-surface-rules --surface-inventory-format yaml
uv run python scripts/validate/stack_change_guard.py --list-hardcoded-surface-rules --surface-inventory-format json
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces --surface-summary-only
uv run python scripts/validate/stack_change_guard.py --strict
python3 scripts/registry/sync_procedure_role_enums.py --check
uv run --with pytest pytest -q \
  tests/unit/test_stack_change_pipeline.py \
  tests/unit/test_stack_change_pipeline_simulated_fixtures.py \
  tests/unit/test_stack_change_guard.py \
  tests/unit/test_stack_priors_compiler.py \
  tests/unit/test_model_descriptor_compiler.py \
  tests/unit/test_model_descriptors_schema.py \
  tests/unit/test_q_scorer.py
```

If code touches API/runtime consumers, add the focused consumer tests for admission, config, health/status, dashboard, vision, seeding, GraphRouter, and system-card generation.

## Non-Goals

- Do not choose the next model stack or run inference in this handoff.
- Do not replace the research registry; it remains evidence/candidate history.
- Do not make historical docs or old replay labels disappear; classify them.
- Do not hand-edit generated YAML to pass validation.
- Do not let fallback constants become "good enough" live truth.
- Do not register broad index updates from a sidecar unless the main workflow requests it.

## Done Criteria

- A documented operator can perform a role model swap by editing structured sources, running the canonical pipeline, and reviewing generated diffs.
- q_scorer, seeding/reward, admission, routing priors, runtime policy classifications, launch/status probes, and planner/operator summaries read stack-prior truth or report explicit degraded fallback provenance.
- `stack_change_pipeline.py check` is the canonical no-inference preflight for launch, AutoPilot resume, and model-stack benchmark interpretation.
- Simulated data-only fixtures prove shared-server swaps, role retirement, tier changes, launch/runtime changes, and VL projector changes without production source edits.
- All current-stack docs/prompts are generated or labelled historical.
