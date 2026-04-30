# Qwen3.6-27B Dense — CPU Feasibility Evaluation

**Status**: stub
**Created**: 2026-04-24 (via research intake deep-dive — intake-455)
**Categories**: local_inference, hardware_optimization, benchmark_methodology
**Priority**: MEDIUM (potential coder/worker model candidate, not yet validated)
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Distinct from**: [`qwen36-production-upgrade.md`](qwen36-production-upgrade.md) (35B-A3B MoE, not this 27B dense-FFN hybrid)
**Related**: [`gpu-acceleration-path.md`](gpu-acceleration-path.md) (where 4090 spec-dec numbers from intake-455 are bookmarked)

## Objective

Evaluate Qwen3.6-27B (released 2026-04-22) as a potential CPU candidate for the coder/worker slot on EPYC 9655. Determine whether the model warrants a registry entry by measuring throughput against the BW-roofline ceiling and quality against the current `coder_escalation` model (Qwen2.5-Coder-32B) on the agentic-coding eval harness.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-455 | Qwen3.6-27B Spec-Decoding on RTX 4090 with 1.7B Same-Family Draft (community note) | low (CPU-foreclosed for spec-dec) | worth_investigating |

Deep-dive: [`research/deep-dives/qwen36-27b-dense-spec-dec-cpu-feasibility.md`](../../research/deep-dives/qwen36-27b-dense-spec-dec-cpu-feasibility.md)

## Architecture clarification (CRITICAL — read before any spec-dec experiments)

Qwen3.6-27B is **NOT** true dense — it is hybrid **Gated-DeltaNet + Gated-Attention** (3:1 GDN:attention; 64 layers total = 48 GDN + 16 Gated-Attn). The "dense" label refers to **dense FFN** (no MoE). Same architecture class as Qwen3.5-27B → CPU spec-dec is **architecturally foreclosed by the GDN verification wall** (see user memory `feedback_qwen35_27b_architecture`).

The intake-455 community note's 5.9× spec-dec speedup on RTX 4090 is **GPU-only** and does NOT transfer to our CPU stack. It is bookmarked for `gpu-acceleration-path.md` only — promote to evaluation when GPU hardware arrives.

## Model Specifications

| Property | Value |
|----------|-------|
| Model | Qwen3.6-27B (Apache-2.0) |
| Release date | 2026-04-22 (HuggingFace) |
| Total parameters | 27B |
| Active params/token | 27B (no MoE) |
| Architecture | Hybrid Gated-DeltaNet + Gated-Attention, dense FFN |
| Layer composition | 64 layers = 48 GDN + 16 Gated-Attn (3:1) |
| Context | 262K extensible to 1M |
| Q4_K_M GGUF size | ~16.8 GB (`unsloth/Qwen3.6-27B-GGUF`) |

## BW-roofline projection (EPYC 9655 NPS4)

Active weights/token at Q4_K_M ≈ **14.9 GB**. Effective DRAM bandwidth ≈ **460 GB/s** at our measured ~24% utilization on this class of workload.

- Theoretical ceiling: 460 / 14.9 ≈ **30.9 t/s at 100% BW utilization**
- Realistic at ~24% utilization: **~7.5–9 t/s single-instance** / **~30 t/s NUMA-4-way aggregate**

This matches existing Qwen3.5-27B measurements since architecture class is identical.

## Work Items

### P1 — CPU throughput probe (MEDIUM, ~4 h)

Measure single-instance and NUMA-4-way decode throughput on `unsloth/Qwen3.6-27B-GGUF` Q4_K_M.

- Single-instance: 96-thread numactl single-NUMA-node configuration, target ~7.5–9 t/s
- NUMA-4-way: 4×48-thread taskset configuration with `--mlock` + `numactl --membind`, target ~30 t/s aggregate
- Persist results (per `feedback_incremental_persistence`)
- Compare against:
  - Qwen3.5-27B baseline (validates architecture-class equivalence)
  - Production `worker_explore` (30B-A3B Q4_K_M @ 49.1 t/s 96t-single-node — `project_96t_single_node_operating_point`)

**Decision gate**: if measured throughput is materially below the BW-roofline projection (e.g. <5 t/s single-instance), abandon further evaluation.

### P2 — Coder-escalation quality A/B (HIGH effort, ~1 day)

Quality A/B vs current `coder_escalation` model on the agentic-coding eval harness.

- Baseline: Qwen2.5-Coder-32B
- Candidate: Qwen3.6-27B
- Eval: full SWE-bench-style suite, scored without think mode (`feedback_think_mode_benchmarks`)
- Persist incrementally (`feedback_incremental_persistence`)

**Decision gate for `coder_escalation` swap**: if Qwen3.6-27B matches or beats Qwen2.5-Coder-32B on agentic-coding score AND P1 throughput is acceptable, propose registry change in a follow-up. If quality is materially worse, retire as a coder candidate.

### P3 — Record explicit no-go on CPU spec-dec (DONE, 10 min)

This handoff explicitly records: **CPU speculative decoding for Qwen3.6-27B is architecturally foreclosed by the GDN verification wall.** Do not run CPU spec-dec experiments on this model. The 4090 spec-dec data points from intake-455 are bookmarked in `gpu-acceleration-path.md` only.

Rationale: hybrid GDN+attention architecture (same class as Qwen3.5-27B) makes draft verification non-equivalent under CPU's serial-decode pattern; verification cost exceeds acceptance gain.

## Open Questions

- Is there a `qwen3.6-coder-27B` variant in the works (parallel to Qwen2.5-Coder-32B)? If yes, that would be the more relevant candidate for P2.
- Does Qwen3.6-27B benefit from the same NPS4 + GGML_NUMA_WEIGHTS=1 settings that landed for the 30B-A3B (per `project_cpu1_phase13_v1`)? Probe in P1.
- Is there a quality vs latency knee where the 27B is interesting only as a higher-precision quant (Q5_K_M / Q6_K) rather than Q4_K_M? Defer to P2 outcome.

## Reporting

After P1 completes, append measured numbers + comparison to baselines under a "Results — P1" section. After P2 completes, append the agentic-coding score table. If a registry swap is proposed, link the follow-up handoff/PR here.

## Notes

- Inference-blocked: P1 and P2 cannot run without a healthy llama-server. Queue accordingly.
- P3 is a non-action recording an architectural foreclosure for future agents who might attempt it.
- This handoff is intentionally separate from `qwen36-production-upgrade.md` (which targets the 35B-A3B MoE — different model, different role). Do not conflate.

## Research Intake Update — 2026-04-28

### New Related Research

- **[intake-501] "Luce DFlash Brings 2x Speculative Decoding to Qwen3.6-27B on a Single RTX 3090"** (NYU Shanghai RITS blog, 2026-04-28)
  - Relevance to this handoff: **GPU-only data point**, bookmarked here because it is the first published Qwen3.6-27B-specific spec-dec measurement (intake-455 was a community note pre-3.6-DFlash-port). Reinforces P3's CPU-foreclosure: speedup is GPU-native (DDTree + 3 custom CUDA kernels for tree-aware SSM state rollback) — none of those primitives port to CPU sequential decode.
  - Key external finding: Qwen3.5-27B-DFlash drafter loads on Qwen3.6-27B unchanged (identical `Qwen35` identifier, layer/head dims). Cross-version drafter portability across the dense-FFN hybrid family.
  - Reported results (RTX 3090): 207.6 tok/s peak Q4_K_M (5.46× vs autoregressive); 128K context Q4_0 sustained 134.78 tok/s; cross-version acceptance length 5.05 (3.5-drafter on 3.6) vs 9.18 (3.5-drafter on 3.5).
  - Delta from current approach: **no change to this handoff's CPU plan**. Bookmarked alongside intake-455 in `gpu-acceleration-path.md`. Promotes only when GPU hardware arrives. Reinforces the architectural-foreclosure note in §"Architecture clarification" — speedup mechanism is parallel-scan + tree verification, neither available on EPYC CPU decode.
