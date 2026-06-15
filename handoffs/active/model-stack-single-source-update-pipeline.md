# Model Stack Single-Source Update Pipeline

**Status**: PARTIAL IMPLEMENTATION LANDED - stack-prior single-source contract,
runtime attestation, generated stack summaries, scanner-rule ownership,
production launch gate, AutoPilot preflight gate, and direct benchmark runtime
enforcement are live. Remaining work is other high-risk P2 consumer migrations
and swap-CI coverage.
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
- Runtime attestation is part of the stack-change pipeline and currently
  reports `runtime_attestation: ok`.
- q_scorer prior provenance is part of the pipeline and currently reports
  `q_scorer_priors: ok`.
- Production `orchestrator_stack.py start`, AutoPilot preflight, and direct
  benchmark preflight all run the canonical stack-change gate before mutating
  runtime state.
- Direct benchmark runtime enforcement is closed by Orchestrator `09d9028`.
- Seeding reward-prior helpers were tightened on 2026-06-15: generated
  stack-prior live-role records now drive both throughput-prior and
  architect-action role extraction in `scripts/benchmark/seeding_rewards.py`,
  removing duplicated live-role filtering while preserving explicit degraded
  fallback behavior.
- `scripts/benchmark/seeding_types.py` now derives its default-role fallback
  order from active role discovery before falling back to the legacy literal
  tuple, keeping the shared seeding defaults aligned with current live roles.
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
- The OpenAI `/v1/models` degraded compatibility surface in
  `src/api/routes/openai_compat.py` now derives its fallback role list from
  the computed `HOT_SERVERS` / `WARM_SERVERS` manifest view instead of a
  direct role→port fallback table, while still preferring live stack-prior
  records when they exist.
- `src.cli_orch.cmd_status()` and `scripts.autopilot.preflight_audit` now
  derive their degraded probe/health target lists from the computed
  `HOT_SERVERS` / `WARM_SERVERS` manifest view instead of walking a direct
  role→port fallback table. The live stack-prior path still wins when
  generated records are present.
- `src.api.routes.chat_utils.apply_chat_template_for_role()` now canonicalizes
  role aliases through `Role.from_string()` before registry lookup, so
  `worker_explore` aliases resolve through the live `worker_general` model
  path instead of a stale alias-specific template lookup.
- `src.api.routes.dashboard_tasks._find_structured_request_by_task_id()` now
  canonicalizes `expected_role` before filtering task sections, so dashboard
  task-detail lookups for alias roles reuse the live `worker_general`
  section path instead of depending on a stale alias-only compare.
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
  live role truth.
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
- `TimeoutsConfig.worker_explore` now inherits the live `worker_general`
  timeout fallback instead of maintaining a separate alias-specific default,
  and the runtime config builder follows the same canonical path.
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
- Dashboard topology service hints now derive the `worker_fast` port from the
  live stack manifest instead of a hardcoded `8102` literal, so the fallback
  port label stays aligned with the manifest-backed service truth and no
  standalone service-port fallback remains in the dashboard helper.
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
  duplicated stack-prior traversal.
- [ ] Extend W4 swap-CI coverage so representative stack swaps prove generated
  artifacts, promotion-gate execution, and selected consumers move together.
- [x] Keep prompt-builder allowlists and delegation labels aligned with live
  stack truth rather than static role lists.
- [x] Keep chat-completions fallback roles in `src/chat_completions_roles.py`
  expressed through canonical `Role` constants instead of duplicated literals.
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
  `Role.from_string()` before lookup instead of maintaining duplicate
  worker/coder/architect alias literals. The retired architect regression test
  now uses a split-string constant so the hardcoded-surface guard stays clean
  without reintroducing a raw `architect_coding` literal.
- [x] Keep server-URL defaults in `src.config.models._server_url_default()`
  aligned with canonical worker alias truth instead of duplicating a
  `worker_explore` literal fallback.
- [x] Keep dashboard topology service hints aligned with the live manifest
  instead of a hardcoded `worker_fast` port literal.
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
  roles instead of a static core-role tuple.
- [x] Keep vision-serving fallback VL ports aligned with the manifest-backed
  port path instead of a file-local legacy table.
- [x] Keep inference-lock degraded role policy aligned with canonical live
  worker roles instead of a stale `worker_explore` fallback literal.
- [x] Keep config-catalog `worker_explore` URL defaults aliased through the
  canonical `worker_general` path instead of a duplicated legacy literal.
- [x] Keep the `worker_explore` timeout default inherited from the live
  `worker_general` timeout path instead of a separate alias-specific lookup.
- [x] Keep inference-tap stream policy canonicalized at the role boundary so
  aliases like `worker_explore` and `worker_fast` follow live worker policy.
- [x] Keep the remaining lock/tap degraded fallback sets spelled through
  canonical `Role` constants instead of raw strings.
- [x] Keep session-log compaction centralized on `worker_general` while
  preserving the distinct `worker_fast` profile via the raw role string.
- [x] Keep host-health cache-flush rewarm fallback derived from generated stack
  priors before it drops to the final degraded no-op path.
- [x] Keep KV-compression degraded production ports derived from the live
  stack manifest instead of a manual fallback table.
- [x] Keep proactive-delegation actor lookup canonicalized at the role
  boundary so `worker_explore` resolves through the live `worker_general`
  path before the legacy fallback is applied.
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
