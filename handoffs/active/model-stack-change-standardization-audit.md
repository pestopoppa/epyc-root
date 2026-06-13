# Model Stack Change Standardization Audit

**Status**: READY FOR MAIN IMPLEMENTATION
**Created**: 2026-06-13
**Priority**: HIGH - stale model constants can silently bias routing, scoring, launch, planner prompts, and benchmark interpretation after a stack change
**Scope**: Documentation/audit handoff only. No inference, AutoPilot, server restarts, code edits, index edits, or progress-log edits were performed.
**Related**: [model-stack-update-pipeline-audit.md](model-stack-update-pipeline-audit.md), [stack-change-governance-pipeline.md](stack-change-governance-pipeline.md), [model-capability-descriptors.md](model-capability-descriptors.md), [fable5-findings-02-routing-decision-architecture.md](fable5-findings-02-routing-decision-architecture.md), [fable5-findings-01-measurement-and-integrity.md](fable5-findings-01-measurement-and-integrity.md)

## Problem Statement

Changing the orchestration model stack is still too easy to do as a collection of manual patches. The live stack now has facts that invalidate older hardcoded assumptions:

- `frontdoor` and `coder_escalation` share the same physical model and server (`qwen3.6-35b-a3b-q8_0` on `http://localhost:8070`), so cost and memory accounting must not double-count them.
- `architect_coding` is retired from the live stack and must not appear in active live priors, launch manifests, routing chains, or scoring defaults except as explicitly legacy/test/historical data.
- `architect_general` and `ingest_long_context` are HOT in live serving truth, so q_scorer and reward paths must not apply WARM memory penalties from older role/process-layout metadata.
- Fable 5 found the same failure mode at the planning layer: prompt/system-card narratives can preserve stale stack facts such as removed ports and pre-swap model identities unless generated from live structured truth.

The project already has a good foundation. The implementation task is to finish standardizing it so a stack change becomes: edit structured truth, compile generated contracts, run fail-closed validators, and update consumers through typed APIs or explicit degraded-mode fallbacks.

## Audit Method

Read-only audit across:

- `/mnt/raid0/llm/epyc-root/handoffs/active/`
- `/mnt/raid0/llm/epyc-orchestrator/docs/`, `src/`, `scripts/`, `orchestration/`, `tests/`
- `/mnt/raid0/llm/epyc-inference-research/docs/`, `scripts/`, `orchestration/`

Lightweight validation run:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces
```

Result on 2026-06-13: exit 0 with `WARN: 146 stack-prior warning(s)`. No inference was run.

Root GitNexus note before main-session review:

- The sidecar audit initially observed a stale root index while writing this new handoff and did not re-index, preserving its narrow write scope.
- Main-session review refreshed root GitNexus after the sidecar returned: `24,209 nodes`, `26,242 edges`, `33 clusters`, `43 flows`.
- `gitnexus impact -r epyc-root handoffs/active/model-stack-change-standardization-audit.md --direction upstream` returned target not found, `impactedCount=0`, `risk=UNKNOWN`, expected for a markdown handoff path.

## Existing Machinery Found

These are the current standardized-process artifacts. Do not build a second registry unless these prove insufficient.

- `/mnt/raid0/llm/epyc-orchestrator/docs/reference/stack-truth-precedence.md`
  - Defines precedence: live serving topology first, model descriptors second, role metadata third, historical/benchmark records last.
  - Explicitly says `server_mode.*.tier` overrides stale `roles.*.memory.residency`, shared mmap roles must not double-count memory, and retired roles such as `architect_coding` must not appear in active live priors.

- `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml`
  - Lean live deployment source for `server_mode.*`, role metadata, runtime defaults, timeouts, and serving topology.
  - Current observed live truth includes `frontdoor` and `coder_escalation` consolidated onto port `8070`, `architect_general` HOT, and `ingest_long_context` HOT.

- `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_descriptors.yaml`
  - Physical model identity/evidence layer keyed by model, not role.
  - Intended bridge between research evidence and deployed routing/scoring consumers.

- `/mnt/raid0/llm/epyc-orchestrator/src/registry/stack_priors.py`
  - Compiles role records from lean registry, descriptors, and stack manifest.
  - Exposes `validate_stack_priors_contract()` and CLI entrypoint via the wrapper script.

- `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/compile_stack_priors.py`
  - CLI wrapper that writes `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml`.

- `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml`
  - Generated consumer contract with `stack_priors_version: 1`.
  - Current status is `compiled_with_gaps`, but it already carries role -> model, serving endpoint/ports/slots/tier, priors, acceleration metadata, evidence, source hashes, and known gaps.

- `/mnt/raid0/llm/epyc-orchestrator/scripts/validate/stack_change_guard.py`
  - Validates source hashes, required contract shape, live-role invariants, procedure enum drift, retired-role leakage, and curated hardcoded surfaces.
  - Supports `--strict`, `--all-hardcoded-surfaces`, category filtering, and exception metadata.

- `/mnt/raid0/llm/epyc-orchestrator/orchestration/stack_change_guard_exceptions.yaml`
  - Default documented exception file for hardcoded-surface findings. Exceptions require classification, owner, rationale, and expiry; valid exceptions remain visible as warnings.

- `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/sync_procedure_role_enums.py`
  - Syncs procedure role choices from generated stack priors.

- `/mnt/raid0/llm/epyc-root/handoffs/active/stack-change-governance-pipeline.md`
  - Existing implementation track. W1/W2 are landed, W3/W4 are partial, W5/W6 remain the key standardization gaps.

- `/mnt/raid0/llm/epyc-root/handoffs/active/model-stack-update-pipeline-audit.md`
  - Existing detailed audit and implementation handoff. This new handoff should be treated as a concise implementation bridge for the main long-horizon workflow, not a replacement.

## Current Single-Source-Of-Truth Proposal

Adopt this as the implementation rule.

| Fact | Source of truth | Generated consumer surface | Notes |
|---|---|---|---|
| Live role -> server/endpoint/port/slot/tier/shared binding | `epyc-orchestrator/orchestration/model_registry.yaml` `server_mode.*`, reconciled with `scripts/server/stack_manifest.py` `ROLE_LAUNCH_META` | `orchestration/derived/stack_priors.yaml` serving block | `server_mode` outranks old role metadata. |
| Physical model identity, modality, context, speed/quality evidence, acceleration compatibility | `orchestration/model_descriptors.yaml`, generated from lean/research evidence where possible | `stack_priors.yaml` model/evidence/acceleration blocks | Descriptors must be model-keyed, not role-keyed. |
| Comprehensive benchmark/candidate history | `epyc-inference-research/orchestration/model_registry.yaml` and benchmark artifacts | Imported into descriptors with provenance/status | Research rows are evidence/candidates, not live deployment truth. |
| q_scorer/reward throughput and memory priors | `stack_priors.yaml` `priors.*` | Typed helper API in `src/registry/stack_priors.py` or a small runtime loader | Current q_scorer still primarily uses registry/descriptors plus fallbacks; migrate to stack priors. |
| Procedure role enums and executor permissions | Generated from `stack_priors.yaml` | `procedure.schema.json`, `procedures/add_model_to_registry.yaml` | Already guarded by `sync_procedure_role_enums.py` and `stack_change_guard.py`. |
| Operator/planner stack summary | Generated from stack priors + attestation | Future system-card/runbook generator | Fable 5 specifically calls out stale prompt/system-card facts as an integrity issue. |

## Observed Current Truth

Grounded in `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml` and the lean registry:

- `frontdoor`
  - model: `qwen3.6-35b-a3b-q8_0`
  - endpoint: `http://localhost:8070`
  - tier: `hot`
  - shared mmap: `true`
  - memory cost: `1.0`
  - known gaps: `ctx_max` and quarter-TPS are not fully structured.

- `coder_escalation`
  - model: `qwen3.6-35b-a3b-q8_0`
  - endpoint: `http://localhost:8070`
  - tier: `hot`
  - shared mmap: `true`
  - memory cost: `1.0`
  - This is the stale qscorer-cost hazard: any consumer that still treats coder escalation as a separate Qwen2.5-Coder-32B server or separate memory owner is wrong for live stack decisions.

- `architect_general`
  - model: `qwen3.5-122b-a10b-q4_k_m`
  - endpoint: `http://localhost:8083`
  - tier: `hot`
  - memory cost: `1.0`
  - known gaps include missing structured overall quality prior and older role performance comments.

- `ingest_long_context`
  - model: `qwen3-next-80b-a3b-q4_k_m`
  - endpoint: `http://localhost:8085`
  - tier: `hot`
  - memory cost: `1.0`
  - known gaps include missing structured quality prior and context/prefill metrics.

- `architect_coding`
  - absent from generated live priors.
  - still appears in guarded hardcoded surfaces and tests/docs, which need either migration, explicit legacy classification, or generated-doc replacement.

## Competing Sources And Drift Risks

These are not all bugs, but each is a place a future stack change can go stale.

1. `q_scorer.py` still has fallback tables.
   - File: `/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/q_scorer.py`
   - Current code names them `FALLBACK_BASELINE_TPS_BY_ROLE` and `FALLBACK_MEMORY_COST_BY_ROLE`, and does skip retired `architect_coding`.
   - It reads live `server_mode` for TPS/memory and overlays descriptors, but it does not yet consume the generated `stack_priors.yaml` contract directly.
   - Implementation implication: keep fallbacks for offline/degraded scripts, but make the live path prefer stack priors with explicit provenance.

2. `stack_manifest.py` still contains stale raw `PORT_MAP` entries.
   - File: `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_manifest.py`
   - `PORT_MAP["coder_escalation"] = 8071`, while `ROLE_LAUNCH_META` documents that coder escalation was consolidated under frontdoor and generated stack priors resolve it to `8070`.
   - Implementation implication: direct `PORT_MAP` consumers are hazardous unless they go through launch metadata/stack priors or are marked legacy.

3. `model_registry.yaml` contains both live topology and older narrative/commentary fields.
   - `server_mode.*` is current live topology.
   - `roles.*`, `process_layout.*`, comments, and docs can preserve older timeouts, memory residency, ports, and benchmark-era labels.
   - Implementation implication: compilers must record conflicts and consumers must not read prose/comments as live truth.

4. LangGraph and role surfaces still reference retired `architect_coding`.
   - Guard examples include `src/graph/langgraph/graph.py`, `src/graph/langgraph/nodes.py`, `src/graph/nodes.py`, `src/parsing_config.py`, and `src/roles.py`.
   - `epyc-orchestrator` `2967526` removed one live launcher hazard: `scripts/server/orchestrator_stack.py` no longer force-enables `ORCHESTRATOR_LANGGRAPH_ARCHITECT_CODING` at API startup.
   - Guard limitation discovered during that fix: the current hardcoded-surface regex is lowercase-only, so uppercase env-var references can bypass warning counts.
   - Some may be active behavior, some may be legacy compatibility. The guard correctly reports them as production blockers until classified or removed.

5. Operator docs and prompt/planner inputs can become source truth by accident.
   - Fable 5 notes stale stack facts in narrative stores and recommends generated system cards from registry/state.
   - Implementation implication: current stack tables in docs/runbooks should be generated from stack priors or labeled historical; do not let manual docs drive routing/scoring.

## Update Checklist For Any Model-Stack Change

Use this sequence for future stack changes. Steps marked "no inference" should be runnable by CI.

- [ ] Identify the change type: role model swap, shared-server consolidation, role retirement, tier change, port/slot change, context change, acceleration/draft/MTP change, or benchmark-only candidate addition.
- [ ] Update structured inputs only:
  - `epyc-orchestrator/orchestration/model_registry.yaml` `server_mode.*` for live deployment topology.
  - `epyc-orchestrator/orchestration/model_descriptors.yaml` for physical model identity and measured/candidate evidence.
  - `epyc-inference-research/orchestration/model_registry.yaml` only for comprehensive benchmark/candidate history, with measurement-status semantics.
  - `scripts/server/stack_manifest.py` only where launcher metadata still lacks generated ownership.
- [ ] Compile descriptors, preserving gaps instead of inventing values.
- [ ] Compile stack priors.
- [ ] Sync procedure role enums.
- [ ] Run loose guard, all-surface guard, and strict guard.
- [ ] Run focused unit tests for stack priors, guard, enum sync, q_scorer, admission, and any touched consumer.
- [ ] Run simulated model-swap tests:
  - shared mmap swap (`frontdoor`/`coder_escalation` style)
  - role retirement (`architect_coding` style)
  - HOT/WARM tier change (`architect_general` or `ingest_long_context` style)
- [ ] Update only generated operator summaries or explicitly historical docs.
- [ ] Before launch, require fresh generated priors and a guard pass or an explicit diagnostic override.
- [ ] After launch, compare running PIDs/ports/flags/binaries against stack priors and restart stale processes if needed.

## Validator And CI Guard Proposal

Near-term guard target:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/registry/compile_descriptors.py --dry-run --allow-incomplete
uv run python scripts/registry/compile_stack_priors.py --allow-incomplete
python3 scripts/registry/sync_procedure_role_enums.py --check
uv run python scripts/validate/stack_change_guard.py
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces
uv run python scripts/validate/stack_change_guard.py --strict
uv run --with pytest pytest -q \
  tests/unit/test_stack_priors_compiler.py \
  tests/unit/test_stack_change_guard.py \
  tests/unit/test_sync_procedure_role_enums.py \
  tests/unit/test_model_descriptors_schema.py \
  tests/unit/test_model_descriptor_compiler.py \
  tests/unit/test_q_scorer.py \
  tests/unit/test_admission.py
```

CI should initially allow loose mode but publish warning counts. Promotion to strict mode should happen after descriptor gaps and unclassified hardcoded surfaces are resolved or documented with expiring exceptions.

Current lightweight guard result to improve from:

- `uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces`
- Result: `WARN: 146 stack-prior warning(s)`, exit 0.
- Major categories:
  - known gaps in generated priors
  - production-blocker retired-role references in graph/parsing/roles surfaces
  - legacy-test retired-role fixtures
  - historical-doc retired-role references

## Implementation Work Packages

### W1 - Make stack priors the live scorer contract

Goal: q_scorer and reward/cost consumers read the generated contract first.

Tasks:

- Add or extend a runtime helper around `src/registry/stack_priors.py` for live role scorer priors.
- Migrate `orchestration/repl_memory/q_scorer.py` live defaults from registry/descriptors to stack priors.
- Keep `FALLBACK_*` tables only for explicit degraded/offline mode.
- Return or log provenance: `stack_priors`, `override`, or `degraded_fallback`.
- Add tests proving:
  - `frontdoor` and `coder_escalation` share memory cost and model identity.
  - `architect_general` and `ingest_long_context` are HOT cost `1.0`.
  - `architect_coding` is absent from live priors.
  - missing stack priors fail closed for production-like callers.

Dependencies: existing stack-priors contract and guard.

### W2 - Classify or remove remaining retired-role production blockers

Goal: `architect_coding` cannot influence live routing, parsing, graph transitions, or launch/status behavior.

Tasks:

- Audit each `stack_change_guard.py --all-hardcoded-surfaces` production-blocker finding.
- Extend or supplement the guard so uppercase retired-role env vars, enum constants, and launch flags cannot hide outside the lowercase `architect_coding` pattern.
- For live code, remove/replace retired role references with stack-prior-derived role sets or current live architect role discovery.
- For legacy compatibility, add explicit exception metadata with owner, rationale, classification, and expiry.
- For tests, rename fixtures or label them as retired-role coverage.

Likely files:

- `src/graph/langgraph/graph.py`
- `src/graph/langgraph/nodes.py`
- `src/graph/nodes.py`
- `src/parsing_config.py`
- `src/roles.py`
- `src/inference/llm_cache.py`
- `scripts/server/orchestrator_stack.py` and launch-env tests for any future legacy env-var recurrence
- related tests under `tests/unit/` and `tests/integration/`

Dependencies: W1 not required, but use the same stack-prior role helpers where practical.

### W3 - Resolve generated-prior gaps needed by strict mode

Goal: `stack_priors.yaml` is complete enough for decision-grade consumers.

Tasks:

- Add structured context fields:
  - model max context
  - effective launch context
  - prefill/long-context metrics where needed
- Add quality/TPS provenance status:
  - decision-grade
  - observation
  - stale
  - gap
- Preserve research-registry evidence with MEASUREMENT.md-style protocol/date/ref metadata.
- Teach strict mode which gaps block live consumers versus which are candidate/historical gaps.

Dependencies: model descriptor coverage and MEASUREMENT.md claim grammar.

### W4 - Standardize launch/status consumers

Goal: ports, tiers, shared-server bindings, and launch requirements are generated or guarded.

Tasks:

- Audit direct `PORT_MAP` and `ROLE_LAUNCH_META` consumers.
- Ensure status/health checks use generated serving records or launcher-classified metadata, not raw stale port maps.
- Decide whether `PORT_MAP["coder_escalation"] = 8071` remains as historical compatibility or should be removed from live-facing maps.
- Extend stack priors or a generated launch manifest with binary family, draft/MTP/spec flags, KV settings, and shared mmap group.

Dependencies: W3 for fuller launch fields.

### W5 - Generate planner/operator stack summaries

Goal: manual docs and planner prompts stop carrying stale model-stack facts.

Tasks:

- Implement a no-inference stack summary generator from stack priors plus running-state attestation.
- Use it for AutoPilot/system-card style prompt inputs rather than hand-maintained stack tables.
- Label old docs historical instead of rewriting every archived mention.
- Add a freshness check so generated summaries cannot be older than their source hashes.

Dependencies: W3 and any Fable 5 system-card work.

### W6 - Add simulated stack-change CI

Goal: prove model changes are data-only.

Tasks:

- Add fixture-based simulated swaps:
  - frontdoor/coder shared model change
  - role retirement
  - HOT to WARM or WARM to HOT tier change
  - long-context model swap with context fields
- Assert regenerated stack priors, q_scorer priors, procedure enums, admission limits, and generated summaries change without code edits.
- Fail if any live consumer reads stale hardcoded values.

Dependencies: W1-W4.

## Dependency Graph

- Existing precedence spec and stack-prior compiler block all consumer migrations.
- W1 and W2 can run in parallel.
- W3 blocks strict CI and robust generated summaries.
- W4 depends on W3 for complete launch fields, but direct stale-port guard work can start now.
- W5 depends on W3 and should align with Fable 5 generated system-card work.
- W6 depends on W1-W4 and becomes the acceptance gate for future stack changes.

## Risks

- Silent degraded fallback: fallback tables keep tests green while live stack truth is missing.
- Over-correcting historical docs: deleting all old model mentions can destroy useful provenance. Prefer generated current docs plus historical labels.
- Treating research registry as live deployment truth: benchmark/candidate records must be imported only through descriptors with provenance/status.
- Launch/process drift: generated files can be fresh while a stale server process is still running. Runtime attestation remains required.
- Guard fatigue: 146 warnings is useful only if warning counts trend down and exceptions expire.
- Over-prescription: `stack_priors.yaml` and descriptors are already the better local pattern. Implementation should extend them, not invent a parallel stack-change system.

## Acceptance Criteria

- A role model swap updates structured registry/descriptor inputs, recompiles generated artifacts, and requires no hand edit in q_scorer, routing priors, admission, procedure enums, status checks, or planner stack summaries.
- `frontdoor` and `coder_escalation` are consistently represented as one shared physical model/server in scorer cost, memory accounting, admission, status, and generated docs.
- `architect_coding` appears only in explicitly classified legacy tests, historical docs, or retired compatibility fixtures, never in live priors or active routing/launch surfaces.
- `architect_general` and `ingest_long_context` are scored as HOT where live server truth says HOT.
- `stack_change_guard.py --strict` is the eventual CI/launch gate, with no unclassified production-blocker warnings.
- Simulated swap tests pass for shared-server consolidation, role retirement, and tier changes.
- Generated stack summaries include source hashes/compiled_at and cannot silently stale.

## Highest-ROI Next Steps

1. Migrate q_scorer live priors to `stack_priors.yaml` first. This directly addresses the stale memory-cost issue and de-biases routing/reward updates.
2. Triage the production-blocker `architect_coding` guard findings in graph/parsing/roles code. Remove live references or classify them with expiring exceptions.
3. Add simulated stack-change tests before broad cleanup. A failing fixture will expose which consumers still bypass the generated contract.
4. Extend stack-prior records with missing context/provenance fields needed for strict mode.
5. Generate planner/operator stack summaries from stack priors so manual prose stops acting as hidden source truth.

## Reporting Instructions

- Update this handoff after each work package with commit hashes, commands run, guard warning counts before/after, and whether inference/AutoPilot remained untouched.
- Keep index edits out of incidental implementation passes. Synchronize `master-handoff-index.md` and domain indices only in a deliberate doc-sync pass.
- Preserve `model-stack-update-pipeline-audit.md` as the detailed audit record; use this file as the implementation bridge for the main workflow.
