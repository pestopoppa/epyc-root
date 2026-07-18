# CPU Prefill-Compute for Large Models

**Status**: SCOPED / PROFILE-GATED (B7 scoping closed 2026-07-18 from the v7
lever audit). Design is complete enough to leave agent-zero-inference mode;
remaining work is PC-0 only — **no inference/bench without operator approval**
(`feedback_no_concurrent_inference`).
**Owner handoff**: this file. **Parent index**: [inference-acceleration-index.md](inference-acceleration-index.md);
sibling of [cpu-inference-optimization-index.md](cpu-inference-optimization-index.md).

**2026-07-18 checkpoint**: an observation-only first `perf record` cell now exists for the
122B architect `p8192/n1` CPU-only shape, but PC-0 remains open because the run was not an
OP-2/MEASUREMENT quiet-window run and lacks paired `perf stat` memory/vector counters.

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
  already green: `data/cpu_optimization/2026-07-03-amd-perf-counter-preflight/`). First
  profile cell + artifact plan is below; do not start kernel work from PC-1/PC-2 alone.
  - [x] **PC-0a observation-only first profile artifact ✅ 2026-07-18**: CPU-only
    122B architect `p8192/n1` run completed under `perf record` at
    `/mnt/raid0/llm/epyc-inference-research/data/cpu_prefill_compute/b7-pc0-prefill-cpu-only-20260718T174148Z/b7-pc0-prefill`.
    It forced `-dev none -ngl 0 -nopo 1 -nkvo 1`, processed `8192` prompt tokens at
    `107.621 t/s`, used max RSS `77,124,940 KB` (`73.55 GiB`), and produced a
    `2988.864 MB` `perf.data` with `721,404` `cycles:u` samples. Top visible samples:
    `libgomp` worker path `42.33%`, CPU GEMM `tinyBLAS_Q0_AVX...gemm4xN` `11.23%`,
    IQK MoE matmul `4.21%`, CPU flash-attn tiled `3.47%`, plus Q4K dequant/matmul
    and `iqk_convert_q4_k_q8_1_r8`. This is a useful positive-direction profile, but
    not a compute-vs-BW verdict; PC-0 still needs the OP-2/quiet-window `perf stat`
    memory/vector counter row before any kernel implementation.
- [x] **PC-1 — quantify the prefill fraction** for GLM/architect long-context turns from
  existing logs (zero-inference): evidence note
  `/mnt/raid0/llm/epyc-inference-research/docs/data/cpu_prefill_compute_pc1_log_sizing_20260718.md`
  shows prompt/prefill already dominates the targeted long-context regimes: GLM-5.2 patch
  review n=12 = 81.0% prompt wall, architect 6K/1024 = 46.8%, ingest 31K/1024 = 75.1%,
  worker 12K/1024 = 83.1%. This sizes EV; PC-0 still must prove compute-bound hot ops. ✅ 2026-07-18
- [x] **PC-2 — norm-tail + Q8→f16 convert-skip design**: scoped against
  `qwen35.cpp` / the prefill graph builder. Verdict: do not create a separate prefill-fusion
  framework; extend the existing CPU graph/operator fusion direction with prefill-specific
  gates. First candidate is qwen35 `ffn_up + ffn_gate` fusion over the same normalized input,
  then GDN projection fusion (`wqkv|wqkv_gate|ssm_beta|ssm_alpha`) because it reuses the same
  activation packing and cuts barriers. Gated norm-tail fusion (`RMS_NORM * ssm_norm * silu(z)`)
  is second-order and should wait until post-matmul-fusion profiles prove it remains hot.
  Implementation stays blocked on PC-0 proving compute-bound prefill hot ops. ✅ 2026-07-18

## PC-0 operator-window plan

Run only inside an operator-approved OP-2 quiet window. Use the existing OP-2
run root if present; otherwise create a dedicated run root under research data.
This plan is intentionally a profile premise check, not a benchmark promotion
or kernel implementation authorization.

First cell: 122B architect prefill at 8K prompt, 1 generated token, 3 reps.
It is the least-coupled large-model target: current registry path is known, the
existing PC-1 log sizing shows a material prompt-wall fraction, and it avoids
GLM reviewer-quality / DSA-top-k protocol coupling.

```bash
export PC0_RUN_ID="${OP2_RUN_ID:-b7-pc0-prefill-$(date -u +%Y%m%dT%H%M%SZ)}"
export PC0_RUN_ROOT="${OP2_RUN_ROOT:-/mnt/raid0/llm/epyc-inference-research/data/cpu_prefill_compute/${PC0_RUN_ID}}/b7-pc0-prefill"
mkdir -p "$PC0_RUN_ROOT"/{dryrun,perf-stat,perf-record,reports}

cd /mnt/raid0/llm/epyc-inference-research
ARCH_MODEL="/mnt/raid0/llm/models/Qwen3.5-122B-A10B-MTP-GGUF/UD-Q4_K_M/Qwen3.5-122B-A10B-UD-Q4_K_M-00001-of-00003.gguf"

./scripts/benchmark/bench_canonical.sh \
  -m "$ARCH_MODEL" -p 8192 -n 1 -r 3 --dry-run -- -o json \
  > "$PC0_RUN_ROOT/dryrun/architect_p8192_n1.dryrun.txt" 2>&1

./scripts/benchmark/bench_canonical.sh \
  -m "$ARCH_MODEL" -p 8192 -n 1 -r 3 --perf -- -o json \
  > "$PC0_RUN_ROOT/perf-stat/architect_p8192_n1.results.json" \
  2> "$PC0_RUN_ROOT/perf-stat/architect_p8192_n1.perf_stat.txt"

perf record -F 99 --call-graph dwarf \
  -o "$PC0_RUN_ROOT/perf-record/architect_p8192_n1.perf.data" -- \
  ./scripts/benchmark/bench_canonical.sh \
    -m "$ARCH_MODEL" -p 8192 -n 1 -r 1 -- -o json \
  > "$PC0_RUN_ROOT/perf-record/architect_p8192_n1.record_results.json" \
  2> "$PC0_RUN_ROOT/perf-record/architect_p8192_n1.record_stderr.txt"

perf report --stdio \
  -i "$PC0_RUN_ROOT/perf-record/architect_p8192_n1.perf.data" \
  > "$PC0_RUN_ROOT/reports/architect_p8192_n1.perf_report.txt"
```

Required PC-0 artifact fields:

| Field | Capture |
|---|---|
| approval | quiet-window/operator approval ref; whether this was folded into OP-2 |
| host | same host-health and perf-counter preflight artifacts as OP-2 |
| binary | `bench_canonical.sh` dry-run output, selected binary path, commit/dirty state, `GGML_IQK=1`, library resolution |
| model | exact model path, shard list/size, role (`architect_general` first cell) |
| command | exact argv/env for dry-run, `--perf` stat run, and `perf record` run |
| result | llama-bench JSON, prompt tokens, generated tokens, reps, stderr |
| profile | `perf_stat.txt`, `perf.data`, `perf_report.txt`, top symbols, IPC/cycles/instructions, DRAM-fill events |
| verdict | compute-bound, BW-bound, or inconclusive; if inconclusive, whether to attach to the child PID or choose a different first cell |

PC-0 closes positive only if the prefill profile is materially different from
the decode roofline: matmul/dequant/norm/fusion-candidate symbols dominate, IPC
and vector-op counters are materially healthier than the decode profile, and
DRAM-fill / memory-stall evidence is not the limiting factor. If the profile
looks decode-like (low IPC, DRAM dominated, barrier/vec_dot roofline), close
this track negative and route the result back to the decode ledger. If the
architect cell is positive but not enough to choose a kernel target, optional
follow-up cells are GLM-5.2 UD-IQ2_M via the GLM DSA runner and/or
ingest-long-context 32K via the Qwen3-Next registry path, both under a fresh
operator-approved profile window.

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
