# Batched-Decode Measurement (E1/E2) + Conditional 8x8 GEMM SIMD (E3)

**Status**: IN PROGRESS — harness + non-decision-grade scout complete; Queue-2 commands are staged in the clean-window manifest; decision-grade E1/E2 still require a reboot/host-health window
**Created**: 2026-06-12
**Priority**: ACTIVE-HIGH — bench-only, ~1 day for E1+E2; rank 2 in the findings-06 "what remains" table; an evidence vacuum under the highest-volume workload (the eval harness)
**Spec**: [fable5-findings-06-kernel-and-concurrency.md](../completed/fable5-findings-06-kernel-and-concurrency.md) §2 (E1/E2/E3) + [MEASUREMENT.md](../../MEASUREMENT.md) P-BENCH-3 — read both before claiming any waypoint
**Related**: [bulk-inference-campaign.md](bulk-inference-campaign.md) (E1/E2 are quiesce-window Queue-2 items); [cpu-shape-specialized-gemv-decode.md](cpu-shape-specialized-gemv-decode.md) (E3 landing zone); [sarathi-serve-cpu-evaluation.md](sarathi-serve-cpu-evaluation.md) (its reopen gate may fire from these results); [within-role-placement-state-machine.md](within-role-placement-state-machine.md) (the multi-instance layer this complements); [cpu-inference-optimization-index.md](cpu-inference-optimization-index.md) (CPU14/CPU17/CPU18 rows)

## Why

Single-instance batched decode has never been measured: CPU14 was never run,
CPU23 deferred multi-stream interference "unless multi-tenant becomes
relevant" — and per findings-02/03 the dominant workload is now the eval
harness (4.6 h/day T1 + 1.3 h/day T0, 43 questions/trial) fanned out across
instances while `cont_batching` sits unexploited. CPU18's own reopen clause
names "eval pipelines"; the trigger has been satisfied for weeks. The batch>1
8x8 kernel body was never written (dispatcher falls back to scalar).

## Waypoints

- [ ] **E1 — CPU14 at last** (half day, quiesce window): one instance, `-np {1,2,4,8,16}`, fixed question batch, on (a) frontdoor Qwen3.6-A3B and (b) a dense control; measure aggregate tasks/hour + per-stream p50/p95 latency per MEASUREMENT.md P-BENCH-3. Acceptance: claims filed with protocol id + attest ref; saturation point identified per model.
- [ ] **E2 — eval-driver A/B** (half day, same window): one T1 eval (43 questions) against a single full instance with `-np 8` continuous batching vs the current 3-concurrent-across-quarters path; metric = wall-minutes/eval (= statistical power per day, per findings-01). Acceptance: the batch serving class is priced; keep-or-kill recommendation for an eval-batch instance set recorded.
- [ ] **E3 — 8x8 GEMM SIMD body** (days, CONDITIONAL): ONLY IF E1 shows intermediate batch leaves per-thread-BW unsaturated — write the AVX-512BW batch>1 GEMM body for the existing dispatcher slot (`arch/x86/repack.cpp:1563-1566`, currently scalar fallback), re-run E1. Work lands under [cpu-shape-specialized-gemv-decode.md](cpu-shape-specialized-gemv-decode.md). Acceptance: E1 delta with kernel on/off, canonical protocol.
- [ ] **E4 — conditional re-promotions** (doc-only first): if E1/E2 confirm the regime, re-promote CPU17 chunked-prefill (the 9.6× rep-1 TTFT amplification is the eval class's pathology) and CPU18 MegaBlocks per their own reopen clauses — both name "eval pipelines". Acceptance: index rows flipped with the E1/E2 evidence cited, or explicitly re-closed.

## Progress Notes

### 2026-06-14 — Harness + exploratory scout

Implemented `scripts/benchmark/server_np_sweep.py` in `epyc-inference-research` as the durable P-BENCH-3 harness:

- Launches one `llama-server` per cell with `-np N`, `-c 32768`, `-t 96`, `-ub 8192`, `--flash-attn on`, `--jinja`, `-ctk q8_0`, `-ctv q8_0`, `--mlock`.
- Uses a fixed deterministic tier-1 question-pool batch and writes selected qids, manifest, per-request JSONL, summary CSV, recommendations, server logs, and per-cell stop events.
- Refuses decision-grade runs when host-health preconditions fail unless `--allow-host-health-warning` is passed; the manifest then marks `decision_grade=false`.
- Verifies every launched server is dead with `ps -p` after SIGTERM/SIGKILL handling.

Smoke: `/mnt/raid0/llm/epyc-inference-research/data/batched_decode/smoke-server-np-sweep-20260614T1847Z` passed one frontdoor `-np 1` cell and verified server PID stopped.

Exploratory scout: `/mnt/raid0/llm/epyc-inference-research/data/batched_decode/exploratory-e1-pbench3-scout-20260614T1848Z` ran both required model+quant targets over `-np {1,2,4,8,16}` with 10 fixed tier-1 prompts and 64-token cap. **Not a claim**: host uptime was >1 week and `kernel.numa_balancing=0`, so the manifest records `decision_grade=false`.

Scout shape:

| Model+quant | Best scout `-np` | Tasks/hour | p95 latency | Notes |
|---|---:|---:|---:|---|
| Qwen3.6-35B-A3B Q8_0 (`qwen36_q8_0`) | 8 | 1816.37 | 19.4s | `-np 16` slightly regressed; aggregate gain from `-np 1` to `-np 8` was ~41%, but p95 rose ~3.8x. |
| Qwen3.6-27B Q8_0 dense control (`qwen36_27b_q8`) | 8 | 837.09 | 38.7s | Dense control scaled more strongly through `-np 8`; `-np 16` regressed and p95 reached ~50s. |

Next decision-grade E1 action: reboot or otherwise satisfy host-health policy, then rerun the same harness at the full fixed batch size (`43` prompts) and target token cap. Treat `-np 8` as the leading candidate but still rerun all N values because the scout was small and non-gating.

### 2026-06-19 — E2 coordinator ready; host-health still blocks claims

Implemented `scripts/benchmark/e2_eval_driver_ab.py` in `epyc-inference-research` commit `25caf78` as the durable E2 run-plan coordinator:

- Emits a two-arm manifest and `commands.sh` for the single full-instance `-np 8` continuous-batching arm plus the current EvalTower `AUTOPILOT_EVAL_CONCURRENCY=3` arm.
- Records P-BENCH-3 attestation, selected 43-question tier-1 prompt qids, primary artifact paths, and the keep-or-kill acceptance target.
- Fails closed by commenting runnable commands when host-health warnings are present; `--allow-host-health-warning` is an explicit scout-only override.

Validation: `uv run python -m py_compile scripts/benchmark/e2_eval_driver_ab.py scripts/benchmark/test_e2_eval_driver_ab.py`; `uv run --with pytest pytest -q scripts/benchmark/test_e2_eval_driver_ab.py` -> 3 passed; `uv run --with ruff ruff check scripts/benchmark/e2_eval_driver_ab.py scripts/benchmark/test_e2_eval_driver_ab.py`; dry-run manifest generation under `/tmp/epyc-e2-validate/e2-dry-validate` correctly produced `status=blocked decision_grade=false` because uptime, NUMA state, and existing llama processes violate the claim gate.

No decision-grade E2/E1 result was binned. Current host state still requires a clean host-health/reboot window before claim-grade P-BENCH-3 measurement. A direct-port RoPE scout against the resident frontdoor server was attempted as non-decision-grade resource utilization only, then stopped after 8/100 unparseable responses; no artifact was written and no result should be used.

Follow-up `epyc-inference-research` commit `74e580e` added the no-inference result summarizer:
`e2_eval_driver_ab.py --summarize-run <run_dir>` reads the batch arm `summary.csv` plus the current
EvalTower `current_quarters.jsonl`, computes wall-minutes/eval and
`speedup_current_over_batch`, and emits `summary.json` with
`keep_candidate` / `kill_candidate` / `scout_only` / `incomplete` status. Non-decision-grade manifests
stay `scout_only`, so the summarizer cannot accidentally promote host-health-warning data into a
production keep/kill claim.

### 2026-06-20 — Queue-2 clean-window manifest wiring

Research `7d2dade` added E2/E1 entries to the tracked clean-window plan:
`docs/data/clean_window_measurement_manifest.json` now has `27` total entries,
`21` ready, and `6` blocked under the observed live port/context constraints,
and `docs/data/clean_window_measurement_commands.sh` includes:

- E2 plan generation:
  `uv run --extra benchmark python scripts/benchmark/e2_eval_driver_ab.py --run-id "$run_id" --prompt-limit 43 --prompt-seed 42 --tier 1 --batch-np 8 --current-concurrency 3`
- E1 decision-grade sweep command:
  `uv run --extra benchmark python scripts/benchmark/server_np_sweep.py --run-id "$run_id" --prompt-limit 43 --prompt-seed 42 --tier 1 --np-levels 1,2,4,8,16`

The E2 command is intentionally a no-inference run-plan generator; it writes the
fresh attested E2 manifest and arm-level `commands.sh`. A smoke against
`/mnt/raid0/llm/tmp/e2_plan_smoke/` during the active AutoPilot window produced
`status=blocked decision_grade=false` with host-health warnings for uptime, NUMA
state, and existing llama processes, proving the planner still fails closed for
claim-grade evidence. No decision-grade E1/E2 result was binned.

Follow-up orchestrator `4bbf1163` added the missing no-inference worker-process
attestation step for the Queue-2 reload. `docs/reference/stack-change-launch-runbook.md`
now pairs the existing `attest_flags.py` feature-state check with
`scripts/validate/attest_orchestrator_workers.py`, which discovers API worker
PIDs through `/config/attest` and reads only requested keys from
`/proc/<pid>/environ`. Live read-only checks at the documented poll budget saw
all six API workers with no feature diffs and no env diffs for the declared
Queue-2 contract (`specialist_routing=true`, `model_fallback=true`, dormant
wave-2 features off, cross-role/placement/reverse-migration/URE/structured-output
process env present). This does not satisfy the host-health/reboot gate for
decision-grade E1/E2; it closes the reload/attestation runbook gap before that
window.

## Gates & pitfalls

- Operator window required: per `feedback_no_concurrent_inference` / `feedback_speed_verify_via_llama_bench`, the operator runs the benches — this handoff prepares commands, harness, and analysis; schedule inside the bulk-campaign Queue-2 quiesce window (one attested reload serves all).
- Do NOT over-extrapolate A3B wins: MoE batching is weaker than dense (distinct tokens hit distinct experts → expert weight traffic grows with batch) — hence the mandatory dense control in E1.
- The 9.6× rep-1 TTFT amplification under concurrent prefill (CPU23) is real; report TTFT separately from steady-state per-stream decode or E2 will look better than it serves.
- Index results by model+quant, never by role (`feedback_model_not_role_indexing`); P-BENCH-3 preconditions (host-health tier, no concurrent inference, interleave re-warm) are binding.
- E3 before E1 is forbidden — the kernel only gets written if the measurement shows compute headroom at intermediate batch.

## Reporting

Tick waypoints here + one-line progress entry per session; on full completion delete the master-index row and move this file to `completed/`; every number follows the [MEASUREMENT.md](../../MEASUREMENT.md) claim grammar (metric, protocol-id, n, date, attest ref).
