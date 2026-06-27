# Prompt-Construction & Sampling Determinism

**Created**: 2026-06-26
**Owner domain**: [routing-and-optimization-index.md](routing-and-optimization-index.md) · master row **N14**
**Status (2026-06-27)**: **DEPLOYED LIVE, attestation-green, COMMITTED (orchestrator `f4a8a3ca`, root docs committed) — D2 live-load probe found no think-loop/revert trigger, but D2 remains open for clean-window reliability/promotion; D3/D4 remain.**

## Current State

A determinism audit of the live orchestrator prompt/sampling path established: **prompt *construction* is deterministic; generation *sampling* was not.** The sampling gaps were deployed-fixed on 2026-06-26 (immediately after the v6+iqk cutover, N13). Stack reloaded (`architect_general` pid→3811260 with `--jinja`; `orchestrator` pid→3812248); `stack_change_pipeline check` → **all gates green, `runtime_attestation: ok`, acceptance: no-inference checks passed.**

**Verified deterministic (no action):** routing artifact `derived/stack_priors.yaml` fresh (7/7 source hashes), no `ORCHESTRATOR_USE_CHAT_COMPLETIONS_ROLES` override, no degraded fallback, template-family selection correct per role, static system prompts, no timestamp/random in builder path, RAG abandoned, `--jinja` inert on `/completion` (no double-templating).

## What landed (deployed + committed)

| # | Change | File(s) |
|---|--------|---------|
| 1–3 | Single `_apply_deterministic_sampling()` helper wired into **all 3** payload sites (`_build_payload` /completion, `_infer_chat_completions` non-stream :518, stream :1193): temperature precedence `acceleration.temperature` → **`generation_defaults.temperature`** (was silently dropped → accidental greedy 0.0) → `request.temperature`; pinned `seed` (fixed `_DETERMINISTIC_SAMPLING_SEED=42`, per-request override via `request.seed`); unified `top_k=40/top_p=0.95/repeat_penalty=1.1` across **both** endpoints (chat path previously sent none → server defaults) | `src/backends/llama_server.py`; `seed` field added to `src/inference/model_server.py` `InferenceRequest` |
| 4 | Removed `architect_general` jinja exclusion (`stack_priors.py:~1158`, was commit `0879ed56`); auto-enrolls it into the cc-set so it routes `/v1/chat/completions` where its registry `enable_thinking=false` (model_registry.yaml:493) fires. Recompiled `derived/stack_priors.yaml`. Verified: jinja=True, enable_thinking=False, cc-set 6→7 = {architect_general, coder_escalation, frontdoor, toolrunner, worker_general, worker_math, worker_summarize} | `src/registry/stack_priors.py` + `orchestration/derived/stack_priors.yaml` |

2026-06-27 no-inference hardening: orchestrator `ab75b5ae` adds regression
coverage for `_apply_deterministic_sampling()` through `_build_payload`,
locking `generation_defaults.temperature` precedence, the pinned default seed
`42`, per-request seed override, and shared `top_k`/`top_p`/`repeat_penalty`
defaults. This protects D1's deployed sampling contract; it does not close D2
or D3 because those remain clean-window live validation tasks.

## Outstanding tasks (priority-ordered)

- [x] **D1 — git commit** ✅ **DONE 2026-06-26** — orchestrator `f4a8a3ca` (llama_server.py, inference/model_server.py, registry/stack_priors.py, derived/stack_priors.yaml), root: this docs commit (docs). **Unpushed** — operator pushes manually.
- [ ] **D2 — J12 architect think-loop probe** *(Queue-2 quiesce window; REVERT-GATE for change #4)*. Change #4 is only safe if `enable_thinking=false` actually suppresses the Qwen3.5-122B hybrid `<think>`-loop (the 2026-04-15 `0879ed56` exclusion guarded a *confirmed* zero-content / 4096-tok "Wait, I found a reference" loop). Run the J12 probe ([bulk-inference-campaign.md](bulk-inference-campaign.md) Queue 2 / §J12): read the `answer` field, `max_turns>=4`, fixed non-truncating `max_tokens`, same tasks both arms. **This now validates a LIVE prod change, not just wiring** — if architect loops, revert change #4 (`stack_priors.py` jinja clause + recompile + reload architect without `--jinja`). Gate: architect +15pp or better (campaign J12 promotion gate). Frontdoor (same family, draft-mtp+jinja+nothink) is the working reference. Operator-run per `feedback_no_concurrent_inference`. 2026-06-27 live-load probe (not quiesce, AutoPilot T2 running) wrote `/mnt/raid0/llm/tmp/j12_architect_think_loop_probe_20260627T090826Z_summary.json` and JSONL. Result: frontdoor 15/15, architect 12/15 by coarse expected-match; **0 `<think>` leaks, 0 known wait-reference loops, 0 repetition-loop flags on both arms**. Architect had two HTTP 504s (`code_02`, `reason_02`) at the queue/deadline boundary under concurrent load, so no immediate revert is indicated, but D2 is not clean-window closed.
- [ ] **D3 — manual canonical bench (sampling quality cert)** *(clean window; certifies #1–3)*. Greedy→sampled(0.1–0.3)+seed shifts output behavior. Certify via P-BENCH canonical recipe (`bench_canonical.sh`/`canonical_recipe.py`) per `/workspace/MEASUREMENT.md`. **Co-schedule with the N13 v6-iqk post-reboot bench** — both want the same clean window.
- [ ] **D4 — sampling-quality instrument-era row** *(human-authored; AFTER D2+D3)*. The N13 kernel/AutoPilot-speed fence is now applied in orchestrator `dcd60332` (`E5-cpu-kernel`, `E5-autopilot-speed`, live AutoPilot `pareto_exclude_before_ts=2026-06-26T22:07:11Z`). The remaining D4 work here is the separate **sampling-determinism `autopilot_quality` boundary** after D2/D3, because greedy→sampled quality should not be certified until the architect revert-gate and canonical bench resolve. Its note should use DEMOTE-TO-PRIOR for pre-boundary quality numbers. `instrument_eras.yaml` remains a human-amendment surface (MEASUREMENT.md §4/§5).

## Dependency graph

```
D1 (commit) ── independent, do now
D2 (J12 probe) ──┐
                 ├──► D4 (era rows)   [don't certify a boundary that might revert]
D3 (canon bench)─┘
D2, D3 ── both want a quiesce/clean window → co-schedule with Queue-2 + N13 post-reboot bench
```

## Cross-cutting

- **vs N13 (v6-iqk):** this deployed immediately after the cutover; D3 and D4(a)=E5 share N13's clean-window + era-row closeout. Treat as one regime change for benching/era purposes.
- **vs J12 (campaign):** J12 "wiring" was closed 2026-06-12; change #4 makes architect the live consumer, so the Queue-2 J12 *probe* now has a concrete deployed arm to validate (revert-gate).
- **vs registry-compile-master-reconcile (N-deferred):** change #4 edits the *lean* `stack_priors.py` jinja computation; when master becomes authoritative (`--compile-registry` ON), carry the architect jinja change into master.

## Key file locations

- Sampler: `src/backends/llama_server.py` (`_apply_deterministic_sampling`, 3 call sites); request seed: `src/inference/model_server.py`.
- Routing gate: `src/registry/stack_priors.py:~1158` (jinja); `src/chat_completions_roles.py` (derivation gate jinja∧enable_thinking==False); `orchestration/derived/stack_priors.yaml` (recompile via `python3 -m src.registry.stack_priors`).
- Gates: `scripts/registry/stack_change_pipeline.py check` (uses `.venv/bin/python3`); `src/registry/registry_validator.py`.
- Lifecycle: `scripts/server/orchestrator_stack.py {reload,status}` (architect_general, orchestrator).

## Reporting

On closing a task: check the box here, update master row **N14** + the routing-index subsystem row, append to `progress/2026-06/`. On full closure (D1–D4 done): extract findings to wiki, move this handoff to `completed/`, delete N14. Memory: [[project_prompt_determinism_plan]], [[feedback_enable_thinking_requires_chat_completions_path]], [[feedback_stack_change_three_gates]].
