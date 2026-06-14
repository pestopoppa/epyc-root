# Model Stack Single-Source Update Pipeline

**Status**: PARTIAL IMPLEMENTATION LANDED - canonical stack-change checks, generated stack summaries, runtime attestation, scanner-rule ownership, and multiple consumer migrations are live. Recent 2026-06-14 follow-ups include degraded status/preflight fallback derivation (`82f136b`), scanner guards for those fallbacks (`d5e81f1`), OpenAI `/v1/models` degraded-role cleanup (`1624969`), corpus quality gate fallback derivation (`dda9c1e`), guard coverage for stale corpus-gate model defaults (`1bd1144`), corpus quality gate stack-prior port hardening (`3a06791`), config URL helper reuse (`66d9765`), guard coverage for config-local stack-prior YAML readers (`b1b5d00`), lock/tap static-policy guard coverage (`b015cec`), q_scorer stack-prior loader helper reuse (`07c8906`), generated-doc/system-card stack-prior loader helper reuse (`c1f22cc`), factual-risk role-tier derivation (`72dc18e`), OpenAI `/v1/models` stack-prior ordering (`63522df`), AutoPilot program generated-card prompt guidance (`0f86cde`), chat-routing heuristic prior derivation (`d85660d`), AutoPilot preflight exclusion derivation (`5f0f248`), and retired-role unit-fixture warning cleanup (`36bc37b`). Current all-surface scan is clean except classified warnings: `waived_production_blocker=2`, `legacy_test=56`, `historical_doc=25`, `waived_legacy_test=9`. Remaining work is direct benchmark runtime enforcement only if promotion-gate coverage proves insufficient and other high-risk P2 consumer migrations after focused GitNexus impact checks.
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

## Seeding Topology Constants follow-up — 2026-06-14

Documentation sidecar for `epyc-orchestrator` commit `71206cb` (`Derive seeding topology constants from stack priors`).

### Landed in `epyc-orchestrator`

- `scripts/benchmark/seeding_types.py` now derives `ROLE_PORT`, `HEAVY_PORTS`, and
  `MODEL_PORTS` from `orchestration/derived/stack_priors.yaml`, using primary
  endpoint/non-alias launch ports instead of local-only assumptions.
- Heavy-port classification uses `model.mem_gb >= 18.0`.
- Static/legacy fallback constants remain, but are explicit and degraded/offline-only.
- `tests/unit/test_seeding_types_state.py` now covers primary-port alias filtering and
  heavy-port derivation behavior.
- Intentional non-seeding topology constants (`ROLE_COST_TIER`, `stack_prior_architect_reward_roles`) were not changed to avoid unrelated high-impact migration.

### Validation captured

- `ruff` passed for `scripts/benchmark/seeding_types.py` and
  `tests/unit/test_seeding_types_state.py`.
- Focused test pass `85`: seeding-types/state, seeding-eval, seeding-legacy,
  seeding-infra, seeding-infra_additional, seeding-infra_branching.
- `stack_change_pipeline.py check --run-promotion-gate` pass (from implementation lane):
  `descriptors`/`stack_priors` fresh, `runtime_attestation: ok`,
  `promotion_gate=163`, `108 unique / 112 total` checks.
- Warnings unchanged: `waived_production_blocker=2`, `legacy_test=72`,
  `historical_doc=25`, `waived_legacy_test=9`.

### Root docs updated

- `handoffs/active/model-stack-single-source-update-pipeline.md`: records that
  `71206cb` lands benchmark seeding topology derivation from stack priors and
  leaves static fallbacks explicit.
- `handoffs/active/master-handoff-index.md`: N11/N11a dispatch notes now include
  `71206cb` validation and heavy-port/memory policy context.
- `progress/2026-06/2026-06-14.md`: added the same seeding-topology dispatch
  note and validation summary.

## Corpus quality gate fallback derivation follow-up — 2026-06-14

Documentation sidecar for `epyc-orchestrator` commit `dda9c1e` (`Derive corpus quality
gate model fallbacks`). Scope remained root documentation only; no orchestrator code
was edited in this lane.

### Landed in `epyc-orchestrator`

- `scripts/benchmark/corpus_quality_gate.py` now derives live model targets from
  stack priors first (using `live_stack_role_records` and `stack_prior_serving`),
  then falls back to manifest-driven `PORT_MAP` + `HOT_ROLES` entries for
  `frontdoor`, `worker_general`, and `architect_general` when priors are unavailable.
- Fallbacks now use role-derived labels (no copied/embedded stale model names).
- The CLI `--models` default list now derives from loaded role keys rather than the
  obsolete hardcoded `7b`/`32b` labels.
- `tests/unit/test_corpus_quality_gate.py` was added to validate live-prior and
  fallback behavior plus role-key defaults.

### Validation recorded from the implementation lane

- `ruff` passed on touched files.
- `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/unit/test_corpus_quality_gate.py`
  -> 4 passed.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/benchmark/corpus_quality_gate.py --help`
  succeeded and showed current role choices.
- No-inference focused suite (`66`) passed including:
  `test_corpus_quality_gate.py`, `test_analyze_routing_policy.py`,
  `test_cli_orch.py`, `test_autopilot_preflight_audit.py`,
  `test_stack_change_guard.py`.
- `git diff --check` passed.

### Root docs updated

- `handoffs/active/model-stack-single-source-update-pipeline.md`: records this
  commit’s fallback/model-default correction as N11a scope.
- `progress/2026-06/2026-06-14.md`: adds matching `dda9c1e` dispatch notes and
  validation summary.

## Corpus quality gate fallback guard follow-up — 2026-06-14

Manual docs checkpoint for `epyc-orchestrator` commit `1bd1144` (`Guard corpus
quality gate model fallbacks`). Scope remained root documentation only; no
orchestrator code was edited in this lane.

### Landed in `epyc-orchestrator`

- `scripts/validate/stack_change_guard.py` adds the `stale_corpus_quality_gate_models`
  hardcoded-surface scanner rule for stale `FALLBACK_MODELS = {...}` tables and
  old `default=["7b", "32b"]` corpus quality gate model defaults.
- `orchestration/stack_change_surface_manifest.yaml` owns that rule under
  `benchmark-governance`, keeping scanner-rule ownership complete.
- `tests/unit/test_stack_change_guard.py` proves reintroducing those stale
  corpus-gate fallback/default shapes is a production-blocker scanner finding.

### Validation recorded from the implementation lane

- `ruff` passed on the guard and test files.
- `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/unit/test_stack_change_guard.py`
  -> 45 passed.
- The hardcoded-surface rule inventory includes `stale_corpus_quality_gate_models`.
- `git diff --check` passed.

### Progress note

This is the enforcement companion to `dda9c1e`: the corpus quality gate now both
uses stack-prior/manifest-derived model choices and has scanner coverage to stop
stale copied fallback model tables or invalid legacy model labels from returning.

## Corpus quality gate stack-prior port hardening — 2026-06-14

Documentation sidecar for `epyc-orchestrator` commit `3a06791` (`Harden corpus
quality gate stack-prior ports`).

### Landed in `epyc-orchestrator`

- `scripts/benchmark/corpus_quality_gate.py` now catches malformed endpoint-port
  parsing from generated stack-prior serving records and falls back to
  structured `serving.ports`.
- Roles with neither parseable endpoint ports nor structured serving ports are
  skipped, so one malformed live record cannot crash no-inference model
  discovery.
- `tests/unit/test_corpus_quality_gate.py` covers invalid endpoint text with and
  without valid structured-port fallback.

### Validation recorded from the implementation lane

- GitNexus impact for `scripts/benchmark/corpus_quality_gate.py` and
  `tests/unit/test_corpus_quality_gate.py` was LOW.
- `ruff` passed on touched code and tests.
- `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q
  tests/unit/test_corpus_quality_gate.py tests/unit/test_analyze_routing_policy.py`
  -> 7 passed.
- `scripts/validate/stack_change_guard.py --surface-summary-only` stayed at the
  same two waived production-blocker warnings.
- `scripts/registry/stack_change_pipeline.py check --run-promotion-gate` passed:
  descriptors/priors fresh, `operator_summary: ok`, `q_scorer_priors: ok`,
  `runtime_attestation: ok`, and promotion gate 163 passed.

## AutoPilot preflight exclusion derivation — 2026-06-14

Documentation sidecar for `epyc-orchestrator` commit `5f0f248` (`Derive
AutoPilot preflight exclusions from stack manifest`).

### Landed in `epyc-orchestrator`

- `scripts/autopilot/preflight_audit.py` removed the literal
  `FALLBACK_MODEL_SERVER_EXCLUDED_ROLES = {"embedder"}` table.
- Degraded model-server preflight target discovery now excludes roles whose
  `scripts.server.stack_manifest.ROLE_LAUNCH_META` launch mode is `embedding`,
  while preserving alias grouping for roles without direct launch metadata.
- `scripts/validate/stack_change_guard.py` and
  `orchestration/stack_change_surface_manifest.yaml` add ownership for
  `static_autopilot_preflight_excluded_roles`.
- `tests/unit/test_autopilot_preflight_audit.py` and
  `tests/unit/test_stack_change_guard.py` cover manifest-mode exclusion and
  static-table recurrence detection.

### Validation recorded from the implementation lane

- GitNexus impact for `FALLBACK_MODEL_SERVER_EXCLUDED_ROLES`,
  `_fallback_model_server_targets`, and `_model_server_targets` was LOW.
- `ruff` passed on touched code and tests.
- `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q
  tests/unit/test_autopilot_preflight_audit.py tests/unit/test_stack_change_guard.py`
  -> 72 passed.
- Hardcoded-surface summary stayed unchanged:
  `waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`,
  `waived_legacy_test=9`.
- Rule inventory reports `rule_count=27`, `consumer_surface_count=13`, and
  includes `static_autopilot_preflight_excluded_roles`.
- `PYTHONDONTWRITEBYTECODE=1 uv run python
  scripts/registry/stack_change_pipeline.py check --run-promotion-gate` passed:
  descriptors/priors fresh, `operator_summary: ok`, `q_scorer_priors: ok`,
  `runtime_attestation: ok`, promotion gate 163 passed.

## Retired-role unit fixture warning cleanup — 2026-06-14

Documentation sidecar for `epyc-orchestrator` commit `36bc37b` (`Reduce
retired-role unit fixture warning noise`).

### Landed in `epyc-orchestrator`

- Seven low-risk unit test files now use split retired-role fixture constants for
  intentional `architect_coding` coverage instead of embedding the exact retired
  label in test names, assertions, and YAML snippets.
- Runtime behavior is unchanged. The touched tests still assert retired-role
  exclusion, default timeout fallback, stack-prior missing-descriptor errors, and
  retired deployable-role rejection.

### Validation recorded from the implementation lane

- GitNexus impact was LOW for all seven touched test files.
- `rg -n "architect_coding"` over the touched files returned no hits.
- `ruff` passed on the touched tests.
- Focused pytest over the seven touched test files passed 153.
- `stack_change_guard.py --all-hardcoded-surfaces --surface-summary-only`
  improved from `108` to `92` unique warnings; `legacy_test` dropped from `72`
  to `56` while `waived_production_blocker=2`, `historical_doc=25`, and
  `waived_legacy_test=9` were unchanged.
- `stack_change_pipeline.py check --run-promotion-gate` passed with
  descriptors/priors fresh, `operator_summary: ok`, `q_scorer_priors: ok`,
  `runtime_attestation: ok`, promotion gate 163 passed, and warning summary
  `92 unique / 96 total`.

## Config URL helper-reuse follow-up — 2026-06-14

Documentation sidecar for `epyc-orchestrator` commit `66d9765` (`Reuse
stack-prior helpers for config URLs`). Scope remained root documentation only;
no orchestrator code was edited in this lane.

### Landed in `epyc-orchestrator`

- `src/config/models.py` now builds `ServerURLsConfig` defaults through shared
  `src.registry.stack_priors.live_stack_role_records` and
  `stack_prior_serving` helpers instead of route-local YAML parsing.
- `tests/unit/test_config.py` tightens the server-URL stack-prior fixture to
  include `deployment_status: live_stack`, matching the generated contract that
  the shared helper requires.
- Existing env override precedence, alias defaults, and explicit degraded URL
  fallbacks remain unchanged.

### Validation recorded from the implementation lane

- GitNexus impact for `_stack_prior_server_urls` and `_format_stack_prior_url`
  was LOW (`impactedCount=2` and `3` respectively), limited to
  `ServerURLsConfig`.
- `ruff` passed for `src/config/models.py` and `tests/unit/test_config.py`.
- `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/unit/test_config.py` ->
  57 passed.
- Broader config/registry/guard suite -> 137 passed.
- `stack_change_pipeline.py check --run-promotion-gate` passed with
  `promotion_gate=163`, `q_scorer_priors: ok`, `runtime_attestation: ok`, and
  unchanged warning buckets (`waived_production_blocker=2`, `legacy_test=72`,
  `historical_doc=25`, `waived_legacy_test=9`).

### Progress note

This is a low-risk P2 `config_model_catalog` follow-up: the surface had already
derived URL defaults from stack priors, and now it uses the shared typed helper
path instead of owning a local YAML reader.

## Config URL helper guard follow-up — 2026-06-14

Manual docs checkpoint for `epyc-orchestrator` commit `b1b5d00` (`Guard config
stack-prior URL helpers`). Scope remained root documentation only.

### Landed in `epyc-orchestrator`

- `scripts/validate/stack_change_guard.py` adds the
  `local_config_stack_prior_yaml_reader` hardcoded-surface rule.
- `orchestration/stack_change_surface_manifest.yaml` owns the rule under
  `config-governance`.
- `tests/unit/test_stack_change_guard.py` proves that reintroducing
  `yaml.safe_load(priors_path.read_text(...))` inside `src/config/models.py`
  becomes a production-blocker finding.

### Validation recorded from the implementation lane

- GitNexus impact for `HARDCODED_SURFACE_RULES` was LOW (`impactedCount=0`);
  `scan_hardcoded_surfaces` was LOW (`impactedCount=5`).
- `ruff` passed on the guard and test files.
- `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/unit/test_stack_change_guard.py`
  -> 46 passed.
- The hardcoded-surface inventory reports `rule_count=18` and includes
  `local_config_stack_prior_yaml_reader`.
- `stack_change_pipeline.py check --run-promotion-gate` passed with
  `promotion_gate=163` and unchanged warning buckets.

### Progress note

This is the enforcement companion to `66d9765`: config server URL defaults now
reuse the shared stack-prior helper path, and scanner coverage blocks the old
local YAML-reader shape from returning unnoticed.

## Operational-consumer helper reuse follow-up — 2026-06-14

Documentation sidecar for `epyc-orchestrator` commit `0a46c1c` (`Reuse stack-prior helpers in operational surfaces`). Scope remains root documentation; no orchestrator code was edited in this lane.

### Landed in `epyc-orchestrator`

- `orchestration/repl_memory/bilinear_scorer.py`, `scripts/autopilot/autopilot.py`, `scripts/server/orchestrator_stack.py`, and `scripts/server/stack_commands.py` now reuse shared stack-prior helper paths that were previously maintained with local constants or duplicated parsing.
- `orchestration/model_descriptors.yaml` and `orchestration/derived/stack_priors.yaml` were regenerated as part of the same tranche to keep generated contracts aligned.

### Validation recorded from the implementation lane

- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate` passed.
- Artifacts/validation state: descriptors and stack priors were fresh; `q_scorer_priors: ok`; `runtime_attestation: ok`; acceptance no-inference checks passed; promotion gate `163` passed.
- Warning summary: `108 unique / 112 total`, `waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`, `waived_legacy_test=9`.

### Progress note

- This closes another operational-surface tranche on N11/N11a. Remaining work remains higher-risk: direct benchmark runtime enforcement follow-up if required and other high-risk P2 consumer migrations.

## Lock/tap static-policy guard follow-up - 2026-06-14

Documentation sidecar for `epyc-orchestrator` commit `b015cec` (`Guard lock tap static
policies`). Scope remained root governance documentation only.

### Landed in `epyc-orchestrator`

- `scripts/validate/stack_change_guard.py` adds
  `static_inference_lock_role_policy` and `static_inference_tap_stream_policy`
  scanner rules.
- `orchestration/stack_change_surface_manifest.yaml` owns both rules under
  `runtime-governance`.
- `tests/unit/test_stack_change_guard.py` now proves direct static
  `HEAVY_ROLES` / `LIGHT_ROLES` / `SAFE_NON_STREAM_ROLES` tables in runtime
  lock/tap files are production-blocker findings, while the current derived
  policy plus explicit `_LEGACY_*` degraded fallback shape stays allowed.

### Validation recorded from the implementation lane

- GitNexus impact for `scan_hardcoded_surfaces` was LOW (`impactedCount=5`);
  `HARDCODED_SURFACE_RULES` was LOW after disambiguation.
- `ruff` passed on the guard and test files.
- `PYTHONDONTWRITEBYTECODE=1 uv run python -m pytest -q
  tests/unit/test_stack_change_guard.py` -> 50 passed.
- `PYTHONDONTWRITEBYTECODE=1 uv run python -m pytest -q
  tests/unit/test_inference_lock.py tests/unit/test_inference_tap.py` -> 44
  passed.
- All-surface summary stayed unchanged:
  `waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`,
  `waived_legacy_test=9`.
- Hardcoded-surface inventory now reports `rule_count=20` and includes both
  lock/tap static-policy rules.

### Progress note

This is the enforcement companion to the lock/tap helper reuse work: lock/tap
runtime policy remains derived from stack priors with explicit degraded
fallbacks, and the scanner now blocks reintroducing fresh static role-policy
tables in those runtime files.

## q_scorer stack-prior loader helper-reuse follow-up - 2026-06-14

Documentation sidecar for `epyc-orchestrator` commit `07c8906` (`Reuse
stack-prior loader in q scorer`). Scope remained root governance documentation
only.

### Landed in `epyc-orchestrator`

- `orchestration/repl_memory/q_scorer.py` now reuses
  `src.registry.stack_priors.load_stack_priors_artifact()` inside
  `_load_valid_stack_priors()` and routes `stack_prior_q_scorer_priors_by_role()`
  through that helper path.
- `scripts/validate/stack_change_guard.py` adds
  `local_q_scorer_stack_prior_yaml_reader` so the old local
  `yaml.safe_load(stack_priors_path.read_text(...))` shape in q_scorer is a
  production-blocker finding.
- `orchestration/stack_change_surface_manifest.yaml` owns that scanner rule
  under `stack-change-governance`.
- `tests/unit/test_stack_change_guard.py` covers the local-reader regression
  shape.

### Validation recorded from the implementation lane

- GitNexus impact for `stack_prior_q_scorer_priors_by_role` was LOW
  (`impactedCount=5`); `_load_valid_stack_priors` was LOW
  (`impactedCount=3`); `scan_hardcoded_surfaces` was LOW (`impactedCount=5`).
- `ruff` passed on q_scorer, stack-change guard, and guard tests.
- `PYTHONDONTWRITEBYTECODE=1 uv run python -m pytest -q
  tests/unit/test_q_scorer.py tests/unit/test_stack_change_guard.py` -> 115
  passed.
- All-surface summary stayed unchanged:
  `waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`,
  `waived_legacy_test=9`.
- Hardcoded-surface inventory now reports `rule_count=21` and includes
  `local_q_scorer_stack_prior_yaml_reader`.
- `PYTHONDONTWRITEBYTECODE=1 uv run python
  scripts/registry/stack_change_pipeline.py check --run-promotion-gate` passed:
  `q_scorer_priors: ok`, `runtime_attestation: ok`, promotion gate 163 tests
  passed, and acceptance reported no-inference checks passed.

### Progress note

This is the enforcement companion to the q_scorer prior-source migration:
q_scorer still enforces stack-prior provenance for live roles, but now uses the
shared stack-prior loader instead of owning a local artifact parser.

## Generated-doc stack-prior loader helper-reuse follow-up - 2026-06-14

Documentation sidecar for `epyc-orchestrator` commit `c1f22cc` (`Reuse
stack-prior loader in generated docs`). Scope remained root governance
documentation only.

### Landed in `epyc-orchestrator`

- `scripts/registry/render_stack_summary.py` now loads stack-prior artifacts via
  `src.registry.stack_priors.load_stack_priors_artifact()` instead of local YAML
  parsing for the generated current-stack summary.
- `scripts/autopilot/gen_system_card.py` reuses that generated-summary helper for
  stack-prior role rows while leaving unrelated registry/baseline YAML reads
  unchanged.
- `scripts/validate/stack_change_guard.py` adds
  `local_generated_docs_stack_prior_yaml_reader`, owned in
  `orchestration/stack_change_surface_manifest.yaml`, so generated stack docs and
  AutoPilot system-card code cannot regress to local stack-prior YAML readers.
- `tests/unit/test_stack_change_guard.py` covers the old generated-doc/system-card
  local-reader shapes.

### Validation recorded from the implementation lane

- GitNexus impact was LOW for `generate_system_card`, `_load_yaml`,
  `render_current_stack_summary`, and `load_yaml`; no named processes were
  impacted.
- `ruff` passed on generated-summary, system-card, stack-change guard, and guard
  test files.
- `PYTHONDONTWRITEBYTECODE=1 uv run python -m pytest -q
  tests/unit/test_autopilot_system_card.py tests/unit/test_stack_change_pipeline.py
  tests/unit/test_stack_change_guard.py` -> 71 passed.
- All-surface summary stayed unchanged:
  `waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`,
  `waived_legacy_test=9`.
- Hardcoded-surface inventory now reports `rule_count=22` and includes
  `local_generated_docs_stack_prior_yaml_reader`.
- `PYTHONDONTWRITEBYTECODE=1 uv run python
  scripts/registry/stack_change_pipeline.py check --run-promotion-gate` passed:
  descriptors/stack-priors fresh, `operator_summary: ok`,
  `q_scorer_priors: ok`, `runtime_attestation: ok`, promotion gate 163 tests
  passed, and acceptance reported no-inference checks passed.

### Progress note

This closes the low-risk generated-doc/system-card loader-reuse gap: current
operator/planner summaries still come from generated stack-prior truth, but their
loader path now uses the same typed helper family as other migrated consumers.

## Factual-risk role-tier derivation follow-up - 2026-06-14

Documentation sidecar for `epyc-orchestrator` commit `72dc18e` (`Derive
factual-risk role tiers from stack priors`). Scope remained root governance
documentation only.

### Landed in `epyc-orchestrator`

- `src/classifiers/factual_risk.py` now derives live role capability tiers from
  generated stack-prior `model.mem_gb` via `live_stack_role_records()` instead of
  a static `_ROLE_TO_TIER` table.
- The factual-risk role adjustment now tracks live stack swaps; in the current
  stack, `frontdoor` follows its shared Qwen3.6 35B server tier instead of the
  stale worker-tier multiplier.
- `_DEGRADED_ROLE_TO_TIER` remains explicit fallback only for missing/malformed
  stack priors and compatibility labels.
- `scripts/validate/stack_change_guard.py` adds
  `static_factual_risk_role_tiers`, owned in the surface manifest under
  `routing-governance`, so the old static role-tier table shape is a
  production-blocker finding.
- `tests/unit/test_factual_risk.py` covers stack-prior-derived live tiers,
  candidate-role exclusion, and degraded fallback behavior.

### Validation recorded from the implementation lane

- GitNexus impact for `src/classifiers/factual_risk.py` was LOW
  (`impactedCount=24`, `direct=4`, no named processes).
- `ruff` passed on factual-risk and stack-change guard files/tests.
- `PYTHONDONTWRITEBYTECODE=1 uv run python -m pytest -q
  tests/unit/test_factual_risk.py tests/unit/test_stack_change_guard.py` -> 98
  passed.
- All-surface summary stayed unchanged:
  `waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`,
  `waived_legacy_test=9`.
- Hardcoded-surface inventory now reports `rule_count=23` and includes
  `static_factual_risk_role_tiers`.
- `PYTHONDONTWRITEBYTECODE=1 uv run python
  scripts/registry/stack_change_pipeline.py check --run-promotion-gate` passed:
  descriptors/stack-priors fresh, `operator_summary: ok`,
  `q_scorer_priors: ok`, `runtime_attestation: ok`, promotion gate 163 tests
  passed, and acceptance reported no-inference checks passed.

### Progress note

This closes another low-risk routing-prior consumer migration: factual-risk role
capability adjustment no longer depends on a hand-maintained role-to-tier map.

## OpenAI model-list stack-prior ordering follow-up - 2026-06-14

Documentation sidecar for `epyc-orchestrator` commit `63522df` (`Derive OpenAI
model order from stack priors`). Scope remained root governance documentation
only.

### Landed in `epyc-orchestrator`

- `src/api/routes/openai_compat.py` removed the hand-maintained
  `PREFERRED_ROLE_ORDER` table for `/v1/models` live-role ordering.
- Live OpenAI-compatible model IDs now keep compatibility aliases first, then
  order live stack roles from generated stack-prior launch topology
  (`frontdoor` first, then generated primary port and role name).
- `DEGRADED_AVAILABLE_ROLES` remains explicit fallback only when generated
  stack-prior records are unavailable.
- `scripts/validate/stack_change_guard.py` adds
  `static_openai_model_role_order`, owned in the surface manifest under
  `api-governance`, so the old static preferred-order table shape is a
  production-blocker finding.

### Validation recorded from the implementation lane

- GitNexus impact for `src/api/routes/openai_compat.py` was LOW
  (`impactedCount=2`, `direct=1`, no named processes).
- `ruff` passed on OpenAI compat and stack-change guard files/tests.
- Focused OpenAI compat, `/v1/models`, and guard tests passed 79.
- All-surface summary stayed unchanged:
  `waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`,
  `waived_legacy_test=9`.
- Hardcoded-surface inventory now reports `rule_count=24` and includes
  `static_openai_model_role_order`.
- `PYTHONDONTWRITEBYTECODE=1 uv run python
  scripts/registry/stack_change_pipeline.py check --run-promotion-gate` passed:
  descriptors/stack-priors fresh, `operator_summary: ok`,
  `q_scorer_priors: ok`, `runtime_attestation: ok`, promotion gate 163 tests
  passed, and acceptance reported no-inference checks passed.

### Progress note

This closes a bounded API surface: `/v1/models` live-role ordering no longer
depends on a hand-maintained current-stack role list.

## AutoPilot program generated-card prompt guidance follow-up - 2026-06-14

Documentation sidecar for `epyc-orchestrator` commit `0f86cde` (`Remove local
stack-prior read from AutoPilot program`). Scope remained no-inference and did
not start AutoPilot.

### Landed in `epyc-orchestrator`

- `scripts/autopilot/program.md` now points operators/planner prompts at
  `uv run python scripts/autopilot/gen_system_card.py --stdout` for the live
  stack endpoint surface instead of embedding a local
  `yaml.safe_load(open("orchestration/derived/stack_priors.yaml"))` snippet.
- The prompt explicitly says structured code paths should use shared
  `src.registry.stack_priors` helpers rather than adding local YAML parsing to
  planner prompts.
- `scripts/validate/stack_change_guard.py` extends
  `stale_autopilot_program_stack_guidance` to catch local `yaml.safe_load`
  stack-prior readers in `scripts/autopilot/program.md`.
- `tests/unit/test_stack_change_guard.py` covers the local-reader prompt
  regression shape.
- `scripts/autopilot/system_card.md` was regenerated after explicitly latching
  AutoPilot paused; the tracked generated state remains `paused: true` at
  `trial_counter: 813`.

### Validation recorded from the implementation lane

- AutoPilot process checks found no live planner/seeding process before and
  after the pause latch.
- `ruff` passed on the stack-change guard and guard tests.
- `gen_system_card.py --check` passed after regeneration.
- `PYTHONDONTWRITEBYTECODE=1 uv run python -m pytest -q
  tests/unit/test_stack_change_guard.py tests/unit/test_autopilot_system_card.py`
  -> 59 passed.
- All-surface warning buckets stayed unchanged:
  `waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`,
  `waived_legacy_test=9`.
- Hardcoded-surface inventory remains `rule_count=24`; the existing
  `stale_autopilot_program_stack_guidance` rule now covers local prompt YAML
  readers.
- `PYTHONDONTWRITEBYTECODE=1 uv run python
  scripts/registry/stack_change_pipeline.py check --run-promotion-gate` passed
  with `operator_summary: ok`, `q_scorer_priors: ok`,
  `runtime_attestation: ok`, and promotion gate 163 passed.

### Progress note

This closes the low-risk planner-prompt local-reader gap left after generated
system-card helper reuse: prompts now reference the generated current stack card
instead of teaching AutoPilot to parse stack-prior YAML directly.

## Chat-routing heuristic prior derivation follow-up - 2026-06-14

Documentation sidecar for `epyc-orchestrator` commit `d85660d` (`Derive chat
routing heuristic priors from stack priors`). Scope remained no-inference and
did not start AutoPilot or model servers.

### Landed in `epyc-orchestrator`

- `src/api/routes/chat_routing.py` removed the static
  `_HEURISTIC_PRIOR_ROLE_CANDIDATES` table.
- `_live_heuristic_prior_roles()` now derives the advisory prior role universe
  from `src.registry.stack_priors.live_stack_role_records()`.
- Baseline prior mass is spread across all live roles while keeping the
  classifier-selected role at the prior strength used by the old four-role
  table.
- `_DEGRADED_HEURISTIC_PRIOR_ROLES` remains explicit fallback only when generated
  priors are unavailable.
- `scripts/validate/stack_change_guard.py` adds
  `static_chat_routing_heuristic_prior_roles`, owned by
  `orchestration/stack_change_surface_manifest.yaml`, so the old static
  candidate tuple is a production-blocker finding.
- `tests/unit/test_chat_routing.py` and `tests/unit/test_stack_change_guard.py`
  cover live-derived role inclusion, degraded fallback, prior-mass preservation,
  and static-table regression detection.

### Validation recorded from the implementation lane

- GitNexus impact for `src/api/routes/chat_routing.py` was LOW
  (`impactedCount=9`, `direct=3`, no named processes). Guard/test/manifest
  impacts were LOW; root docs remained navigation-only HIGH with no
  process/module impact.
- `ruff` passed on chat routing, stack-change guard, and touched tests.
- Adjacent routing suite passed:
  `tests/unit/test_chat_routing.py`,
  `tests/unit/test_chat_routing_coverage.py`,
  `tests/unit/test_pipeline_routing.py`,
  `tests/unit/test_stack_change_guard.py` -> 208 passed.
- All-surface warning buckets stayed unchanged:
  `waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`,
  `waived_legacy_test=9`.
- Hardcoded-surface inventory now reports `rule_count=25` and includes
  `static_chat_routing_heuristic_prior_roles`; `consumer_surface_count=13`.
- `PYTHONDONTWRITEBYTECODE=1 uv run python
  scripts/registry/stack_change_pipeline.py check --run-promotion-gate` passed
  with `operator_summary: ok`, `q_scorer_priors: ok`,
  `runtime_attestation: ok`, and promotion gate 163 passed.

### Progress note

This closes the low-risk `routing_prior_consumers` candidate-table gap: newly
live specialist roles now receive heuristic prior support automatically from
generated stack truth, without changing explicit force/role/classifier routing.

## Vision fallback drift reduction follow-up — 2026-06-14

Documentation sidecar for `epyc-orchestrator` commit `cfe8204` (`Derive vision fallback ports from stack manifest`). Scope remained root governance documentation only; no orchestrator code was edited in this lane.

### Landed in `epyc-orchestrator`

- `src/api/routes/chat_vision.py` now derives VL fallback URL lookup through
  stack-manifest-backed `PORT_MAP` (`_stack_prior_vl_urls`) before static fallback,
  while preserving config URL fallback and keeping `_FALLBACK_VL_PORT_BY_ROLE` as
  explicit degraded fallback.
- `src/api/routes/chat_pipeline/vision_stage.py` now derives fallback VL ports from
  stack-manifest data (`_stack_prior_vl_ports`) for `worker_vision` and
  `vision_escalation`; local static role-port assumptions are now last-resort.
- Tests now cover manifest-based fallback behavior in
  `tests/unit/test_chat_vision.py` and `tests/unit/test_vision_routing.py`.

### Validation recorded from the implementation lane

- `ruff` passed for the two vision modules and tests.
- `uv run pytest -q tests/unit/test_chat_vision.py tests/unit/test_vision_routing.py` ->
  72 passed.
- `stack_change_pipeline.py check --run-promotion-gate` passed with
  descriptors/stack_priors fresh, `q_scorer_priors: ok`, `runtime_attestation: ok`,
  promotion_gate `163`, acceptance no-inference checks passed.
- Warning summary remained `108 unique / 112 total` (`waived_production_blocker=2`,
  `legacy_test=72`, `historical_doc=25`, `waived_legacy_test=9`).
- GitNexus impact was LOW for `_fallback_vl_url_for_role`, `_vl_port_for_role`,
  `_stack_prior_vl_urls`, `_stack_prior_vl_ports`.

### Root docs updated

- `handoffs/active/master-handoff-index.md`: adds 2026-06-14 vision fallback dispatch note.
- `progress/2026-06/2026-06-14.md`: adds dedicated 2026-06-14 vision fallback
  dispatch notes and validation summary.

## Parallel Audit Addendum - 2026-06-14

This pass audited the current standardization path without editing orchestrator production code. The existing handoff is still the right ownership point; no duplicate handoff was created.

GitNexus was refreshed in `epyc-root` before this edit: `24,606 nodes`, `26,671 edges`, `34 clusters`, `44 flows`. The required impact check was:

```bash
gitnexus impact --repo epyc-root handoffs/active/model-stack-single-source-update-pipeline.md --direction upstream
```

Result: target not found, `impactedCount=0`, `risk=UNKNOWN`. This is expected for the markdown handoff path and does not imply code blast radius.

### Current Canonical Sources

Use these as the current stack-change authority chain:

- `epyc-orchestrator/docs/reference/stack-truth-precedence.md` defines precedence: live serving topology first, descriptors second, role metadata third, historical/benchmark records last.
- `epyc-orchestrator/orchestration/model_registry.yaml` `server_mode.*` plus `scripts/server/stack_manifest.py` own live endpoint, port, tier, shared-server, and launch truth.
- `epyc-orchestrator/orchestration/model_descriptors.yaml` owns physical model identity, context evidence, quality/throughput evidence, modality, and known gaps.
- `epyc-orchestrator/orchestration/derived/stack_priors.yaml` is the generated consumer contract. Current contract is `epyc.stack_priors` v4 and includes required role, serving, launch, runtime, and prior fields.
- `epyc-orchestrator/orchestration/stack_change_surface_manifest.yaml` owns scanner rules and 13 model-specific consumer surfaces: q_scorer priors, seeding reward priors, routing, admission, lock/tap, config catalog, health/preflight probes, launch maps, dashboards/system cards, planner guidance, procedure enums, generated stack docs, and runtime attestation.
- `epyc-inference-research/orchestration/model_registry.yaml` remains candidate/benchmark evidence. It must not override live deployment truth without a descriptor/stack-prior import path.

### Current Generated Stack Facts

Verified from `orchestration/derived/stack_priors.yaml` on 2026-06-14:

| Role | Model | Endpoint/ports | Tier | Context | Priors |
|---|---|---|---|---:|---|
| `frontdoor` | `qwen3.6-35b-a3b-q8_0` | `8070`, `8080`, `8180`, `8280`, `8380` | hot | 32768 | tps `24.3`, quality `0.93`, memory `1.0` |
| `coder_escalation` | `qwen3.6-35b-a3b-q8_0` | shared `8070` | hot | 32768 | tps `24.3`, quality `0.93`, memory `1.0` |
| `architect_general` | `qwen3.5-122b-a10b-q4_k_m` | `8083` | hot | 16384 | tps `12.19`, quality `0.8567`, memory `1.0` |
| `ingest_long_context` | `qwen3-next-80b-a3b-q4_k_m` | `8085`, `8185`, `8285`, `8385`, `8485` | hot | 32768 | tps `20.8`, quality `0.9259`, memory `1.0` |
| `worker_general` | `gemma4-26b-a4b-q4_k_m` | `8072`, `8082`, `8182`, `8282`, `8382` | hot | 16384 | tps `60.7`, quality `0.9`, memory `1.0` |
| `worker_vision` | `qwen2.5-vl-7b-q4_k_m` | `8086` | hot | 8192 | tps `20.0`, quality `0.9167`, memory `1.0` |
| `vision_escalation` | `qwen3-vl-30b-a3b-q4_k_m` | `8087`, `8187`, `8287`, `8387`, `8487` | hot | 16384 | tps `27.6`, quality `0.9167`, memory `1.0` |

`architect_coding` is absent from generated live priors. Compatibility handling remains only through explicit legacy alias normalization and retired-role deployability rejection.

### Drift Surfaces Found

- **q_scorer costs**: live defaults now use stack-prior provenance and `stack_change_pipeline.py check --run-promotion-gate` blocks promotion if live q_scorer priors fall back while valid stack priors exist. The old local q_scorer TPS table still exists by design as degraded/offline fallback; keep it named and audited as fallback only.
- **Role memory and HOT/WARM semantics**: the guard enforces HOT live roles with `memory_cost: 1.0`, and the generated contract resolves `architect_general` / `ingest_long_context` as HOT despite older role/process-layout prose elsewhere.
- **Retired `architect_coding`**: current production blockers are waived only for two intentional live exceptions: ingress alias normalization and retired deployable-role denial. All other scanner findings are legacy-test or historical-doc classes.
- **Context, port, and launch assumptions**: context tokens, port sets, binary/runtime flags, MTP/draft paths, and VL projector paths are projected into stack-prior launch/runtime witnesses and checked by runtime attestation. Manual docs such as `docs/reference/commands/QUICK_REFERENCE.md`, historical research registry rows, and old benchmark docs still contain stale ports/models and must remain historical or generated.
- **Memory seed retired-role fixtures**: `scripts/memory/seed_diverse_memories.py`, `scripts/memory/seed_decomposition_memories.py`, `scripts/memory/seed_failure_memories.py`, and `scripts/memory/seed_success_patterns.py` still contain retired-role seed labels, but current hardcoded-surface rules do scan `scripts/memory/**` and classify those findings as `waived_legacy_test`. Do not reopen this as a scanner coverage gap unless future code turns these fixtures into live seed-generation inputs; live generation should normalize retired labels through stack-prior/role-alias helpers.
- **Research/full registry drift**: `orchestration/model_registry_full.yaml`, research docs, and benchmark reports retain old `architect_coding`, `8084`, Qwen2.5-Coder, Qwen3-Coder-30B, and older TPS facts. This is acceptable only as evidence/history; descriptor import must carry measurement status/provenance and must not become live truth.

### Validation Snapshot

Run from `/mnt/raid0/llm/epyc-orchestrator` on 2026-06-14:

```bash
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces --surface-summary-only
```

Result: `108 unique stack-prior warning(s)` / `108 total`, categorized as `waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`, `waived_legacy_test=9`.

```bash
uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate
```

Result: descriptors, stack priors, procedure enums, operator summary, q_scorer prior provenance, and runtime attestation were OK; no concrete live process drift was detected; promotion gate ran 163 no-inference tests and passed.

### Next Implementation Pickup

The next main workflow step should be **focused P2 consumer migration**, not another one-off q_scorer patch and not duplicate memory-seed scanner work:

- Keep the `b015cec` lock/tap static-policy scanner coverage active; any future lock/tap policy edit still needs exact symbol-level GitNexus impact checks and behavior-preserving tests.
- Treat direct benchmark runtime enforcement as a focused follow-up only if `stack_change_pipeline.py check --run-promotion-gate` coverage is insufficient; prior impact on `scripts/benchmark/seeding_infra.py:run_preflight` was HIGH.
- Migrate remaining runtime/benchmark consumers onto shared `src/registry/stack_priors.py` helpers where import boundaries allow, preserving explicit degraded fallbacks.
- Re-run `stack_change_pipeline.py check --run-promotion-gate` and require the warning bucket to remain classified with no new unwaived production blockers.

## Start Here - 2026-06-14 Update

Current implementation result:

- `epyc-orchestrator` `1148ff6` added `validate_live_q_scorer_prior_sources()` in `orchestration/repl_memory/q_scorer.py`.
- `scripts/registry/stack_change_pipeline.py check --run-promotion-gate` now reports `q_scorer_priors: ok/failed` and blocks promotion when any live q_scorer role uses degraded fallback provenance while stack priors are valid.
- The simulated data-only `frontdoor`/`coder_escalation` swap fixture now verifies q_scorer source provenance, and the context/KV/acceleration fixture is complete with `architect_general` quality data.
- Validation reported by the main orchestrator track: py_compile on touched files; ruff on touched files; `pytest -q tests/unit/test_q_scorer.py tests/unit/test_stack_change_pipeline.py tests/unit/test_stack_change_pipeline_simulated_fixtures.py` -> 82 passed; `stack_change_pipeline.py check --run-promotion-gate` -> `q_scorer_priors: ok`, promotion gate 48 passed; hardcoded-surface summary unchanged (`waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`).
- `epyc-orchestrator` `e31ebe1` wires production `scripts/server/orchestrator_stack.py start` to run `uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate` before host prereqs/model launch. Dev starts, `--validate-only`, and migration dry-run skip the gate; emergency diagnostics can bypass with `--skip-stack-change-gate` or `ORCHESTRATOR_SKIP_STACK_CHANGE_GATE=1`.
- The same update refreshed descriptor/stack-prior source hashes in the canonical pipeline artifacts. Validation reported by the main orchestrator track: py_compile on touched launcher/test files; focused pytest `tests/unit/test_orchestrator_stack_reload.py tests/unit/test_stack_change_pipeline.py` -> 27 passed; expanded pytest `tests/unit/test_orchestrator_stack_reload.py tests/unit/test_stack_change_pipeline.py tests/unit/test_build_server_command_helpers.py` -> 69 passed; parser smoke found `--skip-stack-change-gate`; `stack_change_pipeline.py check --run-promotion-gate` passed with promotion gate 48 tests and known warnings only.
- `epyc-orchestrator` `e02930f` adds `audit_stack_change_gate()` to `scripts/autopilot/preflight_audit.py` and runs it as preflight step 0, before model-server, web-search, web-fetch, inference, blacklist, archive-authority, and recent-trial checks. The AutoPilot gate executes `uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate` from the orchestrator repo, fails closed on nonzero exit, OSError, or a 180s timeout, and reports compact `summary:` / `acceptance:` output on success. Unit coverage landed in `tests/unit/test_autopilot_preflight_audit.py` for canonical command shape, failure, and timeout.
- `epyc-orchestrator` `9954631` (`Derive AutoPilot preflight fallback targets from stack manifest`) narrows the model-server preflight target selector by deriving `FALLBACK_MODEL_SERVER_TARGETS`-style values from `scripts.server.stack_manifest` `PORT_MAP` and `HOT_ROLES`, then grouping alias role ports onto the primary HOT role port.
- As part of that same derivation path, `scripts/autopilot/preflight_audit.py::_model_server_targets` now excludes embedder-only ports from AutoPilot model-server health preflight. If manifest-derived discovery fails, the old fallback target list remains as explicit last-resort behavior (`FALLBACK_MODEL_SERVER_TARGETS`).
- Validation recorded for `9954631`: `ruff` passed on `scripts/autopilot/preflight_audit.py` and `tests/unit/test_autopilot_preflight_audit.py`; `uv run pytest -q tests/unit/test_autopilot_preflight_audit.py` -> 11 passed. The same preflight lane reports that `stack_change_pipeline.py check --run-promotion-gate` passed with `runtime_attestation: ok`, `promotion_gate=163`, and warning buckets `waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`, `waived_legacy_test=9`.
- `stack_change_pipeline.py check --run-promotion-gate` in the same lane also reported descriptors/stack-priors fresh and `108 unique / 112 total` warnings while including `acceptance no-inference checks passed`.
- `epyc-orchestrator` `60a2611` (`Derive CLI status fallback targets from stack manifest`) refines `src/cli_orch.py::_stack_status_targets` to derive fallback status targets from `scripts.server.stack_manifest` `PORT_MAP` + `HOT_ROLES`, then group alias roles by primary HOT port. If derivation fails, `FALLBACK_STATUS_TARGETS` remains the explicit last-resort fallback. It also excludes embedder `8090` from model-server fallback checks in `orch status`.
- Validation recorded for `60a2611`: `ruff` passed on `src/cli_orch.py` and `tests/unit/test_cli_orch.py`; `uv run pytest -q tests/unit/test_cli_orch.py` -> 3 passed. `stack_change_pipeline.py check --run-promotion-gate` passed with `descriptors/stack-priors` fresh, `q_scorer_priors: ok`, `runtime_attestation: ok`, `promotion_gate=163`, and warning buckets `waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`, `waived_legacy_test=9` (`108 unique / 112 total`, `acceptance no-inference checks passed`).
- `epyc-orchestrator` `82f136b` (`Derive degraded status targets from stack manifest`) removes duplicated literal fallback target tuples and keeps manifest-derived alias-group targets as the active degraded fallback path for both `src/cli_orch.py` status target resolution and `scripts/autopilot/preflight_audit.py` model-server preflight probes, while preserving explicit last-resort fallback constants when stack-prior/manifest resolution fails.
- Validation recorded for `82f136b`: `ruff` passed on `src/cli_orch.py`, `scripts/autopilot/preflight_audit.py`, `tests/unit/test_cli_orch.py`, and `tests/unit/test_autopilot_preflight_audit.py`; `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/unit/test_cli_orch.py tests/unit/test_autopilot_preflight_audit.py` -> 16 passed; `git diff --check` passed.
- `epyc-orchestrator` `d5e81f1` (`Guard degraded status target fallbacks`) adds hardcoded-surface scanner rules `static_cli_degraded_status_targets` and `static_autopilot_preflight_targets`, plus manifest ownership rows, and reasserts regression protection that reintroduced `FALLBACK_STATUS_TARGETS` and `FALLBACK_MODEL_SERVER_TARGETS` are production blockers.
- Validation recorded for `d5e81f1`: `ruff` on `scripts/validate/stack_change_guard.py` and `tests/unit/test_stack_change_guard.py` passed; `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q tests/unit/test_stack_change_guard.py` -> 44 passed; `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate/stack_change_guard.py --list-hardcoded-surface-rules --surface-inventory-format json` includes both rule IDs; `git diff --check` passed.
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
- `epyc-orchestrator` `211746d` migrates the AutoPilot cache-flush rewarm target resolver in `scripts/autopilot/host_health.py`: rewarm GGUF/MMProj targets now come from the canonical launcher prewarm collector (`scripts.server.stack_prewarm.collect_targets`) over HOT+WARM servers and `build_server_command`, so cache-flush safety uses the same model/projector paths as production launch. The old hardcoded target tuple remains only as degraded fallback, and `scripts/autopilot/flush_cache_safely.py` no longer imports or passes that stale fallback.
- Validation reported for `211746d`: ruff passed on touched files; `uv run pytest -q tests/unit/test_host_health_pause_around_flush.py tests/unit/test_stack_prewarm.py tests/unit/test_safety_gate_mad.py tests/unit/test_safety_gate_baseline_eligibility.py tests/unit/test_safety_gate_diversity.py` -> 69 passed; `uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate` passed with expected warning buckets; live resolver smoke returned 11 targets. This was inference-free stack-governance/AutoPilot hygiene.
- `epyc-orchestrator` `1f002ae` migrates the AutoPilot planner slot-memory query map in `scripts/autopilot/autopilot.py`: planner slot ports now derive from live llama.cpp primary launch entries in `orchestration/derived/stack_priors.yaml`, with the old static map retained only as degraded fallback.
- The same patch cleans `scripts/autopilot/program.md` by removing obsolete exact model/speed guidance and pointing Q-scorer cost/throughput truth to stack priors/system cards. `scripts/validate/stack_change_guard.py` now flags stale AutoPilot program speed/model claims such as `19.6 t/s`, `12.7 t/s`, `Qwen3-Coder-30B`, and `Qwen3.5-35B`; `orchestration/stack_change_surface_manifest.yaml` adds `autopilot.py` and planner tests to the `planner_prompt_guidance` surface.
- Validation reported for `1f002ae`: ruff passed on touched Python files; `uv run pytest -q tests/unit/test_autopilot_creativity.py tests/unit/test_stack_change_guard.py tests/unit/test_autopilot_system_card.py` -> 61 passed; `uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces --surface-summary-only` passed with unchanged warning buckets; `uv run python scripts/registry/render_stack_summary.py --check` passed; `uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate` passed with promotion gate 163 tests.
- `epyc-orchestrator` `91601d0` migrates AutoPilot KV compaction/config-applicator physical primary role ports to `orchestration/derived/stack_priors.yaml`. Explicit role aliases still resolve through an alias-aware lookup, while physical primary roles are derived from stack-prior launch entries rather than static `PRODUCTION_PORTS`.
- The same patch expands planner slot-query port detection so runtime entries marked `ik-pr1744` or `llama-server` are treated as slot-capable, matching the current launch/runtime contract.
- `scripts/validate/stack_change_guard.py` now detects static `PRODUCTION_PORTS = {` in `scripts/autopilot/kv_compress.py`, and the surface manifest owns that KV compaction/runtime-port surface.
- Validation reported for `91601d0`: ruff on touched files passed; focused pytest `tests/unit/test_kv_compress_adaptive.py tests/unit/test_autopilot_creativity.py tests/unit/test_config_applicator.py tests/unit/test_stack_change_guard.py tests/unit/test_autopilot_controller_io.py tests/unit/test_autopilot_actions.py` -> 140 passed; live resolver smoke showed physical roles `{architect_general, frontdoor, ingest_long_context, vision_escalation, worker_general, worker_vision}` and alias roles including `coder_escalation`, `toolrunner`, `worker_math`, `worker_summarize`; `stack_change_guard.py --all-hardcoded-surfaces --surface-summary-only` passed with warning buckets unchanged; `stack_change_pipeline.py check --run-promotion-gate` passed with 163 tests; `git diff --check` passed.
- `epyc-orchestrator` `d0960b0` centralizes runtime stack-prior consumer helpers in `src/registry/stack_priors.py`: `load_stack_priors_artifact`, `live_stack_role_records`, `stack_prior_serving`, endpoint/serving port helpers, `live_role_primary_ports`, and `live_warm_worker_slots`.
- The same patch migrates duplicate stack-prior parsing in `src/runtime/concurrency.py`, `src/parallel_step_executor.py`, and `src/api/routes/chat_pipeline/vision_stage.py` onto the shared helpers, keeping degraded/fail-closed behavior in those consumers.
- Validation reported for `d0960b0`: GitNexus impact for `File:src/registry/stack_priors.py` was MEDIUM with 57 upstream files, 11 direct importers, and no named process impact; ruff passed on touched files; `pytest -q tests/unit/test_stack_priors_compiler.py tests/unit/test_runtime_concurrency.py tests/unit/test_parallel_step_executor.py tests/unit/test_vision_routing.py` -> 77 passed; `pytest -q tests/unit/test_api_imports.py tests/unit/test_stack_change_pipeline.py tests/unit/test_stack_change_guard.py` -> 94 passed; `stack_change_guard.py --all-hardcoded-surfaces --surface-summary-only` passed with unchanged warning buckets (`waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`); `stack_change_pipeline.py check --run-promotion-gate` passed, including 163 promotion-gate tests; `git diff --check` passed.
- `epyc-orchestrator` `dfcd280` extends that helper migration to `src/runtime/inference_lock.py` and `src/runtime/inference_tap.py`, replacing duplicate stack-prior YAML parsing with `live_stack_role_records` and `stack_prior_serving`; legacy fallback constants remain unchanged.
- Validation reported for `dfcd280`: GitNexus impact was LOW for both files (`inference_lock` impactedCount 0; `inference_tap` impactedCount 6 via `src/inference_tap.py`; no named process impact); ruff passed; `pytest -q tests/unit/test_inference_lock.py tests/unit/test_inference_tap.py tests/unit/test_stack_priors_compiler.py tests/unit/test_api_imports.py` -> 88 passed; stack-change guard passed with warning buckets unchanged; stack-change pipeline passed including 163 promotion-gate tests; `git diff --check` passed.
- `epyc-orchestrator` `91c7cba` extends helper reuse to the remaining API probe URL readers in `src/api/routes/health.py` and `src/api/routes/chat_vision.py`. Both now call `live_stack_role_records`, `stack_prior_serving`, and `stack_prior_serving_ports` instead of parsing `orchestration/derived/stack_priors.yaml` locally; `chat_vision.py` also builds its legacy `/vision/analyze` self-call from the current configured API URL with trailing slash stripped.
- Validation note for `91c7cba`: this docs sidecar inspected the commit diff only and did not rerun orchestrator tests or find validation output in the commit metadata. The change is documentation-discoverability only in `epyc-root`.
- `epyc-orchestrator` `a800d8c` extends stack-prior helper reuse to `src/api/routes/openai_compat.py`, `src/api/admission.py`, `scripts/graph_router/action_space.py`, `scripts/graph_router/train_graph_router.py`, `scripts/autopilot/preflight_audit.py`, and `scripts/autopilot/kv_compress.py`, replacing local stack-prior parse and lookup behavior with shared helper calls.
- Validation for `a800d8c` in the implementation lane: focused `ruff` passed, stack-change guard summary remained valid, `stack_change_pipeline.py check --run-promotion-gate` passed with 163 tests, and `git diff --check` passed.
- `epyc-orchestrator` `a858297` adds stack-change guard retired-role legacy-test fixture coverage to `scripts/memory/**/*.py` and adds a dedicated `scripts/memory/*.py` legacy-test exception; the warning summary is now `108` total with `waived_legacy_test=9`. `tests/unit/test_stack_change_guard.py` passed.
- `epyc-orchestrator` `ea0a12c` adds stack-prior helper reuse in routing/benchmarking consumer surfaces: `src/cli_orch.py`, `src/api/routes/dashboard_topology.py`, `src/api/routes/chat_routing.py`, `src/api/routes/chat_summarization.py`, `scripts/benchmark/analyze_routing_policy.py`, and `scripts/benchmark/corpus_quality_gate.py`.
- Validation note for `ea0a12c`: focused `ruff` passed; focused targeted pytest (CLI, dashboard, chat routing + summarization, API imports, routing-policy benchmark analyzers) passed `233`; stack-prior guard summary stayed at `108` with `waived_legacy_test=9`; `git diff --check` passed.
- Benchmark/seeding preflight suites are now included in the canonical launch/AutoPilot promotion gate. Direct edits to benchmark `scripts/benchmark/seeding_infra.py:run_preflight` were intentionally avoided because GitNexus reported HIGH upstream blast radius across benchmark entrypoints; if future acceptance requires direct benchmark runtime enforcement rather than promotion-gate coverage, keep that as a focused follow-up.
- AutoPilot clean window before this patch produced trial `805` as frontier and trial `806` as dominated/healthy. The main agent is separately repairing the archive-authority tail and refreshing orchestrator GitNexus; this sidecar did not run AutoPilot, inference, seeding, or orchestrator code.

Prior lightweight audit result:

- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/registry/stack_change_pipeline.py check` passed in `epyc-orchestrator`: descriptors fresh, stack priors fresh, procedure enums checked, loose/all-surface/strict guard stages non-blocking, `summary: ok`, and the acceptance block printed the promotion-gate command plus surface-inventory command.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces --surface-summary-only` reported `WARN: 99 unique stack-prior warning(s) (99 total)` with `surface_warnings: waived_production_blocker=2, legacy_test=72, historical_doc=25`.
- The live generated contract has the flagged facts correct: `frontdoor` and `coder_escalation` both use `qwen3.6-35b-a3b-q8_0`, port `8070`, HOT tier, shared mmap, and `memory_cost: 1.0`; `architect_general` and `ingest_long_context` are HOT with `memory_cost: 1.0`; `architect_coding` is absent from live stack-prior roles.
- The risk is no longer "q_scorer is definitely wrong by default", "production launch can skip the canonical stack-change gate by default", "AutoPilot preflight can reach model/web/inference checks before the canonical stack-change gate", "the primary current-stack operator summary is hand-copied", "benchmark/seeding preflight regressions are outside the executable promotion-gate target set", "concrete live model/mmproj drift can pass promotion unnoticed", "known-stack listeners/state gaps and concrete binary/runtime flag drift can pass promotion unnoticed", "model-specific consumer surfaces have no enforced ownership inventory", "tap safe-streaming non-stream roles are a static role-name table", "`config_model_catalog` server URL defaults are hand-copied from the stack", "dashboard model-serving port labels come from static port-range hints", "AutoPilot cache-flush rewarm targets are stale hardcoded GGUF/MMProj paths", "AutoPilot planner slot-memory ports and program model-speed guidance are static stack claims", "AutoPilot KV compaction/config-applicator physical role ports are maintained in static production maps", "API health/chat-vision probe URL consumers keep their own stack-prior YAML parsers", "lock/tap runtime files can reintroduce direct static role-policy tables without scanner ownership", or "q_scorer can own a local stack-prior YAML reader while enforcing live prior provenance". q_scorer now prefers stack priors, the promotion gate checks live prior-source provenance, production start runs that gate before launch, AutoPilot preflight runs the same gate first, `dbcae29` makes the current operator stack summary generated and checked by the stack pipeline, `6474204` brings benchmark/seeding preflight suites into the gate, `1457e58` gates promotion on concrete live model/mmproj drift, `3065b8b` gates promotion on the current runtime flag/listener/state target set, `d3643eb` enforces the 13-surface consumer ownership inventory, `0cdc15e` derives tap safe-mode non-stream roles from stack-prior `model.mem_gb`, `f41b1f3` derives config model catalog server URL defaults from generated stack priors while preserving env overrides and degraded fallbacks, `c7928cf` derives dashboard/status model-serving port labels from stack-prior launch entries, `211746d` derives cache-flush rewarm targets from launcher prewarm collection over HOT+WARM launch commands, `1f002ae` derives AutoPilot planner slot-memory ports from stack-prior primary launch entries while guarding stale program speed/model claims, `91601d0` derives KV compaction/config-applicator physical primary ports from stack-prior launch entries with alias-aware explicit lookup, `91c7cba` moves API health/chat-vision stack-prior probe URL lookup onto shared helpers, `b015cec` adds hardcoded-surface guard coverage for direct static lock/tap role-policy tables while allowing explicit `_LEGACY_*` degraded fallbacks, and `07c8906` moves q_scorer stack-prior loading onto the shared helper path with regression guard coverage. The remaining risk is that direct benchmark runtime paths and other high-risk consumer implementations can still bypass or outlive generated truth until the remaining P0/P2 migration work is finished.
- `a800d8c` now extends that helper-first migration to `openai_compat`, `admission`, graph-router, `preflight_audit`, and KV-compaction surfaces; `a858297` adds retired-role legacy-test coverage for `scripts/memory/**/*.py` and records `waived_legacy_test=9` in the stack-change guard; `ea0a12c` continues that same migration path into routing and routing-benchmark helper consumers (`cli_orch`, `dashboard_topology`, `chat_routing`, `chat_summarization`, and two routing-policy benchmark checks).

Use this as the follow-up implementation order:

- [ ] **P0 - Promote the canonical preflight to launch/AutoPilot/benchmark gates.** Production `orchestrator_stack.py start` now runs `stack_change_pipeline.py check --run-promotion-gate` before host prereqs/model launch as of `e31ebe1`, with dev/validate-only/migration dry-run skips and explicit emergency bypass. AutoPilot preflight now runs the same gate first as of `e02930f`, before model/web/inference checks. `6474204` expands the gate target set to benchmark/seeding preflight suites, so launch/AutoPilot promotion now executes those regressions. Runtime attestation is inside that canonical gate as of `1457e58`/`3065b8b`. Keep this waypoint open only for direct benchmark runtime enforcement if required, because GitNexus flagged benchmark `scripts/benchmark/seeding_infra.py:run_preflight` as HIGH upstream blast radius.
- [x] **P1 - Close live-looking q_scorer fallback residue.** `1148ff6` keeps degraded/offline fallbacks but blocks promotion when valid stack priors exist and any live q_scorer role resolves TPS, quality, or memory priors from degraded fallback provenance. Tests now assert source provenance for the flagged roles.
- [ ] **P2 - Expand surface ownership from scanner rules to consumer surfaces.** `d3643eb` lands the first enforced model-specific consumer-surface manifest pass: the guard now requires 13 `consumer_surfaces` (`q_scorer_priors`, `seeding_reward_priors`, `routing_prior_consumers`, `admission_policy`, `lock_tap_policy`, `config_model_catalog`, `health_preflight_probes`, `launch_maps`, `dashboard_status_system_cards`, `planner_prompt_guidance`, `procedure_role_enums`, `generated_stack_docs`, `runtime_attestation`) and reports `consumer_surface_count: 13` in JSON inventory output. `0cdc15e` lands the first `lock_tap_policy` migration by deriving tap safe-mode non-stream roles from stack-prior `model.mem_gb`, currently preserving `SAFE_NON_STREAM_ROLES ['architect_general']`. `f41b1f3` lands the first `config_model_catalog` migration by deriving `ServerURLsConfig` and Pydantic `ServerURLsSettings` defaults from stack-prior server URL aliases, while retaining env override precedence and explicit degraded fallback values. `c7928cf` lands the first `dashboard_status_system_cards` migration by deriving dashboard/status model-serving port labels from stack-prior launch entries while preserving service-only fallback labels and primary physical role precedence. `211746d` lands a `health_preflight_probes` / AutoPilot hygiene migration by deriving cache-flush rewarm GGUF/MMProj targets from canonical launcher prewarm targets over HOT+WARM servers, with the old tuple degraded-only. `1f002ae` lands a `planner_prompt_guidance` migration by deriving AutoPilot planner slot-memory ports from stack-prior primary launch entries, removing stale exact model/speed program guidance, and extending guard/manifest coverage for planner guidance surfaces. `91601d0` lands the KV compaction/config-applicator port migration by deriving physical primary role ports from stack-prior launch entries, preserving alias-aware explicit lookup, making `ik-pr1744` / `llama-server` runtime entries slot-capable for planner queries, and adding guard coverage for stale static `PRODUCTION_PORTS` maps in `kv_compress.py`. `91c7cba` advances `health_preflight_probes`/API probe hygiene by moving `src/api/routes/health.py` and `src/api/routes/chat_vision.py` stack-prior URL resolution onto shared helper APIs. `b015cec` closes the lock/tap static-policy scanner gap by guarding direct static runtime role-policy tables while allowing explicit `_LEGACY_*` degraded fallbacks. `07c8906` moves q_scorer stack-prior loading onto the shared helper path and guards the old local reader shape. Keep P2 open for other high-risk consumer migrations and follow-through validation inside those surfaces.
- `a800d8c` adds that shared-helper usage to openai-compatible API routing, admission, graph-router, and preflight/KV-compaction automation, and `a858297` updates stack-change guard warnings by adding memory-script retirement exception scope (`waived_legacy_test=9`, total warnings `108`) with the same `tests/unit/test_stack_change_guard.py`/promotion-gate validation posture as prior commits.
- `1624969` updates openai-compat `/v1/models` degraded fallback behavior: stack-prior live roles are preferred; if they are unavailable, `DEGRADED_AVAILABLE_ROLES` now aligns with current public roles and excludes `worker_fast` as a public surface (`toolrunner`, `vision_escalation`, `worker_summarize` added while preserving existing public roles).
- `82f136b` removes duplicated literal degraded target tuples for CLI status and AutoPilot preflight by grouping manifest-derived hot ports and roles (excluding embedder) into fallback probe targets with explicit manifest-first behavior.
- `d85660d` removes `src/api/routes/chat_routing.py`'s static heuristic-prior role table and derives advisory prior roles from generated stack-prior live role records, while preserving degraded fallback behavior.
- `3b5a682` removes `src/cli_orch.py`'s literal `embedder` status-exclusion set; degraded CLI status now excludes roles whose `ROLE_LAUNCH_META` launch mode is `embedding`, and `static_cli_status_excluded_roles` prevents that table shape from returning.
- `3a06791` hardens corpus quality gate stack-prior model discovery so malformed endpoint-port text falls back to structured `serving.ports` instead of crashing benchmark setup.
- `5f0f248` removes `scripts/autopilot/preflight_audit.py`'s literal model-server exclusion table; degraded AutoPilot preflight now excludes `embedding` launch-mode roles from `ROLE_LAUNCH_META`, and `static_autopilot_preflight_excluded_roles` prevents that table shape from returning.
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
P2 consumer-surface ownership metadata is enforced as of `d3643eb` and depends on stack-prior contract v4 staying fresh; the tap safe-streaming role table migration landed in `0cdc15e`, `config_model_catalog` server URL default derivation landed in `f41b1f3`, dashboard/status port-label derivation landed in `c7928cf`, degraded target tuple cleanup for CLI status and AutoPilot preflight landed in `82f136b`, AutoPilot cache-flush rewarm target derivation landed in `211746d`, AutoPilot planner slot-port/program-guidance cleanup landed in `1f002ae`, AutoPilot KV compaction/config-applicator physical port derivation landed in `91601d0`, the first shared runtime helper migration for concurrency/parallel/vision consumers landed in `d0960b0`, lock/tap policy helper reuse landed in `dfcd280`, inference-lock degraded fallback role cleanup landed in `a0a251d`, OpenAI model-list degraded-role alignment landed in `1624969`, API health/chat-vision probe URL helper reuse landed in `91c7cba`, lock/tap static-policy scanner coverage landed in `b015cec`, q_scorer stack-prior loader helper reuse landed in `07c8906`, chat-routing heuristic-prior role derivation landed in `d85660d`, and CLI degraded-status embedding-mode exclusion derivation landed in `3b5a682`. Other high-risk consumer migrations remain separate implementation work. Runtime attestation is now a promotion-gate regression target for the current stack-prior runtime contract.
P3 primary-summary generation is closed by `dbcae29`; any remaining doc-surface classification rides P2 ownership or explicit historical-label cleanup.
P1 and P4 are closed for the current stale q_scorer/data-only fixture cases but should remain regression targets in the promotion gate.
AutoPilot promotion is covered by `e02930f`; benchmark/seeding preflight regression coverage is covered by `6474204`; concrete live model/mmproj drift promotion gating is covered by `1457e58`; full current runtime flag/listener/state attestation is covered by `3065b8b`; first-pass consumer-surface ownership enforcement is covered by `d3643eb`; tap safe-streaming non-stream role derivation is covered by `0cdc15e`; config catalog server URL default derivation is covered by `f41b1f3`; dashboard/status port-label derivation is covered by `c7928cf`; AutoPilot cache-flush rewarm target derivation is covered by `211746d`; AutoPilot planner slot-port/program-guidance migration is covered by `1f002ae`; AutoPilot KV compaction/config-applicator physical port derivation and slot-capability detection are covered by `91601d0`; shared runtime stack-prior helpers and the concurrency/parallel/vision migrations are covered by `d0960b0`; lock/tap helper reuse is covered by `dfcd280`; inference-lock fallback role-shape cleanup is covered by `a0a251d`; openai model-list degraded-role alignment is covered by `1624969`; API health/chat-vision probe helper reuse is covered by `91c7cba`; lock/tap static-policy scanner coverage is covered by `b015cec`; q_scorer stack-prior loader helper reuse is covered by `07c8906`; direct benchmark runtime enforcement still depends on the remaining P0 nuance plus actual high-risk P2 consumer migrations. Operator current-stack summary evidence is generated and checked as of `dbcae29`.
```

Stale/hardcoded examples found in this audit:

- `epyc-orchestrator/orchestration/repl_memory/q_scorer.py` still contains degraded TPS/quality/memory fallbacks for offline/degraded operation, but `1148ff6` added `validate_live_q_scorer_prior_sources()` so live-role promotion fails if valid stack priors are bypassed for degraded fallback provenance.
- `epyc-orchestrator/orchestration/repl_memory/q_scorer.py` loads generated stack-prior live priors first and records source provenance; tests now assert that live roles use stack-prior sources when the artifact is valid.
- `epyc-orchestrator/orchestration/derived/stack_priors.yaml:207` and `:326` show `coder_escalation` and `frontdoor` sharing model identity, port `8070`, HOT tier, and `memory_cost: 1.0`; `:469` shows `ingest_long_context` HOT with `memory_cost: 1.0`.
- `epyc-orchestrator/scripts/server/stack_manifest.py:129` is the launcher tier/alias source; `:132` documents `coder_escalation`/`worker_summarize` sharing frontdoor, `:157`/`:158` classify `architect_general` and `ingest_long_context` as HOT, and `:177` documents `architect_coding` removal.
- `epyc-orchestrator/scripts/registry/stack_change_pipeline.py:121` emits the acceptance/warning/promotion/surface-inventory block, while `:588` keeps executable promotion-gate mode behind `--run-promotion-gate`.
- `epyc-orchestrator/scripts/server/orchestrator_stack.py start` runs the executable promotion gate before production host prereqs/model launch as of `e31ebe1`. Dev launches, validate-only, and migration dry-run skip it; bypass must be explicit through `--skip-stack-change-gate` or `ORCHESTRATOR_SKIP_STACK_CHANGE_GATE=1`.
- `epyc-orchestrator/scripts/autopilot/preflight_audit.py` runs the executable promotion gate first as of `e02930f`, before model-server, web-search, web-fetch, inference, blacklist, archive-authority, and recent-trial checks.
- `epyc-orchestrator/scripts/autopilot/host_health.py` derives cache-flush NUMA rewarm GGUF/MMProj targets from `scripts.server.stack_prewarm.collect_targets` over HOT+WARM launch commands as of `211746d`, so AutoPilot flush/recover hygiene follows launcher truth instead of stale static paths.
- `epyc-orchestrator/scripts/autopilot/autopilot.py` derives planner slot-memory query ports from stack-prior live llama.cpp primary launch entries as of `1f002ae`; the old static map is degraded-only.
- `epyc-orchestrator/scripts/autopilot/kv_compress.py` and config-applicator KV compaction now derive physical primary role ports from stack-prior launch entries as of `91601d0`; explicit aliases still resolve through an alias-aware lookup, and planner slot-query detection treats `ik-pr1744` / `llama-server` runtime entries as slot-capable. `stack_change_guard.py` detects static `PRODUCTION_PORTS = {` recurrence in `kv_compress.py`.
- `epyc-orchestrator/src/registry/stack_priors.py` exposes shared runtime consumer helpers as of `d0960b0`; `src/runtime/concurrency.py`, `src/parallel_step_executor.py`, and `src/api/routes/chat_pipeline/vision_stage.py` no longer need local stack-prior YAML parsing for live role/serving/slot lookups.
- `epyc-orchestrator/src/runtime/inference_lock.py` and `src/runtime/inference_tap.py` now reuse those shared helpers as of `dfcd280`; legacy fallback constants remain explicit fallback policy, not fresh stack truth.
- `epyc-orchestrator/src/api/routes/health.py` and `src/api/routes/chat_vision.py` now reuse those shared helpers as of `91c7cba`; API backend health probes and direct/legacy vision probe URLs no longer maintain separate local YAML parsing.
- `epyc-orchestrator/scripts/registry/stack_change_pipeline.py` includes benchmark/seeding preflight suites in `PROMOTION_GATE_TARGETS` as of `6474204`, lifting the promotion gate from 48 tests to 163 tests.
- `epyc-orchestrator/src/api/routes/openai_compat.py` keeps stack-prior live role IDs as `/v1/models` primary source; under degraded-mode parsing, `DEGRADED_AVAILABLE_ROLES` now includes `toolrunner`, `vision_escalation`, and `worker_summarize` and keeps `worker_fast` out of public role output.
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
- `epyc-orchestrator` `0cdc15e` migrates `src/runtime/inference_tap.py` safe-mode non-stream role selection from a static architect-role table to stack-prior-derived `model.mem_gb`, with malformed/missing-prior fallback to prior behavior. The live derived policy remains `SAFE_NON_STREAM_ROLES ['architect_general']`; `b015cec` now guards against direct static lock/tap runtime role-policy tables returning outside explicit `_LEGACY_*` degraded fallbacks.
- `epyc-orchestrator` `dfcd280` keeps the existing lock/tap fallback policy constants unchanged but removes duplicate artifact parsing from `src/runtime/inference_lock.py` and `src/runtime/inference_tap.py` by using the shared `live_stack_role_records` and `stack_prior_serving` helpers.
- `epyc-orchestrator` `a0a251d` refines `src/runtime/inference_lock.py` degraded-role fallback policy without touching normal stack-prior startup: `worker_fast` is removed from shared fallback, and current worker roles (`worker_general`, `worker_explore`, `worker_math`, `toolrunner`, `worker_vision`) are shared-fallback while `worker_summarize` is explicit heavy/exclusive fallback.
- `epyc-orchestrator` `f41b1f3` migrates `src/config/config_model_catalog.py` server URL defaults from hand-copied aliases to generated stack-prior aliases. It derives `ServerURLsConfig` and Pydantic `ServerURLsSettings` defaults from stack-prior truth, preserves environment override precedence, and keeps explicit degraded fallback values aligned with the current stack manifest.
- `epyc-orchestrator` `c7928cf` migrates dashboard/status model-serving port labels from static port-range hints to generated stack-prior launch entries. Alias and candidate records cannot overwrite primary physical-role labels, service-only ports keep explicit fallback labels, and `/dashboard/api/node/{port}` shares `_port_hint` with topology discovery.
- `epyc-orchestrator` `211746d` migrates AutoPilot cache-flush rewarm target discovery from hardcoded GGUF/MMProj tuples to canonical launcher prewarm target collection over HOT+WARM server commands. This narrows the `health_preflight_probes` / AutoPilot hygiene surface while preserving a degraded fallback for missing launcher truth.
- `epyc-orchestrator` `1f002ae` migrates AutoPilot planner slot-memory port discovery from a static map to stack-prior live primary launch entries, removes stale exact model/speed claims from `scripts/autopilot/program.md`, and expands guard/manifest ownership for `planner_prompt_guidance`.
- `epyc-orchestrator` `d0960b0` adds shared runtime consumer helpers to `src/registry/stack_priors.py` and migrates the existing concurrency, parallel step executor, and vision-stage consumers onto those helpers. Treat new runtime consumers as expected to reuse these helpers first; direct artifact parsing is now a debt signal unless import boundaries force it.
- `epyc-orchestrator` `82f136b` updates `src/cli_orch.py::_stack_status_targets` and `scripts/autopilot/preflight_audit.py::_model_server_targets` to derive degraded health checks from manifest hot roles/ports (`PORT_MAP` + `HOT_ROLES`) with embedder exclusion, while preserving explicit fallback lists as last-resort behavior.
- `epyc-orchestrator` `d85660d` derives chat-routing heuristic-prior roles from generated stack-prior live records and guards the old `_HEURISTIC_PRIOR_ROLE_CANDIDATES` table shape.
- `epyc-orchestrator` `3b5a682` derives CLI degraded-status non-model-server exclusions from `ROLE_LAUNCH_META` launch mode instead of a literal `embedder` set; scanner inventory now reports `rule_count=26`.
- `epyc-orchestrator` `3a06791` hardens `scripts/benchmark/corpus_quality_gate.py` stack-prior port parsing by falling back from malformed endpoint text to structured serving ports, keeping no-inference benchmark discovery resilient to a single bad live-role record.
- `epyc-orchestrator` `5f0f248` derives AutoPilot degraded preflight non-model-server exclusions from `ROLE_LAUNCH_META` launch mode instead of a literal `embedder` set; scanner inventory now reports `rule_count=27`.
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
| AutoPilot cache-flush rewarm targets | canonical launcher prewarm target collection over HOT+WARM launch commands | `host_health` cache-flush pause/resume hygiene, degraded fallback only |
| AutoPilot planner slot-memory ports and guidance | stack-prior live llama.cpp primary launch entries plus generated system card/Q-scorer provenance | planner slot memory queries, `program.md`, guard-owned `planner_prompt_guidance` |
| AutoPilot KV compaction/config applicator physical role ports | stack-prior live primary launch entries plus alias-aware explicit lookup | `kv_compress.py`, config applicator KV compaction, planner slot-capability detection, guard-owned static-map regression coverage |

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

As of `e31ebe1`, production `orchestrator_stack.py start` enforces the canonical no-inference promotion gate before host prereqs/model launch. As of `e02930f`, AutoPilot preflight enforces the same gate before model/web/inference checks. As of `1457e58`, the gate includes concrete live model/mmproj drift attestation. As of `3065b8b`, the gate also includes unmanaged known-stack listeners/state gaps and concrete live binary/runtime flag drift. As of `d3643eb`, P2 has enforced ownership metadata for the required consumer surfaces. As of `a0a251d`, `src/runtime/inference_lock.py` degraded-role fallback buckets now match current stack shape (`worker_fast` removed from shared fallback; `worker_summarize` explicit heavy/exclusive fallback; `worker_general`, `worker_explore`, `worker_math`, `toolrunner`, and `worker_vision` in shared fallback). As of `0cdc15e`, the tap safe-mode non-stream role table is derived from stack priors. As of `f41b1f3`, config model catalog server URL defaults are derived from stack-prior aliases with env overrides preserved. As of `c7928cf`, dashboard/status model-serving port labels are derived from stack-prior launch entries. As of `211746d`, AutoPilot cache-flush rewarm targets are derived from canonical launcher prewarm targets. As of `1f002ae`, AutoPilot planner slot-memory ports and program guidance derive from stack-prior/system-card truth with stale speed/model claim guard coverage. This leaves benchmark interpretation/direct runtime enforcement and other high-risk consumer migrations as the remaining model-stack hardening work.

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

Current increment: `34a0407` exposes the existing hardcoded-surface scanner rules as a machine-readable inventory through `hardcoded_surface_rule_inventory()` and the `stack_change_guard.py --list-hardcoded-surface-rules` CLI. `7815318` adds `orchestration/stack_change_surface_manifest.yaml` as the first enforced ownership map for those scanner rules, and the guard/pipeline now fail if the scanner-rule ownership manifest is missing, incomplete, duplicated, category-inconsistent, or promotion-policy inconsistent. `d3643eb` adds the first enforced model-specific `consumer_surfaces` inventory to the same manifest and validates 13 required surface IDs in `stack_change_guard.py`; JSON inventory now reports `consumer_surface_count: 13`. `0cdc15e` lands the first `lock_tap_policy` migration by deriving tap safe-mode non-stream roles from stack-prior `model.mem_gb` while preserving current live behavior. `f41b1f3` lands the first `config_model_catalog` migration by deriving server URL defaults from stack-prior aliases while preserving env overrides and degraded fallback values. `c7928cf` lands the first `dashboard_status_system_cards` migration by deriving model-serving port labels from stack-prior launch entries while preserving service-only fallback labels. `211746d` lands a `health_preflight_probes` / AutoPilot hygiene migration by deriving cache-flush rewarm targets from launcher prewarm collection. `1f002ae` lands a `planner_prompt_guidance` migration by deriving planner slot-memory ports from stack priors and guarding stale program speed/model claims. `b015cec` adds scanner-rule ownership for direct static lock/tap runtime role-policy tables while allowing explicit `_LEGACY_*` degraded fallback constants. `07c8906` moves q_scorer stack-prior artifact loading to the shared helper and guards the old local reader shape. This closes the first W2/P2 enforcement pass for consumer-surface ownership plus concrete consumer migrations and q_scorer/lock-tap regression coverage; actual high-risk consumer migrations remain open.

`d0960b0` lands a W3 helper-centralization tranche that also advances P2 consumer migration hygiene: concurrency caps, parallel burst-worker selection, and vision serving-port lookup now use shared `src/registry/stack_priors.py` helpers instead of duplicate parsing. `dfcd280` extends that helper reuse to lock/tap policy derivation while leaving legacy fallback constants unchanged. `91c7cba` extends helper reuse to API health/chat-vision probe URL readers and removes local YAML artifact parsing from those routes. Future P2 migrations should prefer those helpers for live-role records, serving endpoints/ports, primary launch ports, and warm-worker slots.

Tasks:

- Maintain the enforced `d3643eb` consumer-surface manifest for all required model-specific surfaces: q_scorer, seeding reward priors, routing prior consumers, admission, lock/tap policy, config model catalog, health/preflight probes, launch maps, dashboards/system cards, planner prompt guidance, procedure role enums, generated stack docs, and runtime attestation.
- Keep the distinction clear between "consumer surface owned" and "consumer migrated"; the current manifest identifies and governs every required surface, and `0cdc15e` / `f41b1f3` / `c7928cf` / `211746d` / `1f002ae` / `07c8906` migrate tap safe-streaming, config catalog server URL defaults, dashboard/status port labels, AutoPilot cache-flush rewarm target discovery, AutoPilot planner slot-port/program-guidance surfaces, and q_scorer stack-prior loader reuse, but other high-risk consumers still need typed/generated-truth migration follow-through.
- Keep `lock_tap_policy` runtime behavior derived from stack priors, and keep any remaining local constants explicitly marked as degraded fallback with scanner coverage.
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

Current increment: `d0960b0` added shared runtime helpers in
`src/registry/stack_priors.py` for loading the artifact, iterating live role
records, serving lookup, endpoint/port extraction, live primary ports, and
warm-worker slots. It migrated `src/runtime/concurrency.py`,
`src/parallel_step_executor.py`, and
`src/api/routes/chat_pipeline/vision_stage.py` away from duplicate parsing.
`dfcd280` then migrated `src/runtime/inference_lock.py` and
`src/runtime/inference_tap.py` to the same helper layer. This closes the first
helper-centralization tranche, not the broader W3 surface.

Tasks:

- Add or extend stack-prior helpers for retired roles, scorer priors, policy hints, launch requirements, modality/projector requirements, and generated summary rows.
- Migrate remaining local policy tables where model identity, tier, port, cost, or residency is the underlying reason.
- Prefer the `d0960b0`/`dfcd280` shared helpers for runtime consumers that need live role, serving, endpoint/port, primary-port, warm-worker slot, lock-class, or tap-policy source data; do not add new ad hoc YAML parsers unless import boundaries force it.
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

## KV compression stack-prior architecture metadata documented

Documentation-only sidecar for `epyc-orchestrator` commit `950fad7` (`Prefer stack-prior layer metadata for KV compression`). Scope remained `epyc-root` governance/progress docs only; no orchestrator code was edited.

### Landed in `epyc-orchestrator`

- `orchestration/model_descriptors` compiler now accepts optional architecture metadata from `registry.model`, including `n_layer`/`n_layers`/`num_hidden_layers`/`block_count` and `n_attention_layers`/`attention_layers`.
- Stack-prior generation now propagates the model architecture metadata into `roles.*.model`.
- `scripts/autopilot/kv_compress.py` now reads stack-prior `model.attention_layers` first, then `model.n_layers`; only after that does it fall back to
  `MODEL_LAYER_COUNTS` / `MODEL_LAYER_COUNT_ALIASES`.
- `orchestration/model_descriptors.yaml` and `orchestration/derived/stack_priors.yaml` were regenerated and now only emit optional architecture fields when populated, so current artifacts avoid empty/null layer fields.

### Validation recorded from the implementation lane

- `ruff` passed on touched files.
- Focused pytest passed `35` tests in
  `test_model_descriptor_compiler.py`, `test_stack_priors_compiler.py`,
  `test_kv_compress_adaptive.py`.
- `stack_change_pipeline.py check --run-promotion-gate` passed `163` tests.
- Warning baseline remained `108 unique / 112 total` with
  `waived_production_blocker=2`, `legacy_test=72`,
  `historical_doc=25`, `waived_legacy_test=9`.

### Notes

- `escalation_prewarmer` was deferred because `prewarm_if_complex` and `_send_prewarm` had CRITICAL GitNexus blast radius.
- Sidecar review of `scripts/config/config/models.py` found URL defaults already mostly stack-prior aware; vision/OCR defaults were deferred to a later higher-risk tranche.
