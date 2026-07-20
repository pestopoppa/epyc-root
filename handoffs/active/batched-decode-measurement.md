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
- [ ] **E5 — NUMA×batch interaction sweep** (post-v7-promotion quiet window; the never-measured 2D cross). NUMA-split and `-np` batching have only ever been measured **separately** — NUMA-split built the pinning map; `-np` alone is E1 (single instance). **Hypothesis (roofline):** batching amortizes the per-token weight-read → shifts CPU decode **BW-bound → compute-bound** → the NUMA-locality advantage may **flip at high K**; the crossover in K is unknown and sets the slot-fabric grid shape. Directly tests whether **a single full-machine high-`-np` server beats quarter-batched servers**. **Protocol (reuse the E1 `-np` harness + P-BENCH-3):** per-model 2D grid — **N = each model's *allowed* NUMA-pinned configs** (from `scripts/server/stack_numa.py` `NUMA_CONFIG` + the safe-placement table in [within-role-placement-state-machine.md](within-role-placement-state-machine.md); e.g. frontdoor `{full},{full,q3},{full,q3,q2}`; **worker_general `{full}`-only** — no disjoint quarters, a pure-K test; architect 122B full-only) × **K = `-np ∈ {1,2,4,8,16,32}`**. Two reads: **(i) iso-concurrency** — hold total in-flight = N×K fixed (e.g. 32) and vary the split (`1×32` vs `2×16` vs `4×8` where safe-placement allows) → the direct "one big batched server vs quarter-batched" answer; **(ii)** unconstrained **peak-aggregate (N,K)**. **Metrics:** aggregate decode t/s **and** per-stream p50/p95 latency (P-BENCH-3), paired with a correctness/garbage check; era-stamped, protocol-id + attest ref. **Canonical recipe only:** OMP env stack, `scripts/server/affinity_preflight.py` **live-affinity verify per instance** (the WP-6 bad-affinity artifact is the cautionary tale), per-instance cache warming (drop_caches NUMA re-read trap), throttle check, host-health gate (uptime / `numa_balancing=0`). **Models:** `qwen36_q8_0` (frontdoor 35B-A3B) + `qwen36_27b_q8` (dense control) — both already in the E1 harness — + gemma `worker_general`. **Decides:** the (N,K) provisioning per model for the slot fabric + whether **workload-class lanes** are real (a low-K/high-K crossover). **Feeds** [within-role-placement-state-machine.md](within-role-placement-state-machine.md) per-instance `-np` sizing and [heterogeneous-slot-fabric-residency.md](heterogeneous-slot-fabric-residency.md) (provisioning-pending). **Gating:** post-v7-promotion; runs **LAST in the post-promotion queue** — `inference-batch-loop → architect-model-selection-bench → this` — operator/quiet-window, P-BENCH-3 host-health. Bench-only.

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

## Gates & pitfalls

- Operator window required: per `feedback_no_concurrent_inference` / `feedback_speed_verify_via_llama_bench`, the operator runs the benches — this handoff prepares commands, harness, and analysis; schedule inside the bulk-campaign Queue-2 quiesce window (one attested reload serves all).
- Do NOT over-extrapolate A3B wins: MoE batching is weaker than dense (distinct tokens hit distinct experts → expert weight traffic grows with batch) — hence the mandatory dense control in E1.
- The 9.6× rep-1 TTFT amplification under concurrent prefill (CPU23) is real; report TTFT separately from steady-state per-stream decode or E2 will look better than it serves.
- Index results by model+quant, never by role (`feedback_model_not_role_indexing`); P-BENCH-3 preconditions (host-health tier, no concurrent inference, interleave re-warm) are binding.
- E3 before E1 is forbidden — the kernel only gets written if the measurement shows compute headroom at intermediate batch.

## Reporting

Tick waypoints here + one-line progress entry per session; on full completion delete the master-index row and move this file to `completed/`; every number follows the [MEASUREMENT.md](../../MEASUREMENT.md) claim grammar (metric, protocol-id, n, date, attest ref).
