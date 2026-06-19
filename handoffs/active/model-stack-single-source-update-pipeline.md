# Model Stack Single-Source Update Pipeline

**Status**: PARTIAL IMPLEMENTATION LANDED - stack-prior single-source contract,
runtime attestation, generated stack summaries, scanner-rule ownership,
production launch gate, AutoPilot preflight gate, direct benchmark runtime
enforcement, and representative frontdoor/worker/vision swap-CI coverage are
live. Remaining work is other high-risk P2 consumer migrations plus future
swap-CI expansion as new consumers are migrated.
**Created**: 2026-06-13
**Priority**: HIGH - stale model-specific quantities can silently corrupt
routing, scoring, launch, planner prompts, replay analysis, and operator docs
after a stack change.
**History**:
[model-stack-single-source-update-pipeline-history-2026-06-15.md](../archived/model-stack-single-source-update-pipeline-history-2026-06-15.md)
preserves the completed chronology compacted out of this active handoff.
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

- Source contract is generated through model descriptors and
  `orchestration/derived/stack_priors.yaml`.
- 2026-06-19 no-inference refresh repaired descriptor drift from the
  research registry hash: `stack_change_pipeline.py update` regenerated only
  `orchestration/model_descriptors.yaml` and
  `orchestration/derived/stack_priors.yaml` source-artifact metadata, and the
  follow-up `check --run-promotion-gate` passed with 172 tests.
- Runtime attestation is part of the stack-change pipeline and currently
  reports `runtime_attestation: ok`.
- q_scorer prior provenance is part of the pipeline and currently reports
  `q_scorer_priors: ok`.
- Production `orchestrator_stack.py start`, AutoPilot preflight, and direct
  benchmark preflight all run the canonical stack-change gate before mutating
  runtime state.
- Direct benchmark runtime enforcement is closed by Orchestrator `09d9028`.
- `src.api.admission.AdmissionController.from_defaults()` now loads the current stack-prior-derived backend limits at instantiation time, so new app-state admission controllers pick up fresh generated limits instead of reusing the import-time snapshot.
- `src.registry.stack_priors` now owns stack-prior serving URL and slot-limit
  projection helpers, and Orchestrator `d744d5f` moved both
  `src.config.models` URL defaults and `src.api.admission` backend limits onto
  those typed helpers. The `full:` multi-port format, service URL manifest
  fallbacks, env override precedence, and degraded static admission fallback
  remain unchanged.
- `src.config.models.TimeoutsConfig` now shares a single role-timeout mapping helper across `for_role()` and `role_timeouts_dict()`, so the backward-compatible alias surface is derived from one canonical timeout table instead of duplicate local dict literals.
- `src.config.models.TimeoutsConfig._normalize_timeout_role()` no longer needs a dedicated `worker_explore` branch because the canonical role helper already resolves that alias, leaving only the explicit `worker_fast` compatibility exception.
- `src.config.models._CANONICAL_SERVER_URL_ALIASES` no longer carries a redundant `worker_explore` entry; `Role.from_string()` already canonicalizes that spelling to `worker_general`, so the config-catalog helper stays compatible without duplicating the alias table.
- `src.config.__init__` now canonicalizes `ServerURLsSettings` defaults through the shared role helper and has `TimeoutsSettings.worker_explore` mirror the canonical `worker_general` default, so the settings bridge no longer keeps a separate `worker_explore` source-of-truth branch.
- `scripts.server.stack_env._ROLE_ENV_BLOCKS` now stores the canonical worker CCD env block under `worker_general` instead of `worker`; the helper still preserves `worker` and `worker_explore` back-compat by canonicalizing them before lookup.
- `scripts.server.stack_manifest.LAUNCH_KV_QUANT_CONFIGS` now keeps only canonical worker KV entries, while `src.registry.stack_priors._launch_runtime_record()` canonicalizes `worker_explore` / `worker_general` before selecting KV types so alias callers still resolve through the live worker path without duplicating the manifest table.
- `scripts.server.stack_commands._launch_contract_for_process()` now canonicalizes alias role names through `Role.from_string()` before runtime attestation resolves the live launch contract, so `worker_explore` can still attach to the canonical `worker_general` contract instead of relying only on the raw lookup or port scan fallback.
- Seeding reward-prior helpers were tightened on 2026-06-15: generated
  stack-prior live-role records now drive both throughput-prior and
  architect-action role extraction in `scripts/benchmark/seeding_rewards.py`,
  removing duplicated live-role filtering while preserving explicit degraded
  fallback behavior.
- `scripts/benchmark/seeding_types.py` now derives its default-role fallback
  order from active role discovery before falling back to the legacy literal
  tuple, keeping the shared seeding defaults aligned with current live roles.
- `scripts/benchmark/seeding_rewards.py` now canonicalizes throughput lookups
  and worker-role detection through `Role.from_string()`, and its degraded
  fallback throughput map no longer carries a stale `worker_explore` entry.
- `scripts/benchmark/seeding_types.py` now resolves canonical role names
  through `Role.from_string()` instead of a local worker-explore alias table
  when deriving live active roles and seeding cost tiers.
- The same seeding helper no longer keeps a redundant
  `worker_explore -> worker_general` registry-key alias entry; canonical
  lookup now handles the retired label.
- Planner-facing guidance was tightened on 2026-06-15 so
  `scripts/autopilot/program.md` explicitly treats the generated controller
  system card as the authoritative live view for role, port, context,
  throughput, memory, and tier facts.
- QScorer live-role traversal was consolidated on 2026-06-15 so
  `orchestration/repl_memory/q_scorer.py` now reuses one helper for both
  prior extraction and live-source validation, preserving degraded fallback
  behavior while trimming another local stack-prior walk.
- Registry-based scorer fallbacks were also consolidated on 2026-06-15 via a
  shared `_registry_role_records()` helper, reducing duplicate roles-map walks
  without changing the fallback semantics.
- QScorer fallback tables were canonicalized on 2026-06-15 so the module now
  stores `worker_general` as the source key and materializes
  `worker_explore` at the output boundary, keeping the degraded contract
  intact without duplicating the fallback literals.
- The architect investigate prompt now renders its valid-role allowlist from
  live stack truth in both `src/prompt_builders/review.py` and
  `orchestration/prompts/architect_investigate.md`, keeping prompt labels in
  sync with current delegation targets.
- Delegate-role normalization in `src/api/routes/chat_delegation_config.py`
  now consults `src.roles.Role` before the small legacy alias set, so retired
  labels are handled through central role truth instead of duplicated routing
  branches.
- The delegate-role allowlist itself is now derived from live stack truth in
  `src/api/routes/chat_delegation_config.py`, and the architect decision parser
  clamps TOON/JSON delegate targets against that live set instead of a frozen
  literal.
- Delegate-target validation now stays tied to the live helper
  `_valid_delegate_roles()`; the compatibility export in
  `src/api/routes/chat_delegation.py` remains only so older import paths do not
  break.
- The chat-completions skip surface in `src/chat_completions_roles.py` now
  derives its default from generated stack priors by reading live launch
  metadata (`launch.runtime.flags.jinja` plus
  `acceleration.enable_thinking=false`), with a narrow degraded fallback when
  priors are unavailable.
- Orchestrator `08ec417` tightened that chat-completions degraded fallback:
  when generated priors are unavailable, the fallback now walks computed
  `HOT_SERVERS` / `WARM_SERVERS` order and derives eligible roles from
  `ROLE_LAUNCH_META` launch classes (frontdoor shared process and
  `worker_pool` explore process), canonicalizing aliases through `Role` and
  excluding architect, ingest, vision, embedding, and warm fast-worker launch
  modes. The live generated-prior set remains the primary source.
- `scripts/autopilot/gen_system_card.py` now derives its legacy-role note from
  live stack-prior role records instead of parsing the rendered markdown table,
  and the checked-in system card was regenerated from the current live state.
- `scripts/registry/render_stack_summary.py` now uses the typed
  `stack_prior_endpoint_port()` helper for stack-prior rows instead of parsing
  URLs with a local regex helper, so the generated summary path stays aligned
  with the structured stack-prior API.
- `scripts.server.stack_manifest.validate_against_registry()` now derives its
  launcher-only skip set from the live hot/warm sets, and
  `scripts/registry/stack_change_pipeline.py update` refreshed the generated
  descriptors / stack priors so the source-artifact hashes stayed in sync.
- The OpenAI `/v1/models` degraded compatibility surface in
  `src/api/routes/openai_compat.py` now derives its fallback role list from
  the computed `HOT_SERVERS` / `WARM_SERVERS` manifest view instead of a
  direct role→port fallback table, while still preferring live stack-prior
  records when they exist. The helper now canonicalizes any recognized alias
  spellings it sees in the server lists or live role IDs before deduping so
  the fallback stays on live canonical names.
- Orchestrator `cb7cb80` tightened that `/v1/models` degraded fallback further:
  the fallback order now follows the computed HOT/WARM server manifest order,
  skips manifest roles whose launch mode is `embedding`, and reuses the ingress
  role normalizer for context-specific worker aliases such as `worker_coder`.
  Compatibility aliases (`orchestrator`, `architect`, `worker`) still lead the
  API response, and generated stack-prior role order still wins whenever priors
  are readable.
- `orchestration.repl_memory.routing_classifier.RoutingClassifier.load()`
  now canonicalizes loaded action labels through `Role.from_string()` so
  serialized alias labels like `worker_explore` and `coder` rehydrate to the
  live canonical roles before the fast-path serves them.
- `RoutingClassifier.save()` now writes canonical label values too, so new
  classifier artifacts stop reintroducing stale alias spellings on disk.
- `src.classifiers.role_classifier.classify_role()` now canonicalizes
  architect-class routing inputs through `Role.from_string()` before deciding
  whether a prompt should stay on the thinker path, so the retired
  `architect_coding` alias follows the same canonical boundary as live
  architect roles.
- `src.cli_orch.cmd_status()` and `scripts.autopilot.preflight_audit` now
  derive their degraded probe/health target lists from the computed
  `HOT_SERVERS` / `WARM_SERVERS` manifest view instead of walking a direct
  role→port fallback table. The live stack-prior path still wins when
  generated records are present.
- `src.cli_orch._fallback_status_targets()` now canonicalizes alias roles
  through `Role.from_string()` before grouping status targets, so the
  degraded CLI fallback no longer surfaces `worker_explore` as a separate
  alias name.
- `scripts.autopilot.preflight_audit._fallback_model_server_targets()` now
  canonicalizes alias roles through `Role.from_string()` before grouping
  degraded model-server targets, so the preflight fallback collapses worker
  aliases onto the live `worker_general` role.
- `scripts.autopilot.preflight_audit` now shares live and degraded
  model-server target grouping through the stack-prior serving helpers
  (`stack_prior_serving`, `stack_prior_endpoint_port`) while preserving
  manifest-derived fallback ports for duplicate canonical-role aliases
  (`epyc-orchestrator` `2abbe1d`).
- `src.api.routes.chat_utils.apply_chat_template_for_role()` now canonicalizes
  role aliases through `Role.from_string()` before registry lookup, so
  `worker_explore` aliases resolve through the live `worker_general` model
  path instead of a stale alias-specific template lookup. The helper comment
  now says this generically for the alias family instead of naming the retired
  alias inline.
- `src.api.routes.dashboard_tasks._find_structured_request_by_task_id()` now
  canonicalizes `expected_role` before filtering task sections, so dashboard
  task-detail lookups for alias roles reuse the live `worker_general`
  section path instead of depending on a stale alias-only compare.
- `src.api.routes.dashboard._gate_inflight_by_live_slots()` now canonicalizes
  task roles through `Role.from_string()` before busy-slot matching, so
  dashboard snapshot gating collapses alias labels onto the live
  `worker_general` role instead of surfacing a separate alias path.
- `src.orchestration.dispatcher.Dispatcher` now canonicalizes TaskIR
  `role`/`model_hint` values and step actors through the canonical role
  helper and generic chain-name fallback before applying the local
  compatibility map, so alias inputs like `worker_explore` collapse onto the
  live `worker_general` registry role and `ingest` still resolves to the live
  `ingest_long_context` registry role instead of surviving as separate
  routing spellings.
- `src.proactive_delegation.ProactiveDelegator` now canonicalizes step actors
  through the same live-role helper plus chain-name fallback, so the
  execution path no longer keeps a generic `worker` alias branch in the local
  compatibility table; `worker_explore` still lands on `worker_general` and
  `worker` still resolves through the chain helper.
- `src.graph.compaction` now uses `Role.WORKER_GENERAL` for compaction index
  generation instead of the retired `worker_explore` role label, so the
  summarizer path stays on canonical worker truth while preserving the same
  compaction output shape.
- `ChatPipelineConfig.try_cheap_first_role` now defaults to the canonical live
  `worker_general` role in `src/config/models.py`; no separate mirror field in
  `src/config/__init__.py` needed changes.
- The generic legacy role aliases now resolve centrally through
  `src.roles.Role` (`coder`, `coder_agent`, `researcher*`, `reviewer*`,
  `math_agent`, `vision_agent`, `summarizer*`, `worker_explore`,
  `worker_fast`), while `chat_pipeline.routing_decision` and
  `repl_environment.routing` keep only the context-specific `worker_coder`
  / `worker_code` override locally.
- `src.repl_environment.routing` now also spells its REPL delegate-target
  worker list and delegatable-role set through `Role` constants instead of
  local worker-role string literals; `vision_escalation` remains a literal
  because it is not a first-class enum member.
- `scripts/benchmark/analyze_routing_policy.py` now canonicalizes live
  specialist role names through `Role.from_string()` before computing the
  specialist-utilization summary, so legacy aliases in live priors do not get
  counted as new specialists.
- `scripts/autopilot/host_health.py` now derives its degraded cache-flush
  rewarm GGUF list from generated stack priors before falling back to the last
  resort no-op path, so the page-cache remediation helper no longer carries a
  manual role/model tuple as its first degraded source.
- `scripts/autopilot/kv_compress.py` now derives its degraded production-port
  fallback from the live stack manifest instead of a literal role/port table,
  while preserving the generated-priors primary path and the alias-aware
  `production_ports_from_stack_priors()` behavior.
- `src.runtime.inference_lock.py` and `src.runtime.inference_tap.py` now spell
  their remaining degraded fallback sets through canonical `Role` constants
  instead of raw strings, keeping the final compatibility path aligned with
  live role truth. Orchestrator `e27c946` tightened the lock side further:
  generated stack priors still win, and the degraded fallback derives shared
  light-lock roles from `scripts/server/stack_manifest.py` hot-server metadata
  (`worker_pool` / worker-vision classification) instead of a hardcoded worker
  role list.
- `scripts/graph_router/action_space.py` now canonicalizes raw labels through
  `Role.from_string()` before action lookup, so aliases like `worker_explore`,
  `worker_fast`, `coder`, and `architect_coding` resolve through the live
  canonical action paths instead of relying on duplicate role-specific
  literals. The canonical live action order and degraded fallback set are
  unchanged.
- `orchestration/repl_memory/bilinear_scorer.py` now canonicalizes role keys
  through `Role.from_string()` at model-feature extraction and scorer lookup
  time, so legacy aliases like `worker_explore` collapse onto the live
  `worker_general` model record instead of persisting as separate degraded
  entries.
- `orchestration/repl_memory/strategy_store.py` now fingerprints the live
  `worker_general.md` prompt file instead of the retired worker-explore prompt
  path, so the AP-28 configuration-epoch hash follows the canonical worker
  prompt.
- `src.classifiers.factual_risk._role_tier_for_role()` now canonicalizes role
  names through `Role.from_string()` before checking live stack priors or the
  degraded tier map, and the degraded map no longer carries a redundant
  `worker_explore` fallback entry.
- `src.config.models._server_url_default()` now resolves `worker_explore`
  through the canonical `worker_general` alias path before falling back, so
  the config server-URL default no longer carries a separate worker-explore
  literal while preserving the compatibility URL.
- The same server-URL fallback table no longer keeps separate `coder`,
  `worker`, or `worker_coder` literals; those paths already resolve through
  the canonical `coder_escalation`, `worker_general`, and `worker_fast` alias
  chains.
Recent completed cleanup details are compacted into
[handoffs/archived/model-stack-single-source-update-pipeline-history-2026-06-15.md](../archived/model-stack-single-source-update-pipeline-history-2026-06-15.md)
and the daily `progress/` log so this active handoff stays focused on the
remaining open lanes.
- `src.api.routes.chat_delegation_config.py` now resolves the remaining
  generic delegate aliases through `Role.from_string()` and keeps only the
  special-case `worker_coder` / `worker_code` override local to the delegate
  path.
- `src.prompt_builders.resolver.get_direct_answer_prefix()` now canonicalizes
  its role input through `Role.from_string()` and uses `frontdoor` +
  `worker_general` as the stored direct-answer roles, replacing the old
  `worker_explore` literal.
- The resolver test module was restored after an accidental shrink during the
  checkpoint; the pre-existing prompt-resolver coverage remains intact with the
  new direct-answer assertions added in place.
- The prompt resolver now also prefers the canonical `Role.from_string()`
  family fallback before the older structural `<prefix>_general` fallback, so
  legacy aliases such as `worker_explore` still resolve through the canonical
  worker-family prompt file when a role-specific file is absent.
- `src.classifiers.factual_risk._role_tier_for_role()` now canonicalizes role
  names through `Role.from_string()` before checking live stack priors or the
  explicit degraded tier map, so alias inputs such as `worker_explore` no
  longer depend on a file-local legacy literal.
- `scripts/benchmark/corpus_quality_gate.py` now derives its fallback model
  order from live manifest membership at call time, instead of freezing the
  preferred role tuple in a module constant.
- `src/api/routes/openai_compat.py` now derives its degraded `/v1/models`
  fallback role order from live manifest membership at call time, instead of a
  frozen degraded-role tuple.
- `src/config/stack_templates.py` now checks template roles against live
  stack-prior role records instead of a local retired-role denylist, removing
  the last active-code retired-role guard warning from the stack-change scan.
- Active operator docs were refreshed by `8221971`, historical retired-role doc
  notes were explicitly marked by `d94954a`, and legacy seed fixtures were moved
  to exact inline allowances by `7ad5965`; current warning baseline is
  `0 unique / 0 total`.
- W4 promotion-gate execution/failure coverage landed in Orchestrator
  `d9fd1eb`; system-card swap visibility landed in `4aed83d`;
  health/dashboard stack-prior witnesses landed in `8beaf79`; routing/API
  role-surface witnesses landed in `edd20f7`; broader simulated swap coverage
  remains open as new high-risk consumers are migrated.
- Dashboard topology color resolution now canonicalizes role aliases through
  `Role.from_string()` and drops the duplicate `worker_explore` color entry,
  so dashboard status labels keep the live worker color without carrying the
  retired alias as a separate swatch.
- Dashboard topology service hints first moved the `worker_fast` fallback from
  a hardcoded `8102` literal to manifest data, then Orchestrator `98148f1`
  removed that stale model-serving fallback entirely. Service hints are now
  auxiliary-only; model-serving labels come from stack-prior port hints.
- Current handoff examples that still referenced the retired worker spelling
  now use `worker_general` in the live comparison rows, keeping the active
  docs aligned with the canonical worker role while leaving historical notes
  untouched.
- Guard inventory reports `consumer_surface_count=13` and `rule_count=27`.

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

- [ ] Pick the next high-risk P2 consumer from
  `orchestration/stack_change_surface_manifest.yaml`; run focused GitNexus
  impact before touching production code.
- [ ] Preserve env override precedence and explicit degraded fallbacks whenever
  migrating config or runtime consumers.
- [ ] Continue migrating remaining high-risk P2 consumers from the manifest,
  starting with the next surface that still carries local model facts or
  duplicated stack-prior traversal. After Orchestrator `d744d5f`, the config
  catalog and admission policy share typed serving URL/slot-limit projections.
  After Orchestrator `0c133db` and `c57a029`, GraphRouter action extraction
  and action-index lookup also consume shared canonical role/live-role helpers
  while preserving persisted classifier label order. Continue with the next
  manifest surface that still carries local model facts or duplicated
  stack-prior traversal.
- [x] Centralize stack-prior serving consumer projection for config/admission:
  Orchestrator `d744d5f` added `live_stack_serving_url_values()` and
  `live_stack_serving_slot_limits()` in `src.registry.stack_priors`, removed
  duplicate URL formatting from `src.config.models`, and removed the local
  admission merge loop from `src.api.admission`. Validation: config/admission
  plus registry-helper suites `197 passed`; `stack_change_pipeline.py check
  --run-promotion-gate` passed with `170 passed`; all-surface warning baseline
  stayed at `legacy_test=1`.
- [x] Handle the highest-ROI parked benchmark consumer despite CRITICAL
  GitNexus impact: `scripts/benchmark/seeding_rewards.py:detect_escalation_chains`
  now canonicalizes role aliases before cost-tier ordering and escalation
  reward emission, so benchmark seeding no longer injects retired worker
  action labels from alias-keyed role results.
- [x] Handle the high-blast renderer fallback consumer:
  `scripts/registry/render_stack_summary.py:registry_role_rows` remains as the
  last-ditch dict-only fallback, but normal file-backed summary/system-card
  generation now tries a compiled registry+descriptor fallback first and
  renders those rows through the stack-prior row formatter. Orchestrator
  `a0179cc` added tests proving missing stack priors no longer make the
  operator summary trust stale registry alias rows.
- [x] Handle the high-risk PromptForge path resolver:
  `scripts/autopilot/species/prompt_forge.py::_resolve_prompt_path` (HIGH).
  Orchestrator `4a21649` added characterization tests for the existing
  flat/roles/basename fallback ladder, preserved read/write precedence for
  prompt mutation and GEPA optimization, and added containment checks so
  parent-directory and symlink escapes fail closed.
- [x] Land guarded X-MAS enforce semantics without enabling production
  behavior. Orchestrator `a87bd35` keeps `xmas_routing.mode` default-off and
  allows route mutation only when a complete configured winner table is loaded,
  the classifier is confident, and the request is not explicitly forced;
  failure-veto and downstream guards still run after the X-MAS rewrite.
- [x] Populate and validate the X-MAS 5x5 winner table through the canonical
  inference/eval-gated handoff. Research `4e3ee6c` built the full
  function-axis table from the 500-row sweep; Orchestrator `9f89b5d`
  regenerated `orchestration/xmas_winner_table.yaml` with
  `provenance.source_results` and per-cell evidence. Validation passed:
  `validate_xmas_winner_table.py --table`, `--config`, and the classifier /
  validator tests. `mode: enforce` remains off; the live A/B is still required
  before any production flip.
- [x] Extend W4 swap-CI coverage so representative stack swaps prove generated
  artifacts, promotion-gate execution, and selected consumers move together.
  The replay meta-agent now also exposes `generate_candidate_swap_report()`
  and `--swap-replay` so archive-backed candidate swaps can be replayed
  directly without inventing a new replay subsystem. Orchestrator `d5f119d`
  added a simulated `worker_vision` / `vision_escalation` swap proving
  descriptors, stack priors, operator summary/system-card text, q_scorer
  priors, promotion-gate execution, and vision serving URL/port consumers move
  together. Validation: fixture suite `11 passed`, vision helper/import sweep
  `110 passed`, and stack-change promotion gate `171 passed`.
- [x] Keep prompt-builder allowlists and delegation labels aligned with live
  stack truth rather than static role lists.
- [x] Keep chat-completions fallback roles in `src/chat_completions_roles.py`
  derived from stack-manifest launch classes instead of duplicated literals.
- [x] Keep prompt-family fallback logic aligned with canonical role truth, not
  with ad hoc alias tables.
- [x] Keep delegation report helper role buckets in
  `src/api/routes/chat_delegation_reports.py` aligned with canonical `Role`
  constants and trace logging intact.
- [x] Keep fast-revise worker roles in `src/api/routes/chat_review.py`
  pointed at the canonical live worker role rather than the retired
  `worker_explore` alias.
- [x] Keep the chat cheap-first gate in `src/api/routes/chat.py` keyed to
  canonical live worker roles so it doesn't bypass when routing already chose a
  cheap worker.
- [x] Keep GraphRouter action normalization canonicalized through
  shared stack-prior helpers before lookup instead of maintaining duplicate
  worker/coder/architect alias literals. Orchestrator `0c133db` added
  `canonical_stack_role_id()` and `live_stack_role_ids()` in
  `src.registry.stack_priors`, moved GraphRouter live-action discovery onto
  generated stack-prior live roles, preserved the serialized degraded action
  order, and canonicalizes escalation targets such as retired architect aliases
  without static live-role maps. Validation: GraphRouter/routing/stack-prior
  focused suites `26 passed, 1 skipped`; `stack_change_pipeline.py check
  --run-promotion-gate` passed with `170 passed`; all-surface warning baseline
  stayed at `legacy_test=1`.
- [x] Keep GraphRouter action-index lookup canonicalized without classifier
  label renumbering. Orchestrator `c57a029` added
  `action_index_for_raw_label()`, routed training/debiased verifier extraction
  through canonical action lookup, and added tests proving raw legacy labels
  map onto the existing classifier action list without sorting, compacting, or
  changing saved label-map width/order. Current focused validation:
  `uv run --with pytest pytest -q tests/unit/test_graph_router_action_space.py`
  -> 10 passed.
- [x] Keep the orchestration README visible role tables and routing examples
  using canonical live spellings (`worker_general`, `architect_general`)
  instead of retired aliases. This was a docs-only alignment pass; historical
  capacity numbers were left intact for now.
- [x] Keep benchmark formatter examples aligned with canonical live roles in
  `scripts/benchmark/eval_log_format.py` and the `seeding_rewards.py`
  escalation-chain docstring. This is docs/example cleanup only; the runtime
  escalation detector remains parked because its live path is still
  CRITICAL.
- [x] Keep chapter-level docs examples aligned with canonical live roles in
  `docs/chapters/07-memrl-system.md` and
  `docs/chapters/10-escalation-and-routing.md`. Historical retired-role notes
  remain in place where they are explicitly labeled as historical context.
- [x] Keep the top-level orchestration README and the 02/10 chapter examples
  on canonical live spellings (`worker_general`) in visible role tables and
  cheap-first examples. Historical `architect_coding` notes remain only where
  they are clearly historical.
- [x] Keep server-URL defaults in `src.config.models._server_url_default()`
  aligned with canonical worker alias truth instead of duplicating a
  `worker_explore` literal fallback.
- [x] Keep dashboard topology service hints auxiliary-only; model-serving
  labels, including worker aliases, must come from stack-prior port hints.
- [x] Keep the `ChatPipelineConfig.try_cheap_first_role` default set to the
  canonical live worker role, not the retired `worker_explore` alias.
- [x] Keep ingress worker aliases in
  `src/api/routes/chat_pipeline/routing_decision.py` pinned to canonical
  `Role.WORKER_GENERAL` values instead of local literals.
- [x] Keep worker-task routing defaults in `src/llm_primitives/primitives.py`
  pinned to canonical role constants instead of local alias strings.
- [x] Keep delegation role normalization centralized in `src.roles` and avoid
  reintroducing scattered alias tables in route helpers.
- [x] Keep delegate-target validation tied to the live delegate allowlist, not
  to static route-local role sets.
- [x] Keep `src/tools/web/research.py` synthesis targeting aligned with live
  worker-general stack priors instead of a hardcoded `8082` endpoint and
  frozen chat-template hint.
- [x] Keep health-route fallback backend URLs aligned with manifest-owned hot
  roles instead of a static core-role tuple; the helper now reads
  `HOT_ROLES` directly instead of carrying a separate fallback tuple.
- [x] Keep vision-serving fallback VL ports aligned with the manifest-backed
  port path instead of a file-local legacy table.
- [x] Keep inference-lock degraded role policy aligned with canonical live
  worker roles instead of a stale fallback literal.
- [x] Keep config-catalog worker URL defaults aliased through the canonical
  worker path instead of a duplicated legacy literal.
- [x] Keep inference-tap stream policy canonicalized at the role boundary so
  canonical worker aliases follow live worker policy.
- [x] Keep the remaining lock/tap degraded fallback sets spelled through
  canonical `Role` constants and manifest-derived worker classifications
  instead of raw strings or duplicated worker-role lists.
- [x] Keep session-log compaction centralized on `worker_general` while
  preserving the distinct `worker_fast` profile via the raw role string.
- [x] Keep host-health cache-flush rewarm fallback derived from generated stack
  priors before it drops to the final degraded no-op path.
- [x] Keep KV-compression degraded production ports derived from the live
  stack manifest instead of a manual fallback table.
- [x] Keep proactive-delegation actor lookup canonicalized at the role
  boundary so the canonical worker path resolves before the legacy fallback
  is applied.
- [x] Keep chat timeout fallback lookup canonicalized at the role boundary so
  the canonical worker path reuses the live timeout while `worker_fast`
  keeps its distinct warm-tier timeout.
- [x] Keep dashboard-task commentary aligned with the canonical role boundary
  so the objective-matching helper does not keep naming the retired
  `worker_explore` alias in explanatory text.
- [x] Keep helper comments in `src/features.py` and
  `src/llm_primitives/inference.py` aligned with canonical worker aliases
  instead of naming the retired `worker_explore` label directly.
- [x] Keep the `src/features.py` import list minimal after the helper-comment
  cleanup exposed an unused `dataclasses.field` import.
- [x] Keep `src/config/models.py` server-URL alias tables deduplicated behind
  a single shared `worker_coder -> worker_fast` compatibility constant.
- [x] Keep session-log and dashboard comments aligned with the live worker
  path instead of spelling the retired `worker_explore` alias directly.
- [x] Keep proactive-delegation comments explicit about the canonical
  worker-alias path and preserve the legacy fallback as a single local
  compatibility branch.
- [x] Keep the worker-pool launch helper canonicalized on
  `_build_worker_general_command()` while preserving the retired
  `_build_worker_explore_command()` wrapper for compatibility.
- [x] Keep live inference-serving docs aligned with the canonical worker
  spelling so current rows and examples use canonical live-worker wording.
- [x] Keep the local-inference operating-point note aligned with canonical
  worker spelling so the 96t production baseline is described with the live
  worker name.
- [x] Keep the current serving alias note canonical in `wiki/inference-serving.md`
  without reviving the retired spelling.
- [x] Keep the current worker-general example docs aligned in
  `wiki/memory-augmented.md` and `handoffs/active/routing-truth-restoration.md`.
- [x] Keep the strategy-store epoch-hash note aligned with the canonical
  worker prompt path rather than naming the legacy prompt path inline.
- [x] Keep the hardware-optimization production baseline row aligned with the
  canonical worker spelling instead of the retired `worker_explore` label.
- [x] Keep the multimodal routing comparison aligned with the canonical
  worker spelling instead of the retired `worker_explore` label.
- [x] Keep the quantization summary aligned with the live
  `architect_general` production slot and mark the REAP `architect_coding`
  row as historical only.
- [x] Keep the generated system card note aligned with the live
  `architect_general` architect slot and mark `architect_coding` as historical
  only.
- [x] Keep the storage-safety HOT tier row aligned with the live
  `architect_general` 8083 slot instead of the retired architect-coding
  row, and remove the stale warm duplicate entry.
- [x] Keep the descriptor compiler active-role set canonical so `stack_commands.py`
  no longer re-adds shared aliases that `write_model_descriptors()` already expands.
- [ ] Defer the broad stack-summary renderer rewrite unless a narrower helper
  seam appears; GitNexus marks that surface as high impact.
- [ ] Keep `scripts/autopilot/short_term_memory.md` under review as live run
  state; do not prune it during active AutoPilot execution.
- [ ] Keep completed implementation logs out of active indices; record future
  closures in `progress/` and move closed handoff material to
  `handoffs/completed/` or `handoffs/archived/`.

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
uv run python scripts/validate/stack_change_guard.py --inventory-json /tmp/stack-change-inventory.json
```
