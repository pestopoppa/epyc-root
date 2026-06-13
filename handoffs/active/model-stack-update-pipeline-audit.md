# Model Stack Update Pipeline Audit

**Status**: IN PROGRESS 2026-06-13 - Phase A scanner landed; implementation continues in main workflow
**Priority**: HIGH - stale model constants can silently misroute, mis-score, or launch the wrong stack after a model change
**Scope**: Documentation/audit only. No orchestrator or research code was changed for this draft.
**Related**: [stack-change-governance-pipeline.md](stack-change-governance-pipeline.md), [model-capability-descriptors.md](model-capability-descriptors.md), [routing-truth-restoration.md](routing-truth-restoration.md), [running-state-attestation.md](../completed/running-state-attestation.md), [model-registry-v5-deployment-draft.yaml](model-registry-v5-deployment-draft.yaml), [MEASUREMENT.md](../../MEASUREMENT.md)

## Objective

Audit prior work toward a standardized, safe model/stack-update pipeline and turn the findings into an implementation-ready handoff.

The desired future shape is not a second registry system. Treat the current stack-priors foundation as the emerging core:

- model descriptors own physical model identity and benchmark evidence
- live `server_mode` / stack manifest / runtime attestation own deployed serving truth
- `orchestration/derived/stack_priors.yaml` becomes the generated consumer contract
- validators fail closed when any model-specific consumer still depends on stale hardcoded role/model/port/cost facts

## Current Evidence

- The main stack-governance handoff already exists at `handoffs/active/stack-change-governance-pipeline.md`; W1/W2 are landed, W3 is partial, and W4-W6 remain open.
- The current orchestrator foundation is live:
  - `/mnt/raid0/llm/epyc-orchestrator/docs/reference/stack-truth-precedence.md`
  - `/mnt/raid0/llm/epyc-orchestrator/src/registry/stack_priors.py`
  - `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/compile_stack_priors.py`
  - `/mnt/raid0/llm/epyc-orchestrator/scripts/validate/stack_change_guard.py`
  - `/mnt/raid0/llm/epyc-orchestrator/orchestration/derived/stack_priors.yaml`
  - `/mnt/raid0/llm/epyc-orchestrator/tests/unit/test_stack_priors_compiler.py`
  - `/mnt/raid0/llm/epyc-orchestrator/tests/unit/test_stack_change_guard.py`
- Phase A hardcoded-surface scanning landed in `epyc-orchestrator` `bfa90fa`:
  `stack_change_guard.py` now reports categorized production-blocker,
  legacy-test, and historical-doc surfaces, with normal guard output scoped to
  production blockers and `--all-hardcoded-surfaces` available for full audits.
- `progress/2026-06/2026-06-13.md` records the exact lineage: descriptor consumers for AutoPilot and q_scorer landed first, then `a1e04d5` added the derived stack-prior guardrail. Strict mode is intentionally not green until descriptor gaps and remaining consumers are closed.
- `handoffs/active/model-capability-descriptors.md` is the model-agnostic interface. W3 still lists seeder per-role eval config and stack-launch acceleration args as open consumers.
- The research master registry explicitly says the active per-role stack lives in the orchestrator lean registry: `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`. Current stack-priors compilation reads the lean orchestrator registry, not the research master.

## Prior Art Found

### Current stack-priors foundation

Evidence:

- `stack-truth-precedence.md` declares source precedence: live serving topology, model descriptors, role metadata, then historical records.
- `stack_priors.py` compiles role records with model id, endpoint, tier, throughput, quality prior, memory cost, acceleration metadata, source hashes, and known gaps.
- `stack_change_guard.py` currently validates source hashes, missing live role basics, retired live role `architect_coding`, HOT memory cost, and strict-mode known gaps.

Assessment: this is the right foundation. The main missing pieces are broader consumer migration, stricter drift scanning, simulated swaps, and launch/runbook enforcement.

### Model-capability descriptor pipeline

Evidence:

- `handoffs/active/model-capability-descriptors.md`
- `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_descriptors.yaml`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/compile_descriptors.py`
- `/mnt/raid0/llm/epyc-orchestrator/tests/unit/test_model_descriptor_compiler.py`
- `/mnt/raid0/llm/epyc-orchestrator/tests/unit/test_model_descriptors_schema.py`

Assessment: descriptors are the model identity/evidence layer. The descriptor compiler is still allowed-incomplete for many identities, so consumers must preserve and surface gaps rather than synthesizing silent defaults.

### Routing truth restoration and q_scorer fixes

Evidence:

- `handoffs/active/routing-truth-restoration.md` W5 records the first q_scorer registry-backed baseline repair.
- `/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/q_scorer.py` now prefers descriptor/registry-derived TPS and memory costs but still keeps offline fallback tables.

Assessment: q_scorer is no longer the worst drift source, but the fallback path still needs degraded-mode guardrails and tests proving it cannot masquerade as live production truth.

### Procedure registry recipes

Evidence:

- `/mnt/raid0/llm/epyc-orchestrator/orchestration/procedures/add_model_to_registry.yaml`
- `/mnt/raid0/llm/epyc-orchestrator/orchestration/procedures/update_registry_performance.yaml`
- `/mnt/raid0/llm/epyc-orchestrator/docs/chapters/11-procedure-registry.md`

Assessment: these are partial rollback/YAML recipes, not a safe stack-update pipeline. `add_model_to_registry.yaml` still has stale role enums including `architect_coding` and duplicated `coder_escalation`, and neither procedure compiles descriptors/stack priors, checks consumers, simulates swaps, or validates launch truth.

### Benchmarking and server-mode practices

Evidence:

- `/mnt/raid0/llm/epyc-inference-research/docs/guides/benchmarking-guide.md`
- `/mnt/raid0/llm/epyc-inference-research/docs/reference/benchmarks/SERVER_MODE.md`
- `/mnt/raid0/llm/epyc-inference-research/scripts/validate_model_registry.py`

Assessment: the research side has strong measurement discipline and server-mode mechanics. It still leaves the production-safe update handoff to the orchestrator side: update research results, update registry, then compile/validate downstream artifacts.

### v5 deployment draft and cleanup audit pattern

Evidence:

- `handoffs/active/model-registry-v5-deployment-draft.yaml`
- `handoffs/completed/v5-push-cleanup-audit.md`

Assessment: the v5 work is a useful staged-deployment pattern: keep risky env/binary/flag assignments in a draft, require per-role smoke/bench gates, and only merge into registry after validation. This pattern should be reused for launch-arg/binary-path fields in stack priors.

### Running-state attestation

Evidence:

- `handoffs/completed/running-state-attestation.md`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/attest/generate_attestation.py` if merged in the live branch

Assessment: attestation is the runtime witness needed by stack-change W6. The stack-prior guard currently validates source artifacts, not the running process state after launch.

### Historical doc-drift audits

Evidence:

- `handoffs/completed/docs-chapters-audit/cluster-F.md` identifies `MODEL_MANIFEST.md` as a drifting point-in-time snapshot and recommends generating it from the registry.
- `/mnt/raid0/llm/epyc-inference-research/docs/MODEL_MANIFEST.md` still lists old ports/models and retired `architect_coding` despite saying configuration lives in `model_registry.yaml`.

Assessment: docs and generated public manifests need separate drift policy. They should not block code launch unless they are operator runbooks, but they must not be used as source truth.

## Concrete Failure Modes

1. **Manual docs and model manifests drift into operational advice.**
   - Evidence: `/mnt/raid0/llm/epyc-inference-research/docs/MODEL_MANIFEST.md` lists frontdoor/coder ports as 8080/8081 and keeps `architect_coding` as WARM. Current lean `server_mode` uses frontdoor/coder on 8070 and stack-priors omit `architect_coding`.
   - Risk: operators or agents follow stale docs and launch/probe the wrong port/model.
   - Needed guard: generate operator-facing stack summaries from stack priors, or label manual docs as historical snapshots with a freshness gate.

2. **Fallback tables can reintroduce retired roles or stale speeds.**
   - Evidence: `q_scorer.py` still has fallback role TPS/quality/memory tables; `bilinear_scorer.py` has hardcoded `model_specs` including `architect_coding`, `coder_escalation` as 32B, and worker aliases; `model_quality_signatures.yaml` is marked last updated 2026-04-16 and still carries old active-stack assumptions.
   - Risk: registry/descriptor load failure, fallback-only tests, or disabled descriptor consumers silently score with stale costs/quality.
   - Needed guard: degraded-mode telemetry plus validator checks that fallback tables are not accepted as live production truth.

3. **Seeder defaults can target retired roles even though discovery reads `server_mode`.**
   - Evidence: `/mnt/raid0/llm/epyc-orchestrator/scripts/benchmark/seeding_types.py` has `DEFAULT_ROLES` and `ARCHITECT_ROLES` containing `architect_coding`, while later comments say the role was removed on 2026-05-06.
   - Risk: a manual seeding run or test path can spend time on a retired role or train priors for a non-live path.
   - Needed guard: seeder config should consume stack priors for default roles, cost tier, heavy-port classification, and role aliases.

4. **Serving truth is split across `server_mode`, `stack_manifest`, comments, and historical ports.**
   - Evidence: `stack_manifest.py` still has `PORT_MAP["coder_escalation"] = 8071` while `ROLE_LAUNCH_META` consolidates it under frontdoor and the lean registry `server_mode.coder_escalation.port` is 8070. `stack_priors.py` currently resolves this, but consumers that read raw maps directly can disagree.
   - Risk: probes, contention scheduling, or launch validation can check a dead port or double-count a shared server.
   - Needed guard: consumers should use the stack-prior serving record or a single stack API, not raw port maps.

5. **Launch binary and acceleration requirements are still special-cased outside generated priors.**
   - Evidence: `stack_manifest.py` hardcodes gemma4 worker model paths, MTP draft path, ik-llama notes, and vision model paths; `model-capability-descriptors.md` W3 explicitly says stack-launch acceleration args are still open.
   - Risk: a model swap updates registry/descriptors but launch still uses incompatible binary, draft, `enable_thinking`, KV, or spec flags.
   - Needed guard: stack priors must include launch requirements and `orchestrator_stack.py` must either consume them or fail closed when they are unresolved.

6. **The current stack-change guard is too narrow for model-swap safety.**
   - Evidence: `stack_change_guard.py` validates hashes, basic live role shape, retired live roles, HOT memory cost, and strict known gaps. It does not yet scan hardcoded model specs, procedure enums, docs/runbooks, seeder defaults, bilinear features, or launch constants.
   - Risk: generated artifact is fresh while a downstream consumer remains stale.
   - Needed guard: W3 strict mode needs a curated hardcoded-surface scanner with allowlist categories: production blocker, degraded fallback, legacy test, historical doc.

7. **Research master to orchestrator lean sync is not proven by the stack-prior artifact.**
   - Evidence: research `docs/MODEL_MANIFEST.md` says the orchestrator lean copy is compiled from the master at stack-launch time; current stack-priors source hashes cover only the lean registry and descriptors.
   - Risk: research benchmark evidence changes but the lean registry or descriptors are not regenerated, so production consumes stale priors.
   - Needed guard: stack-prior source metadata should include the research registry or descriptor compile provenance when research evidence is an input.

8. **Quality and measurement provenance can collapse into unqualified priors.**
   - Evidence: `stack_priors.yaml` has `quality_overall: null` for some roles and known gaps; `q_scorer.py` still carries baseline quality constants; `MEASUREMENT.md` requires protocol/date/attestation for decision-gating numbers.
   - Risk: routing cost/quality decisions use observation-grade numbers as if they were gate-grade.
   - Needed guard: quality/TPS priors must carry measurement status and consumers must distinguish decision-grade values from observations.

9. **Runtime attestation is not yet part of stack-change validation.**
   - Evidence: running-state attestation has a completed handoff, while stack-change W6 remains open.
   - Risk: source artifacts validate, but the old stack process keeps running after code/config changes.
   - Needed guard: start/reload path should run stack-change guard before launch and attestation after launch, with stale-process detection.

10. **Tests and docs can preserve dead live roles without an explicit legacy label.**
    - Evidence: `docs/ARCHITECTURE.md` still shows escalation chains through `architect_coding`; multiple tests force or reference `architect_coding`.
    - Risk: future agents treat test/doc references as live production intent.
    - Needed guard: mark retired-role references as test-only/historical, or make the validator report them separately from production blockers.

## Proposed Phased Implementation

### Phase A - Inventory and classify hardcoded surfaces

- [x] Add a no-inference scanner under `epyc-orchestrator/scripts/validate/` or extend `stack_change_guard.py`.
- [x] Output categories: production blocker, legacy test, and historical docs.
- [ ] Add an external allowlist/config once production blockers start being closed and intentional exceptions need owner/review metadata.
- Initial live findings from `bfa90fa`: production blockers remain in seeding/eval defaults, seeding reward TPS fallback, bilinear model specs, legacy CLI probing, procedure role enums, API/config/routing surfaces, LangGraph nodes, runtime tap/lock helpers, and OpenAI compatibility docs. These are now machine-visible instead of a manual `rg` checklist.

### Phase B - Expand stack-prior coverage

- Add launch requirements to derived priors: binary path/family, draft model, MTP/spec fields, `enable_thinking`, KV settings, NUMA policy, shared-mmap grouping, and runtime incompatibilities.
- Add provenance for research-registry/descriptor source inputs, not just lean registry hashes.
- Preserve `known_gaps` as first-class fields. Do not fill null quality/speed with silent constants.

### Phase C - Migrate remaining live consumers

Priority order:

1. [x] `scripts/benchmark/seeding_types.py`: default roles and active discovery cost tiers now consume stack-prior/default-live truth where available (`epyc-orchestrator` `72f7dc2`). Remaining seeding work: ports/heavy classification still come from registry/fallback maps; `scripts/benchmark/seeding_rewards.py` reward-cost migration is intentionally deferred because GitNexus marks `compute_comparative_rewards` CRITICAL.
2. [ ] `orchestration/repl_memory/bilinear_scorer.py`: derive `ModelFeatures` from stack priors/descriptors instead of hardcoded `model_specs`.
3. [ ] `orchestration/model_quality_signatures.yaml`: keep as legacy fallback only, or generate it from descriptors with a visible `_source` and `compiled_at`.
4. [ ] `scripts/server/orchestrator_stack.py` / `stack_manifest.py`: consume stack-prior launch requirements or fail when descriptor/registry acceleration disagrees with hardcoded launch metadata.
5. [ ] Operator docs/manifests: generate current stack tables from stack priors or mark snapshots as non-authoritative.

### Phase D - Strict guard and simulated model-swap CI

- Make `stack_change_guard.py --strict` pass only when descriptor gaps for live roles are closed or explicitly accepted.
- Add simulated swaps using temporary registry/descriptor fixtures:
  - one shared-mmap role swap (`frontdoor`/`coder_escalation`)
  - one worker-family swap (`worker_general` MTP/binary requirements)
  - one retired-role removal check (`architect_coding`)
- Acceptance: derived priors and consumer outputs change from data only; no production code edits required.

### Phase E - Launch/runbook integration

- Pre-launch: compile descriptors, compile stack priors, run strict guard.
- Launch: use stack-prior serving/launch fields where available.
- Post-launch: run running-state attestation and compare ports, PIDs, flags, binary paths, and live role bindings against stack priors.
- Runbook: one command sequence for "change model assignment safely"; include rollback to previous generated artifacts and restart/attestation requirements.

## Validation Commands

No inference required for these commands unless a later phase explicitly adds operator-approved benchmark gates.

```bash
cd /mnt/raid0/llm/epyc-orchestrator

python3 -m py_compile \
  src/registry/stack_priors.py \
  scripts/registry/compile_stack_priors.py \
  scripts/validate/stack_change_guard.py \
  scripts/registry/compile_descriptors.py \
  src/registry/model_descriptors.py \
  orchestration/repl_memory/q_scorer.py

uv run python scripts/registry/compile_descriptors.py --dry-run --allow-incomplete
uv run python scripts/registry/compile_stack_priors.py --allow-incomplete
uv run python scripts/validate/stack_change_guard.py
uv run python scripts/validate/stack_change_guard.py --all-hardcoded-surfaces
uv run python scripts/validate/stack_change_guard.py --strict

uv run --with pytest pytest -q \
  tests/unit/test_stack_priors_compiler.py \
  tests/unit/test_stack_change_guard.py \
  tests/unit/test_model_descriptors_schema.py \
  tests/unit/test_model_descriptor_compiler.py \
  tests/unit/test_q_scorer.py

rg -n 'architect_coding|Qwen3-Coder-32B|Qwen3-Coder-30B|Qwen3.5-35B|Qwen3.6|REAP-246B|808[0-9]|807[0-9]|baseline_tps|max_throughput_tps' \
  orchestration src scripts tests docs

git diff --check
```

Cross-repo registry sanity:

```bash
cd /mnt/raid0/llm/epyc-root
python3 scripts/validate/validate_registry.py

cd /mnt/raid0/llm/epyc-inference-research
python3 scripts/validate_model_registry.py
```

Expected current state: strict stack-prior validation may fail until descriptor gaps and remaining consumer migrations are complete. Treat that as a known blocker, not a regression.

## Dependencies

- `model-capability-descriptors.md` W2/W3 must finish enough live descriptor evidence for strict compile.
- `stack-change-governance-pipeline.md` W3-W6 owns the actual implementation path.
- `routing-truth-restoration.md` keeps routing expansion frozen; do not use this pipeline as an excuse to reopen cascade changes without fresh measured gates.
- `running-state-attestation.md` supplies the post-launch runtime witness for W6.
- `MEASUREMENT.md` governs which TPS/quality numbers can gate model promotion.
- Research full registry remains the comprehensive benchmark record; orchestrator lean registry remains current active serving truth until an explicit sync/compile path replaces that split.

## Explicit Next Steps for Main Workflow

1. In `stack-change-governance-pipeline.md`, keep W4 focused on consumer migration and cite this audit as the hardcoded-surface inventory.
2. Implement the Phase A scanner first. It is no-inference, gives immediate drift visibility, and prevents W4 from becoming a manual grep checklist.
3. Migrate `seeding_types.py` and `bilinear_scorer.py` next; they are the clearest remaining live-or-near-live hardcoded consumers after q_scorer and AutoPilot planner signatures.
4. Extend `stack_priors.py` to include launch requirements before changing `orchestrator_stack.py`. Launcher migration without generated launch facts would just move the hardcoding.
5. Add simulated model-swap tests before marking W4/W5 complete. The acceptance criterion is data-only model substitution with no stale role/model/port/cost leakage.
6. Wire strict guard + attestation into launch only after strict mode can pass or produce intentional, operator-readable exceptions.

## Reporting Instructions

- Update this handoff when an audited failure mode is closed or reclassified.
- Update `stack-change-governance-pipeline.md` for waypoint progress and validation results.
- Do not edit master indices until the main workflow performs a deliberate doc-sync pass.
- Any benchmark-derived number added during implementation must follow `MEASUREMENT.md` claim grammar.
