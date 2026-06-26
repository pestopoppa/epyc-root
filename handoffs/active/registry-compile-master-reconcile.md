# Reconcile master registry + enable `--compile-registry` (single-source-of-truth)

**Status:** OPEN (deferred from the 2026-06-26 v6-iqk cutover; not required by it)
**Priority:** Medium — removes a standing class of config-drift bugs; not user-facing
**Created:** 2026-06-26 (operator request, during v6-iqk-promotion)

## Problem
The lean orchestrator registry (`epyc-orchestrator/orchestration/model_registry.yaml`) is **supposed** to be COMPILED from the master research registry (`epyc-inference-research/orchestration/model_registry.yaml`) by `src/registry/registry_compiler.py` at stack launch (`orchestrator_stack.py start --compile-registry`). But `--compile-registry` is **default-OFF** (verified `scripts/server/stack_commands.py:644-655`):

> "Default OFF until the master + orchestrator are reconciled (today the master itself has an internal acceleration disagreement on architect_general — `roles.X.acceleration.type=speculative_decoding` vs `server_mode.X.acceleration.type=moe_expert_reduction`). Fix the master first, then enable this flag."

So today the **lean registry is hand-maintained and authoritative** (its `architect_general` block is annotated "2026-05-09 reconciled: this block is now the single source of truth"). This means every registry change must be hand-applied to lean (and the master kept in sync manually) — a recurring drift hazard. The v6-iqk cutover (`v6-iqk-promotion.md`) works around it by editing lean-authoritative + syncing master by hand.

## Objective
Make the master registry internally self-consistent, then enable `--compile-registry` so the lean registry is GENERATED (filtered to active roles per `ROLE_LAUNCH_META` + transitive deps), restoring master as the single source of truth and eliminating lean/master hand-sync drift.

## Scope / tasks
1. **Reconcile the master `architect_general` dual-source acceleration** — `roles.architect_general.acceleration` vs `server_mode.architect_general.acceleration` disagree. Pick the authoritative one (post-cutover this is MTP / draft-mtp, per the v6 cutover) and make both consistent. Audit ALL roles for the same `roles.X` vs `server_mode.X` acceleration disagreement (the validator at `src/registry/registry_validator.py` flags these).
2. **Diff compiled-lean vs hand-maintained-lean** — run `registry_compiler.load_or_compile` to a scratch path, diff against the live lean. Every divergence is either a master bug to fix or a hand-edit to migrate into master.
3. **Migrate worker-pool hardcodes into the registry** — `stack_manifest.py` (`WORKER_POOL_MODELS`, `EXPLORE_DRAFT_MODEL`, `WORKER_MTP_*`) duplicate registry data as the worker-pool fallback; fold into the registry so the compiler is the single source.
4. **Enable `--compile-registry`** in the start path once compiled-lean == intended-lean and the consistency validator is green; keep the `ORCHESTRATOR_REGISTRY_NO_COMPILE=1` escape hatch.
5. Remove the "single source of truth" hand-edit annotations once master drives compilation.

## Key files
- `epyc-orchestrator/src/registry/registry_compiler.py` (the compiler), `registry_validator.py` (consistency gate)
- `epyc-orchestrator/scripts/server/stack_commands.py:644-674` (the `--compile-registry` opt-in + disable comment)
- `epyc-orchestrator/scripts/server/stack_manifest.py` (worker-pool hardcodes to fold in)
- master `epyc-inference-research/orchestration/model_registry.yaml`; lean `epyc-orchestrator/orchestration/model_registry.yaml`

## Verification
`registry_compiler` output == intended lean (diff clean); `registry_validator.validate_or_raise` green; `orchestrator_stack.py start --compile-registry` produces a byte-stable lean across re-runs (cache-key no-op); `stack_change_pipeline.py check` green.

## Notes
Independent of the v6-iqk cutover — that ships on the lean-authoritative path. This is the cleanup that makes master authoritative again. ROI: eliminates the lean/master hand-sync drift class permanently.
