# Model Stack Update Pipeline Audit

**Status**: IN PROGRESS 2026-06-13 - parallel audit refresh complete; main workflow should implement W1-W3 below
**Priority**: HIGH - stale model constants can silently misroute, mis-score, launch the wrong stack, or corrupt AutoPilot/replay data after a model change
**Scope**: Audit and implementation handoff. No inference, AutoPilot, orchestrator code, research code, or index files were changed by this pass.
**Related**: [stack-change-governance-pipeline.md](stack-change-governance-pipeline.md), [model-capability-descriptors.md](model-capability-descriptors.md), [routing-truth-restoration.md](routing-truth-restoration.md), [running-state-attestation.md](../completed/running-state-attestation.md), [MEASUREMENT.md](../../MEASUREMENT.md)

## Objective

Turn the existing stack-prior work into a robust, repeatable, fail-closed pipeline for changing orchestration-stack models and all model-specific quantities:

- role -> model binding
- role -> serving endpoint, ports, slots, shared-server binding, and hot/warm state
- q_scorer and seeding reward cost/TPS/quality priors
- routing priors, role budgets, role enums, admission limits, lock/tap classifications, and launch requirements
- generated operator docs/runbooks and runtime attestation

The audit conclusion is clear: the project already has the right foundation, but the process is not yet standardized enough to make model swaps data-only. The next step is not another manual q_scorer-style patch; it is to harden `stack_priors.yaml` as the generated contract and migrate every live consumer to that contract or to an explicit degraded-mode fallback.

## Existing Pipeline Artifacts

These are the real standardized-pipeline artifacts found in the current root/orchestrator trees:

- `/mnt/raid0/llm/epyc-orchestrator/docs/reference/stack-truth-precedence.md`
  - Defines precedence: live serving topology first, descriptors second, role metadata third, historical records last.
  - Explicitly states that `server_mode.*.tier` overrides stale `roles.*.memory.residency`, shared mmap roles must not double-count memory, and retired roles such as `architect_coding` must not appear in active live priors.
- `/mnt/raid0/llm/epyc-orchestrator/src/registry/stack_priors.py`
  - Compiles role records from lean registry, model descriptors, and stack manifest.
  - Current output includes a versioned consumer contract plus serving endpoint/ports/slots/tier, priors for throughput/quality/memory, acceleration metadata, model identity, source evidence, and known gaps (`69057f3`).
- `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/compile_stack_priors.py`
  - Writes `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml`.
- `/mnt/raid0/llm/epyc-orchestrator/scripts/validate/stack_change_guard.py`
  - Validates generated artifact contract shape, freshness, live-role gaps, retired-role leakage, generated procedure enums, and curated hardcoded surfaces.
  - `--all-hardcoded-surfaces` currently reports production blockers, legacy tests, and historical docs separately; `--surface-exceptions` reads documented, expiring exceptions (`e162c7c`).
- `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/sync_procedure_role_enums.py`
  - Syncs `add_model_to_registry.yaml` role choices and `procedure.schema.json` executor roles from stack priors.
- `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_descriptors.yaml`
  - Physical model identity/evidence layer. Descriptors are keyed by model, not role.
- `/mnt/raid0/llm/epyc-root/handoffs/active/stack-change-governance-pipeline.md`
  - The implementation track. W1/W2 are landed; W3 and W4 are partially landed; W5/W6 remain open.

GitNexus note before this handoff edit: root was refreshed via `scripts/gitnexus-analyze.sh` to `24,182 nodes | 26,209 edges | 43 flows`. `gitnexus impact --repo epyc-root handoffs/active/model-stack-update-pipeline-audit.md --direction upstream` returned target not found, `UNKNOWN` risk, `impactedCount=0`, which is expected for this doc path.

## Current Drift Examples

The following examples are evidence-backed reasons this work should stay high ROI and should not be handled as one-off cleanup.

1. `scripts/benchmark/seeding_rewards.py` still owns a stale TPS table.
   - `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seeding_rewards.py:46` defines `DEFAULT_BASELINE_TPS`.
   - It has duplicate `coder_escalation` keys, stale `frontdoor: 18.3`, stale `coder_escalation: 39.44`, stale `architect_general: 6.75`, retired `architect_coding: 10.3`, and stale `ingest_long_context: 6.29`.
   - Current stack priors say frontdoor/coder_escalation share `qwen3.6-35b-a3b-q8_0` on port `8070`, throughput `24.3`, memory cost `1.0`; `architect_general` is HOT with throughput `12.19`; `ingest_long_context` is HOT with `14.4-20.8` evidence compiled to `20.8`.
   - Risk: seeding rewards train cost-aware memory/routing on a dead stack picture.

2. API routing and delegation still contain retired live-role constants.
   - First cleanup landed in `epyc-orchestrator` `b1402a2`: `src/api/routes/chat_delegation_decision.py` no longer keeps `architect_coding` budget defaults, and the live guard warning count dropped from 85 to 83.
   - Second cleanup landed in `epyc-orchestrator` `481516c`: `src/api/routes/chat_pipeline/delegation_stage.py` and `src/api/routes/chat_pipeline/proactive_stage.py` no longer treat retired `architect_coding` as an architect entrypoint, and the live guard warning count dropped from 83 to 81.
   - Third cleanup landed in `epyc-orchestrator` `519f710`: `_role_to_task_type()` no longer contains the redundant retired-role check, and the live guard warning count dropped from 81 to 80.
   - Fourth cleanup landed in `epyc-orchestrator` `d9c053c`: `/v1/models` now derives live model IDs from `stack_priors.yaml` plus compatibility aliases, and the live guard warning count dropped from 80 to 79.
   - Fifth cleanup landed in `epyc-orchestrator` `1b9db81`: `dashboard_snapshot.py` no longer carries a retired in-flight age override, and the live guard warning count dropped from 79 to 78.
   - `/mnt/raid0/llm/epyc-orchestrator/src/api/routes/chat_routing.py:260` still seeds `_heuristic_role_priors` with `architect_coding`; GitNexus marks that function HIGH impact because it feeds streamed chat routing.
   - Risk: production routing surfaces can still emit or score a retired role even though stack priors omit it as live.

3. Config models intentionally preserve dead URLs/timeouts for compatibility.
   - `/mnt/raid0/llm/epyc-orchestrator/src/config/models.py:411` documents `architect_coding` as removed but keeps `http://localhost:8084,http://localhost:8184` at line 417.
   - Timeout config still has `architect_coding` at lines 488-490 and returns it from role maps at lines 552 and 572.
   - Risk: compatibility fields can be mistaken for current stack truth unless generated consumers distinguish retired, degraded, and live roles.

4. Raw launch maps can disagree with generated serving truth.
   - `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_manifest.py:30` maps `coder_escalation` to `8071`, while `ROLE_LAUNCH_META` says coder escalation was consolidated under frontdoor and stack priors resolve it to `8070`.
   - Current stack priors show `coder_escalation.serving.endpoint=http://localhost:8070`, `ports=[8070,8080,8180,8280,8380]`, `slots=1`, `shared_mmap=true`.
   - Risk: any consumer reading `PORT_MAP` directly instead of stack priors can probe or gate a dead port.

5. The generated contract now has explicit shape validation but remains semantically incomplete.
   - `epyc-orchestrator` `69057f3` embeds a versioned `epyc.stack_priors` contract and makes `stack_change_guard.py` reject artifacts missing required role/serving/prior fields.
   - `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml:1` is still compiled with gaps.
   - `architect_general` has `quality_overall: null` and gaps at lines 34-77.
   - `frontdoor` and `coder_escalation` record shared serving truth and memory cost correctly at lines 78-205, but still have `ctx_max` and quarter-TPS gaps.
   - `worker_general` has ik-llama launch metadata and MTP metadata, but the descriptors still report role/server conflicts for aliases that share the runtime.
   - Risk: consumers need to preserve gaps and fail closed where decision-grade priors are required.

6. The validator is finding the right problems, but it is not yet strict-green.
   - `uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces` currently reports 200 warnings, including production blockers in seeding/eval scripts, API/config/routing, LangGraph nodes, runtime inference lock/tap helpers, and historical docs/tests as separate categories.
   - This is good machinery; it now needs exception metadata and consumer migration so strict mode can become a real launch gate.

7. q_scorer is improved but still demonstrates the fallback-policy issue.
   - `/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/q_scorer.py:55` keeps fallback TPS, quality, and memory tables for degraded scripts/tests.
   - Registry-derived TPS and memory paths begin at lines 259 and 304; these now prefer current registry/server mode and skip retired roles.
   - Risk: this is acceptable only if fallbacks are auditable degraded mode, not silent live truth.

## Proposed Source-Of-Truth Design

Adopt this rule for every stack/model change:

1. **Edit structured truth only.**
   - Physical model identity and measured evidence: `orchestration/model_descriptors.yaml`.
   - Live serving topology, ports, slots, tiers, shared bindings, and deployment intent: `orchestration/model_registry.yaml` `server_mode.*`.
   - Temporary launch witness until fully generated: `scripts/server/stack_manifest.py` `ROLE_LAUNCH_META`.

2. **Compile exactly one consumer contract.**
   - `orchestration/derived/stack_priors.yaml` is the generated contract for model-specific consumers.
   - It must include role, model id, endpoint/ports/slots, tier/memory cost, TPS/quality priors with measurement provenance, context window, launch binary, draft/MTP/spec settings, KV settings, modality, shared mmap group, source hashes, and known gaps.

3. **Consume through a typed API, not ad hoc YAML parsing.**
   - Add or extend a small loader, for example `src/registry/stack_priors.py` runtime helpers, so production code can ask for:
     - live roles
     - retired roles
     - role serving record
     - role scorer priors
     - role budget/policy hints
     - launch requirements
     - high-cost/lock/tap classifications
   - Tests and scripts may read YAML directly only when imports would create a cycle; they must still preserve degraded-mode warnings.

4. **Make fallback tables explicit degraded mode.**
   - Fallback constants should be named `DEGRADED_*` or `FALLBACK_*`, must exclude retired live roles unless testing legacy behavior, and must emit or return provenance that says "not live stack truth".
   - Production validators should fail if a live consumer silently accepts fallback values while stack priors are present.

5. **Require data-only simulated swaps.**
   - A model swap is not complete until fixture-based tests prove that changing registry/descriptors regenerates consumer outputs without code edits.

## Work Packages

### W1 - Harden the stack-prior contract and guard

Goal: make `stack_priors.yaml` complete enough to be the only model-specific consumer contract.

Tasks:

- DONE foundation in `69057f3`: add an explicit versioned contract plus structural validation for stack priors.
- Extend compiled records with missing consumer fields:
  - context window / effective max context
  - decision-grade TPS and quality status
  - launch binary path/family and runtime incompatibilities
  - draft/MTP/spec decode knobs
  - KV/cache settings
  - shared mmap group id and memory-accounting owner
  - role policy hints needed by API budgets/routing if those remain role-specific
- Add source metadata for research-registry/benchmark evidence where descriptors depend on research artifacts, not just the lean orchestrator registry.
- DONE foundation in `e162c7c`: add an external exception allowlist for `stack_change_guard.py` with owner, category, rationale, expiry/review date, and whether the exception is live, degraded fallback, legacy test, or historical doc.
- PARTIAL in `e162c7c`: strict mode now keeps valid waived hardcoded-surface findings visible as warnings instead of promoting them to errors; unresolved descriptor/global-gap policy still needs final strict-mode tightening.

Acceptance:

- `uv run python scripts/registry/compile_stack_priors.py --allow-incomplete` preserves known gaps.
- strict mode can distinguish "blocked live consumer" from "documented fallback" without hiding either.
- Adding a retired live role to a production consumer fails the guard.

### W2 - Migrate highest-risk live consumers

Goal: eliminate model-specific hardcoding from live scoring/routing/config behavior.

Priority order:

1. `scripts/benchmark/seeding_rewards.py`
   - Replace `DEFAULT_BASELINE_TPS` with stack-prior-derived TPS/cost data.
   - Keep an explicit degraded fallback for offline tests.
   - Treat this as a separate blast-radius pass because `compute_comparative_rewards` was previously marked CRITICAL.
2. `src/api/routes/chat_delegation_decision.py`
   - DONE first cleanup in `b1402a2`: removed `architect_coding` from live budget defaults.
   - Remaining follow-up: derive architect/delegation budget maps from stack-prior role policy or live architect roles instead of a local static table.
3. `src/api/routes/chat_pipeline/delegation_stage.py` and `src/api/routes/chat_pipeline/proactive_stage.py`
   - DONE cleanup in `481516c`: retired `architect_coding` no longer triggers delegated/proactive architect branch behavior.
4. `src/api/routes/chat_routing.py`
   - PARTIAL cleanup in `519f710`: removed the redundant retired-role check from `_role_to_task_type()` and added live-role mapping coverage.
   - Remaining HIGH-impact follow-up: build `_heuristic_role_priors()` from live stack-prior roles, not a static dict containing retired roles.
5. `src/api/routes/openai_compat.py` and `src/api/routes/dashboard_snapshot.py`
   - DONE cleanup in `d9c053c`: OpenAI-compatible `/v1/models` now reads deployed roles from stack priors and keeps only non-retired degraded fallback roles plus aliases.
   - DONE cleanup in `1b9db81`: dashboard in-flight task age overrides no longer include retired `architect_coding`.
6. `src/config/__init__.py` and `src/config/models.py`
   - Separate live role config from retired compatibility fields.
   - Prefer stack-prior endpoints/timeouts where possible; make dead-port compatibility visibly retired.
7. `src/runtime/inference_lock.py`, `src/runtime/inference_tap.py`, and `src/graph/**`
   - Derive high-cost/streaming/exclusive-role classifications from stack priors or explicit role policy.
   - Confirm whether LangGraph retired-role nodes are dead code or active; either remove from live graph or label legacy/test-only.

Acceptance:

- `stack_change_guard.py --all-hardcoded-surfaces` production-blocker count drops materially after each pass.
- q_scorer, seeding reward costs, routing priors, admission limits, procedure role enums, and API examples all agree on the same live roles.
- `architect_coding` remains only in historical docs, retired compatibility tests, or explicit legacy fixtures.

### W3 - Build the repeatable stack-change workflow

Goal: one command sequence for safe model changes, usable by the main agent or a human operator.

Tasks:

- Add a no-inference stack-change workflow script or documented command target that runs:
  - descriptor compile/check
  - stack-prior compile/check
  - procedure enum sync check
  - stack-change guard strict mode
  - consumer snapshot tests
  - simulated model-swap tests
  - source/derived artifact freshness checks
- Add fixture-based simulated swaps:
  - shared-mmap role swap, e.g. frontdoor/coder_escalation same-GGUF group
  - worker-family swap with launch requirements, e.g. gemma4 worker MTP/ik binary
  - retired-role removal, e.g. `architect_coding`
- Add pre-launch and post-launch gates:
  - pre-launch: strict stack-change guard must pass or require an explicit diagnostic override
  - launch: launcher consumes generated launch requirements where available
  - post-launch: running-state attestation compares live PIDs/ports/flags/binary paths against stack priors
- Generate or refresh operator-facing stack summaries from stack priors so manual docs do not become source truth.

Acceptance:

- A model assignment can be changed in structured inputs, generated artifacts update, and no live consumer requires hand-editing.
- Launch refuses stale generated priors unless an explicit diagnostic override is present.
- Runtime attestation detects stale running processes after config/code changes.

## Validation Strategy

No inference is required for W1-W3 until a later benchmark gate explicitly requests it.

```bash
cd /mnt/raid0/llm/epyc-orchestrator

python3 -m py_compile \
  src/registry/stack_priors.py \
  scripts/registry/compile_stack_priors.py \
  scripts/registry/sync_procedure_role_enums.py \
  scripts/validate/stack_change_guard.py \
  scripts/registry/compile_descriptors.py \
  src/registry/model_descriptors.py \
  orchestration/repl_memory/q_scorer.py \
  scripts/benchmark/seeding_rewards.py

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

git diff --check
```

Use focused extra tests for each W2 consumer pass. Do not run AutoPilot or llama inference while implementing this handoff unless a later explicit benchmark/attestation step requires it.

## Non-Goals

- Do not restart AutoPilot or run inference as part of this audit handoff.
- Do not design a second registry. The point is to make descriptors, lean registry `server_mode`, stack manifest launch metadata, and generated stack priors cohere.
- Do not rewrite all historical docs. Historical references should be labeled or generated separately; production launch should not depend on them.
- Do not suppress guard findings without owner/rationale/expiry metadata.
- Do not reopen learned-routing expansion work. Routing-truth restoration remains frozen until the measured gates in the routing handoffs justify expansion.
- Do not edit master or sub-index files during implementation except in a deliberate doc-sync pass.

## Reporting Instructions

- Update this handoff when an audited failure mode is closed, reclassified, or assigned an explicit exception.
- Update `stack-change-governance-pipeline.md` only for waypoint progress and validation results.
- Keep `master-handoff-index.md`, `routing-and-optimization-index.md`, and `model-capability-descriptors.md` out of incidental edits; those have broader blast radius and should be synchronized deliberately.
- Progress notes should include exact commands, guard warning counts before/after, and whether AutoPilot/inference was paused.
