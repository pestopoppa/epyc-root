# NUMA-Disaggregated Prefill / Decode — Feasibility Investigation

**Status**: stub (created 2026-04-26 via research intake batch — disaggregated-serving literature)
**Categories**: inference_serving, hardware_optimization, kv_cache
**Priority**: MEDIUM (feasibility-gated; could collapse to NOT-PURSUED if Tier 2b critique generalizes to our regime)
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`inference-research-index.md`](inference-research-index.md), [`inference-research-index.md`](inference-research-index.md)
**Related**: [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) (the live CPU shapes are one full 96t instance and two 48t halves per quarterable role — quarters retired 2026-07-30, numa-topology-cutover-resume-20260730.md:96 — the closest existing analogue)

**Hygiene note (2026-05-27)**: Second-pass backlog audit flagged this handoff for DEREFERENCE. Keep the active surface to the Phase 0 xGMI KV-transfer falsification test and the multi-tenant reopen condition; move chronology/literature context out of domain index rows.

> **Correction 2026-09-26 (research intake `intake/orch-prior-art-20260926`, `intake-1810#02`):** this stub's topology premise is wrong for this host. The EPYC 9655 host is **one socket, NPS4 = 4 NUMA nodes** (`lscpu`: `Socket(s): 1`, `NUMA node(s): 4`, captured 2026-09-26 in `/mnt/raid0/llm/tmp/dive-intake-1810/sources/host_lscpu_20260926.txt`). There is **no xGMI inter-socket link**, so the Phase 0 xGMI KV-transfer falsifier cannot run as written. Between NPS4 nodes, KV in DRAM stays addressable from every node: there is no copy to make, only a remote-node read penalty. The disaggregation that stays live here is the one intake-1810 measures: **GPU prefill vs CPU decode** over one DRAM-resident weight copy. llama.cpp's op-offload already does that split inside one process (KV in host RAM, experts streamed per ubatch, `fable5-window2-findings-02-heterogeneous-gpu.md:165-167`). The open question is therefore whether a *separate* prefill instance ever beats it. The multi-tenant reopen trigger is already recorded as fired (`sarathi-serve-cpu-evaluation.md:12`, 2026-07-18).

## Objective

Evaluate whether prefill/decode disaggregation yields net throughput-under-SLO gains on this host — one EPYC 9655 socket (NPS4, 4 NUMA nodes) plus one MI210 — in the form intake-1810 measures: long prefill on the GPU with weights streamed from DRAM, decode on the CPU against the same DRAM-resident weight copy, short prompts prefilled on the CPU. *(Re-scoped 2026-09-26; the original 2-socket / 8-node / KV-over-xGMI premise does not match the host — see the correction note above.)*

**This is a feasibility study, not an implementation proposal.** Tier 2b literature search (2026-04-26) surfaced strong counter-evidence; the burden of proof for proceeding is on this stub.

## Research Context

| Intake ID | Title | Verdict | Notes |
|-----------|-------|---------|-------|
| intake-459 | DistServe (arXiv:2401.09670) | worth_investigating | Foundational; 4.48× throughput on summarization vs vLLM colocated |
| intake-460 | Splitwise (arXiv:2311.18677) | new_opportunity | Goodput-under-SLO framing; per-phase machine specialization |
| intake-472 | Mooncake (arXiv:2407.00079) | adopt_patterns | KVCache-centric pool + cache-aware Conductor scheduler |
| intake-468 | ORCA (OSDI'22, no arXiv) | adopt_patterns | Iteration-level + selective batching foundation |
| intake-469 | Sarathi v1 (arXiv:2308.16369) | superseded by intake-048 (Sarathi-Serve) | Counter-architecture: chunked prefill instead of disagg |
| intake-1810 | Cloud-grade-SLO MoE serving on dual EPYC 9355 + 2× RTX 5090 (OSDI'26) | adopt_patterns | dive-verified. Long prefill → GPU weight streaming, decode → CPU over ONE shared DRAM weight copy, <2K chunked, decode batched to a target (intake-1810#02). Its 4K switch is a policy on an unquantified PCIe 5.0 link, not a crossover (intake-1810#01). The disaggregated form dedicates a GPU to prefill; KV handoff not costed. No code released. |
| intake-1817 | Dynamo PR #7977 — heterogeneous XPU-prefill / CPU-decode example | declined (port) | dive-verified. Examples-only launch scripts; no device-class routing or Planner support (intake-1817#0, intake-1817#2). The mechanism lives in vLLM's CPU_ATTN decoder + NIXL KV transfer (intake-1817#5); we serve llama.cpp, dual residents are quant-asymmetric, and the in-process op-offload split (correction note) needs no KV handoff. |

## Tier 2b Counter-Evidence (must be addressed before proceeding)

1. **Workload-sensitivity**: Disaggregation can REGRESS 20-30% on small workloads, short prompts, or low concurrency (BentoML handbook; vLLM disagg_prefill experimental docs explicitly state "does not improve throughput").
2. **Sarathi-Serve counter-argument** (intake-048): chunked prefill + stall-free hybrid batching achieves the same prefill/decode interference elimination WITHOUT KV migration. Sarathi authors note disagg "could be challenging in the absence of high-bandwidth interconnects."
3. **NVIDIA "Beyond the Buzz"** (arXiv:2506.05508, Jun 2025 — first systematic study): disagg only wins on prefill-heavy traffic + larger models. Static splits lose. Requires dynamic rate-matching + elastic scaling.
4. **KV-transfer overhead dominates at short prompts / low QPS**: Splitwise §overhead and Together.ai's CPD blog both show transfer becoming a significant TBT fraction even on InfiniBand.
5. **EPYC-specific bandwidth concern**: xGMI inter-socket ≈ 64 GB/s/dir vs NVLink ≈ 900 GB/s. KV-transfer tax on EPYC is **proportionally worse** than on the GPU systems where these papers were validated. *(Void on this host, 2026-09-26: single socket, no xGMI — see the correction note. The link that matters is PCIe Gen4 x16 to the MI210, measured H2D 28.89 GB/s, gpu-acceleration-path.md:313-316.)*
6. **Single-user regime mismatch**: Per `feedback_canonical_baseline_protocol`, our production target is single-session inference. Disagg's win condition is **multi-tenant, prefill-heavy, long-context, large model** — opposite of our regime. The user-flagged "EPYC NUMA analogue" intuition runs into a real workload-regime wall.

## Key Question

Is there ANY workload regime on this host where NUMA-disaggregated prefill/decode beats both:
- (a) the existing stack shapes (one full 96t prefill-favorable instance + two 48t halves), which is already a soft form of phase specialization, AND
- (b) chunked-prefill / Sarathi-Serve-style hybrid batching?

Plausible candidates for "yes":
- Large-batch seeding runs (bench/eval) where TTFT matters less and prefill is genuinely compute-bound
- Long-context (32k+) prompts where prefill dominates and KV-transfer overhead amortizes
- Multi-replica autoresearch sessions with heterogeneous prompt lengths

Plausible candidates for "no" (default expectation):
- Interactive single-user sessions
- Short-context coding/chat workloads
- REAP-246B / large MoE that already saturates aggregate bandwidth from a single instance

## Proposed Phase 0 — re-scoped 2026-09-26 (original xGMI test void on a 1-socket host)

Phase 0 is the CPU-vs-MI210 prefill crossover, owned by mi210-big-model-and-acceleration-roadmap.md PF1 (not duplicated here). The superseded xGMI steps asked for inter-socket KV-transfer bandwidth; there is no inter-socket link on this host.

**Reopen trigger (durable, no checkbox until it fires):** PF1 reports a GPU-prefill regime (L* ≤ 32K). Then NPD-1: on the served over-HBM MoE, measure decode TPOT inflation while ONE concurrent long prefill runs through in-process op-offload (the interference 1810 disaggregates away; CPU23 measured 9.6× first-decode TTFT amplification under concurrent CPU prefill, sarathi-serve-cpu-evaluation.md:110). Spec a separate prefill instance only if the inflation exceeds a bound predeclared in that run's manifest. If PF1 finds no regime ≤ 32K, close this handoff's GPU branch; the CPU-only question stays with INF-49.

## Open Questions

- What does Sarathi-Serve performance look like on EPYC NUMA? (Cheaper to evaluate than disagg; may obviate this stub entirely.)
- Does Mooncake's KVCache pool design (intake-472) translate to NUMA DRAM tiering even without disagg, as a pure prefix-cache improvement?
- Does the existing DS-7 quarter-scheduler already capture most of the available gain via instance specialization?

## Notes

- User flagged disaggregation as the "most interesting finding" of the 2026-04-26 intake batch, motivating this stub. Tier 2b critique surfaced after that flag; this stub records the qualified scope honestly.
- Do NOT propagate the 4.48× / 1.4× / 525% headline numbers from DistServe / Splitwise / Mooncake without the workload caveats above. Those are goodput-under-SLO multi-tenant GPU numbers, not transferable defaults.
- Closely related: [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) Phase F (KVCOMM) is the existing closest-analogue work and should be the integration point if this stub advances past Phase 0.

## Progress checklist

- [ ] BLOCKED on mi210-big-model-and-acceleration-roadmap.md PF1 (CPU-vs-MI210 prefill crossover); the xGMI falsifier is void on a 1-socket host (2026-09-26); then NPD-1 per the reopen trigger, or close the GPU branch
