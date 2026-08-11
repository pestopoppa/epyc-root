# Batched-Decode Measurement (E1/E2) + Conditional 8x8 GEMM SIMD (E3) + NUMA×batch (E5)

> ## ⛔ SUSPENDED PENDING RE-MEASUREMENT (2026-07-30)
>
> **Scope: all E5 (NUMA×batch) throughput results** — the 31-cell Stage-B sweep of
> 2026-07-29/30 and the 69-cell W0 scout, which swept the same placement shapes through the
> same harness. A wiring defect in the shapes under test makes every absolute throughput
> value and every cross-cell ranking below unusable. **Re-measurement on the corrected
> placement is IN PROGRESS.**
>
> **Root cause.** The swept shapes inherit the current production wiring's NUMA defect:
> `stack_numa.py:66-67` defines `NUMA_NODE0 = "0-47,96-143"` and
> `NUMA_NODE1 = "48-95,144-191"`, each of which **straddles a pair of NPS4 nodes**, and
> launches them **without `numactl --interleave`**. This host is NPS4 —
> `node0 = 0-23,96-119`, `node1 = 24-47,120-143`, `node2 = 48-71,144-167`,
> `node3 = 72-95,168-191` — so a "half-machine" cpuset spans two nodes while the weights
> first-touch onto whichever node loads them, and every thread on the other node pays a
> remote-access penalty on every weight read. The E5 affinity artifact for this shape
> recorded `pages_by_node {N0: 9226101} / total 9226101` — all 35.2 GiB resident on node0
> while the thread team spanned node0+node1. **`numactl --interleave` binds at FIRST TOUCH
> only**, so it is a silent no-op against a warm page cache; that is why the defect
> survived casual checking, and why a warm re-test appears to "confirm" the bad number.
>
> **Measured 2026-07-30** — `llama-bench` tg128, no speculative decoding,
> `Qwen3.6-35B-A3B-MTP-Q8_0` (the frontdoor model):
>
> | placement | page cache | tok/s |
> |---|---|---:|
> | straddling cpuset, no interleave — **= CURRENT PRODUCTION wiring** | warm | **7.81 ± 3.82** |
> | straddling cpuset, no interleave | cold | 10.28 |
> | straddling cpuset **+ interleave**, `-t 96` | cold | 15.35 |
> | **full machine `taskset -c 0-95` + `numactl --interleave=all`, `-t 96`** | cold | **23.43 ± 0.07** |
>
> The winner is the canonical bench recipe, and it beats the wiring E5 measured through by
> **3.0×** — Stage-B priced the frontdoor model at roughly **one third of its true speed**.
> With MTP speculative decoding ON at that winning placement, single stream measures
> **36-39 tok/s**, independently matching the AutoPilot production anchor
> (`median_request_tps` median **35.7**, n=154, band 35-40).
>
> **Instrument validated; alternative explanations ruled out.** A single-NPS4-node arm
> (24 physical cores, `-t 48`) measured **8.80** tok/s against the registry-documented
> **8.90** — a 1% match, so the measuring instrument is sound and the defect is in the
> wiring under test, not the meter. Ruled out as causes: a v8 kernel regression (v7 and v8
> both measure **9.76**, identical); iqk (it never engages for Q8_0 — gated behind an unset
> `GGML_IQK_Q8_0`); MTP head overhead; and mmap page-faulting.
>
> ### SUSPENDED — do not cite, do not gate on
>
> - **ALL absolute throughput values** — tok/s, tasks/hour, aggregate rates — in every E5
>   results block below.
> - **ALL cross-cell rankings.** Every cell was bandwidth-bound under the defect, and the
>   penalty scaled with how many NUMA nodes each shape's cpuset straddled — so the ranking
>   measures the defect, not the shapes. Per the Stage-B config grid below, `C1`/`C1b` for
>   `qwen36_q8_0` and `qwen3_next_80b` are the straddling halves, while `C2`/`C3` are the
>   `NUMA_Q*` quarters, which are exactly the four NPS4 nodes and therefore node-local.
>   The shapes were not penalised alike.
> - **RETRACTED: the Stage-B headline "C3 (four quarters) loses at every clean iso-T rung"**
>   — and, on the same grounds, W0's opposite "C3 quarters aggregate-optimal for EVERY
>   model". Neither direction is established.
> - **RETRACTED: the per-model "winning shape" reads** ("35B wants one half, gemma one full
>   machine + interleave, 80B two node-local halves"). The 35B recommendation names the
>   defective straddling half specifically, which today's numbers contradict directly
>   (7.81 warm vs 23.43 at full machine + interleave).
> - Note for the re-run: for `qwen36_q8_0` and `qwen3_next_80b` the shape that actually won
>   today — full machine `0-95` + `--interleave=all` — **was not in the Stage-B grid at
>   all**; it appeared only as gemma's `C1`. The corrected grid must include it per model.
>
> ### SURVIVES — still valid, NOT suspended
>
> - The **0.0% error rate on every cell** (31/31 Stage-B, and the W0 cells). An error-rate
>   read does not depend on memory bandwidth.
> - Every **harness defect fix** landed during the campaign: throttle-gate cpuset scoping
>   (`98cfff44`), the never-emitted `--reasoning` flag (`5d6a17f2`), `find_llama_processes`
>   identifying by `/proc/<pid>/exe` (`4a5b6bc7`), and the undeclared `httpx` dependency
>   (`040a2ad7`).
> - The **protocol / manifest / attestation machinery itself** — pre-registered cell grids,
>   the affinity-preflight hard gate, the capture contract, and the deterministic-replay
>   ledgers. The instrument is reusable as-is for the re-measurement.
>
> **Not covered by this notice**: the 2026-07-03 / 2026-07-06 **E1/E2** tables further below
> are a separate single-instance campaign, already demoted to pre-v7 historical priors.
> Their placement has not been audited against this defect and no claim either way is made
> here.
>
> Per [MEASUREMENT.md](../../MEASUREMENT.md) the suspended numbers are **retained verbatim
> and annotated — never edited, never deleted** (append-only). Each affected block below
> carries an inline `⛔ SUSPENDED 2026-07-30` marker.

**Status**: IN PROGRESS — A3B E1 and E2 decision-grade evidence landed 2026-07-03; E2 is a keep-candidate for an eval-batch serving class; shadow metadata/feature-gate, default-off warm eval-batch frontdoor hook, guarded activation probe, and plan-only/apply activation-window runners landed; 2026-07-05 activation window smoked through and rolled back cleanly; dense-control E1 tail completed 2026-07-07 as useful but not pristine host-exclusive evidence · **E5 (NUMA×batch interaction sweep) added 2026-07-20 — runs LAST in the post-v7-promotion queue: inference-batch-loop → architect-model-selection-bench → this.** · **⛔ 2026-07-30: all E5 throughput results (Stage-B + W0) SUSPENDED pending re-measurement on the corrected placement — see the suspension notice above.**
**Created**: 2026-06-12
**Priority**: ACTIVE-HIGH — bench-only, ~1 day for E1+E2; rank 2 in the findings-06 "what remains" table; an evidence vacuum under the highest-volume workload (the eval harness)
**Spec**: [fable5-findings-06-kernel-and-concurrency.md](../completed/fable5-findings-06-kernel-and-concurrency.md) §2 (E1/E2/E3) + [MEASUREMENT.md](../../MEASUREMENT.md) P-BENCH-3 — read both before claiming any waypoint
**Related**: [bulk-inference-campaign.md](bulk-inference-campaign.md) (E1/E2 are quiesce-window Queue-2 items); [cpu-shape-specialized-gemv-decode.md](cpu-shape-specialized-gemv-decode.md) (E3 landing zone); [sarathi-serve-cpu-evaluation.md](sarathi-serve-cpu-evaluation.md) (its reopen gate may fire from these results); [within-role-placement-state-machine.md](within-role-placement-state-machine.md) (the multi-instance layer this complements); [inference-research-index.md](inference-research-index.md) (CPU14/CPU17/CPU18 rows)

## Why

Single-instance batched decode has never been measured: CPU14 was never run,
CPU23 deferred multi-stream interference "unless multi-tenant becomes
relevant" — and per findings-02/03 the dominant workload is now the eval
harness (4.6 h/day T1 + 1.3 h/day T0, 43 questions/trial) fanned out across
instances while `cont_batching` sits unexploited. CPU18's own reopen clause
names "eval pipelines"; the trigger has been satisfied for weeks. The batch>1
8x8 kernel body was never written (dispatcher falls back to scalar).

## Waypoints

- [x] **E1 — CPU14 at last** (half day, quiesce window): one instance, `-np {1,2,4,8,16}`, fixed question batch, on (a) frontdoor Qwen3.6-A3B and (b) a dense control; measure aggregate tasks/hour + per-stream p50/p95 latency per MEASUREMENT.md P-BENCH-3. Acceptance: claims filed with protocol id + attest ref; saturation point identified per model. **2026-07-03 update**: A3B arm is complete and decision-grade. **2026-07-07 update**: dense-control tail completed at `epyc-inference-research/data/batched_decode/e1-pbench3-dense-control-iqk-20260707T022917Z/` after aborting the missing-IQK attempt. All `qwen36_27b_q8 -np {1,2,4,8,16}` cells completed `43/43` with `0` errors; tasks/hour scaled `20.11 -> 124.62`, aggregate predicted t/s `1.07 -> 6.81`, and p95 latency rose `240.9s -> 674.0s`. The MI210 server remained live, so treat the dense-control tail as useful evidence, not pristine host-exclusive decision evidence. ✅ 2026-07-07
- [x] **E2 — eval-driver A/B** (half day, same window): one T1 eval (43 questions) against a single full instance with `-np 8` continuous batching vs the current 3-concurrent-across-quarters path; metric = wall-minutes/eval (= statistical power per day, per findings-01). Acceptance: the batch serving class is priced; keep-or-kill recommendation for an eval-batch instance set recorded. **2026-07-03 update**: orchestrator `7cb71a4e` landed the default-off `eval_batch_serving` feature flag plus explicit EvalTower request metadata (`workload_class=eval_batch`, shared batch id, background priority). Orchestrator `e9312a17` then added the default-off warm `eval_batch_frontdoor` serving hook on port `18070`; orchestrator `276a1eef` added the guarded preflight/smoke probe. The 2026-07-04 follow-up adds `scripts/benchmark/eval_batch_serving_activation_window.py`, a plan/apply/rollback wrapper that starts only `eval_batch_frontdoor`, reloads the API with `ORCHESTRATOR_FEATURE_EVAL_BATCH_SERVING=1`, runs the smoke probe, and rolls back unless `--keep-enabled` is explicit. **2026-07-05 update**: the activation window completed as `status=smoke_passed_rolled_back`; `eval_batch_frontdoor` launched on port `18070`, API workers attested `eval_batch_serving=true` during probe, the smoke answer was `ok`, the tap hit expected port `18070`, and rollback disabled the feature + stopped `eval_batch_frontdoor`. Activation now has decision-grade evidence; representative quality/eval telemetry is the next remaining gate before any default EvalTower path change.
- [x] **E2 — eval-tower window runner** (same lane): `scripts/benchmark/eval_batch_serving_evaltower_window.py` now packages the compare-and-rollback loop for the current EvalTower arm versus the temporary eval-batch arm. Default mode is plan-only; live mutation requires `--apply --confirm-clean-window`, active AutoPilot blocks by default unless `--allow-autopilot-active` is explicit, and the resulting evidence is non-decision-grade in that case. The runner calls the existing activation helpers, rolls back unless `--keep-enabled` is requested, and writes JSON/MD outputs under `orchestration/reports/eval_batch_serving_evaltower_<timestamp>/`. Tests landed in `tests/unit/test_eval_batch_serving_evaltower_window.py`; validation passed with `uv run pytest -q tests/unit/test_eval_batch_serving_activation_window.py tests/unit/test_eval_batch_serving_evaltower_window.py` (`12 passed`), `uv run ruff check scripts/benchmark/eval_batch_serving_evaltower_window.py tests/unit/test_eval_batch_serving_evaltower_window.py`, and `python3 -m py_compile ...`. Plan-only smoke wrote `/mnt/raid0/llm/tmp/evalbatch-evaltower-plan-smoke-2/summary.json` with `status=plan_only`, `applied=false`, `decision_grade=false`, `autopilot_active=true`, 3 activation commands, and 2 rollback commands.
- [x] **E3 — 8x8 GEMM SIMD body** (days, CONDITIONAL): **NO-GO / CLOSED for now**. 2026-07-18 zero-inference decision: E1/E2 show a serving/topology win, not per-thread compute headroom, and the newer CPU roofline classifies decode-side SIMD/ALU work as bandwidth-killed. Do not write the AVX-512BW batch>1 GEMM body unless a future counter run contradicts the roofline. ✅ 2026-07-18
- [x] **E4 — conditional re-promotions** (doc-only first): **PARTIAL REOPEN TO MEASUREMENT ONLY**. 2026-07-18 zero-inference decision: CPU17/Sarathi reopens only to the long-prompt mid-stream TBT measurement gate because eval-batch is the named workload class; CPU18/MegaBlocks remains gated pending evidence that padding/capacity-factor cost is material. ✅ 2026-07-18
- [ ] **E5 — NUMA×batch interaction sweep** (post-v7-promotion quiet window; the never-measured 2D cross). NUMA-split and `-np` batching have only ever been measured **separately** — NUMA-split built the pinning map; `-np` alone is E1 (single instance). **Hypothesis (roofline):** batching amortizes the per-token weight-read → shifts CPU decode **BW-bound → compute-bound** → the NUMA-locality advantage may **flip at high K**; the crossover in K is unknown and sets the slot-fabric grid shape. Directly tests whether **a single full-machine high-`-np` server beats quarter-batched servers**. **Protocol (reuse the E1 `-np` harness + P-BENCH-3):** per-model 2D grid — **N = each model's *allowed* NUMA-pinned configs** (from `scripts/server/stack_numa.py` `NUMA_CONFIG` + the safe-placement table in [within-role-placement-state-machine.md](within-role-placement-state-machine.md); e.g. frontdoor `{1×half},{2×half},{4×q}` — full+quarter mixes excluded per the 2026-07-21 mode-exclusivity contract [refreshed 2026-07-23, audit C4; the original `{full,q3}`-style mixed examples are superseded]; worker_general `{1×full},{4×q}`; architect 122B out of E5 scope — see the 2026-07-23 design section) × **K = `-np ∈ {1,2,4,8,16,32}`**. Two reads: **(i) iso-concurrency** — hold total in-flight = N×K fixed (e.g. 32) and vary the split (`1×32` vs `2×16` vs `4×8` where safe-placement allows) → the direct "one big batched server vs quarter-batched" answer; **(ii)** unconstrained **peak-aggregate (N,K)**. **Metrics:** aggregate decode t/s **and** per-stream p50/p95 latency (P-BENCH-3), paired with a correctness/garbage check; era-stamped, protocol-id + attest ref. **Canonical recipe only:** OMP env stack, `scripts/server/affinity_preflight.py` **live-affinity verify per instance** (the WP-6 bad-affinity artifact is the cautionary tale), per-instance cache warming (drop_caches NUMA re-read trap), throttle check, host-health gate (uptime / `numa_balancing=0`). **Models:** `qwen36_q8_0` (frontdoor 35B-A3B) + `qwen36_27b_q8` (dense control) — both already in the E1 harness — + gemma `worker_general`. **Decides:** the (N,K) provisioning per model for the slot fabric + whether **workload-class lanes** are real (a low-K/high-K crossover). **Feeds** [within-role-placement-state-machine.md](within-role-placement-state-machine.md) per-instance `-np` sizing and [heterogeneous-slot-fabric-residency.md](heterogeneous-slot-fabric-residency.md) (provisioning-pending). **Gating:** post-v7-promotion; runs **LAST in the post-promotion queue** — `inference-batch-loop → architect-model-selection-bench → this` — operator/quiet-window, P-BENCH-3 host-health. Bench-only.

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

### 2026-07-03 — Clean-window A3B E1 + E2 keep-candidate

Decision-grade quiet-window measurement landed after pausing AutoPilot cleanly,
stopping the CPU stack, fixing the P-BENCH-3 host-health NUMA check to match the
canonical `kernel.numa_balancing=0` policy, and restarting the stack afterward.
AutoPilot resumed at trial counter `1095` after the measurement window.

E1 A3B artifact:
`/mnt/raid0/llm/epyc-inference-research/data/batched_decode/e1-pbench3-clean-20260703T1912Z/`.
The completed `qwen36_q8_0` rows are decision-grade (`host_health_warnings=[]`,
no pre-existing llama processes, governors `performance`, NUMA balancing `0`):

| `-np` | success | tasks/hour | aggregate predicted t/s | p50 latency | p95 latency |
|---:|---:|---:|---:|---:|---:|
| 1 | 43/43 | 577.97 | 21.26 | 7.04s | 12.31s |
| 2 | 43/43 | 839.08 | 28.88 | 2.76s | 17.95s |
| 4 | 43/43 | 796.31 | 27.28 | 4.70s | 38.81s |
| 8 | 43/43 | 799.03 | 27.50 | 13.53s | 66.17s |
| 16 | 43/43 | 846.72 | 29.14 | 23.17s | 109.69s |

Interpretation: throughput saturates early for the A3B eval primitive; `-np 2`,
`-np 8`, and `-np 16` are all close on aggregate throughput, while tail latency
rises sharply after `-np 2`. The mandatory dense-control manifest entry did not
complete: `qwen36_27b_q8 -np 1` was stopped before a summary row after diagnostic
logs showed about `0.59` generated tok/s on long responses. Treat the dense
control as unresolved and do not use this artifact as a complete dense-control
E1 result.

E2 artifact:
`/mnt/raid0/llm/epyc-inference-research/data/batched_decode/e2-pbench3-clean-20260703T1940Z/`.
The generated A/B summary is decision-grade and records `status=keep_candidate`:

- batch arm: single full `qwen36_q8_0` server with `-np 8`, 43/43 successes,
  `135.479s` wall time, `2.258` wall-minutes/eval, `1142.61` tasks/hour,
  `0.0` error rate, p95 `49.01s`.
- current arm: live EvalTower fan-out with `AUTOPILOT_EVAL_CONCURRENCY=3`,
  `658.193s` wall time, `10.970` wall-minutes/eval, quality `2.233`,
  reliability `1.000`, aggregate speed `43.867` t/s.
- comparison: batch arm is `4.858x` faster by wall-minutes/eval.

Next action: add the actual dedicated eval-batch serving endpoint/launcher shape
and guarded execution hook behind the already-landed `eval_batch_serving` flag,
then re-run representative quality/eval telemetry before changing the default
AutoPilot eval path. E3 remains conditional: do not start the 8x8 GEMM SIMD body
solely from this result; the A3B E1 table shows throughput saturation but the
winning E2 wall-time result is primarily a serving/topology opportunity.

### 2026-07-03 — Eval-batch metadata gate

Orchestrator `7cb71a4e` landed the first conservative A7 hook stage without
changing evaluator execution:

- `src/features.py` declares `eval_batch_serving`, default-off in both tests and
  production, exposed through the existing runtime flag/config attestation path.
- `scripts/autopilot/eval_tower.py` stamps each `_eval_batch()` with one shared
  `evaltower-<label>-<timestamp>-<n>q` id and sends requests through
  `call_orchestrator_forced()` with `request_priority=background`,
  `workload_class=eval_batch`, and `batch_id=<shared id>`.
- `scripts/benchmark/seeding_orchestrator.py` accepts optional
  `request_priority`, `workload_class`, and `batch_id` fields while preserving
  legacy background-priority behavior for existing callers.

GitNexus impacts before edit: `call_orchestrator_forced` HIGH
(`impactedCount=17`, `processes_affected=4`) and `EvalTower._eval_batch` HIGH
(`impactedCount=24`, `processes_affected=1`), so the main thread handled it.
Validation: `102 passed` for the focused seeding/EvalTower/features/runtime flag
slice, focused Ruff clean, py_compile clean, and `git diff --check` clean.

At that checkpoint, EvalTower still did **not** route to a single `-np 8`
server. The follow-up hook below adds the missing endpoint/launcher surface but
keeps it default-off pending explicit activation and representative telemetry.

### 2026-07-03 — Default-off eval-batch frontdoor hook

Orchestrator `e9312a17` landed the second conservative A7 hook stage. It
creates a deployable test hook for the E2 batch-serving shape while keeping the
normal hot stack and default AutoPilot eval path unchanged:

- `scripts/server/stack_manifest.py` and `stack_numa.py` define a launcher-only
  warm role, `eval_batch_frontdoor`, on port `18070`, using frontdoor-family
  model/runtime settings with an `-np 8`, `-c 32768`, `-t 96`, `-ub 8192`, q8 KV,
  flash/Jinja/mlock serving shape.
- `scripts/server/orchestrator_stack.py` adds a scoped
  `eval_batch_frontdoor` command builder. The command uses embedded Qwen NEXTN
  speculative decoding and omits `-md` when the draft path resolves to the same
  GGUF as the target, preserving the CPU self-draft duplicate-load fix.
- `scripts/server/stack_commands.py`, `src/registry/registry_compiler.py`, and
  `src/registry/model_descriptors.py` keep the warm hook out of normal hot
  starts and generated active-role descriptors.
- `src/api/routes/chat_pipeline/routing.py` adds a default-off,
  request-scoped rewrite: when `eval_batch_serving` is enabled, a request is
  real-mode eval-batch traffic, no explicit `server_urls` override is present,
  and the configured eval-batch endpoint is healthy, frontdoor-family roles are
  routed to the eval-batch endpoint for that request only.

GitNexus impacts for the edited launch/routing surfaces were LOW after the
prior metadata stage. Validation: py_compile on all touched server/registry/API
files; `187 passed` across `test_registry_compiler.py`,
`test_stack_manifest_imports.py`, `test_build_server_command_helpers.py`, and
`test_pipeline_routing.py`; focused Ruff/syntax checks; `git diff --check`.

This is still not a production flip. Next action is a coordinated activation
window: warm-start `eval_batch_frontdoor`, reload the API with
`ORCHESTRATOR_FEATURE_EVAL_BATCH_SERVING=1` and
`ORCHESTRATOR_EVAL_BATCH_FRONTDOOR_URL=http://localhost:18070`, then collect
representative EvalTower quality/reliability/throughput telemetry before
changing defaults.

### 2026-07-03 — Eval-batch serving probe harness

Orchestrator `276a1eef` added
`scripts/benchmark/eval_batch_serving_probe.py`, a guarded activation probe for
the default-off eval-batch serving lane:

- default mode is read-only preflight: check orchestrator `/health`, check warm
  `eval_batch_frontdoor` `/health`, sample `/config/attest` for
  `eval_batch_serving`, detect active AutoPilot, and emit the exact activation
  commands.
- `--smoke --confirm-clean-window --require-enabled` sends one real
  `/chat` request with `workload_class=eval_batch`, background priority, shared
  `batch_id`, and direct frontdoor routing, then verifies the structured
  inference tap hit port `18070`.
- smoke refuses active AutoPilot by default; `--allow-autopilot-active` is
  explicit non-claim-grade load telemetry only.

Live no-inference preflight artifact:
`/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/eval_batch_serving_probe_live_preflight_20260703T234518Z/summary.{json,md}`.
It is `status=blocked`, `decision_grade=false`: orchestrator API health is OK,
AutoPilot is active, sampled API workers have `eval_batch_serving=false`, and
the warm endpoint is absent (`eval_batch_frontdoor health is not OK`). This is
the expected default-off state.

Next activation command:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/benchmark/eval_batch_serving_activation_window.py --apply --confirm-clean-window
```

Default behavior is plan-only. The live 2026-07-04 plan artifact at
`/mnt/raid0/llm/tmp/eval_batch_activation_plan_live/summary.{json,md}` confirms
the expected blocked/default-off state while AutoPilot is active: API healthy,
AutoPilot active, eval-batch flag disabled, and port `18070` absent. Use
`--keep-enabled` only if the activation smoke passes and the operator wants to
leave the lane enabled for representative EvalTower telemetry.

### 2026-07-05 — Eval-batch activation smoke passed, then rolled back

The activation window on `epyc-orchestrator` commit `132c595d` completed with
`status=smoke_passed_rolled_back` and `decision_grade=true`. The dedicated
`eval_batch_frontdoor` service came up on port `18070`, sampled API workers
attested `eval_batch_serving=true`, the smoke response was `ok`, and the
structured tap confirmed traffic on `18070`. The follow-up rollback disabled
the feature and stopped `eval_batch_frontdoor`, so the live default path stayed
unchanged.

This closes the activation/rollback deliverable for E2. The handoff stays open
for representative quality, reliability, and throughput telemetry before any
default EvalTower path change, while E1 dense-control remains unresolved and E3
still depends on the E1 result.

### 2026-07-06 — P-BENCH-3 sweep checkpoint

The clean-window sweep `e1-pbench3-20260706T1529Z` completed the full
`qwen36_q8_0` ladder (`np=1,2,4,8,16`) and wrote `summary.csv` before the
`qwen36_27b_q8` dense-control tail was intentionally interrupted. The 35B arm
is decision-grade and shows the expected throughput/latency tradeoff:

- [x] `qwen36_q8_0` P-BENCH-3 ladder complete (`np=1,2,4,8,16`) ✅ 2026-07-06
- [x] `qwen36_27b_q8` dense-control rerun completed at `e1-pbench3-dense-control-iqk-20260707T022917Z`; missing-IQK attempt marked aborted. ✅ 2026-07-07

| `-np` | success | tasks/hour | aggregate predicted t/s | p50 latency | p95 latency |
|---:|---:|---:|---:|---:|---:|
| 1 | 43/43 | 533.72 | 19.63 | 7.50s | 13.66s |
| 2 | 43/43 | 569.69 | 19.61 | 4.54s | 28.32s |
| 4 | 43/43 | 642.99 | 22.03 | 5.40s | 47.12s |
| 8 | 43/43 | 697.21 | 24.00 | 14.08s | 76.04s |
| 16 | 43/43 | 860.45 | 29.62 | 23.86s | 115.95s |

The 27B dense-control run reached the long-tail decode phase at `np=1` and was
then stopped so the quiet window could be returned to the operator. That keeps
the dense-control status explicit instead of implicitly treating the sweep as
fully complete. The stack was restored afterward and is back in `STACK READY`
state.

### 2026-07-23 — E5 harness preparation (design-only, zero inference; WP-12 worktree session side quest)

Full sweep design prepared per the E5 waypoint; no code written (the harness
lives in `epyc-inference-research/scripts/benchmark/`, outside this session's
write scope) and no inference run. Everything below is mechanically executable
by the implementing session + operator.

**Cell grid (pre-registered; 2026-07-23 operator review folded in — 2×half
added as the whole-machine provisioning candidate).** Indexed by model+quant,
never role. Configs per model (shapes from `NUMA_CONFIG`; bench ports 19xxx to
avoid any prod collision):

| Model | C1 (1×half) | C1b (2×half, one per NUMA node) | C2 (2×q, q2+q3 — mechanism probe) | C3 (4×q) |
|---|---|---|---|---|
| `qwen36_q8_0` (35B-A3B Q8, ~37 GB/inst) | half0 `0-47,96-143` ×96t | + half1 `48-95,144-191` ×96t | 2×48t | 4×48t |
| `qwen36_27b_q8` (dense control, ~29 GB) | shape UNRESOLVED for dense — scout runs 1×half0 vs 1×full-machine `0-95` at K∈{1,8}; Stage-B C1 adopts the winner (full-machine rows double as E1 continuity anchors) | + half1 ×96t | 2×48t | 4×48t |
| `qwen3_next_80b` ingest arm (~45 GB; W4, operator-added 2026-07-23) | half0 ×96t | + half1 ×96t | — | 4×48t |
| `gemma4-26B-A4B Q4_K_M MTP` (~16 GB) | full `0-95` ×96t + `numactl --interleave=all` — NO half shape (half-pinning crashes the MTP draft path, `tensor buffer not set`) | — | — (scout-only) | 4×48t |

Notes: (0) **Config-list semantics**: C1/C1b/C2/C3 are ALTERNATIVE serving
configs for one model, swept as separate cells — never co-deployed. C1 is a
provisioning CANDIDATE + E1-continuity anchor (audit C4 relabel: the realized
stack is QUARTERS-only — **C3 is the status-quo production shape**; gemma's
1×full is DISABLED by placement_policy=full_disabled; the solo big shape C1
describes serves nowhere today). Every anchor cell still means the model's
TOP optimized production recipe on that shape (full spec-dec stack; "anchor"
NEVER means an unoptimized baseline, per the 2026-07-23 operator directive).
C1 also remains the denominator of the scaling read C1@K vs C1b@K ("does
adding the second node-local half double aggregate?"). (i) The "1×big" shape is
**MODEL-SIZE-DEPENDENT**, not universal: for ~35B-class A3B MoE the half wins
(April 2026-04-17 head-to-head, NODE0-local 27.06 t/s vs
full-machine+interleave 26.60 t/s — cache locality beats channel
parallelism), while the 122B architect legitimately takes the full machine
(Probe B 2026-05-04: 1×full+interleave 12.19 t/s vs 4.3 t/s/instance split —
NOTE these are pre-E7-era, pre-NEXTN-self-draft figures cited for SHAPE
DIRECTION only, hypothesis grade per MEASUREMENT.md, never throughput
references; the current architect top spec includes the v6 NEXTN recipe).
Hence the dense-control C1 shape is treated as unresolved (scout decides),
and the architect stays OUT of E5 scope: the waypoint's model list excludes
it, architect-model-selection-bench runs BEFORE E5 and may swap the model,
and its 1×full-vs-4×per-node question already has era-labeled prior data
(12.19 vs 16.86 t/s aggregate, registry reopen note) — optional W5 only on
operator request, at the then-current architect model's top spec.
(ii) `NUMA_CONFIG` has no half1 instance for the frontdoor/ingest families —
the harness SYNTHESIZES the `48-95,144-191`×96t shape on bench ports only; no
prod cpuset changes, no §H recert trigger. (iii) **CORRECTED 2026-07-23 (lineup-dossier archaeology)**: the C1b
half-pair co-run HAS been measured once — the 2026-05-26 operator-requested
DUAL-HALF experiment (certified affinity, halves at 8073/8074/8075) came out
**negative across all three roles** (co-run ratios frontdoor 0.455 / ingest
0.524 / vision 0.541 ≈ each half halves under concurrency → aggregate ≈
serial; mechanism: two 48c halves contend on the memory channels serving the
shared mmap'd weight pages, exactly why 24c quarters scale and halves don't;
`progress/2026-05/2026-05-26.md:844-849`, reverted same day, never standing
config). Pre-v7-era ⇒ **direction-only prior** under E6-cpu-kernel — E5
still measures C1b (kernel + model era changed), but the scout should probe
C1b EARLY and prune hard if the ~0.5 co-run signature reappears; the
provisioning-candidate framing should not presume C1b is live until it beats
this prior. WP-9's actual mixed pair (frontdoor-half0 + ingest-half1,
different models) remains its own §H contention-matrix cell at the lineup
event.

K = per-instance `-np`, capped so total in-flight ≤ 43 (the fixed P-BENCH-3
prompt batch): C1 × {1,2,4,8,16,32}; C1b/C2 × {1,2,4,8,16}; C3 × {1,2,4,8}.

**Stage-B decision-grade set per model (~13 cells):** two pre-registered
comparison families —
- **Whole-machine provisioning (the E5 decision):** iso-T pairs {C1b@T/2 vs
  C3@T/4} for T ∈ {8,16,32} — "two big node-local batched servers vs four
  quarter-batched servers" at equal in-flight;
- **Half-machine mechanism (roofline flip):** iso-T pairs {C1@T vs C2@T/2}
  for T ∈ {16,32} — identical 48-core resource split 1-way vs 2-way, the
  purest NUMA-locality-vs-batch-amortization read;
plus scaling-efficiency pairs {C1@K vs C1b@K} at K ∈ {4,8} (does the second
node-local half double aggregate — the half-grain J5 analogue), and solo
anchors C1@1 (ties to E1) and C3@1. Gemma runs {1×full, 4×q} only (~8 cells).
Legacy mixed shapes (half+q2+q3) are EXCLUDED from Stage B: the 2026-07-21
mode-exclusivity contract deprecates full+quarter co-placement; scout may
probe one mixed cell for curiosity, never for provisioning.

**Protocol decisions (deltas from E1, each with rationale):**
1. **KV budget scales with K** (`-c = <per-stream ctx>×K`, floor 8192, q8 KV,
   `-fa on`): the binding reason is WORK-PARITY across K — decode-time KV read
   traffic follows the stream's actual sequence length (identical across K for
   a fixed prompt set); allocation sets the per-stream CEILING. Under E1's
   fixed-total convention (`-c 32768`) per-stream context shrinks with K
   (32k@1 → 1k@32), so high-K cells would TRUNCATE long answers — doing less
   work per task and inflating tasks/hour. Constant per-stream context makes
   every cell complete the same workload, and matches production footprint
   realism (a K-slot server allocates K streams' worth of real KV state).
   The per-stream constant is a SIZING RULE, not a magic number: smallest
   power of two ≥ max(tier-1 prompt + generation cap + margin) — expected
   2048; implementer verifies against the actual pool. E5 K=1 cells therefore
   aren't byte-comparable to E1 rows; the scout cross-checks direction against
   the E1 ladder before Stage B.
   **Unified KV (`--kv-unified`) — corrected 2026-07-23 after operator review**
   (the original "deliberately out, not production shape" line was written
   without checking project history — it IS a documented project axis:
   tree-spec multi-path verification requires it and our fork FORCE-enables
   `kv_unified` for DRAFT_TREE configs, `common/speculative.cpp:2668`; old
   NUMA/tree bench sweeps passed it on dense arms and deliberately omitted it
   on SSM arms; PR #18730 upstream). Base E5 protocol stays SPLIT KV — it is
   what today's realized stack serves (explicit slots + MTP linear p_split=0 →
   default `kv_unified=false`) and keeps E1 comparability — but: (i) any cell
   running a tree-spec config gets unified FORCED by our own fork, so
   `kv_unified` is a per-cell MANIFEST/attestation field, never assumed; (ii)
   the scout adds one paired probe (qwen36 C1@16, split vs `-kvu`) to price
   the tradeoff on EPYC — unified buys elastic per-stream capacity (no
   truncation ceiling without over-allocating; cross-seq prefix sharing) at
   the cost of per-stream KV contiguity (scattered cells on a BW-bound
   decode), cell/defrag management, and pool-capacity interference between
   streams; ≥5% delta at the probe escalates a split-vs-unified Stage-B arm
   to the operator; (iii) SSM/hybrid arms (ingest W4) keep unified OFF per
   the tree-spec Phase-8 scar (hybrid+kv_unified allocator/acceptance
   failures).
2. **Production spec-dec ON** (`feedback_bench_max_opt` / compare-vs-top-spec):
   qwen36 arms run embedded NEXTN self-draft, gemma runs its draft-mtp recipe
   (all 8 launch params). Record per-cell draft accept-rates — spec-dec ×
   batching interplay is itself unmeasured. The Stage-A probe explicitly tests
   np×spec-dec compatibility per model (gemma MTP ASSERT/wedge risk): if a
   model wedges at np>1, document, notify operator, and run that arm
   spec-dec-off as an explicitly-caveated separate arm — never silently.
   **Operator directive (2026-07-23, absolute): baseline (spec-off /
   unoptimized) configs NEVER run outside explicitly-labeled
   inference-research benchmark arms — never as serving shapes, anchors, or
   reference points. Every "anchor" cell in this sweep means the model's TOP
   optimized production recipe.**
3. **TTFT reported separately** from steady-state per-stream decode (CPU23
   9.6× concurrent-prefill amplification) — closed-loop driver records TTFT,
   per-stream p50/p95 completion latency, and aggregate tasks/hour with the
   ramp window trimmed.
4. **Warming**: `drop_caches` only between MODELS (operator step), then
   per-instance pinned warm-up generation (1 prompt, 32 tok) before any
   measured cell — the shared-mmap first-touch trap
   (`feedback_drop_caches_numa_eviction`) means an unpinned re-read pins one
   node and poisons every quarter cell after it.
5. **Per-cell preconditions**: per-instance LIVE affinity verification via
   the cell-manifest preflight mode that audit C3 builds (the existing
   `affinity_preflight.py` is NUMA_CONFIG-role-keyed and has NO `--live-only`
   flag — it cannot gate the synthesized half1/bench-port shapes as-is; the
   WP-6 bad-affinity artifact is the cautionary tale), throttle check,
   `numa_balancing=0`, no pre-existing llama processes; ps-verified kill
   between cells. **`GGML_IQK=1` set in EVERY cell's server env and recorded
   as a manifest/attestation field alongside `kv_unified`** (audit C1,
   execution-blocking: the v7 iqk runtime gate — without it K-quant/legacy
   cells silently run un-iqk'd; the aborted 2026-07-07 "missing-IQK" dense
   run is the cautionary tale). The harness env imports
   `scripts/lib/canonical_recipe.py` constants instead of keeping a private
   `DEFAULT_ENV` copy (recipe-drift risk). Decision-grade refuses on any
   warning (E1 semantics).
6. **Correctness pairing**: store every response; post-hoc offline score with
   the E7-era B7 scorer; garbage gate per cell = parse-failure ≤ 2/43 and no
   repetition-loop flags, else the cell is marked degraded (speed number
   demoted to observation).

**Pre-registered decision rules** (read before results exist, to avoid
post-hoc cherry-picking):
- **R1 crossover**: at each iso-T, a split wins on aggregate tasks/hour with a
  ≥10% margin; smaller margins = tie → prefer the status-quo quarters split.
  The K* where 1×big first beats 4×q (if anywhere) is the roofline-flip point.
- **R2 lanes**: report the (aggregate, p95) Pareto per model; lanes are "real"
  iff the peak-aggregate cell's p95 exceeds 3× that config's K=1 p95 (or 60s
  absolute) while some lower-K cell holds ≥70% of peak within SLA.
- **R3 eval-lane pricing** (amended per audit C2 — decision-blocking): the E2
  rows (batch 2.258 vs current 10.970 wall-min/eval, 2026-07-03) are
  DEMOTED-TO-PRIOR under three era boundaries (E6-cpu-kernel v7 cutover
  2026-07-20, E7-eval-instrument, E4-quality-core-v2 — and the eval unit
  itself changed, 43-q legacy T1 → 50-item core_v2): direction only, they
  CANNOT gate the lane decision. Before applying R3, RE-BASELINE the
  "current EvalTower fan-out" arm FRESH under v7 + core_v2 + the WP-12 fleet
  layer (one measured row; the batch arm is already re-measured by the E5
  cells themselves), then convert each candidate cell to wall-minutes/eval
  against that fresh baseline. Option (b) remains a zero-code remap under the
  WP-12 fleet layer (an eval-only RoleBinding on a batch-shaped fleet — live
  as of the 2026-07-23 flip).
- **R4 slot-fabric provisioning row**: per model, (config, K) = the
  smallest-latency cell achieving ≥90% of peak aggregate → feeds the
  per-instance `-np` sizing in within-role-placement-state-machine.md and the
  heterogeneous-slot-fabric provisioning table. **Output schema is
  MODEL-KEYED capability data** (model+quant → {solo shape, NUMA-splitting
  potential, per-shape -np optimum, ctx/KV config, spec recipe + accept
  rates, kv_unified attestation}) per the ratified fabric optionality
  contract: models own their optimal config; roles are policy references
  over it; the orchestration layer consumes only the resulting contention
  matrix of the deployed model stack.
- **Spec interpretation note**: the waypoint's "worker_general {full}-only"
  is read as "no full+quarter mixes" — the 4×q worker config is included
  because 1×full@32 vs 4×q@8 is precisely the sweep's money comparison and
  4×q is the live burst mode (WP-8 acceptance shape). Flag to operator at
  scheduling if the literal reading was intended.

**Quiet-window schedule** (queues behind inference-batch-loop →
architect-model-selection-bench per the post-promotion order): **W0** scout —
all models, full grid incl. C1b, 64-token cap, non-decision-grade, prunes
Stage B (~2-2.5 h); **W1** `qwen36_q8_0` Stage B (~4-5 h at ~13 cells);
**W2** gemma Stage B (~2-3 h at ~8 cells); **W3** dense control Stage B
(~4-6 h; slowest decode — control evidence for the MoE-batching-weaker
hypothesis, can lag without blocking W1/W2 provisioning reads); **W4** ingest
`qwen3_next_80b` arm (operator-added 2026-07-23; configs C1/C1b/C3 as
separate cells — C1b's half-pair ratio is same-shape evidence for WP-9;
schedule appetite is the operator's call).
RAM is a non-constraint throughout (worst case 4×45 GB ingest + KV on 1.1 TB,
stack stopped).

**Harness delta spec = audit C3, execution-blocking** (extend
`server_np_sweep.py` or sibling `server_numa_np_sweep.py` in
epyc-inference-research — the existing script is SINGLE-server with hardcoded
`numactl --interleave=all` and cannot run C1b/C2/C3 cells as-is): (a)
cell-manifest input (model, config_id, instances[{cpu_list, port, threads,
numactl_policy}], np, c, prompt caps); (b) multi-server launch/teardown per
cell with per-instance taskset pinning + per-SHAPE numactl policy (interleave
ONLY for full-machine/gemma-MTP shapes) + OMP env stack + `GGML_IQK=1`
imported from `canonical_recipe.py` constants + ps-verified kill; (c)
closed-loop per-stream driver round-robining the 43-prompt pool across N×K
streams, recording TTFT / per-stream latency / trimmed aggregate; (d)
per-instance affinity preflight wired as a hard cell gate — requires
EXTENDING `affinity_preflight.py` with an arbitrary-{cpuset, port}
cell-manifest mode (today role-keyed, no live-only flag); (e) E1-style
manifest with protocol-id P-BENCH-3 (the waypoint blesses reuse), era stamp,
attestation incl. iqk + kv_unified fields, decision_grade gating; (f) iso-T
comparison table + R1-R4 rule evaluation in the summarizer.

- [x] E5 sweep design + cell grid + decision rules + window schedule prepared (design-only, zero inference) ✅ 2026-07-23
- [x] E5 harness implementation ✅ 2026-07-23 (research `b294daa0` + orchestrator `6a55aeed`): `server_numa_np_sweep.py` (multi-instance, canonical env incl. `GGML_IQK=1` via `build_canonical_env`, preflight hard gate, ps-verified teardown, N×K closed-loop driver, E1-style manifest+attestation, dry-run default + `--execute --i-have-operator-grant` double gate, R1–R4 summarizer) + `e5_cell_manifests.py` with the **pre-registered 116-cell grid COMMITTED** (frozen pre-registration artifact) + `affinity_preflight.py` cell-manifest mode. 148 offline tests green (47+54+25+22). Built via 7-agent workflow with 2-lens adversarial review (13 findings, 12 fixed). Two findings bind execution:
  - **POOL-DRIFT (binding, solved by pinned qids)**: the 2026-07-21 E7 pool rebuild changes the `tier=1, seed=42, limit=43` draw — re-sampling would select a different batch including a 101,655-char tulving prompt (breaks the 2048 ctx sizing AND E1 comparability). All 43 E1 qids verified present in the current pool → the manifests pin `prompt_batch.selection="pinned_qids"` + a 4096-char fail-closed cap. General lesson for ANY pool consumer: seed-N draws are pool-version-dependent; pin qids, never re-sample across era boundaries.
  - **E5 sampling regime — DECIDED ✅ 2026-07-23** (operator: "sampling regime as recommended"; research `6b9a90c7`): **production temp+seed42 for every cell** (realized serving defaults: qwen36+gemma temp .3/top_k 40/top_p .95/min_p .05/seed 42; ingest 80B production is already greedy with seed pinned 42; dense control inherits the qwen36 regime). temp-0 exists ONLY in five `-e1parity` **twin cells** of the E1-tied solo anchors (qwen36 C1@1/C3@1; dense C1@1/C3@1 + scout-full@1) so the E1 direction cross-check runs regime-clean — twins carry the `e1_parity_anchor` variant tag, `decision_grade_intent=false`, and the summarizer excludes them from R1/R2/R4 (no regime mixing inside decision rules). Grid: 116 → **121 cells**, regenerated + committed.
  - **`--device none/--device-draft none` discovered necessity**: the v7 binary is HIP-capable — without the explicit pin, E5 CPU cells could silently offload draft work to the MI210. Wired into the harness launch args.
- [x] Operator queue-clear GRANTED ✅ 2026-07-23 ("agreed, proceed"): inference-batch-loop live island exhausted (all parked on operator/build/data gates); architect-bench decision phase complete (well-powered NULL); RP-5/A2-CPU slotted AFTER E5 W0/W1 (ownership transferred to the CPU session — see architect-model-selection-bench.md)
- **⛔ SUSPENDED 2026-07-30 — the W0 scout block below is retained verbatim but its throughput values and rankings are WITHDRAWN.** W0 swept the same C1/C1b/C2/C3 placement shapes through the same harness as Stage-B, so it carries the identical straddling-cpuset NUMA defect (see the suspension notice at the top of this file). The aggregate figures quoted below (qwen36 2028 @np4, gemma 5076 @np8 / 1.78x iso-T, dense 1415 @np2, 80B 2520 @np4) and the "**C3 quarters aggregate-optimal for EVERY model**" scout-physics conclusion are **RETRACTED**, as are the C1b second-node payoff read and the dense C1 shape resolution — all are cross-shape rankings under an unequal per-shape penalty. **What survives**: 69/69 cells clean, the e1parity twins as a regime-clean cross-check of *direction*, and the run/manifest provenance. W0 was already observation-grade (it ran under `--allow-host-health-warning` at 20-day uptime), so nothing decision-grade depended on it. ORIGINAL ENTRY:
- [x] **E5 W0 — EXECUTED COMPLETE ✅ 2026-07-23/24: 69/69 cells clean across all 4 model groups** (run dirs `e5-w0-{qwen36-nothink,gemma,dense,80b}-*` under research `data/batched_decode/`; scout physics: C3 quarters aggregate-optimal for EVERY model — qwen36 2028 @np4 / gemma 5076 @np8 = 1.78x iso-T vs interleaved full / dense 1415 @np2 / 80B 2520 @np4; C1b second-node payoff MODEL-DEPENDENT — loses for MoE-35B, wins for dense + 80B; dense C1 shape RESOLVED = half0 beats full-machine at K=1 and K=8; e1parity twins banked). Original staging text preserved below for the record. ORIGINALLY: **E5 W0 — STAGED, fire in the next operator-present quiet window** (~2-2.5h, CPU-only, `--device none` pinned): **W0 EXECUTING 2026-07-23 evening** (operator: full CPU-window authority). CORRECTED invocation — the earlier staged `--window W0` flag was fabricated; the harness is one-model-group-per-invocation BY DESIGN: per group `.venv/bin/python scripts/benchmark/server_numa_np_sweep.py --manifest-dir data/batched_decode/e5_manifests_w0/<model_key> --execute --i-have-operator-grant --allow-host-health-warning --run-id e5-w0-<model>-<UTC>`, with `sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'` before each group (session has sudo — no operator step). Serving stack STOPPED for the window (named-component stops; classifier declined `stop --all`); 18072/MI210 vacated → full 69-cell grid. **`--allow-host-health-warning` is required and correct for W0**: host uptime is 20 days and the harness refuses decision-grade P-BENCH-3 runs past 1 week — W0 is scout/non-decision by design and the warning is recorded per cell. **⚠ W1/Stage-B PRECONDITION: operator host reboot** (uptime policy; reboots are operator-only) before any decision-grade window. Preconditions: (1) operator present for `drop_caches` transitions between models (root; harness prewarm handles the `feedback_drop_caches_numa_eviction` trap after each); (2) **the MI210 experiment's host threads (port 18072, cores 88-95) overlap node-3 cell cpusets** — the per-cell preflight will correctly FAIL node-3-touching cells (C3, C1b-half1, gemma full-machine) while it runs: pause/re-pin the GPU server for the window, or accept a partial W0 with node-3 cells deferred; (3) no eval/autopilot traffic during cells (serving stack stays up; bench ports 19xxx disjoint); (4) attestation auto-records GGML_IQK/kv_unified/sampling per cell
- [x] **W0 summarizer + Stage-B prune** ✅ 2026-07-28 — all four W0 runs now carry observation-grade `offline_scores.jsonl` plus provenance (2,967 saved responses total) and regenerated summaries/rules. W1 prunes only throughput-only `qwen36_q8_0-C1b-{np4,np8,np16}`; W2 retains its full C1/C3 family but is **invalid for quality/garbage interpretation** because the original Gemma capture stored reasoning text without an answer channel; W3 retains its full grid because the C1b@16 vs C3@8 comparison degraded across metric bases; W4 retains its full grid, but high-K `raw_fallback` rows are demoted from decision-grade use. The frozen manifests are unchanged; derivative plan: `data/batched_decode/e5_pre_reboot_20260728/stage_b_prune_plan.json` SHA-256 `cabd10bd0fe52ed04ca28e314ad0ab8d505de9e5db571115d16c48d0832daee8` (append-only provenance supersession chain; predecessors `06b0abb2ca7abaf004ce56658a8c3753ea719ebdc4f1b50bec65a015954d4f8b` -> `9b4d4f034e3da01cbaaa652838aa9bb481855853180e8deb2dfafc27d69396b8` -> current. The 2026-07-29 append re-attributes the Gemma W0 430/430 from a capture defect to reasoning-mode-ON and retracts the claim that `efd0980c` alone makes W2 safe; it also records the W3 CPU-scope removal. Selection and frozen manifests unchanged.)
- [x] **Stage-B pre-window readiness verification (zero inference)** ✅ 2026-07-29 — post-reboot host-health gate returns ZERO warnings (uptime 49 min, `numa_balancing=0`, no static freq caps) so Stage-B is decision-grade eligible with **no** `--allow-host-health-warning`; kernel verified `production-consolidated-v8` @`67a433bf4` (binary 10107); all four region-lock regions free; host fully quiesced (0 llama-server, 13/1133 GB used, AutoPilot down); all 45 pruned Stage-B manifests present and dry-running clean (exit 0: W1 11, W2 8, W3 14, W4 12); all 5 GGUFs present on disk; launch args confirmed carrying `--device none`/`--device-draft none`, production spec-dec, `-c` = 2048×K floored at 8192, production sampling temp .3/seed 42, n_predict 256.
- [x] **E5 instrument defect — under-load throttle gate was cpuset-blind; FIXED + operator-ratified** ✅ 2026-07-29 (research `98cfff44`) — `cpu_freq_throttle_warnings()` counted boosting cores across all 96 physical cores and required ≥80, but C1 pins 48 physical cores (0-47) and C2 pins 48 (48-95); the idle remainder parks near base clock, so the gate **could never pass for a partial-machine cell**. W0 evidence has zero counterexamples: every 96-core cell passed (C1b 15/15, C3 11/12), every 48-core cell failed (C1-half 0/13, C2 0/10) at counts 53-78, and the two *full-machine* C1 variants (gemma `taskset 0-95`, dense `C1-scout-full`) passed. Throttle warnings feed `gate_warnings` → `hard_gates_passed` → `decision_grade`, so **19 of 45 Stage-B cells** (W1 7/11, W3 7/14, W4 5/12, W2 0/8) would have been force-demoted to observation-grade — including **100% of the pre-registered half-machine mechanism family `{C1@T vs C2@T/2}`**, the roofline-flip read that is E5's core hypothesis. **Not repairable after the fact**: `FreqSampler.result()` persisted only the aggregate count and discarded the per-core vector, so deterministic replay did not apply — the same evidence-retention gap that made the W0 Gemma capture unrecoverable. Fix scopes the gate to the cell's pinned physical cores at the **unchanged** 2.5 GHz threshold and **unchanged** 80/96 ratio (a 96-core cell still needs exactly 80; C1/C2 need 40 of 48 — verified against live sysfs), and persists the full per-core vector in `throttle_check`. Measurement safety gate = human-amendment-only, so this was **presented as a decision package and ratified by the operator before any edit**, never patched unilaterally. 5 new tests pin the semantics incl. the exact W0 failure shape and a full-machine no-loosening guard; 55 passed, ruff clean.
- [ ] **E5 protection defect — non-llama ROCm processes and SMT siblings are invisible to cell-mode exclusion (filed 2026-07-29).** `affinity_preflight.py` discovers foreign overlap only through `LLAMA_PROC_PATTERN` matched to the `argv[0]` basename, so a `python` ROCm/PyTorch/TRL trainer is uncounted and can inherit unrestricted affinity on a pinned E5 cell. Its raw logical-CPU intersection is also SMT-blind: GPU host threads `184-191` and an E5 `0-95` cell share physical cores `88-95`, but have an empty logical-id intersection. Port the GPU tooling's sibling-folded `recert_roles` semantics into cell mode and fail closed on relevant non-llama GPU/training process overlap before any `decision_grade=true` Stage-B cell. **Containment:** no MI210 training workload may start during E5; the training-viability smoke is deferred until the host is released.
- [ ] **Operator decision pending — instrument-era row for the gate re-scoping.** Era registry rows are human-amendment-only. The change alters no measured value (throughput/latency are untouched) — only decision-grade *eligibility* — so it may not warrant an era row; flagging rather than assuming. W0 records stay unedited per MEASUREMENT.md (append, never edit).
- [x] **W3 (dense control `qwen36_27b_q8`) — DROPPED BY OPERATOR DECISION, not deferred / not blocked / not failed** ✅ 2026-07-29 — operator: *"27b_q8 is scheduled to run residently on the GPU"*, so a CPU-side dense-control sweep measures a shape that will never serve. This is a scope change, not a deferral: the E5 model list's dense-control arm is superseded for the CPU plane. The 14 pruned W3 cells are **not run**. Durable record: coordinator `msg-20260729T155710Z-45`, operator-instructed in-pane. Reason: 27b_q8 is planned for promotion as a **GPU-resident tenant** (P2-2a dense-27B, VERIFIED LANDED against the `qwen36_27b_stock_q8` tenancy row), so a CPU NUMA×batch sweep would measure a configuration that will never exist in production. **This is a SCOPE change, not a result change** — existing W3 references and the W0 W3 scout data already recorded are retained unedited, per the append-never-edit rule. **Revised sweep scope: 31 of 45 cells** (W1 11 + W2 8 + W4 12), covering **three** model groups; revised wall-clock ≈ **2.5–3 h** from 16:18Z, measured at 5.77 min/cell over the first six W1 cells (the earlier 13–17 h figure predates both the drop and the measured rate). Any artifact update must state the sweep covered three model groups **and why the fourth was dropped**, so no reader infers W3 failed or was lost. The campaign driver was killed and replaced mid-flight before it could auto-launch W3.
- [x] **E5 harness: `--reasoning` was never emitted; gemma4 W2 ran with reasoning ON** ✅ 2026-07-29 (research `5d6a17f2`) — the harness had no `--reasoning` emit at all, so every cell ran at llama-server's `--reasoning auto`. For `arch=gemma4` that default is **ON**, while both model registries record `reasoning: 'off'` for this GGUF — so W2 was not running the production recipe it exists to mirror. **Measured**: the 2026-07-29 capture smoke returned **41/43** `response_capture_missing_answer_text`, every failure HTTP 200 with `predicted_n` exactly 256, empty `response_text` and a populated `reasoning_text` of 599–1174 chars ending mid-sentence — the entire Stage-B budget spent inside the reasoning channel before the answer channel opened. Server log clean: no wedge, no OOM, no truncation (max `n_tokens` 850 vs `n_ctx_slot` 2048), draft acceptance 0.92, nothing within 38× of the 900 s timeout. **The capture contract works and the fail-close fired truthfully** — and this is the same signature behind W0's 430/430, which was misread as a capture bug. Fix emits `--reasoning` (server-side, template-independent, unlike `enable_thinking` which some templates ignore); 19 gemma4 manifests amended with `reasoning:'off'` plus append-only provenance, restoring the pre-registered intent rather than changing it. **Scope verified**: qwen36 W1 carries `enable_thinking:false` and is confirmed clean live (46/46 nonempty answers, 0 reasoning); W0 dense and 80B produced 989/989 and 645/645 nonempty answers — gemma4 is the sole exposure.
- [x] **E5 harness: two launch-blocking defects fixed** ✅ 2026-07-29 — (1) `httpx` was an **undeclared** dependency of the `--execute` path; the 2026-07-26 venv rebuild dropped it and the first Stage-B launch aborted *after* starting and cleanly tearing down a llama-server (research `040a2ad7`). A dry-run cannot catch it because dry-run never touches HTTP. (2) `find_llama_processes` matched the whole `ps args` string, so a coordinator bus relay whose text merely **quoted** `llama-server` tripped the clean-runtime gate on an empty host; the same matcher backs the **per-cell** health gate, so mid-run it would have failed that cell and silently demoted it out of decision-grade (research `4a5b6bc7`). Now resolved via `/proc/<pid>/exe`, which still catches instances launched under `taskset`/`numactl`.
- [ ] **T=32 cells return `empty_trimmed_window` → observation-only (discovered mid-campaign 2026-07-29)** — *(⛔ throughput values quoted in this item are SUSPENDED 2026-07-30 — the structural `empty_trimmed_window` finding and its offline-replay remedy are unaffected and still stand.)* — confirmed live on `qwen36_q8_0-C1-np32`: `decision_grade=False`, raw 428.4 / trimmed 0.0, err 0.0%. Structural: `trimmed_aggregate` takes `ramp_end = min(end of successes)` and `drain_start = max(start of successes)`, so when `np` approaches the 43-prompt batch almost nothing both starts after the first completion and ends before the last start. Affects **every T=32 cell** (C1-np32, C1b-np16, C2-np16, C3-np8, and the W2/W4 equivalents) — i.e. the **top rung of both pre-registered decision families**, iso-T {C1@32 vs C2@16} and {C1b@16 vs C3@8}. Low/mid-K rungs (np 1/4/8/16 solo) are unaffected and came back `dg=True`. **Deferred, not lost**: the full per-request start/end/latency ledger is persisted in `requests.jsonl`, so a ratified alternative steady-state rule can be applied **offline** to these exact runs — deterministic replay before regeneration, no re-run needed. Not fixed in-flight because the trimmed-window definition is measurement-instrument territory (human-amendment-only) and changing it mid-campaign would invalidate the cells already banked. Escalated: `msg-20260729T161839Z-45-mainA`.
  - [x] **Offline replay DONE + decision package delivered ✅ 2026-08-11 (`mainA`)** —
    `/mnt/raid0/llm/tmp/e5-a6-trimmed-window/A6-decision-package.md`, with a reproducible driver
    (`replay_candidates.py`). Zero cells; replay over the persisted `requests.jsonl` ledgers.
    **Scope correction to the item above: it is 5 cells, not "every T=32 cell".** Two of the five are
    np=16 (`qwen36_q8_0-C2-np16`, `qwen3_next_80b-C1b-np16`) while **three other np=16 cells passed**
    (`qwen36_q8_0-C1-np16`, `gemma4…-C1-np16`, `qwen3_next_80b-C1-np16`). The trigger is whether any
    single request straddles the interval — arrival/completion interleaving — **not the np level**, so
    a rule keyed on T=32 would fix the wrong thing and still leave two cells blocked.
    **The finding that decides it:** all 5 blocked cells have a valid PRIMARY metric; they are blocked
    only by an empty window in the SECONDARY tasks/hour number, which the 2026-07-30 ruling says ranks
    nothing. And `throughput_basis` is `wallclock_fallback` for **all 34 Stage-B rows including the 26
    that passed** — the gate enforces strict steady-state rigour on the demoted metric while the
    promoted one runs on a fallback basis corpus-wide, ungated.
    **Candidates replayed** (rescue / of 26 moved >5% / worst move): pctile-10 5/5, 18, +148% ·
    pctile-20 5/5, 21, +93% · plateau-50 5/5, 20, +186% · plateau-80 5/5, 14, +164% ·
    **decouple 5/5, 0, 0%**. Every window *redefinition* rescues all five and silently rewrites the
    banked secondary number for 14–21 of the 26 already-passing cells; none re-grades a cell to zero,
    but republishing 21 of 26 banked numbers at up to triple value is the substantive form of the
    hazard. They move because they are a different definition, not a repair: the status-quo window is
    a legitimate conservative rule that simply degenerates at high K.
    **Recommendation: decouple** — stop gating `decision_grade` on the secondary trim, leave
    `trimmed_aggregate` untouched, surface `trimmed_window_empty` and caveat verdicts via the
    `_apply_basis_caveat` path landed under A5. Only candidate that rescues all five while changing
    zero banked numbers. **Cost stated plainly:** promoting 5 cells to decision-grade is itself a real
    grade change on banked cells — which is why it is a token, not an edit.
  - [ ] **Operator token OUTSTANDING** — one ask: decouple `decision_grade` from the secondary
    trimmed-tasks/hour window, promoting the 5 listed cells, with `trimmed_window_empty` as a caveat.
    `TRIM_DEFINITION` is **not** amended and every banked number stands. Nothing further is owed by
    this lane until it is signed.
- [ ] **R2/R4 mix metric bases and let a non-decision-grade cell win the Pareto peak (discovered 2026-07-29 by pre-validating the summarizer on a COPY of the live partial W1)** — *(⛔ every tasks/hr figure quoted in this item is SUSPENDED 2026-07-30. The defect it identifies is a metric-BASIS inconsistency — raw vs trimmed — which is scale-invariant, so the finding and its fix survive the suspension and must be applied before the re-measured cells are aggregated.)* — R2 names `qwen36_q8_0-C2-np16` peak at **578.6 tasks/hr on `aggregate_basis=raw_fallback`**, above `C2-np8` at **462.8 on `trimmed`**; `C2-np16` is `decision_grade=false` (`empty_trimmed_window`). R4's `per_shape_np_optimum` picks the same cell on the same basis and flags `mixed_metric_basis: true`. **The arithmetic settles it**: like-for-like, `C2-np8` raw **669.2** > `C2-np16` raw **578.6**, and on trimmed `C2-np16` has no value at all — so it wins on *no* consistent basis. It only appears to win because it is compared on raw while its rival is compared on trimmed, and raw is systematically higher (includes the ramp-up burst, skips steady-state trimming). **This upgrades the 16:18Z T=32 finding**: those cells do not merely fail to contribute, they *actively contaminate* R2/R4 by winning comparisons they should not be in — a reader would wrongly conclude 2×quarter @np16 is the peak provisioning shape. **R1 is unaffected** — it already guards per-pair (`mixed_metric_basis: false` on the clean half-machine T=16 pair, where C2@8 462.8 beats C1@16 327.0 by 29.3% on a consistent trimmed basis). Fix = apply R1's existing guard to R2/R4: exclude `decision_grade=false` cells from aggregation, or refuse a peak whose basis differs from its rivals. **Not changed in-flight** — instrument code, campaign live on it, and changing aggregation mid-run would make banked cells non-comparable. Pure post-hoc read, so it is fixable and re-runnable **offline** against the same run dirs at zero inference cost. Escalated `msg-20260729T162849Z-50-mainA`.
  **✅ 2026-08-11 (`mainA`) — LANDED, research `4fb44869`. Half of this was already fixed; the other half was real.**
  **Already fixed, verified by offline replay of `e5-w1-qwen36-20260729T154725Z`:** the 2026-07-30 metric
  ruling made R2/R4 filter `decision_grade=false` rows *before* selecting and rank on tok/s, not
  tasks/hour. `qwen36_q8_0-C2-np16` — the cell this item names — is now in `observation_only_cells`
  and excluded from both rules, and R4 recommends `C2-np8`, which this item itself calls the correct
  answer. The raw-vs-trimmed peak contamination described above **cannot occur today**.
  **Still real, now fixed:** R2/R4 computed `mixed_throughput_basis` / `mixed_metric_basis` and never
  fed either into `status`, so a verdict could emit `status="decision_grade"` beside its own
  `mixed_throughput_basis: true`. R1 has demoted to `winner_caveated` since review F3. Added
  `_apply_basis_caveat`, mirroring R1's contract exactly — `decision_grade` keeps describing the
  member CELLS and is untouched, so nothing can re-grade a banked cell; only `status` carries it.
  **No banked result changes, proven not asserted:** re-derived `rules.json` for all three run dirs
  with and without the change — byte-identical apart from `created_at`. Measured separately: 0 of 3
  run dirs have a mixed basis among decision-grade cells, so the guard is currently unreachable in
  banked data and is a structural fix, not a re-grade.
  Tests 61 → 64 (mixed path both bases; the compliant same-basis path, so the guard cannot fire on
  everything; and that an `insufficient_decision_grade_data` refusal is never rewritten into a
  caveated verdict). `pytest` is absent in this environment — the suite is stdlib-only by design and
  was run with a plain runner (`/mnt/raid0/llm/tmp/e5-a5-replay/run_tests.py`), 64/64 green.
- [ ] **KERNEL-ERA MIS-STAMP: every E5 manifest claims a v7-lineage era while running v8 (found 2026-07-29)** — `e5_cell_manifests.py:76` pins `ERA_CPU_KERNEL = "E6-cpu-kernel"`, set 2026-07-23 (`b294daa0`) and never revisited across the 2026-07-25 v8 cutover. **Note the trap**: era ordinals do NOT track kernel versions — the `cpu_bench` timeline is E0, E1, `E5-cpu-kernel` (v6+iqk), `E6-cpu-kernel` (**v7**, `instrument_eras.yaml:67-78`), `E8-cpu-kernel` (v8). There is no `E7-cpu-kernel`. Reading "E6" as "v6" is the natural and wrong inference, and is why this survived a cutover. **6 confirmed mis-stamps**, all claiming v7-lineage with `attestation.binary_version = 10107 (67a433bf4)` = v8: E5 W1, E5 W4 (**live, `decision_grade=true`**), both W2 capture smokes, and two Laguna SWE-oracle artifacts carrying `meta.kernel="v7-candidate"` against a sibling `plan.json` pinning `production-consolidated-v8`. **Two compounding defects**: (a) `e5_cell_manifests.py:763-764` *rejects* any manifest corrected to `E8-cpu-kernel` — the validator enforces the stale value; (b) `_warn_if_era_stamps_stale()` (`:1138-1151`) fires only `if era_id not in text`, but era registries are **append-only**, so a superseded id is always still present and the check can never fire for it — only for a *deleted* era, which the policy forbids. **A staleness detector whose only trigger is deletion, in a system that never deletes.** That is why the v8 cutover passed green. **Scale/containment**: 208/208 `data/batched_decode` manifests carry `E6-cpu-kernel`, 0 carry E8 — 4 executed-on-v8, 6 W0 runs genuinely v7 and correctly labelled, 198 un-executed templates. The era stamp lives **only** in `manifest.json` (no `cells`/`events`/`requests`/`responses` jsonl carries it), and appears in 0 files outside `data/batched_decode`. **Recoverable — nothing needs re-measurement**: every affected artifact records `attestation.binary_version`. **Fix (needs a human token, era semantics) — ORDER IS LOAD-BEARING.** ⚠ **My first recommendation was WRONG and is retracted**: simply setting `ERA_CPU_KERNEL` to `E8-cpu-kernel` would have **stopped the running campaign**. `server_numa_np_sweep.py:297 revalidate_cells()` (docstringed *fail closed*) runs `validate_cell_manifest` over every manifest it loads, and `cmd_sweep:1803` raises on any error — so flipping the constant makes the sweep refuse to start against all 208 E6-stamped manifests, including the 198 un-executed templates W2/W4 depend on. Caught by the auditor (`msg-20260729T173845Z-75`), independently endorsed by `inference`. Correct order: **(1)** replace equality-to-current-constant validation with a **date- and scope-derived** lookup — the validator must accept the era that was *current when the manifest was pre-registered*, which is the append-only-respecting rule and keeps the 198 templates valid; **(2)** make the stale check compare a stamp against that derived current-at-date scoped era rather than testing registry *membership*; **(3)** only then emit forward stamps from the derived era. **Do NOT substitute a new hard-coded constant** — `E8` hardcoded goes stale at v9 exactly as `E6` did at v8. Append dated corrections rather than editing banked artifacts. *Irony worth keeping*: the comment at `e5_cell_manifests.py:74-75`, three lines above the constant, already reads `E6-cpu-kernel: v7 cutover 2026-07-20` — the correct mapping was adjacent the whole time. Not changed in-flight: W4 is executing this harness. Escalated `msg-20260729T173508Z-55-mainA`.
- [ ] **Era-repair package DESIGNED but NOT READY — it fixes the generator, not the mechanism (2026-07-29)** — prepared post-release, adversarially reviewed, **verdict: do not present for a token**. Four blockers, the first two structural:
  **(1)** `server_numa_np_sweep.py:1748` builds the run manifest as `"era": first.manifest.get("era")` — the era block is copied **verbatim** from the cell template at execution time and the registry is never consulted. The package repairs `make_cell` in `e5_cell_manifests.py`, so after the *full* package is applied every remaining run still mints a mis-stamped manifest (reproduced: stamps `E6-cpu-kernel` while `derive_era('cpu_bench', now)` = `E8-cpu-kernel`). Verified independently at that line.
  **(2)** The proposed validator cannot catch the artifacts it exists for: a run manifest inherits the cell's pre-registration date so `E6` validates clean, and run manifests never pass through `revalidate_cells` at all (only `Cell` objects do). **Nothing binds `era.cpu_kernel` to `attestation.binary_version`** — the only field that witnesses the executed instrument.
  **(3)** The recommended variant permanently whitelists the exact stale `{E6-cpu-kernel, E7-eval-instrument}` pair, unbounded in time and count — a green check that means nothing, structurally the same failure as the dead detector it replaces.
  **(4)** Its backfill is not gated on campaign end and would rewrite 191 cell manifests including the 12 the live W4 run loaded.
  **(5) The stale-pin defect is a PAIR, not a single constant — I missed this all day.** `e5_cell_manifests.py:77 ERA_EVAL_INSTRUMENT = "E7-eval-instrument"` sits **one line below** `ERA_CPU_KERNEL` and is stale for the same reason (`eval_quality`'s current era is plain `E8`, registry `:166-168`). `validate_cell_manifest:763-771` checks `cpu_kernel`, `eval_instrument` **and** `source`, each by equality — so **the campaign-breaking fail-closed hazard applies twice**, and a repair touching only line 76 still breaks the sweep on line 77. Caught by the auditor; verified directly. The complete set of genuinely stale code constants is **three** across three repos (`e5_cell_manifests` ×2, `instrument_era_guard` ×1) — bounded, not open-ended.
  **The discriminator that makes a sweep safe**: a pin naming a specific **past** era on purpose is *correct*; a pin meant to track the **current** era is stale. `dashboard.py:2575 _PARETO_SPEED_DEINFLATE_ERA_ID = "E2"` is the former — a rescale **boundary** where pre-E2 speeds are multiplied by `pareto_pre_epoch_speed_factor`. A pattern-based bump would silently move it and corrupt every historical speed read. 673 lines across 317 files name superseded eras and nearly all are legitimately historical; that is the append-only design working.
  **Correct direction**: bind the stamp to `attestation.binary_version` at **run-manifest construction**, not only at cell generation — otherwise the template is fixed and the mint stays open. Rework after host release against a quiesced tree. No re-measurement implied; identity stays recoverable from persisted evidence. Design + review evidence in `/mnt/raid0/llm/tmp/era-repair/`; nothing was written into any repo tree.
  - [x] **A7 decision package delivered ✅ 2026-08-11 (`mainA`)** —
    `/mnt/raid0/llm/tmp/era-repair/04-a7-decision-package.md`. Recommended splitting into two
    independently-signable tokens; **Token 1 was signed the same day** (receipt
    `artifacts/operator/receipts/RATIFY-CONSOLIDATED-ERA-ROWS-20260811.json`, era rows attested
    21:35:01Z). `E9-cpu-kernel` verified at `instrument_eras.yaml:413` (v9, `0db32c06`, binary 10125).
    Four corrections to the item above, all re-derived against the tree, not inherited:
    **(a)** the run-manifest era copy is at `server_numa_np_sweep.py:1895`, not `:1748` — and the
    sharper statement is that `"era": first.manifest.get("era")` and `"attestation": attestation` sit
    in the *same dict literal* 34 lines apart, so the witness and the claim are written side by side
    and the claim ignores the witness. No plumbing is missing, only the binding.
    **(b)** the stale-constant set is **four, not three** — see the new checked item below.
    **(c)** the corpus is **210, not 208**; MIS-STAMPED is **6, not 4**. The two extra runs
    (`e5-w2-capture-smoke-20260729T183019Z`, `e5-w2-gemma-20260729T183151Z`) landed **36 minutes after
    the 07-29 census was taken** — the generator kept minting `E6` while the defect was being written
    up.
    **(d)** the refused backfill deserves a stronger refusal than "ungated": of the 191 pre-registered
    cell manifests, **≥138 are correct at registration** (all added in `b294daa04f` @
    2026-07-23T16:30:41Z, inside the E6 window) and 16 more are dropped-W3 cells that will never
    execute, so a blanket rewrite to `E8` would be **wrong for 72% of its targets**. Its premise, not
    its gating, is what fails.
  - [ ] **Token 2 still OUTSTANDING, and the v9 signature added a new constraint on it.** The
    consolidated era token introduced a **scope collision**: `E8-cpu-bench-throttle-scope` (an
    eligibility boundary) and the kernel-cutover rows now share `scope: cpu_bench`, so *latest-by-from-date*
    and *last-appended* disagree for any instant in 2026-07-29..2026-08-10 —
    `derive_era("cpu_bench", 2026-07-29)` returns `E8-cpu-bench-throttle-scope`, **not**
    `E8-cpu-kernel`. Any Token-2 derivation must resolve kernel era by more than scope alone or the 6
    mis-stamped run manifests receive a second wrong answer. **Also**: the 07-29 prototype is
    **date-only** — neither `era_derivation_prototype.py` nor `validator_prototype.py` reads
    `attestation.binary_version` at all, so the "bind to binary_version" direction above is design
    intent that was never implemented; and the registry has no structured `binary_version` field (it
    lives in free-prose `note:`), so there is nothing to bind to without a schema addition.
- [x] **FOURTH stale era constant — a LIVE TOOL OUTAGE, fixed ✅ 2026-08-11 (`mainA`), research `bcfcd0a5`** — `epyc-inference-research/scripts/benchmark/cpu_prefill_v8_regression_runner.py:480` pinned the same `{E6-cpu-kernel, E7-eval-instrument}` pair, but unlike the other three it fails **CLOSED**: it asserts `scoped[-1].get("id") == expected_id` and raises `registry active <scope> row drifted`. Verified by execution against the live registry — it raises on **both** scopes, so the v8 prefill regression runner **could not start at all**, and had not been able to since the v8 cutover of 2026-07-25. Nobody hit it because nobody invoked it. Its docstring says it binds to the **active** eras, so this was accidental staleness, not a deliberate historical pin. **Not repinned** — a constant there goes stale at every cutover by construction, which v9 proved a second time. Now derives the active row from the append-only registry (last row of a scope = newest), deliberately positional rather than date-derived *because of the scope collision noted above*. Still fails closed on a missing file, an empty scope, a row with no id or no `from`, and a mid-hash registry change. Verified binding: `cpu_bench` → `E9-cpu-kernel`, `eval_quality` → `E16-eval-history-scoped-quiescence-v10-quality`. **The old drift test REQUIRED the outage** — it appended a newer era and asserted the attestation raised — so it was replaced, not adjusted; a guard whose green state is the defect cannot survive the fix. Added a literal-scan test that no era id is a string literal in the runner, verified to fail against the pre-fix source (which hardcodes two).
- [ ] **THIRD stale era constant, AutoPilot fail-safe (routed to `inference`, not mine to touch)** — `epyc-orchestrator/src/autopilot_core/instrument_era_guard.py:26` `E7_EVAL_INSTRUMENT_ERA_ID = "E7-eval-instrument"`, stale since `eval_quality` moved to E8 on 2026-07-25. Its own comment says the constant **MUST** match the registry row it stands in for, and it is the **fail-safe fallback used when the registry read fails** — so on registry failure AutoPilot fails **open to a stale era**. `tests/unit/test_instrument_era_guard_eval_quality.py:46` asserts it equals the stale literal, so **the test pins the staleness**. Same fixture-masking pattern as the dead detector. All three lines verified directly.
- [ ] **Era ids are not derivable by pattern — three traps, one rule (2026-07-29, verified)** — recorded here because all three bit real work today and the same rule defeats all three.
  **(a) Ordinals do not track kernel versions.** `E5-cpu-kernel` = v6+iqk, `E6-cpu-kernel` = **v7**, `E8-cpu-kernel` = v8, and there is no `E7-cpu-kernel` at all. Reading "E6" as "v6" is the natural inference and it is wrong — it caught me mid-campaign.
  **(b) Names do not follow a scheme, even within one cutover.** The *same* v8 instant `2026-07-25T18:38:43Z` produced three rows with three conventions: `E8-cpu-kernel` (scope `cpu_bench`, `:140`), `E8-autopilot-speed` (`autopilot_speed`, `:155`), and plain **`E8`** (`eval_quality`, `:166`). `grep -c E8-eval-instrument` = **0** — so bumping `instrument_era_guard.py:26` by pattern writes a **phantom id that resolves to nothing**. Caught by the auditor; I verified the grep and the three-convention split myself.
  **(c) A presence check never detects supersession** in an append-only registry — the dead detector above.
  **THE RULE**: *derive* the era from the registry by **scope + latest `from:` date**; never extrapolate a name, never pin a literal. One rule, all three traps.
  Related, and the most dangerous instance: `instrument_era_guard.py:26` is AutoPilot's **fail-safe fallback**, consumed when registry resolution *fails* — so it substitutes a stale guess exactly when the authoritative source is unavailable, and nothing downstream can tell that apart from a correct resolution. If it is made fail-closed, the refusal must name **which scope** failed and the last known era, or someone will re-add a fallback constant to silence it and reintroduce the defect as a fix. AutoPilot territory — routed, not touched.
- [x] **W2 focused post-fix capture smoke — PASSED ✅ 2026-07-29** (`e5-w2-capture-smoke-20260729T183019Z`, verdict exit 0, `decision_grade=true`, `dry_run=false`). Decisive before/after inversion once `--reasoning off` reached the server (research `5d6a17f2`): **empty answer text 41/43 → 0/43**; **rows carrying `reasoning_text` 43/43 → 0/43** (no reasoning channel emitted at all); **offline-scorer `parse_ok` 0/43 → 43/43**; `capture_fail_close_cells` 0; `failures: NONE`. This closes the W2 precondition **and confirms the re-attribution**: the capture contract was always sound and its fail-close fired truthfully — reasoning-mode-ON was what consumed the 256-token budget. Note property 3 (the offline scorer sees scoreable answer text) is now genuinely **exercised**, which the pre-fix run never reached. The decision-grade Gemma W2 sweep started automatically behind the gate at 18:31:51Z. Original text below.
- [x] ~~W2 focused post-fix capture smoke~~ (superseded by the PASSED entry above) — before the decision-grade Gemma W2 sweep, run a focused generated-answer capture check using the hardened SSE contract: persist `reasoning_text` separately, require nonempty answer-text deltas when tokens were generated, and prove the offline scorer sees scoreable answer text — **and confirm the launch line actually carries `--reasoning off`**, which is what PREVENTS the failure; the smoke only DETECTS it (re-attributed 2026-07-29, research `5d6a17f2`: the budget sink was reasoning-mode-ON, not the capture parser). The historic W0 Gemma `430/430` parse failures have no raw SSE ledger and cannot be recovered. **Precondition on the operator artifact**: this smoke must pass BEFORE any decision-grade W2 run; the published results artifact's W2 section (see below) must stop describing the Gemma group as quality-invalid only once real quality data exists from this smoke.
  - [x] **W2 smoke STAGED + verdict tooling landed (zero inference)** ✅ 2026-07-29 (research `c48bcb60`) — `scripts/benchmark/e5_w2_capture_smoke_check.py` gives the smoke a pass/fail verdict instead of an eyeball, checking all three required properties; property 3 runs the **real** offline scorer rather than a proxy, because (1) and (2) can both hold while every answer still strips to nothing. Per-cell parse-failure budget is the scorer's own 2, not a looser smoke-only threshold; an empty ledger fails rather than passing by vacuous truth. **Negative control already run**: against a *copy* of the historic W0 Gemma run it fails all three properties and exits 1 (430/430 empty answers, 0 reasoning fields, 43/43 parse failures in each of 10 cells) — copy, not the historic dir, since the scorer writes into the run dir and history is appended, never edited. Confirms the precise W0 mechanism: HTTP 200, `predicted_n=64`, `response_text=""` — the old parser read only `content`/`delta.content` while gemma emits `reasoning_content`, so the answer channel captured nothing and the reasoning was never persisted anywhere (hence "no raw SSE ledger"). Smoke manifest `data/batched_decode/e5_manifests_w2_capture_smoke/` uses the registered C1 (1×full+interleave) W2 shape at the Stage-B 256-token cap, production sampling, pinned 43-question batch, `decision_grade_intent=false`. 8 new tests, ruff clean. **The smoke itself still needs an inference window — it has not been run.**
- **⛔ SUSPENDED 2026-07-30 — the Stage-B result block below is retained verbatim but its throughput values and rankings are WITHDRAWN.** Every cell ran on placement shapes carrying the straddling-cpuset NUMA defect (see the suspension notice at the top of this file), so all 31 cells were bandwidth-bound at roughly one third of the model's true speed and were penalised unequally by straddle count. **The HEADLINE below — "C3 (four quarters) loses at every clean iso-T rung" — is RETRACTED**, together with the three iso-T margins (29.3% / 40.0% / 47.5% / 26.5%) and the per-model winning-shape reads; the comparison measures the defect, not the shapes. **What survives from this entry**: 31 cells at **0.0% error**, the clean-window hygiene (no `--allow-host-health-warning`, no `--skip-clean-check`, zero host-health warnings, host released with zero orphans), and the decision-grade/observation-grade bookkeeping. Re-measurement is in progress; the operator artifact must carry the retraction. ORIGINAL ENTRY:
- [x] **E5 Stage-B COMPLETE ✅ 2026-07-29 — 31 cells, three model groups, 0.0% error on every cell, 26/31 decision-grade.** Runs `e5-w1-qwen36-20260729T154725Z` (11 cells, 9 DG), `e5-w4-80b-20260729T165639Z` (12, 10 DG), `e5-w2-gemma-20260729T183151Z` (8, 7 DG). No `--allow-host-health-warning`, no `--skip-clean-check`, zero host-health warnings, host released 18:45:19Z with zero orphans. **HEADLINE: C3 (four quarters) loses at every clean iso-T rung in all three groups** — W1 C2@8 > C1@16 by 29.3%; W2 C1 > C3 by 40.0% (T=8) and 47.5% (T=16); W4 C1b@4 > C3@2 by 26.5%, tie at T=16. All `mixed_metric_basis: false`. **Quarters is the realized production shape**, so this reverses W0 on the axis that matters. The *winning* shape is model-dependent — 35B wants one half, gemma one full machine + interleave, 80B two node-local halves — which is itself the slot-fabric finding. **Evidence for a provisioning decision, not the decision**: one pass per cell, T=32 pending offline re-derivation. The local operator artifact was updated in place with the W0 grids retained verbatim.
- [x] **R1's basis caveat is PRESENTATIONAL — a consumer cannot see it** ✅ 2026-07-29 (auditor-verified at the line). `server_numa_np_sweep.py:2162` sets `mixed_metric_basis`; `:2163-2168` attaches a note whose own words are *"verdict caveated, not decision-grade"*; then `:2172-2181` sets `status = "winner"` **without ever reading the flag**. It reaches output only at `:2695`, appended to the human-readable summary line — so a human reading prose sees the caveat while a consumer joining on `status`/`winner_config` ingests a caveated verdict as decision-grade. **Fix shape (instrument code, human-gated, not applied):** when the flag is true, `status` must not be plain `winner` — emit `winner_caveated` or `insufficient_data`, changing the field a consumer keys on while keeping the margin and note. Same class as the day's other findings: *the instrument knows; the output does not carry the knowledge.*
- [ ] **E5 W1-W4 runs — UNBLOCKED (reboot landed); awaiting an exclusive inference window** — the `BLOCKED_ON_OPERATOR_SCHEDULED_REBOOT` gate is **lifted** (host rebooted 2026-07-29 ~13:42Z; uptime well inside the P-BENCH decision-grade window). All prep is complete and dry-run-verified — see the two ✅ items above and the runbook `epyc-inference-research/data/batched_decode/E5_STAGE_B_RUNBOOK.md`. Remaining blocker is **scheduling, not readiness**: E5 decision-grade is mutually exclusive with ANY llama-server on the host (`host_health_warnings()` counts `existing_llama_processes` **unfiltered**; `--coexist-allow-pattern` relaxes only `ensure_clean_runtime` and teardown, not the health gate — enforced at run start **and** per-cell mid-run, so a stack bringup mid-window kills the remaining cells). Do **not** pass `--allow-host-health-warning`/`--skip-clean-check` here: both force `decision_grade=false` for the whole run (they were correct for W0 at 20-day uptime; they are wrong now). Original text retained below for the record. ORIGINALLY: **BLOCKED_ON_OPERATOR_SCHEDULED_REBOOT** — all W0-derived execution prep is complete, but operator-scheduled reboot remains a hard P-BENCH-1/3 boundary. After reboot, run W1-W4 only in the quiet window; W2 additionally requires its focused post-fix capture smoke. R1-R4 remain withheld until clean decision-grade Stage-B cells exist.
  - **Operator-facing artifact MUST be updated in place when W1-W4 land, not left stale.** The authoritative local E5 results record is `artifacts/operator/e5_w0_preliminary_results.html`; its sibling markdown declares itself superseded and non-authoritative and must not be used as a generation source. The HTML currently leads with an OBSERVATION-GRADE banner (W0 ran under `--allow-host-health-warning` at 20d uptime). When decision-grade results land: (1) update the local HTML in place from the verified run evidence; (2) rewrite the OBSERVATION-GRADE banner/framing, not just the numbers — it is false once decision-grade figures exist, and decision-grade figures must carry the full claim grammar `(metric, protocol-id, n/reps, date, attestation ref)` per `MEASUREMENT.md`; (3) RETAIN the W0 scout figures alongside the new W1-W4 decision-grade figures — per `MEASUREMENT.md` historical numbers are era-labelled and appended, never edited to "fix" them, so any scout-vs-confirmed drift stays visible; (4) the W2 subsection specifically must keep stating quality-invalid status until the focused post-fix capture smoke (above) has passed and real quality data exists. Hosted presentation mirrors are outside this task.
- [x] **ROOT CAUSE FOUND — E5 measured through a straddling-cpuset NUMA defect; all Stage-B + W0 throughput SUSPENDED** ✅ 2026-07-30 — the swept placement shapes inherit the production wiring's defect: `stack_numa.py:66-67` `NUMA_NODE0 = "0-47,96-143"` / `NUMA_NODE1 = "48-95,144-191"` each straddle a **pair** of NPS4 nodes (`node0 = 0-23,96-119`, `node1 = 24-47,120-143`, `node2 = 48-71,144-167`, `node3 = 72-95,168-191`) and are launched with **no `numactl --interleave`**, so weights first-touch onto a single node and the other node's threads pay a remote-access penalty on every weight read — the E5 affinity artifact for this shape recorded `pages_by_node {N0: 9226101} / total 9226101`, all 35.2 GiB on node0 under a node0+node1 thread team. **`--interleave` binds at FIRST TOUCH only**, hence a silent no-op against a warm page cache: the defect survives casual checking and a warm re-test appears to confirm the bad number. **Quantified** (`llama-bench` tg128, no spec-dec, `Qwen3.6-35B-A3B-MTP-Q8_0`): straddling+no-interleave **warm = the current production wiring** `7.81 ± 3.82` t/s; same cold `10.28`; straddling **+interleave** cold `-t 96` `15.35`; **full machine `taskset -c 0-95` + `numactl --interleave=all` cold `-t 96` = `23.43 ± 0.07`** — a **3.0×** gap, i.e. Stage-B priced the frontdoor model at ~one third of its true speed. With MTP spec-dec ON at the winning placement, single stream measures **36-39** t/s, independently matching the AutoPilot production anchor (`median_request_tps` median **35.7**, n=154, band 35-40). **Instrument sound**: a single-NPS4-node arm (24 physical cores, `-t 48`) measured `8.80` vs the registry-documented `8.90` — 1% match. **Ruled out**: v8 kernel regression (v7 and v8 both `9.76`, identical), iqk (never engages for Q8_0 — gated behind an unset `GGML_IQK_Q8_0`), MTP head overhead, mmap page-faulting. Suspension notice + per-block retraction markers landed at the top of this handoff; suspended numbers retained verbatim per the append-never-edit rule.
- [ ] **RE-MEASURE E5 Stage-B on the corrected placement** — re-run the 31-cell Stage-B grid (W1 `qwen36_q8_0`, W2 gemma, W4 `qwen3_next_80b`) with correct NUMA policy per shape, then re-derive R1-R4. Binding requirements: (a) **add full machine `0-95` + `numactl --interleave=all` as a swept shape for `qwen36_q8_0` and `qwen3_next_80b`** — today's winner was present in the old grid only as gemma's `C1`, so the qwen36/80B grids could not have found it; (b) every straddling-cpuset cell must either carry `--interleave` or be declared as an explicit defect-replication control, never left implicit; (c) **`drop_caches` before every cell and record `pages_by_node`** — `--interleave` is a no-op on a warm cache, so a warm cell silently measures the defect; (d) attest the numactl policy per instance alongside the existing affinity preflight, and fail closed when policy and cpuset disagree; (e) reuse the existing harness unchanged (it is not implicated — see SURVIVES in the notice) so the re-run stays comparable, and re-check the still-open T=32 `empty_trimmed_window` and R2/R4 mixed-basis items above against the new runs. Needs an exclusive inference window under the same clean-window terms as Stage-B.
- [ ] **Fix the production cpuset wiring in `stack_numa.py` (orchestrator; gated on the re-measurement)** — `frontdoor` idx0 (port 8070) and `ingest_long_context` idx0 (port 8085) both pin `NUMA_NODE0 = "0-47,96-143"` with **no `numactl_policy`**, which is the defective shape measured at `7.81` t/s warm. `eval_batch_frontdoor` (18070) uses the same cpuset but does carry `interleave=all`; `worker_general` (8083) already uses `NUMA_FULL` + `interleave=all` and is unaffected. **The justification comment in the file is invalid evidence**: the April 2026-04-17 head-to-head (`26.60` interleave vs `27.06` NUMA_NODE0, "B beats A by 1.7%") predates the 2026-04-24 NPS4 reboot — the cpuset genuinely WAS one node then — and its source CSV records `spec == "baseline"`, i.e. speculative decoding OFF. `ingest_long_context` cites that same dead head-to-head to "keep parity" and inherits the defect with no data of its own. The `NUMA_NODE0`/`NUMA_NODE1` names are NPS2-era artefacts and have been misleading since the NPS4 reboot; the `NUMA_Q*` quarters are correctly named and ARE the four NPS4 nodes. **Status: annotated in place 2026-07-30, change deliberately NOT applied** — the wiring is held unchanged so the re-measurement stays comparable with the recorded AutoPilot operating point being re-anchored against. Production serving-path change → operator-gated; apply only once the corrected Stage-B reports.
- [ ] **Retract the suspended figures in the operator-facing E5 artifact** — the authoritative local HTML (`artifacts/operator/e5_w0_preliminary_results.html`) carries the Stage-B headline and therefore still presents retracted numbers. Add the suspension banner and the "C3 never wins" retraction while retaining the figures verbatim (append-only). Do not regenerate it from the superseded markdown.

## Gates & pitfalls

- Operator window required: per `feedback_no_concurrent_inference` / `feedback_speed_verify_via_llama_bench`, the operator runs the benches — this handoff prepares commands, harness, and analysis; schedule inside the bulk-campaign Queue-2 quiesce window (one attested reload serves all).
- Do NOT over-extrapolate A3B wins: MoE batching is weaker than dense (distinct tokens hit distinct experts → expert weight traffic grows with batch) — hence the mandatory dense control in E1.
- The 9.6× rep-1 TTFT amplification under concurrent prefill (CPU23) is real; report TTFT separately from steady-state per-stream decode or E2 will look better than it serves.
- Index results by model+quant, never by role (`feedback_model_not_role_indexing`); P-BENCH-3 preconditions (host-health tier, no concurrent inference, interleave re-warm) are binding.
- E3 before E1 is forbidden — the kernel only gets written if the measurement shows compute headroom at intermediate batch.

## Reporting

Tick waypoints here + one-line progress entry per session; on full completion delete the master-index row and move this file to `completed/`; every number follows the [MEASUREMENT.md](../../MEASUREMENT.md) claim grammar (metric, protocol-id, n, date, attest ref).

- [ ] **Eval-batch serving lane decision (tabled here 2026-07-23 from the EV-BASELINE-E7 session)**:
  the retired `eval_batch_frontdoor` lane (port 18070, warm launcher-only, -np 8 — "not a
  distinct model-routing role") posed the question: dedicated eval lane vs quiet-window 4-wide
  fan-out on production quarters (this week's proven regime). Decide WITH the E5 NUMA×batch(-np)
  mapping data, not before: E5 tells us what a batch lane costs/yields per placement. Design
  options to evaluate then: (a) no lane — quiet-window fan-out suffices; (b) resurrect a CPU lane
  as a WP-12 fleet with an eval-only role bound to it (outside-quiet-window evals without
  touching interactive traffic); (c) **push batched eval decoding to the MI210 GPU** — an
  eval-lane fleet on the GPU under heterogeneous-slot-fabric-residency.md ("everything is a
  slot"), freeing ALL CPU quarters for interactive traffic. Note: the robust eval structure these
  designs waited on now EXISTS (decision-grade P-CAL instrument, honest error rows, per-question
  artifacts, resume/retry) — the queued design ideas across the notes can now be tested properly.

## Pre-execution audit (2026-07-23)

READ-ONLY pre-execution audit of the E5 sweep design (the `2026-07-23 — E5 harness
preparation` note above), run before the execution phase against the realized system. All
claims verified with file:line citations; no inference, no process management. **Verdict:
GO-WITH-CORRECTIONS.** The design is sound, correctly scoped design-only/zero-inference, and
its R4 output already matches the ratified fabric contract. The gating work is the (unbuilt)
multi-server harness, plus three bounded corrections that do not change the sweep's shape.

### Verdict per dimension

**1. Staleness vs realized system — STALE (correctable).**
- **Fleet layer is POST-FLIP, not mid-flip.** `epyc-orchestrator` `4ca6859a` merged the fleet
  layer (2026-07-23 13:23Z) and `a172d2dd` wired `ORCHESTRATOR_FLEET_LAYER=1` as the durable
  launch default (14:22Z). The E5 design was written concurrently and CORRECTLY assumes
  post-fleet-layer serving (R3's "zero-code remap … an eval-only RoleBinding on a batch-shaped
  fleet"). Realized-first machinery (`scripts/server/realized_fleet.py`, ESC-8) is present and
  the design's realized-mode awareness is consistent. → CLEAN on this sub-point.
- **Realized stack is QUARTERS-based; C1 is NOT the live production shape.**
  `orchestration/derived/stack_priors.yaml` reports frontdoor `numa_policy:
  4x48t_quarter_instances`; `stack_numa.py:184` sets worker_general `placement_policy:
  full_disabled` (quarters-only, no 8072, DISPATCH-A 2026-07-21). The design repeatedly labels
  C1 "the current production solo shape" / "production-shape anchor". That is inaccurate for a
  quarters-only realized stack and **outright wrong for gemma**, whose live production shape is
  4×q — its 1×full (0-95) instance is DISABLED. R1's own tie-break ("prefer the status-quo
  quarters split") already treats quarters as status-quo, contradicting the grid-note. FIX:
  relabel C1 as a provisioning CANDIDATE + E1-continuity anchor; C3 (quarters) is the
  status-quo production shape. (Sweeping C1 as a candidate is fine — the correction is
  interpretive, not structural.)
- **E1/E2 baseline numbers are PRE-v7 historical priors.** `instrument_eras.yaml` E6-cpu-kernel
  boundary = 2026-07-20T13:30:13Z (v7 cutover, `6ad45fa3ff`). The E1 A3B ladder (2026-07-03 /
  07-06) and the E2 rows (batch 2.258 vs current 10.970, 2026-07-03) were measured on v6+iqk
  (E5-cpu-kernel era), pre-E7-eval-instrument (2026-07-21) and pre-E4-quality-core-v2
  (2026-07-23). Under E6 they are **demote-to-prior — direction/hypothesis only, cannot gate**.
  The design uses them correctly for DIRECTION (scout cross-check; April/May shape figures
  flagged hypothesis-grade). But **R3 gates the eval-lane decision on "batch 2.258 vs current
  10.970"** — a demoted number gating a decision, and the eval unit itself changed (43-q legacy
  T1 → 50-item core_v2). See correction C2.
- eval_batch_frontdoor "retired": accurate. Still in code as a warm launcher-only, default-off
  role (`stack_numa.py:88`, port 18070) — "retired" = deprovisioned, not deleted. No task
  assumes it is a live lane. → CLEAN.
- worker_vision -np: the -np>1 MTP-assert risk (`orchestrator_stack.py:779-784`) is real and
  the E5 Stage-A np×spec-dec wedge probe (design point 2) covers that class. → CLEAN.

**2. Measurement-constitution compliance — MOSTLY CLEAN; two gaps.**
- (a) codified recipe: E5 reuses `server_np_sweep.py` (the durable P-BENCH-3 harness), which
  the waypoint blesses — NOT ad-hoc `llama-bench`/`run_benchmark.py`. CLEAN. Nit: that harness
  keeps its OWN `DEFAULT_ENV` (`server_np_sweep.py:46`) instead of importing
  `scripts/lib/canonical_recipe.py` constants — a recipe-drift risk per
  `feedback_use_codified_recipes_not_memory`.
- (b) protocol id / era / attestation / decision_grade gating: all declared (design delta-spec
  e). CLEAN.
- (c) OMP stack: present and correct in `DEFAULT_ENV` (PROC_BIND=spread, PLACES=cores,
  WAIT_POLICY=active, DYNAMIC=false, KMP_BLOCKTIME=10). throttle / numa_balancing=0 /
  host-health / ps-verified kill: all enforced by the inherited harness. **GAP: `GGML_IQK=1`
  (the v7 iqk runtime gate, CLAUDE.md) is absent from `DEFAULT_ENV` and unmentioned in the
  design** — this is exactly the "missing-IQK" trap that aborted the 2026-07-07 dense-control
  run (only the re-run `…-iqk-…` was kept). See correction C1. Affinity: the design mandates
  live verification but cites a non-existent `--live-only` flag and the tool is NUMA_CONFIG-role
  -keyed (cannot gate synthesized half1/bench-port shapes) — see correction C3.
- (d) correctness pairing: design point 6 (store every response, E7-era B7 scorer offline,
  parse-fail ≤2/43 + repetition-loop gate, speed demoted to observation on a degraded cell).
  CLEAN.
- (e) quiet-window gating + instrument identity (solo vs overlapped): present — cells are
  solo instance-sets; C1b is an explicitly-labeled co-run. CLEAN.

**3. Design coherence — CLEAN.** All four waiting consumers are covered:
  (a) eval-lane → R3 (with the C2 re-baseline correction); (b) node-partitioned
  arm-parallelism → C1b (2×half) + iso-T {C1b@T/2 vs C3@T/4}; (c) slot-fabric pricing → R4
  emits MODEL-KEYED capability data, which is exactly the first population the ratified fabric
  contract asks for (`heterogeneous-slot-fabric-residency.md:117` "E5 R4 rows are the first
  population"); (d) -np sizing → R4 feeds `within-role-placement-state-machine.md`. iso-T
  arithmetic and the K-caps (total in-flight ≤43) are internally consistent (C1×{1..32},
  C1b/C2×{1..16}, C3×{1..8}). Minor: E5 sweeps a single quant per model, so the fabric
  contract's (CPU-quant, GPU-quant) pairing axis stays single-valued — out of E5 scope (quant
  choice is architect-bench's axis), acceptable.

**4. Executability — GAP (harness unbuilt) + two script-reference nits.**
- **The multi-server harness does NOT exist.** `server_np_sweep.py` is single-server (docstring
  line 2; `build_server_command` hardcodes `numactl --interleave=all` with no per-instance
  taskset pinning, lines 376-407) — it cannot run C1b/C2/C3 multi-instance cells as-is.
  `server_numa_np_sweep.py` is absent. The delta spec (a-f) is substantial (multi-launch,
  per-instance pinning, closed-loop N×K driver, per-cell affinity gate) and is correctly an
  OPEN checkbox. Implementation time is separate from the run-time estimates and is unbudgeted.
- `affinity_preflight.py` has NO `--live-only` flag (args are `--roles`, `--output`,
  `--require-memory-locality`, `--memory-locality-threshold`) and is NUMA_CONFIG-role-keyed, so
  it cannot validate E5's SYNTHESIZED half1 (`48-95,144-191`) bench-port instances without a
  cell-manifest mode. Delta-spec (d) must build this, not just wire the existing tool.
- **Models all present** (CLEAN): frontdoor `Qwen3.6-35B-A3B-MTP-Q8_0.gguf` (37.8 GB); dense
  control `Qwen3.6-27B-MTP-Q8_0.gguf` (29 GB); gemma `gemma-4-26B-A4B-it-Q4_K_M-current.gguf`
  (~14 GB); ingest `…/lmstudio-community/Qwen3-Next-80B-A3B-Instruct-GGUF/…-Q4_K_M.gguf`
  (~48 GB — the registry-declared Q4_K_M, NOT the `models/…i1-IQ2_M.gguf`; the design's "~45 GB"
  is correct). Results schema/ledger defined (E1-style manifest, `data/batched_decode/`).
- Run-time estimates (W0 ~2-2.5h … W3 ~4-6h) are plausible against the E1 decode rates.

**5. Checkbox hygiene — CLEAN (one stale prose line).** Waypoint checkboxes are accurate (E1/E2
/E3/E4 done; E5 design ✅; harness impl + W0-W3 runs open). No task assumes the eval_batch
frontdoor lane is live or pre-fence routing. Nit: the E5 waypoint PROSE (line 26) still lists
frontdoor configs as `{full},{full,q3},{full,q3,q2}` (full+quarter mixes), superseded by the
2026-07-21 mode-exclusivity contract; the design note's "Spec interpretation note" already
excludes mixed shapes from Stage B, so this is handled in the design but the waypoint sentence
is stale.

### GO / NO-GO: **GO-WITH-CORRECTIONS**

The sweep design is executable in shape and correctly gated (post-v7 quiet window, LAST behind
inference-batch-loop → architect-model-selection-bench). Predecessor status at audit time:
inference-batch-loop is parked/operator-gated (not terminal), architect-bench is "GPU bench
complete" with CPU-gated items outstanding (RP-5/RP-3/Phase-2) — confirm the operator considers
the queue clear before scheduling. Apply the three corrections below; none blocks design sign-off,
but C1 and C3 are execution-blocking (must land in the harness before any decision-grade cell).

### Corrected / added task list

- [x] ✅ 2026-07-28 VERIFIED ALREADY IMPLEMENTED (stale checkbox — landed with research `b294daa0`; independent verification at committed HEAD: harness composes env via `canonical_recipe.build_canonical_env`, fail-closes on `env_expectation` mismatch, records `ggml_iqk` in per-cell rows + run-manifest attestation; proven live in W0 `cells.jsonl`) — **C1 (execution-blocking) — set `GGML_IQK=1` per cell + record it as a manifest/attestation
  field.** Add to the harness env (or the canonical env it should import); without it, K-quant/
  legacy-quant cells (gemma Q4_K_M, dense 27B Q8) silently run without iqk — the aborted
  2026-07-07 "missing-IQK" run is the cautionary tale. Attest the iqk state alongside
  `kv_unified`.
- [x] **C2 (decision-blocking for R3) — current-arm re-baseline DONE ✅ 2026-07-23.** Measured
  FRESH under E6-cpu-kernel (v7) + E4-quality-core-v2 + WP-12 fleet layer + the **restored
  big+quarters lineup** (post-restoration, post-locality-heal), current-arm-only via
  `--skip-batch-arm`, PRODUCTION escalation (not pinned — this prices the lane as it actually
  runs): **27.546 wall-min/eval** (core_v2, 50 items, 45 scored, reliability 0.90 floor-clean,
  quality 1.667, resolved eval_concurrency 3 — the restored half occupies q0+q1 so frontdoor's
  disjoint fan-out is half+q2+q3). Report:
  `epyc-orchestrator/orchestration/reports/r3_current_arm_rebaseline_corev2_20260723/`.
  Per-item: 27.546/50 = **0.551 min/item** (0.612 per scored item) — feed this as the R3
  baseline file's `items_per_eval=50` row. Secondary observation (NOT the baseline): a
  legacy-pool-draw run under the same lane measured 21.87 min (different question set;
  `r3_current_arm_rebaseline_20260723/`). Config deltas vs the 2026-07-23-morning current-arm
  row (23.87 min): concurrency 4→3 (restored-geometry resolution), escalation pinned→production,
  lineup quarters-only→big+quarters — the morning row was a reseed input, not an R3 baseline.
  **C10-F1 addendum (2026-07-23, from the WP-12 case-10 live gate)**: the current-arm's
  within-role concurrency mechanism is **6-uvicorn-process spread × per-process per-role
  `Semaphore(1)`** (every live role resolves `get_role_max_concurrency()==1` because
  `live_warm_worker_slots()` filters `tier=="warm"` and all live roles are `hot`), with
  cross-process disjointness from region flocks — NOT a role-level concurrency cap of N. A
  `--workers 1` API serializes each role fully. Model the current-arm baseline accordingly and
  record the API worker count in the arm's attestation. Fix task filed in
  [wp12-fleet-layer-design.md](wp12-fleet-layer-design.md) (C10-F1 follow-up).
- [x] ✅ 2026-07-28 VERIFIED ALREADY IMPLEMENTED (stale checkbox — `server_numa_np_sweep.py` multi-instance N×K harness + orchestrator `affinity_preflight.py --cell-manifest` mode landed `6a55aeed`/`52978844`/`29779bcc`; hard per-cell gate confirmed: preflight before requests, non-zero exit aborts cell, `decision_grade` requires `live_affinity_verified`; 105+27 targeted tests pass at committed HEAD; all 190 committed manifests validate) — **C3 (execution-blocking) — build the multi-server harness + cell-manifest affinity gate.**
  `server_numa_np_sweep.py` (or extend `server_np_sweep.py`): per-instance taskset pinning +
  correct per-shape numactl policy (interleave only for full/gemma-MTP), multi-launch/teardown
  with ps-verified kill, closed-loop N×K driver (TTFT + per-stream p50/p95 + trimmed aggregate),
  and a per-cell affinity preflight that accepts arbitrary {cpuset, port} cells (the existing
  `affinity_preflight.py` is role-keyed and has no `--live-only` flag — extend it or add a
  manifest mode).
- **C4 ADDENDUM (2026-07-23 lineup restoration)**: the quarters-only premise is OBSOLETE — the
  operator ruled the v7-cutover big-instance drop accidental and the lineup was restored same
  day (orchestrator `95dffc88`: frontdoor half 8070 + worker full 8072 + ingest half 8085 live,
  `burst_prefer_quarters`). **C1 (1×half) is therefore the LIVE production solo shape again**
  for frontdoor/ingest (and 1×full for gemma), not merely a provisioning candidate; C3 remains
  the live burst shape. The R3 current-arm re-baseline MUST run under this restored lineup.
  Contention-matrix note: big∥quarter co-run rows are pre-v7-era priors (hash-fresh,
  semantically demoted) — E5's cells re-measure the underlying physics anyway.
- [ ] **C4 (interpretive) — relabel C1** as a provisioning candidate / E1-continuity anchor, not
  "the current production solo shape" (realized stack is quarters-only; gemma's 1×full is
  DISABLED). Optionally refresh the stale waypoint prose (line 26) to the mode-exclusive config
  list the design note already uses.
