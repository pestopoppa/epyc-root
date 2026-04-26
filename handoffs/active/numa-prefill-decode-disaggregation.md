# NUMA-Disaggregated Prefill / Decode — Feasibility Investigation

**Status**: stub (created 2026-04-26 via research intake batch — disaggregated-serving literature)
**Categories**: inference_serving, hardware_optimization, kv_cache
**Priority**: MEDIUM (feasibility-gated; could collapse to NOT-PURSUED if Tier 2b critique generalizes to our regime)
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md), [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**: [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) (DS-7 already pre-warms 1×96t prefill-favorable + 4×48t decode-favorable instances per role — closest existing analogue)

## Objective

Evaluate whether GPU-style prefill/decode disaggregation (DistServe, Splitwise, Mooncake) yields net throughput-under-SLO gains on EPYC 9655's 2-socket / 8-NUMA-node topology by routing prompt-prefill work to a compute-favorable instance and decode work to a bandwidth-favorable instance, with KV migration over xGMI.

**This is a feasibility study, not an implementation proposal.** Tier 2b literature search (2026-04-26) surfaced strong counter-evidence; the burden of proof for proceeding is on this stub.

## Research Context

| Intake ID | Title | Verdict | Notes |
|-----------|-------|---------|-------|
| intake-459 | DistServe (arXiv:2401.09670) | worth_investigating | Foundational; 4.48× throughput on summarization vs vLLM colocated |
| intake-460 | Splitwise (arXiv:2311.18677) | new_opportunity | Goodput-under-SLO framing; per-phase machine specialization |
| intake-472 | Mooncake (arXiv:2407.00079) | adopt_patterns | KVCache-centric pool + cache-aware Conductor scheduler |
| intake-468 | ORCA (OSDI'22, no arXiv) | adopt_patterns | Iteration-level + selective batching foundation |
| intake-469 | Sarathi v1 (arXiv:2308.16369) | superseded by intake-048 (Sarathi-Serve) | Counter-architecture: chunked prefill instead of disagg |

## Tier 2b Counter-Evidence (must be addressed before proceeding)

1. **Workload-sensitivity**: Disaggregation can REGRESS 20-30% on small workloads, short prompts, or low concurrency (BentoML handbook; vLLM disagg_prefill experimental docs explicitly state "does not improve throughput").
2. **Sarathi-Serve counter-argument** (intake-048): chunked prefill + stall-free hybrid batching achieves the same prefill/decode interference elimination WITHOUT KV migration. Sarathi authors note disagg "could be challenging in the absence of high-bandwidth interconnects."
3. **NVIDIA "Beyond the Buzz"** (arXiv:2506.05508, Jun 2025 — first systematic study): disagg only wins on prefill-heavy traffic + larger models. Static splits lose. Requires dynamic rate-matching + elastic scaling.
4. **KV-transfer overhead dominates at short prompts / low QPS**: Splitwise §overhead and Together.ai's CPD blog both show transfer becoming a significant TBT fraction even on InfiniBand.
5. **EPYC-specific bandwidth concern**: xGMI inter-socket ≈ 64 GB/s/dir vs NVLink ≈ 900 GB/s. KV-transfer tax on EPYC is **proportionally worse** than on the GPU systems where these papers were validated.
6. **Single-user regime mismatch**: Per `feedback_canonical_baseline_protocol`, our production target is single-session inference. Disagg's win condition is **multi-tenant, prefill-heavy, long-context, large model** — opposite of our regime. The user-flagged "EPYC NUMA analogue" intuition runs into a real workload-regime wall.

## Key Question

Is there ANY workload regime on this host where NUMA-disaggregated prefill/decode beats both:
- (a) the existing DS-7 dynamic stack with single-instance 96t prefill-favorable + 4×48t decode-favorable (which is already a soft form of phase specialization), AND
- (b) chunked-prefill / Sarathi-Serve-style hybrid batching?

Plausible candidates for "yes":
- Large-batch seeding runs (bench/eval) where TTFT matters less and prefill is genuinely compute-bound
- Long-context (32k+) prompts where prefill dominates and KV-transfer overhead amortizes
- Multi-replica autoresearch sessions with heterogeneous prompt lengths

Plausible candidates for "no" (default expectation):
- Interactive single-user sessions
- Short-context coding/chat workloads
- REAP-246B / large MoE that already saturates aggregate bandwidth from a single instance

## Proposed Phase 0 — Cheap Falsification Test (before any implementation)

Before writing any code, validate the bandwidth premise:
1. Measure xGMI (inter-socket) sustained KV-cache-shaped transfer bandwidth empirically. Compare against KV-cache size for a representative 30B-A3B prompt at 4k / 16k / 32k context.
2. Compute: at what context length does transfer time drop below, say, 10% of the corresponding decode time?
3. If the cross-over context is unrealistically high (>32k for our typical workloads), close the handoff with a Phase 0 falsification report and move on.

If Phase 0 passes: proceed to Phase 1 (single-prompt prototype with manual KV migration via `--kv-cache-export` / shm).

## Open Questions

- What does Sarathi-Serve performance look like on EPYC NUMA? (Cheaper to evaluate than disagg; may obviate this stub entirely.)
- Does Mooncake's KVCache pool design (intake-472) translate to NUMA DRAM tiering even without disagg, as a pure prefix-cache improvement?
- Does the existing DS-7 quarter-scheduler already capture most of the available gain via instance specialization?

## Notes

- User flagged disaggregation as the "most interesting finding" of the 2026-04-26 intake batch, motivating this stub. Tier 2b critique surfaced after that flag; this stub records the qualified scope honestly.
- Do NOT propagate the 4.48× / 1.4× / 525% headline numbers from DistServe / Splitwise / Mooncake without the workload caveats above. Those are goodput-under-SLO multi-tenant GPU numbers, not transferable defaults.
- Closely related: [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) Phase F (KVCOMM) is the existing closest-analogue work and should be the integration point if this stub advances past Phase 0.
