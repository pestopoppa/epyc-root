# CPU Decode Roofline Program — Qwen3.8-Flash-Next (qwen4exp) at the machine ceiling

**Status**: AUDITED 2026-09-02 — implementation-ready. Directed by the operator 2026-09-02: the **hard,
non-speculative gains FIRST**; the MTP head that the conversion dropped is restored **LAST** (Axis E),
because that multiplier is easy to tack on and multiplies whatever token cost the hard work leaves.
Supersedes the single-bet framing of INF-67: the fused decoder is one axis of a roofline program.
**Created**: 2026-09-02 · **Audited**: 2026-09-02 (every number re-derived from its primary record — see
*Audit log*; the pre-audit version carried a doubled bandwidth denominator, a retracted expert-path
figure and an unsourced byte count)
**Priority**: HIGH — the served artifact streams ~4.2 GB of weights per token; at this machine's DRAM
bandwidth that is a 10–20 ms token (50–100 t/s) before speculation, and we measure ~95 ms
**Categories**: hardware_optimization, local_inference, moe_optimization, kernel_architecture
**Workstream**: Inference Acceleration
**Parent index**: [`inference-research-index.md`](inference-research-index.md) (row INF-70)
**Related**:
- [`cpu-fused-decoder-blocks.md`](cpu-fused-decoder-blocks.md) (INF-67) — the fused decoder's design
  record and phase checklist; Axis A here is its live viability task list
- [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) (INF-10) — the refuted
  fusion arms and the `GGML_PERF`/symbol profile it prescribed (B1 here satisfies it)
- [`batched-decode-measurement.md`](batched-decode-measurement.md) and
  `epyc-inference-research/scripts/lib/canonical_recipe.py` — the canonical prefix, flags and OMP stack
- [`../completed/qwen4exp-uniform-iq4xs-baseline-control.md`](../completed/qwen4exp-uniform-iq4xs-baseline-control.md)
  (INF-68, ratified OP-32) — the artifact rule, the required comparison baseline, the +15.2% quant-mix result
- [`../completed/cpu-decode-flops-roofline-audit.md`](../completed/cpu-decode-flops-roofline-audit.md) —
  the calibrated DRAM-traffic counters on this host (`ls_dmnd_fills_from_sys.dram_io_all` +
  `ls_hw_pf_dc_fills.dram_io_all`, ×64 B) that B1/C1 use
- Axis E riders: [`qwen38-flash-next-fp8-evaluation.md`](qwen38-flash-next-fp8-evaluation.md) (INF-63, the
  same FP8 re-acquisition), [`qwen-mtp-llamacpp-port.md`](qwen-mtp-llamacpp-port.md) (INF-46),
  [`speculative-decoding-mtp-refresh.md`](speculative-decoding-mtp-refresh.md) (INF-50),
  [`dflash2-block-drafter-experimental-build.md`](dflash2-block-drafter-experimental-build.md) (INF-62, the
  alternative drafter — `--spec-type` takes one value)

## Why this model, why this box

Qwen3.8-Flash-Next: 125B total / 6B active, 512 experts × 10 used, 48 layers (36 Gated-DeltaNet + 12 QSA
sparse-attention, each followed by MoE), 4-stream hyper-connections, vocab 248,320 — and a **51B-parameter
PLE n-gram hash table** (`per_layer_token_embd.weight`, 160-wide rows, iq4_nl, ~27 GB) of which each token
gathers only `(ngram_size−1) × heads_per_ngram` rows. A lookup table that size is what 1.1 TB of RAM is
for and what no GPU on this host can hold; the active compute is a 6B-parameter model. Under the canonical
`--no-mmap` recipe the table is fully resident (lazy row reads are an mmap-only path), so the PLE costs
DRAM *latency* for a handful of rows per token and essentially no bandwidth. The per-token cost is the
routed experts, the dense stack and the lm_head streaming from DRAM — a bandwidth problem the machine is
sized for — plus a dispatch floor the current graph pays ~7,000 times per token. This program takes the
token to the machine's ceiling in order of hardness: dispatch floor and weight stream first, the fused
decoder as the structural bet, the MTP multiplier last.

## Scope

**IN**: making a single non-speculative token cheaper on CPU (Axes A–D), then restoring the dropped MTP
head (Axis E).
**OUT, by operator direction 2026-09-02**: **GPU / expert offload** — deferred, not refuted; do not spend
on it. **Speculative decoding before Axes A–D have their first measured results** — the operator's
position: *"We can always tack on the speculative drafter and get that performance bump. That's easy. I
want the agent to tackle hard-to-get gains."* The one Axis E item permitted early is E1 (the source
re-download), because it is I/O-only and gates E2–E5 by ~6 h of wall time — and it must not overlap a
measurement window (a 185 GB download churns the page cache).

## The gap — corrected ledger

Every row names its record and its conditions. **Measured** = a number someone read off an instrument;
**computed** = arithmetic on measured inputs; **retired** = do not cite.

| quantity | value | status | record / conditions |
|---|---|---|---|
| decode, **required comparison baseline** (OP-32 opt. B): uniform IQ4_XS | **95.1 ms/token (10.52 ±0.05 t/s)** at t48; 102 ms (9.79) at t64 | measured | INF-68 `2026-08-31-inf68-baseline-control.md`: fresh Release clone @ `7cdd7c97b` (build 10151), `taskset -c 0-95 numactl --interleave=all`, OMP spread/cores/active/dynamic-false, `GGML_IQK=1`, `-mmp 0`, tg128 r5, load-gated clean windows |
| decode, UD-IQ4_XS (the served file) | 109.5 ms (9.13 ±0.04) t48 | measured | same run; uniform is +15.2% |
| ~~74 ms / 13.46 t/s~~ | **retired — does not reproduce** (−32% on the same lineage and recipe) | retired | `2026-08-28.md:206` origin; `2026-08-31.md:228` and INF-68 Finding 2 retraction |
| bytes streamed per token | **≈ 4.16 GB** = dense 2.344 + routed experts 1.296 (10/512 × 48 layers, avg 2.70 MB/expert) + `output.weight` 0.521 (Q6_K, 2560×248320) | computed 2026-09-02 from the artifact's tensor table (`gguf_dump`, 1224 tensors) | replaces the retired "2.8–3.4 GB", which was a different model's 2026-05-28 figure. Notable: `ffn_gate_inp` (router) is stored **F32** — 252 MB/token (6%) just to route; `ffn_down_exps` is **Q5_1** in the "uniform" file (640 % 256 ≠ 0, so IQ4_XS is impossible and llama-quantize fell back) |
| DRAM bandwidth, theoretical | 460.8 GB/s (12 ch × 4800 MT/s × 8 B) | spec | DIMM speed is a consistent working assumption on the record (`2026-08-28.md:199`), never instrumented |
| DRAM bandwidth, measured **copy** | **212 GB/s, read+write already counted** | measured (conditions incomplete) | `bench_stream3.cpp` 2026-08-29: 2 GiB arrays, malloc + parallel first-touch, default 96 threads, NUMA mode and OMP placement unrecorded. The tool divides 4 GiB by the copy time of a 2 GiB array — standard STREAM convention |
| ~~425 GB/s "traffic"~~ | **retired — a double count** | retired | the tool's "traffic" column multiplies the already-read+write copy figure by 2 again. Never measured on this box. Every "% of 425" in the pre-audit handoff, the ~8% fraction, the "1.3–4% expert path" and the DGX-Spark comparison inherited it |
| DRAM bandwidth, **read-only, under the decode recipe** | **NOT MEASURED** | — | the only read-only figure (80–90 GB/s, `2026-08-28.md:181`) is the refuted single-node first-touch artifact. **C0 produces this number.** |
| roofline (bytes ÷ read bandwidth) | between **19.6 ms (51 t/s)** at the proven 212 GB/s and **~10.4 ms (96 t/s)** if reads reach ~85% of theoretical, as a well-placed 12-channel EPYC normally does | computed | the true ceiling sits between these until C0 lands |
| achieved fraction | **21% → 11%** of the two bounds | computed | 19.6/95.1 and 10.4/95.1 |
| graph nodes per token | **7,906** pre-fusion; **6,887** after `MEAN_D1` + `MOE_TOPK_NORM` (the baseline build) | measured | `2026-08-28.md:88,142` and round 1 (`7902 → 6887`, −13%). The "~5,850 / ~6,800" in INF-67 are in no record |
| thread-0 compute per node | 5–8 µs | measured, **excludes barrier wait** | `GGML_CPU_PROF` times the compute call only; the graph barrier at `ggml-cpu.c:3274` is outside its window. Three measurements, round 5 |
| barrier wait per node, and the count of sync events per token | **NOT MEASURED** | — | round 1 inferred "~53 ms barrier/dispatch" by subtraction at the 128 ms pre-NUMA-fix baseline; round 5 declared it "not barriers" from three failed *kernel* fusions. Neither is a measurement. **D0 produces both numbers.** |
| expert path (`mul_mat_id`), in-function per-call | 68–88 µs × 144 calls = **10–13 ms/token**; ≈ 100–130 GB/s aggregate on ~1.3 GB | measured (pre-NUMA-fix box state, UD artifact with IQ3_S experts) | `2026-08-28.md:170,190` — the `[mmid_prof]` in-function timer. **This retracts the "5.6–17 GB/s" figure in the same record**, which was the per-op profiler contaminated by cross-node waits |
| dense path (`mul_mat`), 797 calls/token | in-function median ~20 µs (Q8_0 dense) → ~16 ms if representative; profiler-attributed 57 ms (72 µs/call) *including waits* | partly measured | `2026-08-28.md` rounds 2/3/6. The 40 ms between the two figures is wait time nobody has assigned. **B1 settles the split** |
| fused decoder, same debug build, `-t 1` | fused 1350 ms vs graph 350 ms (**3.86×**); fused gemv 1141 / other 215 | measured (non-claim) | `2026-09-01-inf67.md`; safe only as a same-window ratio |
| ~~28 ms gemv / 46 ms non-gemv~~, ~~65 µs × 144 = 9.4 ms~~ | **retired** | retired | a partition of the retired 74 ms; the constants are "unmatched by committed records" (INF-68 audit). The in-function medians above are the sourced equivalents |

**What the ledger says.** A token is roughly one third weight streaming at ~100–150 GB/s-class rates and
roughly one half per-node fixed cost, with the remainder unassigned. The two ceilings are therefore
**bandwidth** (C0 measures it; Axis B converts more of it) and the **dispatch floor** (D0 measures it;
Axis D lowers it). The fused decoder (Axis A) attacks the second structurally; Axis E multiplies whatever
is left. No comparison to other hardware is admissible until C0 exists.

## Ordering

1. **C0 → C5** (one session, under one region claim, ~1 h of box time): the denominator and the anchor.
   Until both land, no absolute before/after claim is admissible — only same-window ratios.
2. **B1 + D0** (one session, no new kernels): the per-path GB/s split and the per-node floor, on the C5
   build. These two numbers rank every lever below by ms/token at stake.
3. **Levers by measured ROI**: Axis D (D1–D7) and Axis B (B2–B4) are independent of each other and of
   Axis A; run them in parallel sessions, each against the C5 anchor in the C5 build.
4. **Axis A** continues in its own session against the same anchor (A-GATE).
5. **Axis E** after A–D report their first measured results — except E1, which may run in any
   non-measurement window.

If this ordering is overruled, say so in this file with the reason; it is a recommendation with a reason,
not a gate.

## Axis C — measurement (FIRST; cheap, and it makes every other axis legible)

- [ ] **C0 — measure the roofline denominator: read-only DRAM bandwidth under the decode recipe.**
      Extend `bench_stream3.cpp` (on disk under `/tmp/qwen4exp-builds/`, or rewrite it under the research
      repo) with a **read-only** kernel (sum-reduce over a 2 GiB buffer, and a second "gemv pattern"
      variant: 2560-element rows dotted against a resident vector), malloc + parallel first-touch, run
      under exactly the recipe prefix — `taskset -c 0-95 numactl --interleave=all` with the OMP stack —
      at t ∈ {24, 48, 64, 96, 192}, best of 5. Report GB/s per thread count with the counting convention
      stated (bytes read only). Cross-check one point with the DRAM fill counters
      (`perf stat -e ls_dmnd_fills_from_sys.dram_io_all,ls_hw_pf_dc_fills.dram_io_all`, ×64 B) so the
      counter method is calibrated for B1. This is the number every "% of roofline" divides by. ~15 min.
- [ ] **C5 — re-anchor the baseline in ONE clean build.** Build the fusion tree at its current tip in
      Release (record the commit and `llama-server --version` build id — this is *the C5 build*; every
      lever below reports against it). Artifact: the OP-32 uniform IQ4_XS file (record path and a fresh
      SHA-256 — none is on record). Recipe: the `canonical_recipe.py` wrapping at t ∈ {1, 48, 64}, r5,
      tg128 + pp512, `-mmp 0`, `GGML_IQK=1`. Two arms: **OMP stack ON** (canonical) and **OFF** — the
      −32% between the 08-28 record and INF-68 on the same lineage is unexplained, and the record already
      documents a 3–4× swing from exactly this stack on another model. Capture box state before and
      during: governor, a `scaling_cur_freq` sample under load, `numa_balancing`, THP `enabled`/`defrag`,
      `numastat -p <pid>` (proves the interleave actually happened), `AnonHugePages` from
      `/proc/<pid>/smaps_rollup`, loadavg and the INF-68 in-window sampler. Add one `perf stat` DRAM-fill
      count over a fixed token count → achieved GB/s per token directly. Deliverables: ms/token and
      achieved GB/s at each t, % of C0, the true 1T→48T scaling, and the first *measured* instrumentation
      penalty (same commit built Release vs `-DGGML_CPU_PROF`). ~45 min of box time.
- [ ] **C1 — report every decode result as achieved GB/s against the C0 number, alongside ms/token,**
      with the build id, thread count and artifact on every row. A t/s number alone does not answer
      "is this lever worth it".
- [ ] **C2 — every instrument gets a sanity assertion before its output is believed**, and every table
      states what its instrument cannot see. This campaign produced four self-observation failures
      (post-compute dumps of freed memory, an eval-callback latching onto the wrong node, a NULL-deref
      debug print that cost a multi-hour crash hunt, a profiler mis-attributing 90% of what it named).
      The audit added a fifth class: `GGML_CPU_PROF` **excludes barrier wait by construction**, so its
      per-node figures are a floor on compute, not a cost per node. `component <= total && duration >= 0`
      catches the fourth for free; "which side of the barrier is the timer on" catches the fifth.
- [ ] **C3 — hold the BUILD constant, not just the artifact, and chase every derived figure when a
      number is retired.** OP-32 ratified the artifact rule; this campaign shows the same applies to the
      build (a debug-build 1T number divided by a clean-build 48T number produced a "4.7×" that was
      really 2.8×). Ratios inside one build, one window, one artifact are admissible when absolutes are
      not — "same-window ratios are safe" is the usable form. And **retracting a number is not done
      until every quantity computed from it has an explicit disposition — survives / invalid /
      re-derive — and the survivors' own inputs are traced to a primary record.** The pre-audit version
      of this file kept "27% of roofline" as a survivor because it "used only the profiled gemv and the
      measured bandwidth"; both inputs turned out unsound (the doubled 425 and an unrecorded 28 ms).
      Mark invalid rather than substituting a rescaled value.
- [ ] **C4 — a control arm for every claim.** The fused path's "84% gemv" was uninterpretable until the
      graph was measured at the same thread count in the same build; the control took one run and
      inverted the conclusion. No same-conditions control, no claim.
- [ ] **C6 — belief-kernel wiring before the first C5 run.** C0/C5/B1/D0 are new measurement producers.
      Source-table row filed in `scripts/vidya/adapters/README.md` and task **SC53** in
      [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md): one `ClaimTuple` per
      `llama-bench` arm beside the run directory (artifact path + SHA, build id, full recipe, `-t`, n,
      reps, box-state capture) via the existing measurement ladder. Wire the write side with C5, not after.

## Axis D — the dispatch floor (the largest term, and the least measured)

The facts this axis rests on (fusion tree `exp/cpu-fusion-qwen4exp-20260829`, audited 2026-09-02):
every build directory is an **OpenMP** build (`GGML_OPENMP=ON`, gcc + libgomp), so the barrier is
`#pragma omp barrier` — libgomp's centralized barrier — and `--poll` is a no-op (it only exists in the
internal-threadpool path). The graph loop (`ggml-cpu.c:3228-3276`) issues **one full-team barrier after
every non-empty node** with no elision logic of any kind; `params.nth` is fixed once per graph, so ops with
`n_tasks == 1` (SCALE, GET_ROWS, ARGMAX, SOFT_MAX at one row, `MOE_TOPK_NORM` at batch 1, most unaries)
run on thread 0 while 47 threads spin into the barrier. Every batch-1 `mul_mat` pays a **second** barrier
inside the op after `from_float` quantizes the single activation row split across all 48 threads (10
blocks of Q8_K for 48 threads — 38 quantize nothing); every `mul_mat_id` pays its own internal barrier
after a serial row-grouping by thread 0 and a 512-entry scan by every thread. A 640-row projection is
sprayed as 14 rows per thread with no small-matrix threshold. The only CPU-side fusion is
`RMS_NORM+MUL`. None of the older CPU1-track barrier work (`GGML_CCD_POOLS`, `BARRIER_LOCAL`) exists in
this tree or in production. `tests/test-barrier.cpp` exists (2000 tiny mul_mats on the *internal*
threadpool). Host THP is `enabled=[always] defrag=[always]`, but ggml allocates weights with
`posix_memalign(64)` and never asks for huge pages.

- [ ] **D0 — measure the per-node floor directly; count the sync events per token.** (a) Build
      `test-barrier` twice — the internal threadpool (as-is) and an OpenMP twin — plus a barrier-only
      variant (2000 × SCALE on 16 elements) and run each at t ∈ {1, 8, 16, 24, 48, 64, 96} under the OMP
      stack: **µs per barrier vs thread count, per runtime**. (b) From `GGML_CPU_PROF_NODES` (extend it
      past 260 nodes) count, for one token on the C5 build: non-empty nodes, `mul_mat` internal barriers
      (797), `mul_mat_id` internal barriers (144), and the number of *consecutive thread-0-only* node
      pairs and *same-partition elementwise* node pairs (the D2 candidates). Deliverable: the dispatch
      floor in ms/token = Σ sync events × µs/barrier(t), and the ranked list of what D1–D3 can remove.
      Zero new kernels; one session.
- [ ] **D1 — remove the internal `mul_mat` / `mul_mat_id` barrier at batch 1.** For `ne11 == 1` every
      thread quantizes the whole activation row redundantly into thread-local `wdata` (2560 elements,
      ~1 µs) instead of splitting it 48 ways and synchronizing; for `mul_mat_id` at `n_tokens == 1` the
      row→expert map is trivial and can be built per thread, deleting the serial grouping, the barrier
      and the 512-entry scan. Removes ~940 sync events per token, bit-exact by construction. Expected:
      940 × µs/barrier(48) from D0 — 3–6 ms/token if the barrier is 3–6 µs. Gate: greedy generation +
      logit diff vs the C5 build.
- [ ] **D2 — barrier elision between nodes that do not need one.** Two safe classes, both decided at
      plan time (the standing TODO at `ggml-cpu.c:3244` to move fusion detection into `ggml_graph_plan`
      is the natural home — a per-node "barrier required" bitmap): (i) consecutive nodes that both run
      on thread 0 only; (ii) consecutive row-parallel elementwise nodes over the same shape with the
      same `ith/nth` partition and no cross-row reads (each thread reads only rows it wrote). This is
      what the three round-5 *kernel* fusions were reaching for; they lost because the fused kernels'
      own overhead ate the saving — eliding the barrier has no kernel. Count first (D0-b), then
      implement class (i), then (ii) with a per-op-pair contiguity/broadcast guard. Gate: greedy +
      logit diff, `test-llama-archs`, and the arch roundtrip that caught the round-5 intermediate-dst
      bug.
- [ ] **D3 — the barrier implementation itself.** Three cheap arms measured by the D0 harness first,
      then in situ: (a) the same tree built with **clang + libomp** (the canonical v5 recipe's runtime;
      libomp's barrier is hierarchical — `KMP_PLAIN_BARRIER_PATTERN` hyper/dist — where libgomp's is
      flat; `KMP_BLOCKTIME` set in `ggml_cpu_init` only applies there); (b) `GGML_OPENMP=OFF` — ggml's
      own spin barrier plus `--poll`/`--cpu-strict`, which then become live; (c) if neither reaches
      ~1.5–2 µs at 48 threads, a **hierarchical barrier patch** (per-CCD counter on a CCD-local cache
      line, then one top-level counter of 12) in `ggml_barrier` — ~100 lines. Stake: (µs/barrier(48) −
      2 µs) × sync events per token from D0; at the round-1 inference of ~6.6 µs and ~7,800 events that
      is up to ~35 ms/token, which is why D0 comes first.
- [ ] **D4 — thread count × placement sweep, after D1–D3 change the floor.** t ∈ {48, 64, 96, 192} with
      `OMP_PLACES=cores OMP_PROC_BIND=spread` versus explicit masks (`--cpu-mask` works in OpenMP builds;
      4 threads per CCD across all 12 CCDs vs 8 per CCD on 6, which decides how many GMI links carry the
      weight stream). The recorded "t64 sweet spot" and "t96 sync collapse" were measured under the old
      barrier; a cheaper barrier moves the optimum toward more threads and more bandwidth. Same build,
      same window, same artifact.
- [ ] **D5 — huge pages.** Measure first: `AnonHugePages` in `/proc/<pid>/smaps_rollup` during a C5
      run. If the weight buffers are not ~100% huge, add `MADV_HUGEPAGE` with 2 MB alignment in
      `ggml_backend_cpu_buffer_type_alloc_buffer` (`ggml-backend.cpp:2314` → `ggml_aligned_malloc`) —
      one self-contained change; the 2026-05-28 record shows khugepaged alone (~26 MB/s) cannot
      coalesce a 98 GB buffer inside a bench window. Stake: page-walk overhead on a 4.16 GB/token stream
      through 4 KB pages, 0–8%; decisive either way in one run.
- [ ] **D6 — the 797 small dense gemvs.** Bucket them by weight bytes from the D0-b node dump (the
      4-stream hyper-connection loras at 2560×320, the F32 router, indexer projections, shared expert).
      Levers in order: cap `nchunk0` so a thread never gets fewer than ~64 rows (idle threads still hit
      the graph barrier, so this only helps once D2 elides it); concatenate the per-stream lora weights
      at load into one `mul_mat` per hc site (fewer nodes, same math, bit-exact if accumulation order is
      preserved); quantize the F32 router (B4). Measure the dense-path in-function median before and after.
- [ ] **D7 — upstream CPU-side fusion sync.** The fusion tree has no upstream remote (`origin` and
      `prod` are local paths), so this needs a scratch clone with a network fetch of `ggml-org/llama.cpp`
      master. List the `ggml-cpu` commits since the champion's base that add fused variants
      (`ggml_cpu_try_fuse_ops`, the reserved `FUSE_*` enum in `ops.cpp:4013`, `TOP_K`, fused GLU/ADD
      chains, MoE-path changes) and port the bit-exact ones. Report the node-count delta on the C5
      build before claiming anything.

## Axis B — the weight stream: bytes per token and achieved GB/s per path

- [ ] **B1 — split the token by path and report achieved GB/s, not just ms — on the C5 build.** Use
      the in-function timers (`[mm_prof]`/`[mmid_prof]`, `build-cpu-prof`) for dense `mul_mat` vs expert
      `mul_mat_id` time, the tensor table for bytes per path (dense 2.344 / experts 1.296 / lm_head
      0.521 GB), and the DRAM fill counters over a fixed token count for total traffic — the three must
      reconcile (C2). Until this exists every other number in this axis is unanchored. This is INF-10's
      prescribed profile, still never run on this model.
- [ ] **B2 — decide what binds the expert path: per-call fixed cost or bandwidth.** The audit's
      reading of `mul_mat_id` says fixed cost (14–54 rows = 19–26 KB per thread per expert, two barriers
      per op, a serial grouping phase, ~130 GB/s in-function), and the retracted "5.6–17 GB/s" is not
      evidence of latency. Test it two ways, same build, same window: (i) `--override-kv
      qwen4exp.expert_used_count=int:N` for N ∈ {10, 5, 2, 1} — expert-path ms vs bytes: the slope is the
      per-byte cost, the intercept the per-call fixed cost; (ii) the same op at t ∈ {8, 24, 48}. **Time
      not scaling with bytes means fixed-cost-bound, not latency-bound** — do not read it as the
      pre-audit text did. If fixed-cost-bound: D1 and B3 are the levers. If bandwidth-bound: B4 and D4.
- [ ] **B3 — restructure `mul_mat_id` for batch 1.** Beyond D1's barrier removal: chunk across
      (expert × rows) jointly so each thread streams ≥ ~100 KB of one contiguous expert slab instead of
      14 rows of each; and **fuse up+gate** into one op. The two tensors are both IQ4_XS `[2560,640,512]`,
      so a `[2560,1280,512]` `ffn_gate_up_exps` is a per-expert byte-level concatenation — producible
      offline with `gguf-py` from the existing GGUF, no requant and no HF source (the 2026-08-28
      `--fuse-gate-up-exps` re-conversion attempt was never reported). Halves the expert-path op count
      (144 → 96 calls/token). Verify this tree's `build_moe_ffn` handles a fused gate-up tensor before
      producing the file; gate on greedy + logit diff.
- [ ] **B4 — the bytes budget: requantize what is streamed for no reason.** From the tensor table, per
      token: `ffn_gate_inp` **F32 → F16 or Q8_0** (−126 to −190 MB, 3–4.5%, routing logits tolerate it —
      verify top-10 agreement on a fixed prompt set); `output.weight` **Q6_K → Q5_K or IQ4_XS** (−80 to
      −200 MB; PPL/KL check on a fixed corpus); `ffn_down_exps` **Q5_1 → IQ4_NL** (block-32, so the
      640-wide rows fit, and it has the AVX2 8×8 repack path the UD file already used; −18% of ~590 MB).
      Each is a `llama-quantize --tensor-type` override on the existing GGUF. Every change makes a **new
      artifact**: per the artifact rule a delta is measured with the artifact identical on both arms, so
      the comparison is new-artifact-vs-uniform in the same build and window, and any headline is the
      served artifact's number. Quality gate alongside speed (`feedback_pair_speed_with_correctness_check`).
- [ ] **B5 — the from-source uniform artifact (with E1).** The OP-32 uniform file is a quant-from-quant
      of the unsloth UD shards ("speed control only — not quality-representative", INF-68). The E1
      re-download makes a from-source uniform IQ4_XS trunk possible in the same conversion that emits the
      MTP head; it closes INF-68's caveat and gives Axis E its target. Same recipe, same window, both
      files, before either becomes the served artifact.
- [ ] **B6 — interleave striping vs expert-local placement (deprioritized).** Expert weights are
      per-expert contiguous slabs (expert is the outermost GGUF dimension) — the pre-audit
      "interleaved rows / page-scatter" hypothesis is dead on arrival. The residual question is whether
      `--interleave=all` page-striping *inside* a 2.7 MB slab costs anything versus node-local
      placement. Only worth a run if B2 says the path is bandwidth-bound.

## Axis A — finish the fused decoder's viability test (INF-67)

The go/no-go was answered 2026-09-01: the batched `mul_mat` is callable on staged tensors, so the per-row
`vec_dot` in `FusedMM::dot` is a fixable implementation error, not a structural one. INF-67 remains the
design record; this is the live task list.

- [ ] **A1 — batched `mul_mat` substitution in `lora_mm`/`FusedMM`.** **Judge it on the gemv column
      ALONE, same build both arms**: 1141 ms → ~300 ms at 1T is success (the graph's own 1T gemv is of
      that order). Do NOT judge on total — see the trap below.
- [ ] **A2 — scratch arena.** Replace the per-layer `ggml_init`/free with one arena sized once. The
      "~2.5 GB/token of churn" is an **unsourced code-reading estimate** — the record describes the
      ~215 ms "other" cost only qualitatively; measure it before quoting it. This is half the viability
      case, not a Phase-4 nicety.
- [ ] **A3 — strip the debug I/O** before any timing is reported (~114 `fprintf`/`fopen` sites, ~70
      `getenv`, several in expert inner loops — counts as of 2026-09-01).
- [ ] **A4 — the safety contract** before any serving exposure: hook becomes OPT-IN
      (`supports_fused_decode()` is unconditionally `true` today, no residency checks), all persistent
      state commits atomically at end-of-token, repack guards on `tensor->extra` + type, remove the
      `t_logits` write that relies on allocation-ordering luck.

**⚠ The measurement trap on A1.** With the churn still present, a *perfect* gemv fix reads fused ≈ 300
(gemv) + 215 (other) = **~515 ms at 1T vs the graph's 350** — still 1.5× slower, because the graph's own
1T non-gemv cost is only ~50 ms. A1 and A2 are individually fatal; the design needs both. With both, the
ambition is the weight stream at the machine's rate (~32 ms for 4.16 GB at 130 GB/s, less as Axis B/D4
raise the rate) plus a fused-path overhead that has to be measured — **≈ 25–30 t/s if that overhead is
≤ 10 ms**. That is the ambition to test, not a predicted result. The fused/graph ratio (3.86× at 1T) is
the honest interim metric; it is same-build and roughly stable across thread counts.

- [ ] **A-GATE**: fused ≤ graph at 1T on BOTH the gemv column and the other column, **both arms in the
      SAME build**, then re-measure at 48 threads — again same-build — before comparing to the C5 anchor.
      Only then does the bit-exactness hunt resume.

## Axis E — restore the MTP head (speculative decoding), LAST

**Facts (audited 2026-09-02).** The HF release carries a ~4B-parameter MTP head; our converter module
`conversion/qwen4exp.py:28-30` drops it by policy (`supports_mtp_export = False; no_mtp = True`), while the
base converter already exports MTP heads for DeepSeek-V3, GLM4-MoE, Hunyuan, MiMo, EXAONE and Gemma4 as
`blk.N.nextn.*` tensors with `nextn_predict_layers` metadata (`--mtp` / `--no-mtp`). Production v9 already
has the complete speculative driver — `--spec-type draft-mtp` (`common/speculative.cpp:1702`), generic
across architectures, needing only the target graph to export the pre-final-norm hidden state
(`t_h_nextn`, precedent `src/models/qwen35moe.cpp:110-137`) and a sibling `mtp-*.gguf` head file. The gap
is therefore: no source weights on disk, ~30 lines of converter mapping, and the `qwen4exp.cpp` graph
export plus the head's decoder graph. Neither of the two GGUFs on disk contains the head, so **this
strictly requires the HF source**; the OP-32 "Option C" disk blocker (90 GB free) is gone (736 GB free
on 2026-09-02).

- [ ] **E1 — re-acquire the source.** `Qwen/Qwen3.8-Flash-Next-FP8` at the revision pinned in INF-63
      (`f88480ebce48…`, ~173–185 GB, 131 shards). Fetch `config.json` and `model.safetensors.index.json`
      **first** (small): they name the MTP tensors and the shards holding them, which decides full vs
      partial download and gives the head's hyper-parameters (layer type, whether it re-runs the PLE
      gather and the hc streams per draft token). Unauthenticated HF is ~9 MB/s (≈6 h full); one download
      at a time on this host; **never during a measurement window**. Shared with INF-63 and B5.
- [ ] **E2 — converter.** In `conversion/qwen4exp.py`: `supports_mtp_export = True`, drop `no_mtp`,
      map the MTP block onto `MODEL_TENSOR.NEXTN_{EH_PROJ, EMBED_TOKENS, ENORM, HNORM, SHARED_HEAD_HEAD,
      SHARED_HEAD_NORM}` (and whatever layer tensors the head carries), `add_nextn_predict_layers(1)`.
      Emit trunk (`--no-mtp`) and head (`--mtp`) as two files; quantize the trunk uniform IQ4_XS from
      source (B5) and the head Q8_0 (~4 GB). Keep the FP8-PLE dequant/scale patch this module already has.
- [ ] **E3 — graph.** In `qwen4exp.cpp`: export `t_h_nextn` (qwen35moe precedent), load the nextn
      tensors under `mparams.load_mtp`, and build the head's `LLM_GRAPH_TYPE_DECODER_MTP` graph from the
      existing layer builders (GDN or attention block + MoE, `eh_proj` over `[enorm(embed); hnorm(h)]`,
      shared head norm + lm_head). Validate with the arch test plus a greedy-agreement check between
      draft and target on a fixed prompt set.
- [ ] **E4 — measure α before tuning anything** (`feedback_measure_alpha_before_specdec_investment`):
      acceptance per draft position on the production prompt mix, `--draft-max` ∈ {1, 2, 3, 4}, on the
      C5 recipe and the C5 build with the from-source trunk. Precedents: gemma4 MTP 58–95% acceptance;
      Qwen native MTP 41.9 t/s vs 31 plain vs ~18 with an external drafter.
- [ ] **E5 — the comparison arms, one `--spec-type` at a time**: plain, `ngram-mod` (free, no head —
      but the recorded 2.8× n-gram win was a warm-context self-copy artifact, true gain ≤ +1.7%),
      `draft-mtp`, and the INF-62 DFlash2 block drafter. Same build, same window, same trunk artifact.
- [ ] **E-GATE**: acceptance-weighted t/s against the non-speculative C5 number for the same trunk,
      reported per the artifact rule. Note the PLE regime: under `--no-mmap` the 51B table is resident
      and every draft token pays its own PLE gather and hc stream mixing; that cost is part of the
      measured acceptance-weighted number, not something to subtract.

## Reporting

Non-claims (no protocol id, no attestation) are welcome and expected while exploring — label them.
Anything that gates a keep/revert decision needs the codified recipe and an attestation per
`agents/shared/MEASUREMENT_POLICY.md`, including its **artifact rule** (ratified OP-32): an absolute
headline is the served artifact's number; a delta is measured with the artifact held identical on both
arms. The uniform IQ4_XS file is the required comparison baseline for this model until B5 replaces it by
the same procedure. Every row carries: build id, thread count, artifact (path + SHA), recipe (with the OMP
stack stated), n and reps, and — after C0 — achieved GB/s and % of the measured read bandwidth.

## Audit log — 2026-09-02

Audit of the 2026-09-02 draft against primary records (`progress/2026-08/2026-08-28.md`, the INF-67/INF-68
records, the artifact's tensor table, the fusion tree's `ggml-cpu.c`, and the bandwidth tool's source).
Corrections applied in this file:

1. **425 GB/s retired** — `bench_stream3.cpp` divides 4 GiB by the copy time of a 2 GiB array (read+write
   already counted, standard STREAM); its "traffic" column doubles again. Measured copy is 212 GB/s at an
   unrecorded thread count without the OMP stack; read-only bandwidth under the recipe was never measured
   → **C0**. The DGX-Spark comparison is withdrawn until C0 exists.
2. **"5.6–17 GB/s expert path" retired** — the same record retracts it (`2026-08-28.md:170,190`): the
   per-op profiler was contaminated by cross-node waits; in-function timing gives 68–88 µs/call,
   ~100–130 GB/s. Axis B rebuilt on the fixed-cost hypothesis with a discriminating test (B2).
3. **Bytes per token corrected** from "2.8–3.4 GB" (another model's 2026-05-28 figure) to ≈ 4.16 GB from
   the artifact's tensor table; the F32 router, the Q6_K lm_head and the Q5_1 down-experts surfaced (B4).
4. **"28 ms gemv" retired as a measured number** — its constants are in no committed profiler record
   (INF-68 audit); the in-function medians are the sourced equivalents. "27% of roofline" fell with it.
5. **Node count corrected** to the measured 7,906 / 6,887 (INF-67's ~5,850 / ~6,800 are unsourced).
6. **B3 (prefetch at router time) rewritten** — the router reads the post-attention state
   (`qwen4exp.cpp:314-360`); no in-layer window exists, and `madvise(WILLNEED)` is inapplicable under
   `--no-mmap`. **B4 (expert locality) demoted to B6** — experts are contiguous slabs.
7. **Axis D added** — the dispatch floor was the largest term in every accounting and had no tasks: the
   profiler that produced "5–8 µs/node" cannot see barrier wait, and the tree's barrier, internal
   matmul barriers, absent elision, THP and runtime choice were never examined.
8. **Axis E added** (operator direction): MTP restoration as a rider on INF-46/50/62/63, sequenced last.
9. Recipe made explicit (the `canonical_recipe.py` prefix + OMP stack; INF-68 used it, the 08-28 bandwidth
   run did not), C5 gained the OMP on/off arm and the box-state capture, C6 wires the belief kernel.
10. INF-68 path fixed (`../completed/`), INF-67 given a pointer to this task list, wiki
    `benchmark-methodology.md` correction 1 rewritten as the fifth correction.
