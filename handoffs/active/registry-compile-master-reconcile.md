# Reconcile master registry + enable `--compile-registry` (single-source-of-truth)

**Status:** OPEN (deferred from the 2026-06-26 v6-iqk cutover; not required by it). First no-inference hardening slice landed in orchestrator `c3ac153f`: `--compile-registry` now expands `ROLE_LAUNCH_META.shared_with_first_n` aliases before compiling, and tests prove aliases such as `coder_escalation` / `worker_summarize` survive the lean projection.
**Priority:** Medium — removes a standing class of config-drift bugs; not user-facing
**Created:** 2026-06-26 (operator request, during v6-iqk-promotion)

## Problem
The lean orchestrator registry (`epyc-orchestrator/orchestration/model_registry.yaml`) is **supposed** to be COMPILED from the master research registry (`epyc-inference-research/orchestration/model_registry.yaml`) by `src/registry/registry_compiler.py` at stack launch (`orchestrator_stack.py start --compile-registry`). But `--compile-registry` is **default-OFF** (verified `scripts/server/stack_commands.py:644-655`):

> "Default OFF until the master + orchestrator are reconciled (today the master itself has an internal acceleration disagreement on architect_general — `roles.X.acceleration.type=speculative_decoding` vs `server_mode.X.acceleration.type=moe_expert_reduction`). Fix the master first, then enable this flag."

So today the **lean registry is hand-maintained and authoritative** (its `architect_general` block is annotated "2026-05-09 reconciled: this block is now the single source of truth"). This means every registry change must be hand-applied to lean (and the master kept in sync manually) — a recurring drift hazard. The v6-iqk cutover (`v6-iqk-promotion.md`) works around it by editing lean-authoritative + syncing master by hand.

## Objective
Make the master registry internally self-consistent, then enable `--compile-registry` so the lean registry is GENERATED (filtered to active roles per `ROLE_LAUNCH_META` + transitive deps), restoring master as the single source of truth and eliminating lean/master hand-sync drift.

## Scope / tasks
1. **Reconcile the master live-role facts** — the current validator passes both files, but a scratch compile from master still rewrites live semantics. Concrete stale master fields found 2026-06-27:
   - `server_mode.frontdoor` / `roles.frontdoor` still point at pre-MTP `Qwen_Qwen3.6-35B-A3B-Q8_0.gguf`, port `8080`, slots `1`, and `acceleration.type=none`; live lean uses `Qwen3.6-35B-A3B-MTP-Q8_0.gguf`, port `8070`, slots `2`, and `draft-mtp`.
   - `server_mode.coder_escalation` / `roles.coder_escalation` still mirror the old frontdoor path/port and stale predecessor metadata; live lean shares the MTP frontdoor server on `8070`.
   - `server_mode.architect_general` still points at non-MTP `Qwen3.5-122B-A10B-Q4_K_M...` plus external `Qwen3.5-0.8B-Q8_0` draft; live lean points model and draft at the v6 MTP GGUF and carries `draft_max=4`, `lookup=false`, and `enable_thinking=false`.
   - `process_layout` in master still marks ingest/vision warm and lists obsolete draft hot residents; live lean marks `frontdoor`, aliases, `worker_general`, `ingest_long_context`, `worker_vision`, and `vision_escalation` hot with only `architect_general` warm.
2. **Decide compile output shape before enabling default** — current compiler intentionally drops catalog/history sections (`observations`, `runtime_quirks`, `deprecated_models`, `optimized_params`, `kernel_audits`) and filters `roles`/`server_mode` to active roles plus dependencies. That may be desirable for a true lean runtime file, but it is not byte-equivalent to the current hand-maintained lean. Either migrate consumers away from these lean-side catalog sections or explicitly preserve the sections needed by runtime/docs before enabling default compile.
3. **Keep alias projection fixed** — orchestrator `c3ac153f` added `active_roles_from_launch_meta()` and wired `cmd_start --compile-registry` plus the compiler CLI to include `shared_with_first_n` aliases. Preserve this behavior in future compile changes.
4. **Diff compiled-lean vs intended lean** — run `registry_compiler.load_or_compile` to a scratch path, diff against the live lean, and classify every divergence as a master bug, an intentional lean-only runtime section, or a compiler keep/drop rule.
5. **Migrate worker-pool hardcodes into the registry** — `stack_manifest.py` (`WORKER_POOL_MODELS`, `EXPLORE_DRAFT_MODEL`, `WORKER_MTP_*`) duplicate registry data as the worker-pool fallback; fold into the registry so the compiler is the single source.
6. **Enable `--compile-registry`** in the start path only once compiled-lean == intended-lean and the consistency validator is green; keep the `ORCHESTRATOR_REGISTRY_NO_COMPILE=1` escape hatch.
7. Remove the "single source of truth" hand-edit annotations once master drives compilation.

## Key files
- `epyc-orchestrator/src/registry/registry_compiler.py` (the compiler), `registry_validator.py` (consistency gate)
- `epyc-orchestrator/scripts/server/stack_commands.py:644-674` (the `--compile-registry` opt-in + disable comment)
- `epyc-orchestrator/scripts/server/stack_manifest.py` (worker-pool hardcodes to fold in)
- master `epyc-inference-research/orchestration/model_registry.yaml`; lean `epyc-orchestrator/orchestration/model_registry.yaml`

## Verification
`registry_compiler` output == intended lean (diff clean); `registry_validator.validate_or_raise` green; `orchestrator_stack.py start --compile-registry` produces a byte-stable lean across re-runs (cache-key no-op); `stack_change_pipeline.py check` green.

Latest validation:

- 2026-06-27 orchestrator `c3ac153f`: `py_compile` for `src/registry/registry_compiler.py`, `scripts/server/stack_commands.py`, and `tests/unit/test_registry_compiler.py`; `pytest -q tests/unit/test_registry_compiler.py tests/unit/test_stack_manifest_imports.py` -> `62 passed`; `ruff check` and `git diff --check` on touched files pass.
- Scratch compile after alias expansion validates with `registry_validator.py`; it now keeps alias role records (`coder_escalation`, `worker_summarize`, `worker_math`, `toolrunner`) in `roles`, but master still lacks some corresponding `server_mode` alias records and still carries stale live facts. Do not enable default compile yet.

## Notes
Independent of the v6-iqk cutover — that ships on the lean-authoritative path. This is the cleanup that makes master authoritative again. ROI: eliminates the lean/master hand-sync drift class permanently.
