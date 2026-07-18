# CPU Prefill-Compute for Large Models

**Status**: NEW / SCOPING (opened 2026-07-18 from the v7 lever audit). Design + profile-first
only — **no inference/bench without operator approval** (`feedback_no_concurrent_inference`).
**Owner handoff**: this file. **Parent index**: [inference-acceleration-index.md](inference-acceleration-index.md);
sibling of [cpu-inference-optimization-index.md](cpu-inference-optimization-index.md).

## Thesis

The CPU **decode** roofline is exhausted (Qwen3.6-27B Q8 decode @96t = 0.17 IPC, **96.6% of
cycles memory-stalled** — DRAM-bandwidth-bound, not ALU-bound; see
[cpu-shape-specialized-gemv-decode.md](cpu-shape-specialized-gemv-decode.md)). That roofline
does **NOT** bound **prefill**: prefill is `M>1` GEMM, compute-bound, with a far better
compute:BW ratio, so SIMD/fusion levers that are dead-on-arrival for decode can actually
fire during prefill. For **large models at long context** (GLM-5.2 754B, 122B architect,
Qwen3.6 long-context ingest), **prefill dominates wall-clock** — and prefill-compute is a
genuinely untapped regime on this EPYC 9655.

This track exists so prefill-compute is not invisible: the decode-focused handoffs
explicitly de-scope it ("prefill is already 200–500 t/s, rarely the single-user bottleneck"
— true for *short* prompts on *small* models, **false** for GLM/architect long-context).

## Candidate levers (all profile-first)

| Lever | Source / anchor | Est. EV | Why prefill (not decode) |
|---|---|---|---|
| **Prefill Q8→f16 convert-skip** | findings-05c §Axis "orthogonal lever when L7 deferred" | ~+15% | Removes per-tile dequant on the compute-bound prefill GEMM |
| **High-batch norm-tail fusion** | findings-05c ("43% of B=128 time is the norm tail") | high @ large-M | Norm tail is a serial fraction that grows with batch/prefill width |
| **Per-op operator/graph fusion (barrier-count)** | GEMV §fusion; shared with the decode barrier-fusion lever | +10–15% | Same fusion pass; its ceiling is higher in the compute-bound regime |
| **Chunked-prefill / MegaBlocks (CPU17/CPU18)** | GEMV CPU18 (blocked-CSR-COO); Sarathi eval | +2–5% single-user; larger multi-tenant | **Workload-gated**, NOT roofline-killed — reopens under batched / multi-tenant / prefill-heavy MoE |
| **Prefill-decode disaggregation** | (untracked; no anchor) | latency-shape only | Only meaningful if a prefill-heavy / multi-tenant workload materializes |

## First actions (zero-inference / design)

- [ ] **PC-0 — profile-first premise check**: `perf record` a **long-context large-model
  prefill** shape (GLM-5.2 UD-IQ2_M and/or 122B architect at 8K/32K prompt) and confirm the
  hot ops are **compute-bound** (high VALUBusy / low memory-stall) before any kernel work.
  If BW-bound, this whole track collapses to the decode ledger — record and close. Bundle
  the `perf record` into the next OP-2 quiet window (shares the AMD perf-counter preflight,
  already green: `data/cpu_optimization/2026-07-03-amd-perf-counter-preflight/`).
- [ ] **PC-1 — quantify the prefill fraction** for GLM/architect long-context turns from
  existing logs (zero-inference): what % of turn wall-clock is prefill vs decode at 8K/32K/64K?
  This sizes the whole track's EV before any kernel spend.
- [ ] **PC-2 — norm-tail + Q8→f16 convert-skip design**: scope the two highest-EV levers
  against `qwen35.cpp` / the prefill graph builder; identify the exact fusable clusters.

## Cross-links / dependencies

- Shares the operator-fusion machinery with the CPU **decode** barrier-fusion lever
  ([cpu-shape-specialized-gemv-decode.md](cpu-shape-specialized-gemv-decode.md), OP-2 #1 CPU lever).
- Overlaps **GLM DSA D2 (sparse final-attention, prompt-path)** and **D3 (Lightning-Indexer
  CPU kernel)** in [llama-cpp-dsa-contribution.md](llama-cpp-dsa-contribution.md) — both are
  prefill/long-context levers; coordinate profiling.
- GPU sibling for hybrid models = **K28 GDN long-prefill recurrence kernel**
  ([mi210-big-model-and-acceleration-roadmap.md](mi210-big-model-and-acceleration-roadmap.md)).

## Reporting

Update this handoff first; append `progress/YYYY-MM/YYYY-MM-DD.md` with the profile artifact
+ compute-vs-BW verdict; if PC-0 falsifies the premise, close this stub and note it in the
inference-acceleration-index.
