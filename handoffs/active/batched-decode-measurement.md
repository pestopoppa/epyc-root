# Batched-Decode Measurement (E1/E2) + Conditional 8x8 GEMM SIMD (E3)

**Status**: SPEC'D, not started (from the Fable 5 architecture review)
**Created**: 2026-06-12
**Priority**: ACTIVE-HIGH — bench-only, ~1 day for E1+E2; rank 2 in the findings-06 "what remains" table; an evidence vacuum under the highest-volume workload (the eval harness)
**Spec**: [fable5-findings-06-kernel-and-concurrency.md](fable5-findings-06-kernel-and-concurrency.md) §2 (E1/E2/E3) + [MEASUREMENT.md](../../MEASUREMENT.md) P-BENCH-3 — read both before claiming any waypoint
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

## Gates & pitfalls

- Operator window required: per `feedback_no_concurrent_inference` / `feedback_speed_verify_via_llama_bench`, the operator runs the benches — this handoff prepares commands, harness, and analysis; schedule inside the bulk-campaign Queue-2 quiesce window (one attested reload serves all).
- Do NOT over-extrapolate A3B wins: MoE batching is weaker than dense (distinct tokens hit distinct experts → expert weight traffic grows with batch) — hence the mandatory dense control in E1.
- The 9.6× rep-1 TTFT amplification under concurrent prefill (CPU23) is real; report TTFT separately from steady-state per-stream decode or E2 will look better than it serves.
- Index results by model+quant, never by role (`feedback_model_not_role_indexing`); P-BENCH-3 preconditions (host-health tier, no concurrent inference, interleave re-warm) are binding.
- E3 before E1 is forbidden — the kernel only gets written if the measurement shows compute headroom at intermediate batch.

## Reporting

Tick waypoints here + one-line progress entry per session; on full completion delete the master-index row and move this file to `completed/`; every number follows the [MEASUREMENT.md](../../MEASUREMENT.md) claim grammar (metric, protocol-id, n, date, attest ref).
