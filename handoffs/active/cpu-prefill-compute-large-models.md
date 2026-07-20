# CPU Prefill-Compute for Large Models

**Status**: SCOPED / PROFILE-GATED (B7 scoping closed 2026-07-18 from the v7
lever audit). Design is complete enough to leave agent-zero-inference mode;
remaining implementation work is PC-4 only — **no inference/bench without operator approval**
(`feedback_no_concurrent_inference`).
**Owner handoff**: this file. **Parent index**: [inference-acceleration-index.md](inference-acceleration-index.md);
sibling of [cpu-inference-optimization-index.md](cpu-inference-optimization-index.md).

**2026-07-19 checkpoint**: PC-0 first-cell profiling is positive from both the current
experimental CPU build observation (`1.47` IPC) and the OP-2 quiet-window production-v6 profile
cell (`112.730698 t/s`, `1.09` IPC, `68.597` CPUs utilized). PC-3 then resolved the large
`(deleted)` mapping as LLVM OpenMP `libomp.so.5`; the hottest offset is a worker spin/pause
loop, not an unknown llama.cpp math kernel. The first implementation direction is therefore
barrier-count / graph-fusion work around qwen35 prefill boundaries, with MoE math packing as
a follow-up, not a blind dot-product rewrite.

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

- [x] **PC-0 — profile-first premise check ✅ 2026-07-19**: `perf record` a **long-context large-model
  prefill** shape (GLM-5.2 UD-IQ2_M and/or 122B architect at 8K/32K prompt) and confirm the
  hot ops are **compute-bound** (high VALUBusy / low memory-stall) before any kernel work.
  If BW-bound, this whole track collapses to the decode ledger — record and close. Bundle
  the `perf record` into the next OP-2 quiet window (shares the AMD perf-counter preflight,
  already green: `data/cpu_optimization/2026-07-03-amd-perf-counter-preflight/`). First
  profile cell is now closed positive; PC-3 has selected the first implementation target as
  OpenMP barrier/graph-fusion pressure, not a low-level dot-kernel rewrite.
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
  - [x] **PC-0b observation-only paired counter artifact ✅ 2026-07-18**: same CPU-only
    122B architect `p8192/n1`, `r=3` perf-stat row completed at
    `/mnt/raid0/llm/epyc-inference-research/data/cpu_prefill_compute/b7-pc0-prefill-cpu-only-20260718T204820Z-main/b7-pc0-prefill`.
    Experimental v7 `41ae83402`, `build-hip/bin/llama-bench`, `-dev none -ngl 0 -nopo 1 -nkvo 1`,
    Qwen3.5-122B-A10B Q4_K_M, `96` threads. Result: `8192` prompt tokens at mean
    `108.750 t/s` (`112.554`, `107.043`, `106.654`), `339.47s` wall, `85.168` CPUs utilized,
    max RSS `77,118,108 KB`, `0.92` IPC, vector MAC `8.456e12`, vector all `2.264e13`,
    scalar all `8.856e11`, demand DRAM fills `1.575e10`, and hardware-prefetch DRAM fills
    `4.332e10`. This is a strong positive-direction counter row for the prefill-compute
    premise, but still observation-grade because it overlapped with the Qwable MI210 replay
    and was not a fresh OP-2 quiet-window/post-reboot run.
  - [x] **PC-0c current-source IQ2 prefill/decode sizing artifact ✅ 2026-07-19**:
    CPU-only Qwen3.5-122B UD-IQ2_M run completed under the experimental v7
    CPU binary at
    `/mnt/raid0/llm/epyc-inference-research/data/cpu_prefill_compute/20260719T014801Z_qwen35_122b_iq2_cpu_prefill/summary.json`.
    Command forced `--device none`, `-ngl 0`, `96` threads, f16 KV, and `GGML_IQK=1`;
    `llama-bench` reported backend `CPU`, device `none`, and empty GPU info.
    Result: `pp2048 122.31 t/s`, `pp8192 114.40 t/s`, `tg16 6.24 t/s`, max RSS
    `40062336 KB`, wall `1:33.18`, exit `0`; pre/post `rocm-smi --showpids`
    had no KFD PIDs. This sizes the IQ2 CPU prefill path and hybrid-placement
    economics, but the `tg16` decode row is too slow for a primary CPU-only lane.
  - [x] **PC-0d current experimental CPU-build profile artifact ✅ 2026-07-19**:
    CPU-only Qwen3.5-122B Q4_K_M architect `p8192/n1` reran on the experimental
    CPU build at
    `/mnt/raid0/llm/epyc-inference-research/data/cpu_prefill_compute/b7-pc0-prefill-experimental-20260719T083513Z-codex/b7-pc0-prefill`.
    Source dryrun HEAD was `6ad45fa3f`; the binary reported build commit
    `9882c2c69`, linked `libllama*`/`libggml*` from `build-k24-cpu/bin`, and
    forced `-dev none -ngl 0 -nopo 1 -nkvo 1` with `GGML_IQK=1`. Result:
    `pp8192 121.963712 t/s` mean over `r=3`, `tg1 5.739871 t/s`, `1.47` IPC,
    `92.660` CPUs utilized, vector MAC `8.456e12`, vector all `2.264e13`,
    demand DRAM fills `1.479e10`, and hardware-prefetch DRAM fills `3.661e10`.
    `perf record` captured a `10.323 GiB` profile with zero lost samples; top
    children were `GOMP_barrier`/OpenMP barrier path `43.12%`,
    `ggml_iqk_try_mul_mat_id` `22.16%`, `iqk_mul_mat_moe` `18.93%`,
    `ggml_compute_forward_mul_mat` `16.52%`, `llamafile_sgemm` `14.75%`, and
    CPU flash-attn `5.88%`. Summary artifact:
    `/mnt/raid0/llm/epyc-inference-research/docs/data/cpu_prefill_compute_pc0_experimental_20260719.md`.
    Interpretation: PC-0 premise is positive from observation evidence; the
    next lever is barrier-count/operator fusion and qwen35 prefill graph fusion,
    not a blind decode-style GEMV rewrite. It still needs OP-2-grade rerun or
    retro-certification before decision use.
  - [x] **PC-0e OP-2 quiet-window production-v6 profile artifact ✅ 2026-07-19**:
    frozen production-v6 `bench_canonical.sh` cell completed at
    `/mnt/raid0/llm/epyc-inference-research/data/cpu_prefill_compute/pc0-op2-20260719T225343Z`.
    The binary reported build commit `91745611f` / build number `9774`; the
    production tree was observed at `production-consolidated-v6` `91a8424ea`
    after the run. The bench reported backend `CPU`, empty `gpu_info`, and
    postflight ROCm showed no KFD PIDs. Result: `pp8192 112.730698 t/s`
    mean over `r=3`, `tg1 4.989817 t/s`, `1.09` IPC, `68.597` CPUs utilized,
    vector MAC `4.410e12`, vector all `7.690e12`, demand DRAM fills
    `1.954e10`, and hardware-prefetch DRAM fills `4.549e10`. `perf record`
    captured `10837.601 MB` / `1,348,833` samples; bounded no-children and DSO
    reports had `0` lost samples, with `46.47%` in `libggml-cpu.so.0.15.2` and
    `49.57%` in an unresolved `(deleted)` main `llama-bench` mapping. Summary:
    `/mnt/raid0/llm/epyc-inference-research/docs/data/cpu_prefill_compute_pc0_op2_20260719.md`.
    Verdict: PC-0 premise closes positive, but implementation target selection
    needs a cleaner symbolized mapping before kernel work.
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
  PC-3 later selected barrier/graph-fusion pressure as the first implementation target;
  low-level math rewrites remain follow-up work unless post-PC-4 profiles keep them hot. ✅ 2026-07-18
- [x] **PC-3 — symbolized target-selection pass ✅ 2026-07-19**: resolve the OP-2 `(deleted)` main-binary
  mapping or rerun a bounded `perf record` with stable binary/symbol capture so the first
  kernel edit targets a proven hot path. Acceptable outputs: a no-children and children
  report with resolved `llama-bench`/OpenMP/library symbols, or an address-resolution note
  that maps the unresolved addresses to exact source/functions in the sampled binary.
  Result: build-id `597017da07b7fbe219d04036e9ca30d46654951b` is
  `/usr/lib/llvm-20/lib/libomp.so.5`; hot offset `0x7fea0` is an OpenMP worker
  spin/pause loop (`38.36%` self), not a llama.cpp kernel. The children report
  ranks `ggml_graph_compute_thread` at `48.30%`, `ggml_iqk_try_mul_mat_id` /
  `iqk_mul_mat_moe` at `22.67%` / `22.51%`, `ggml_compute_forward_mul_mat` at
  `10.37%`, CPU flash-attn at `5.59%`, and GDN/RMS/SSM at about `1-2%` each.
  Summary:
  `/mnt/raid0/llm/epyc-inference-research/docs/data/cpu_prefill_compute_pc3_target_selection_20260719.md`.
- [ ] **PC-4 — experimental qwen35 prefill barrier/graph-fusion prototype**:
  implement only in `llama.cpp-experimental`, default-off, after checking the
  current v7 promotion branch. First prototype should reduce graph-node/OpenMP
  dispatch count around qwen35/qwen35moe prefill same-input compute islands
  before touching low-level IQK dot kernels. Acceptance: exact-output smoke plus
  repeated `p8192/n1` profile showing lower libomp spin/pause share and lower
  wall time.
  - [x] **PC-4a — graph-node trace scaffold prepared ✅ 2026-07-19**:
    experimental-only patch in `/mnt/raid0/llm/llama.cpp-experimental` adds
    default-off `LLAMA_QWEN35_PREFILL_TRACE=1` logging in
    `src/models/qwen35.cpp` and `src/models/qwen35moe.cpp`. It reports
    per-layer graph-node deltas and final graph-node count for qwen35/qwen35moe
    prefill graph construction, without changing default execution or numerics.
    Validation: `cmake --build build-k24-cpu --target llama-bench -j 16` passed
    on experimental branch `experimental-v7-refresh-20260716` at `12a292f0c`;
    `git diff --check` and ASCII checks passed. The llama.cpp patch remains
    uncommitted pending explicit operator review/commit approval for that repo.
  - [x] **PC-4b — trace run + target decision ✅ 2026-07-19**: traced the
    qwen35moe `p8192/n1` CPU-only cell on post-candidate experimental build
    `12a292f0c` / binary `10099`; the validated v7 promotion candidate remains
    frozen at `6ad45fa3ff` / binary `10098`. Initial non-verbose artifact
    completed but emitted no trace because `llama-bench` suppresses logs unless
    `-v` is passed. The valid verbose artifact
    `/mnt/raid0/llm/epyc-inference-research/data/cpu_prefill_compute/pc4b-qwen35-trace-verbose-20260719T235218Z/`
    exited `0`, resolved experimental shared libraries, and cleaned up with no
    AutoPilot/llama/KFD PIDs. Result: `pp8192 112.082350 t/s`, `tg1 4.311924
    t/s`, max RSS `77043932 KiB`. Trace: `45` graph builds, final graph nodes
    `4471`, recurrent `linear_attn` layer deltas `92/99`, full-attention deltas
    `75`. Report:
    `/mnt/raid0/llm/epyc-inference-research/docs/data/cpu_prefill_compute_pc4b_trace_20260719.md`.
    Decision: high-delta island is the recurrent `linear_attn` path, not full
    attention, but layer-level trace is still too coarse for a safe fusion.
  - [x] **PC-4c — recurrent linear-attn sublayer trace ✅ 2026-07-20**: add a deeper
    default-off trace inside qwen35/qwen35moe recurrent `linear_attn` to break
    down GDN, SSM, shared expert, routed expert, norm, and residual islands
    before selecting an implementation. Do not claim PC-4 complete until an
    exact-output/profile-guarded implementation shows lower libomp spin/pause
    and lower wall time.
    - [x] **PC-4c-a — level-2 trace instrumentation prepared ✅ 2026-07-20**:
      `/mnt/raid0/llm/llama.cpp-experimental` now supports
      `LLAMA_QWEN35_PREFILL_TRACE=2` for qwen35/qwen35moe subphase graph-node
      deltas while preserving `=1` as the existing layer-only trace. The patch
      is post-candidate research only; validated with
      `cmake --build build-k24-cpu --target llama-bench -j 16`,
      `ctest --test-dir build-k24-cpu -R '^test-llama-archs$' --output-on-failure`,
      `git diff --check`, and ASCII scan. Per llama.cpp local instructions, the
      patch is intentionally uncommitted until explicit operator commit approval.
    - [x] **PC-4c-b — level-2 trace run ✅ 2026-07-20**: qwen35moe `p8192/n1`
      CPU-only trace completed at
      `/mnt/raid0/llm/epyc-inference-research/data/cpu_prefill_compute/pc4c-qwen35-subtrace-20260720T001959Z/`
      with `LLAMA_QWEN35_PREFILL_TRACE=2`. Result: exit `0`, `pp8192
      118.040030 t/s`, `tg1 5.339296 t/s`, max RSS `77038696 KiB`, `45`
      graph builds, final graph nodes `4471`, and clean process/GPU cleanup.
      Median graph-node deltas: recurrent `linear_attn_total=53`, per-layer
      `ffn_total=40`, `full_attn_total=29`; inside recurrent attention the
      largest sub-islands are `conv_state=15`, `gated_delta_net=13`, and
      `ssm_state=8`. Report:
      `/mnt/raid0/llm/epyc-inference-research/docs/data/cpu_prefill_compute_pc4c_subtrace_20260720.md`.
  - [x] **PC-4d — profile-confirmed default-off prototype target ✅ 2026-07-20**: use PC-4c
    evidence to choose between recurrent `conv_state`/`gated_delta_net`/`ssm_state`
    fusion and same-input MoE/FFN graph fusion. Do not implement a default-off
    prototype until the follow-up profile ties the chosen island to lower
    libomp spin/pause and wall time on repeated `p8192/n1`. Decision: choose
    same-input MoE/FFN barrier-count reduction first, and explicitly reject a
    recurrent-GDN-first prototype for the current evidence set. PC-3/PC-0 put
    OpenMP spin/barrier at `38.36-43.12%` and MoE `mul_mat_id` at
    `22.51-22.67%`, while GDN/SSM/RMS remain about `1-2%`. PC-4c's graph-node
    deltas explain the recurrent island but do not override the timing profile.
    Report:
    `/mnt/raid0/llm/epyc-inference-research/docs/data/cpu_prefill_compute_pc4d_target_selection_20260720.md`.
  - [x] **PC-4e — MoE/FFN boundary diagnostic ✅ 2026-07-20**:
    add or reuse default-off diagnostics around `build_layer_ffn` /
    `build_moe_ffn` to separate router/top-k, gate-up, down-projection,
    shared-expert, and aggregation graph/timing islands. Result: qwen35moe-local
    FFN boundary trace ran CPU-only at
    `/mnt/raid0/llm/epyc-inference-research/data/cpu_prefill_compute/pc4e-qwen35-ffn-subtrace-20260720T003822Z/`
    with exit `0`, `pp8192 115.842650 t/s`, `tg1 5.266122 t/s`, and clean
    process/GPU cleanup. Routed `ffn_moe` accounts for `32` of the stable
    `40` FFN graph nodes on every layer; shared expert/gate/gating/add account
    for only `8` combined. Report:
    `/mnt/raid0/llm/epyc-inference-research/docs/data/cpu_prefill_compute_pc4e_ffn_trace_20260720.md`.
  - [x] **PC-4f — routed MoE helper boundary diagnostic ✅ 2026-07-20**:
    added a narrow, default-off diagnostic inside routed `build_moe_ffn` to
    separate router/weights, gate-up, activation, down projection, weighting,
    per-expert view expansion, and expert aggregation. Result: qwen35moe
    `p8192/n1` CPU-only trace ran at
    `/mnt/raid0/llm/epyc-inference-research/data/cpu_prefill_compute/pc4f-qwen35-routed-moe-subtrace-20260720T004730Z/`
    with exit `0`, `pp8192 110.411171 t/s`, `tg1 5.162607 t/s`, and clean
    process/GPU cleanup. Median routed-MoE graph-node deltas: router/weights
    `11`, expert views `8`, aggregation `7`, while gate-up/activation/down/
    weighting total only `6`. Report:
    `/mnt/raid0/llm/epyc-inference-research/docs/data/cpu_prefill_compute_pc4f_routed_moe_trace_20260720.md`.
  - [x] **PC-4g — compact aggregation scheduling prototype rejected ✅ 2026-07-20**:
    tested a default-off prototype that skipped eager `ggml_build_forward_expand`
    calls for routed MoE expert views and aggregation adds. The cheap
    `llama-simple` exact-output smoke passed byte-for-byte, but the real
    qwen35moe `p8192/n1` cell regressed: default `141.588462 t/s` prompt and
    `5.242545 t/s` decode versus compact `100.069829 t/s` prompt and
    `4.840255 t/s` decode. The prototype code was reverted; do not re-propose
    this view/add expansion skip without a new mechanism. Report:
    `/mnt/raid0/llm/epyc-inference-research/docs/data/cpu_prefill_compute_pc4g_compact_aggregation_20260720.md`.
  - [ ] **PC-4h — router/weights profile-first follow-up**:
    profile the routed `ffn_moe_router_weights` island before another scheduling
    prototype. The target is top-k/routing/weights scheduling, not a
    `mul_mat_id` math rewrite and not the rejected view/add expansion skip.
    Acceptance: resolved profile evidence that router/weights are tied to
    libomp spin/pause or wall time, followed by one default-off prototype with
    exact-output smoke and repeated `p8192/n1` lower spin/wall-time evidence.

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
