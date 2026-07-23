# Batched-Decode Measurement (E1/E2) + Conditional 8x8 GEMM SIMD (E3) + NUMA×batch (E5)

**Status**: IN PROGRESS — A3B E1 and E2 decision-grade evidence landed 2026-07-03; E2 is a keep-candidate for an eval-batch serving class; shadow metadata/feature-gate, default-off warm eval-batch frontdoor hook, guarded activation probe, and plan-only/apply activation-window runners landed; 2026-07-05 activation window smoked through and rolled back cleanly; dense-control E1 tail completed 2026-07-07 as useful but not pristine host-exclusive evidence · **E5 (NUMA×batch interaction sweep) added 2026-07-20 — runs LAST in the post-v7-promotion queue: inference-batch-loop → architect-model-selection-bench → this.**
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
prod cpuset changes, no §H recert trigger. (iii) The C1b half-pair co-run has
never been measured (J5 measured quarter pairs) — SAME-SHAPE evidence for
WP-9's distinct-halves design; WP-9's actual mixed pair (frontdoor-half0 +
ingest-half1, different models) remains its own §H contention-matrix cell at
the lineup event.

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
- [ ] E5 harness implementation (research-repo session; harness delta spec above = audit C3, with C1's `GGML_IQK=1` env+attestation — both execution-blocking before any decision-grade cell)
- [ ] E5 W0-W3 runs (operator quiet windows, after the post-promotion queue)

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

- [ ] **C1 (execution-blocking) — set `GGML_IQK=1` per cell + record it as a manifest/attestation
  field.** Add to the harness env (or the canonical env it should import); without it, K-quant/
  legacy-quant cells (gemma Q4_K_M, dense 27B Q8) silently run without iqk — the aborted
  2026-07-07 "missing-IQK" run is the cautionary tale. Attest the iqk state alongside
  `kv_unified`.
- [ ] **C2 (decision-blocking for R3) — do not gate on the pre-v7 E2 numbers.** Re-baseline the
  "current EvalTower fan-out" arm FRESH under E6-cpu-kernel (v7) + E4-quality-core-v2 + the
  WP-12 fleet layer before applying R3; the batch arm is already re-measured by the E5 cells.
  Treat E1's C1@1 tie and the "batch 2.258 / current 10.970" figures as direction-only priors.
- [ ] **C3 (execution-blocking) — build the multi-server harness + cell-manifest affinity gate.**
  `server_numa_np_sweep.py` (or extend `server_np_sweep.py`): per-instance taskset pinning +
  correct per-shape numactl policy (interleave only for full/gemma-MTP), multi-launch/teardown
  with ps-verified kill, closed-loop N×K driver (TTFT + per-stream p50/p95 + trimmed aggregate),
  and a per-cell affinity preflight that accepts arbitrary {cpuset, port} cells (the existing
  `affinity_preflight.py` is role-keyed and has no `--live-only` flag — extend it or add a
  manifest mode).
- [ ] **C4 (interpretive) — relabel C1** as a provisioning candidate / E1-continuity anchor, not
  "the current production solo shape" (realized stack is quarters-only; gemma's 1×full is
  DISABLED). Optionally refresh the stale waypoint prose (line 26) to the mode-exclusive config
  list the design note already uses.
