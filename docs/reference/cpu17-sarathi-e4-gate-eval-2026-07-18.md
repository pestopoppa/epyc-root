# CPU17 Sarathi / Batched-Decode E4 Gate Evaluation — 2026-07-18

**Scope**: no-inference evaluation from existing evidence only. No production
kernel, stack, registry, or active index was modified.

**Verdict**: CPU17/Sarathi is **partially reopened to measurement only**, not to
implementation. Batched-decode E2 satisfies the old "multi-tenant / eval-batch
serving" trigger strongly enough to justify a targeted long-prompt mid-stream
TBT gate if eval-batch serving remains a production candidate. It does not yet
justify Sarathi scheduler work, `-ub` default changes, or production rollout.

## Current Evidence

- `handoffs/active/sarathi-serve-cpu-evaluation.md` says CPU17 was
  deprioritized for the single-user decode regime, not empirically closed for
  multi-tenant serving. Its explicit reopen trigger is a workload shift to
  multi-tenant API or prefill-heavy serving.
- The 2026-04-26 CPU17 quick probe
  (`/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-26-cpu17/SUMMARY.md`)
  swept `-ub {128,256,512,1024,2048}` on Coder-30B Q4_K_M with combined
  `pp4096 + tg32`. Decode stayed flat at about `46-47 t/s` across all `-ub`
  values, while smaller chunks damaged prefill substantially (`-52.3%` at
  `-ub 128`, `-30.0%` at `-ub 256`, `-13.2%` at the default `-ub 512` versus
  `-ub 2048`). That closes the single-user tuning case.
- CPU23 Phase 2.2
  (`/mnt/raid0/llm/epyc-inference-research/data/cpu_optimization/2026-04-28-cpu23-interference-metrics/decision.md`)
  found first-decode TTFT amplification under concurrent prefill: `9.6x` on
  sync-bound MoE Coder-30B, `1.15x` on BW-bound frontdoor MoE, and `1.08x` on
  dense/hybrid. Steady-state decode during ongoing prefill stayed within about
  `+/-2%` of baseline. CPU23 explicitly deferred multi-concurrent-decode
  interference unless multi-tenant production becomes relevant.
- `handoffs/active/batched-decode-measurement.md` E2 is decision-grade
  keep-candidate evidence for an eval-batch serving class: one full
  `qwen36_q8_0 -np 8` batch arm completed a 43-question eval in `2.258`
  wall-minutes versus `10.970` wall-minutes for the current 3-concurrent
  EvalTower path, a `4.858x` wall-time speedup. Activation smoke later passed
  and rolled back cleanly; representative EvalTower quality/reliability/
  throughput telemetry is still the remaining gate before any default path
  change.
- The CPU optimization index already classifies the E4 outcome as a doc-only
  partial reopen: CPU17 reopens only to the long-prompt mid-stream TBT
  measurement gate because eval-batch is the named workload class.

## Gate Decision Options

1. **Re-close CPU17 entirely**: reject. This would ignore that E2 produced a
   real eval-batch serving candidate, which is the workload-shift trigger named
   by the CPU17 handoff.
2. **Reopen CPU17 to implementation**: reject. Existing data does not show that
   chunked-prefill scheduling improves eval-batch quality, wall time, or TBT on
   this host. The single-user `-ub` sweep was negative for smaller chunks, and
   CPU23 only showed a first-token tail pathology, not steady-state decode loss.
3. **Reopen CPU17 to measurement only**: accept. The next valid step is a narrow
   measurement of long-prompt arrival during in-flight eval-batch decode, with
   TBT spike, p95/p99 latency, eval wall time, and aggregate throughput compared
   across the default scheduler and candidate `-ub` settings.

## Already Closed

- Single-user CPU17 tuning is closed negative: no decode-speed signal appeared
  across `-ub`, and smaller chunks regress prefill.
- Default production behavior should remain unchanged. Existing continuous
  batching plus default `-ub 512` remains the practical baseline.
- No Sarathi-specific scheduler integration is justified from the current
  evidence.
- No production v6 kernel or production stack change is implicated by this
  evaluation.

## What Would Reopen It Further

CPU17 should move beyond "measurement only" only if a clean-window eval-batch
interference run shows a material tail-latency win without unacceptable
throughput loss. A concrete reopen bar:

- workload: the actual eval-batch serving shape or its faithful harness;
- scenario: long prompt arrives while multiple decode streams are already
  in-flight;
- comparison: default `-ub 512` versus smaller/larger candidate chunk settings,
  and preferably default scheduler versus any explicit chunked-prefill policy;
- required signal: at least `30%` reduction in in-flight decode TBT spike or
  p95/p99 latency, with no material regression in eval wall-minutes, success
  rate, or quality telemetry.

If the eval-batch lane is killed by representative EvalTower telemetry, CPU17
should return to parked/deprioritized status without running this measurement.

## Is Measurement Justified Now?

Not as a standalone operator interruption today. The evidence justifies adding
CPU17's TBT-interference cell to the next already-approved eval-batch or
clean-window measurement package, not launching an immediate separate inference
window.

Reasoning: E2 proves eval-batch serving is worth continued evaluation, but the
remaining upstream gate is still representative EvalTower quality/reliability/
throughput telemetry. CPU17 measurement becomes decision-useful only if that
lane continues to look deployable. Until then, Sarathi-specific inference would
compete with higher-priority clean-window work while producing only conditional
evidence.

## Recommended Next Action

Keep CPU17 marked as **measurement-gated** and attach one no-default-change
TBT-interference cell to the next eval-batch serving window. Do not implement a
Sarathi scheduler, change `-ub` defaults, or touch production v6 unless the
measurement clears the tail-latency gate above and the eval-batch lane remains a
production candidate.
