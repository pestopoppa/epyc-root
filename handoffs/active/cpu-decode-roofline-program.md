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
- Axis E riders: `unsloth/Qwen3.8-Flash-Next-GGUF` `MTP/` (the published heads, revision `5d16c055`),
  [`qwen38-flash-next-fp8-evaluation.md`](qwen38-flash-next-fp8-evaluation.md) (INF-63 — its FP8
  re-acquisition is no longer needed for MTP), [`qwen-mtp-llamacpp-port.md`](qwen-mtp-llamacpp-port.md) (INF-46),
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
want the agent to tackle hard-to-get gains."* The one Axis E item that ran early is E1, the download of
the published MTP heads (I/O-only, ~6 GB, done 2026-09-02 at the operator's direction); nothing else in
Axis E starts before A–D report.

## The gap — corrected ledger

Every row names its record and its conditions. **Measured** = a number someone read off an instrument;
**computed** = arithmetic on measured inputs; **retired** = do not cite.

| quantity | value | status | record / conditions |
|---|---|---|---|
| **decode anchor (C5, 2026-09-02), uniform IQ4_XS, placement PROVEN interleaved** | **98.6 ms/token (10.14 ±0.04 t/s)** at t48 on the INF-68 build 10151; **99.1 ms (10.09 ±0.04)** on the C5 build 10196 (`58c345093`, Release, gcc 15.2, OpenMP, graph path via `GGML_FUSED_DECODE_OFF=1`); t64 9.73 / 9.69; t96 9.67; OMP placement stack OFF 9.76 (−3%); **t1 = 5.04 t/s (198 ms)** → 1T→48T scaling **2.0×** | measured | `/mnt/raid0/llm/tmp/inf70/results-c5v2-20260902T103808Z/` (per-arm logs, in-window `numastat -p`, `AnonHugePages`, MHz). Recipe = INF-68's exactly (`taskset -c 0-95 numactl --interleave=all`, OMP spread/cores/active/dynamic-false, `GGML_IQK=1`, `-mmp 0`, tg128+pp512 r5, region-locked, load-gated) **plus per-node page-cache eviction before load**. Artifact SHA-256 `4bfb98496364f8721c1e3ea084a238d690c52b1042a317e05fb43b756c9f8957`. Model pages per node 27.4 / 23.5 / 23.5 / 19.6 GB; `AnonHugePages` = 100% of RSS. INF-68's 10.52 reproduces within 4% |
| **the same run with the box AS-IS** (nodes full of page cache) | **130.7 ms (7.65 ±0.03)** t48, 7.22 t64; pp512 124 vs 176 | measured | same build, same recipe, 12 minutes earlier; model pages per node **57.7 / 10.7 / 8.0 / 17.7 GB** under `--interleave=all`. **Placement alone is −25% decode / −30% prefill.** This is the mechanism behind the 08-28 → 08-31 "−32%": the kernel's zone fallback ignores the interleave policy when the chosen node has no free pages |
| decode, UD-IQ4_XS (the served file), **placement proven interleaved** | **109 ms (9.18 ±0.01)** t48, 8.73 t64; pp512 136 | measured 2026-09-02 (`results-c5fu-20260902T111721Z/`) | INF-68's 9.13 reproduces; uniform is **+10.5%** over UD under clean placement (+15.2% in the INF-68 window). The 08-28 **13.46 t/s does not reproduce under any regime measured** — retired for good |
| ~~74 ms / 13.46 t/s~~ (UD, 08-28) | **retired**: UD under clean placement measures 9.18 t/s on the same lineage and recipe; as-is 7.65 (uniform). Nothing measured today reaches 13.46 — treat the 08-28 row as unexplained, not as a target | retired | `2026-08-28.md:206`; `2026-08-31.md:228`; the 2026-09-02 arms |
| bytes streamed per token | **≈ 4.16 GB** = dense 2.344 + routed experts 1.296 (10/512 × 48 layers, avg 2.70 MB/expert) + `output.weight` 0.521 (Q6_K, 2560×248320) | computed 2026-09-02 from the artifact's tensor table (`gguf_dump`, 1224 tensors) | replaces the retired "2.8–3.4 GB", which was a different model's 2026-05-28 figure. Notable: `ffn_gate_inp` (router) is stored **F32** — 252 MB/token (6%) just to route; `ffn_down_exps` is **Q5_1 in layers 0–5 and IQ4_NL in the other 42** (640 % 256 ≠ 0, so IQ4_XS is impossible; `use_more_bits` picks Q5_1 for the first n_layer/8) — corrected by B4 on 2026-09-02 |
| DRAM bandwidth, theoretical | **460.8 GB/s today** (12 ch × 4800 MT/s × 8 B); **537.6 GB/s at the DIMMs' rated 5600** | measured config (SMBIOS type 17, 2026-09-02) | Supermicro H13SSL-NT, 12 × Samsung M321RYGA0PB0-CWMCJ 96 GB 2R DDR5 RDIMMs, one per channel, **rated 5600 MT/s, configured 4800**. One DIMM per channel is the fast population on SP5 (the 4800 cap belonged to EPYC 9004; a 9655 supports 6000 at 1DPC). Operator: BIOS memory clock → 5600 at the next reboot; **re-run C0 and C5 after it** — every bandwidth-bound number scales by up to +17% |
| DRAM bandwidth, measured **copy** | **212 GB/s, read+write already counted** | measured (conditions incomplete) | `bench_stream3.cpp` 2026-08-29: 2 GiB arrays, malloc + parallel first-touch, default 96 threads, NUMA mode and OMP placement unrecorded. The tool divides 4 GiB by the copy time of a 2 GiB array — standard STREAM convention |
| ~~425 GB/s "traffic"~~ | **retired — a double count** | retired | the tool's "traffic" column multiplies the already-read+write copy figure by 2 again. Never measured on this box. Every "% of 425" in the pre-audit handoff, the ~8% fraction, the "1.3–4% expert path" and the DGX-Spark comparison inherited it |
| **DRAM bandwidth, read-only, under the decode recipe (C0, measured 2026-09-02)** | **152.6 GB/s at 48 threads, 165.6 at 96** (read-sum); gemv-pattern 153 / 167; copy 92 / 94 (STREAM convention, RFO); copy-NT 134; triad 102–105 — **with free memory on every node**. Box AS-IS: a flat **67–77 GB/s from 24 to 192 threads**, identical to one node's 3 channels (66 GB/s at 24 threads `membind=0`) | measured (`bench_readbw`, `results-c5v2-…/c0-evicted.txt`, `results-20260902T102729Z/c0-readbw.txt`) | Even with clean placement, a single process under NPS4 software interleave reads at **33–36% of the 460.8 GB/s theoretical**; one node alone reaches 57% of its 115 GB/s. **C0-c (four node-local processes at once, 24 threads each): 38 + 42 + 38 + 54 = 171 GB/s aggregate — each node drops from 66 GB/s alone to ~40 when all four stream.** The cap is therefore **global (~170 GB/s), not per-node channels and not remote-quadrant traffic** — the memory subsystem delivers ~37% of nominal in every locality pattern, which points at the uncore: memory clock, UCLK:MEMCLK ratio, Infinity-Fabric P-state/APBDIS, DF C-states or DRAM power-down — BIOS-level, see C8. Huge pages made no difference to the microbench |
| roofline (bytes ÷ read bandwidth) | **27 ms/token (37 t/s)** at the measured 153 GB/s the recipe delivers today; **9 ms (111 t/s)** against the 460.8 GB/s theoretical | computed | 4.16 GB ÷ 153 GB/s; the gap between the two rows is the NPS4/placement question, not the kernel's |
| achieved fraction | **27% of the recipe's bandwidth; 9% of theoretical** | computed | 27/99.1 and 9/99.1 |
| **the token, decomposed by the profiler (D0/B1, 2026-09-02)** | **97.3 ms = 62.9 ms in the 941 weight-path nodes (43% of read BW on average: small gemvs 40%, lm_head 94%) + 33.4 ms in 3,468 non-weight nodes + 22.5 ms of barrier/straggler wait folded across both; 5,410 sync events ≈ 10.3 ms of it** | measured (build 10197, thread-0 wall after the barrier, reconciles to +0.9%) | replaces the by-difference estimate. The bandwidth-only floor is 27 ms (4.16 GB at 153 GB/s); the rest is small-gemv inefficiency (~36 ms above the floor), non-weight compute (~33 ms) and waits. Adding threads no longer helps (t64 −4%, t96 −4%; B2: 8→48 threads +7%) |
| tiny `mul_mat` node cost in the real OpenMP build (`test-barrier`, 2000 × [64×128] Q4_0) | **0.50 µs at 1T, 3.0 at 8T, 3.7 at 24T and 48T, 5.5 at 96T** per node | measured (`results-c5v2-…/d0-test-barrier.txt`) | a matmul node pays two barriers (`from_float` + graph) ≈ 2 × 1.9 µs — consistent with the primitive; ~940 matmuls + ~6,000 other nodes ≈ **15 ms/token of barriers at 48T** |
| instrumentation penalty, 1T | debug/`GGML_FUSED_PROF` build 350 ms vs Release 198 ms = **1.77×** | measured (same lineage, `58c345093` vs the INF-67 debug tree) | the fused decoder's 1350 ms at 1T is therefore **~6.8× slower than the clean graph**, not 3.86× |
| graph nodes per token | **7,906** pre-fusion; **6,887** after `MEAN_D1` + `MOE_TOPK_NORM` (the baseline build) | measured | `2026-08-28.md:88,142` and round 1 (`7902 → 6887`, −13%). The "~5,850 / ~6,800" in INF-67 are in no record |
| thread-0 compute per node | 5–8 µs | measured, **excludes barrier wait** | `GGML_CPU_PROF` times the compute call only; the graph barrier at `ggml-cpu.c:3274` is outside its window. Three measurements, round 5 |
| barrier primitive, measured 2026-09-02 | **1.9 µs at 48 threads, 2.4 µs at 64, 3.2 µs at 96** (libgomp `omp barrier`, OMP stack on, threads 4 per CCD); ggml's flat atomic barrier 1.9 / 2.1 / 2.8 µs; a per-CCD hierarchical prototype 2.1 / 2.1 / 2.8 µs (**no gain**); barrier + 1 µs of private work = 2.8 µs at 48T | measured (`bench_barrier`, `results-20260902T102729Z/d0-barrier.txt`) | At ~7,800 sync events/token that is **~15 ms at 48T, ~25 ms at 96T** — real, but well under half of the 35–55 ms per-node budget. The remainder is dispatch, tiny-op compute and straggler wait, which the D0-b node census must split. The libomp-via-`LD_PRELOAD` arm **hung** (GOMP ABI shim) — D3a needs a real clang+libomp build. Sync events per token: still to be counted (D0-b) |
| **expert path (`mul_mat_id`), by N-sweep extrapolation (B2, 2026-09-02)** | **~19.7 ms/token at 65.8 GB/s** (uniform IQ4_XS, build 10196, clean placement); marginal cost of expert bytes 1/15.44 = 64.8 GB/s (53% on the confound-free N=10→5 step) | measured (four N arms + controls, same window) | replaces the pre-fix in-function estimate (68–88 µs × 144 ≈ 10–13 ms on the UD file). ~8.5 ms of the 19.7 is bytes at 153 GB/s; **~11 ms is the current per-expert 48-way split** (14–54 rows per thread, ten short streams per op). The old "5.6–17 GB/s" remains retracted |
| dense path (`mul_mat`), 797 calls/token | in-function median ~20 µs (Q8_0 dense) → ~16 ms if representative; profiler-attributed 57 ms (72 µs/call) *including waits* | partly measured | `2026-08-28.md` rounds 2/3/6. The 40 ms between the two figures is wait time nobody has assigned. **B1 settles the split** |
| fused decoder, same debug build, `-t 1` | fused 1350 ms vs graph 350 ms (**3.86×**); fused gemv 1141 / other 215 | measured (non-claim) | `2026-09-01-inf67.md`; safe only as a same-window ratio |
| ~~28 ms gemv / 46 ms non-gemv~~, ~~65 µs × 144 = 9.4 ms~~ | **retired** | retired | a partition of the retired 74 ms; the constants are "unmatched by committed records" (INF-68 audit). The in-function medians above are the sourced equivalents |

**What the ledger says (measured 2026-09-02, profiler-confirmed).** With placement fixed, a 97 ms token is
**63 ms in 941 weight-path nodes that reach only 40% of the machine's read bandwidth because they are
small (the one big gemv reaches 94%), 33 ms in 3,468 nodes that move no weights (9.3 ms of it GET_ROWS on
one thread), and 22 ms of barrier and straggler wait spread across both (10 ms of it the 5,410 barrier
primitives themselves).** Two ceilings, in this order: (1) the **dispatch floor** —
~70 ms, and more threads do not buy it down (t96 is slower than t48); Axis D and Axis A attack it, and it
is where 2–3× lives; (2) **bandwidth** — the recipe gets 153 GB/s of a 460.8 GB/s machine: placement
(fixed by eviction, −25% otherwise), then NPS4's software interleave (C0-c decides between BIOS NPS1 and
per-quadrant sharding), then the 4800→5600 MT/s BIOS change. Axis B's bytes levers scale the 27 ms only.
Axis E multiplies whatever is left. The DGX-Spark comparison stays withdrawn: this box currently *reads*
at 153 GB/s in the configuration that serves.

## Ordering

1. ~~**C0 → C5**~~ ✅ done 2026-09-02 (ledger). Every absolute number below reports against **99.1 ms /
   153 GB/s** with the eviction step in the recipe. **C7 (make the placement fix permanent) is the first
   open item**, because without it every later measurement silently regresses to the as-is regime.
2. **B1 + D0** (one session, no new kernels): the per-path GB/s split and the per-node floor, on the C5
   build. These two numbers rank every lever below by ms/token at stake.
3. **Levers by measured ROI**: Axis D (D1–D7) and Axis B (B2–B4) are independent of each other and of
   Axis A; run them in parallel sessions, each against the C5 anchor in the C5 build.
4. **Axis A** continues in its own session against the same anchor (A-GATE).
5. **Axis E** after A–D report their first measured results (E1, the head download, is already done).

If this ordering is overruled, say so in this file with the reason; it is a recommendation with a reason,
not a gate.

## Axis C — measurement (FIRST; cheap, and it makes every other axis legible)

- [x] **C0 — measure the roofline denominator: read-only DRAM bandwidth under the decode recipe.** ✅ 2026-09-02
      — 152.6 GB/s at 48T / 165.6 at 96T with free memory on all nodes; 67–77 GB/s as-is (ledger).
      Remaining sub-question **C0-c**: four node-local processes at once (`c5_followup.sh`, running at
      audit close) — if the aggregate approaches 4 × 66 GB/s, the single-process 153 is the NPS4 fabric and
      BIOS NPS1 / per-quadrant sharding become Axis B levers. The counter cross-check could not run: `perf`
      is not installed in this container. Original task text follows for the method.
      Extend `bench_stream3.cpp` (on disk under `/tmp/qwen4exp-builds/`, or rewrite it under the research
      repo) with a **read-only** kernel (sum-reduce over a 2 GiB buffer, and a second "gemv pattern"
      variant: 2560-element rows dotted against a resident vector), malloc + parallel first-touch, run
      under exactly the recipe prefix — `taskset -c 0-95 numactl --interleave=all` with the OMP stack —
      at t ∈ {24, 48, 64, 96, 192}, best of 5. Report GB/s per thread count with the counting convention
      stated (bytes read only). Cross-check one point with the DRAM fill counters
      (`perf stat -e ls_dmnd_fills_from_sys.dram_io_all,ls_hw_pf_dc_fills.dram_io_all`, ×64 B) so the
      counter method is calibrated for B1. This is the number every "% of roofline" divides by. ~15 min.
- [x] **C5 — re-anchor the baseline in ONE clean build.** ✅ 2026-09-02 — 10.14 / 10.09 t/s at t48 (INF-68
      build 10151 / C5 build 10196), t1 5.04 t/s, OMP-stack-off −3%, artifact SHA recorded, placement proven by
      in-window `numastat -p`; the as-is arm (7.65 t/s) measured the mechanism (ledger). The libomp arm was
      dropped (the `LD_PRELOAD` shim hangs). Original task text follows for the method. Build the fusion tree at its current tip in
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
- [x] **C6 — belief-kernel wiring before the first C5 run.** ✅ 2026-09-02 — `inf70_roofline_ledger.py` + `cli.py ingest inf70`; 147 claims / 441 frames over the three measured run dirs, zero refusals; `tests/vidya` 763 passed (SC53 ✅). C0/C5/B1/D0 are new measurement producers.
      Source-table row filed in `scripts/vidya/adapters/README.md` and task **SC53** in
      [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md): one `ClaimTuple` per
      `llama-bench` arm beside the run directory (artifact path + SHA, build id, full recipe, `-t`, n,
      reps, box-state capture) via the existing measurement ladder. Wire the write side with C5, not after.
- [ ] **C7 — make the placement fix permanent, everywhere a CPU model is loaded.** *(a) ✅ 2026-09-02 —
      research branch `inf70/c7-placement` (6f7bdadb, pushed; merge to research `main` is the owning
      session's/operator's step — the auto-mode classifier refuses a branch→main push from this session):
      `scripts/utils/numa_evict.py`, `scripts/utils/numa_placement_check.sh` (exit 3 above 40% share),
      `bench_canonical.sh --pre-evict-gib` (default 40) with the in-window placement proof as a REQUIRED row,
      `canonical_recipe.py` constants + the eighth drift-class entry; 15 + 34 tests pass. Launch-path half
      ✅ prepared, default OFF: orchestrator branch `inf70/c7-placement` (e9d4b817, pushed) adds
      `numa_pre_evict_gib` (role field), pre-evict before `Popen` and a `[numa-placement]` log fold; 283 + 136
      tests pass; enabling is a one-line `stack_topology.yaml` edit and the priors recompile must precede the
      merge because the prior hashes pin `orchestrator_stack.py`/`stack_numa.py`. (b) audited — no CPU
      server live (below). (c) still open — the durable form.* Measured 2026-09-02: when a
      NUMA node has no free pages, `numactl --interleave=all` is silently ignored for that node's share and the
      model lands wherever memory is free (57.7 GB of 96 on node 0), costing −25% decode / −30% prefill. The
      box is normally in that state (1,085 GB of page cache). Three deliverables: (a) `canonical_recipe.py`
      and `bench_canonical.sh` gain a **pre-load step** — per-node free check, then either `drop_caches`
      (root) or the targeted membind allocate-and-touch eviction (`/mnt/raid0/llm/tmp/inf70/where_pages.py`,
      ~30 s per 30 GiB) — and record `numastat -p <pid>` in-window as a required row; a run without it is
      not an interleaved measurement. (b) **Audit the live production servers** (read-only: `numastat -p` on
      each `llama-server` pid in the orchestrator stack) and hand the owning session the list of skewed ones
      for an eviction + restart at their boundary — this is almost certainly the mechanism behind
      [`numa-placement-defect-20260730.md`](numa-placement-defect-20260730.md) and the "frontdoor at 46% of
      canonical" drift. **(b) audited 2026-09-02 11:49Z (read-only):** no CPU `llama-server` is live at all —
      the orchestrator API answers on :8000 with no CPU model resident, so the fix belongs in the launch path
      before the next stack start, not in a restart. The two long-lived model processes found: `sd-server`
      (Ernie image turbo, 12 GB, up since 08-21, `-t 96`, interleave policy set) sits **8 / 40 / 32 / 19 %**
      across nodes — the same fallback; and the autokernel loop's GPU `llama-bench` is 89 % on node 3 by
      design (host threads pinned to 184-191). Per-node free after this session's evictions: 70 / 31 / 34 /
      24 GB — still uneven, so the next 98 GB interleaved load will skew again without (a). **Recurrence
      2026-09-02 (B4, D7a, PROF each saw one): a run skewed even after eviction reached ≥ 40 GiB free per
      node inside the lock (B4: 44.6/23.5/23.5/2.4 GB with node 3 at 41 GB free at eviction time) — the
      allocator still falls back under concurrent page-cache growth (a 180 GB download was writing all
      afternoon). Eviction reduces the odds; only the in-window `numastat` proof makes a run valid, and
      only a durable form closes it.** (c) Decide the durable form with the operator: `vm.zone_reclaim_mode=1` (reclaim on
      the intended node before falling back — system-wide, hurts file-heavy work), a drop_caches hook in the
      stack's launch path, or BIOS NPS1 (hardware interleave makes the placement question disappear; C0-c
      says whether it also lifts the 153 GB/s). Memory note: `feedback_page_cache_defeats_numa_interleave`.
- [ ] **C8 — the BIOS session at the next reboot (operator-executed; this task prepares and verifies).**
      C0-c shows a **global ~170 GB/s read cap** (37% of nominal) that no software placement lifts, and the
      DIMMs run at 4800 of their rated 5600 MT/s. Prepare a one-page checklist for the operator's BIOS
      session on the H13SSL-NT: (1) DDR5 memory clock 5600 MT/s (DIMMs rated; 9655 supports 6000 at 1DPC);
      (2) **UCLK:MEMCLK = 1:1 (UCLK DIV1 mode)** — a 1:2 ratio halves controller bandwidth and would
      match the observed ~37%; (3) **APBDIS = 1 with fixed SOC/DF P-state P0** and DF C-states disabled
      (AMD's bandwidth-sensitive tuning guidance; a low fabric P-state caps DRAM bandwidth globally);
      (4) DRAM power-down / memory power-down mode disabled; (5) keep NPS4 for now (C0-c says locality is
      not the binding term; revisit NPS1 only after 1–4); (6) leave IOMMU/SMT as they are. Verification,
      immediately after the reboot and before anything else loads: `numactl -H` free per node, then the
      C0 microbench (`bench_readbw`, 2 min) — target ≥ 300 GB/s read at 96T on a 12-channel 5600 MT/s
      socket; then C5 (15 min) and record both in this ledger with the new build/BIOS state. Every
      bandwidth-bound number in the program moves with this; the dispatch floor (~70 ms) does not.
- [ ] **C9 — `llama-perplexity` returns NaN for qwen4exp; there is no PPL/KL gate for this model.**
      Measured 2026-09-02 on build 10196 against the OP-32 uniform artifact: `nan` from chunk 1 under
      `-b 2048` / `-b 512` / `-fa 1` / `-c 2048`; the same binary returns `PPL = 17.29 ± 3.29` on
      Qwen3-1.7B-Q8_0, so the tool is sound and the defect is architecture-specific — suspect the
      all-logits (`n_outputs > 1`) path, which `llama-bench` and server generation never exercise. Until
      fixed, quant quality can only be gated by greedy-generation agreement
      (`agents/b4/gen_arm.sh` + `compare_gen.py`), which cannot prove equivalence. **Blocks B4's, B5's,
      INF-71's and every future quant decision on this model.** Note E2c's finding on the single-token vs
      batched forward when investigating — the all-logits path is the batched path.

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
`posix_memalign(64)` and never asks for huge pages. **Measured 2026-09-02 (D0-a):** the barrier primitive is
1.9 µs at 48 threads and 3.2 µs at 96 in the exact runtime the graph uses, and a hierarchical prototype does
not beat it — so the 5–8 µs thread-0 compute per node plus the barrier is ~2 µs of synchronisation and the
rest is dispatch, tiny-op work and waiting for the slowest thread. **C5 then sized the whole floor: ~70 ms of
a 99 ms token, of which barriers are ~15 ms; the ~55 ms remainder is tiny-op compute that does not
parallelise (the same ops cost ~45 ms single-threaded) plus imbalance.** That moves the weight of this axis
from D3 (the primitive) to D0-b/c (which nodes carry the 55 ms), D2 (fewer sync points) and, above all, to
Axis A's structural answer — fewer, fatter nodes — which this measurement now supports with clean numbers.

- [x] **D0 — measure the per-node floor directly; count the sync events per token.** ✅ 2026-09-02 —
      (a) barrier primitive (ledger); (b)+(c) on build 10197 (`inf70/prof`, `-DGGML_CPU_PROF` with a third
      thread-0 timestamp AFTER the graph barrier, a measured `ggml_barrier()` counter, per-path bytes and
      the full node table; zero measurable overhead with the profiler off or on: 10.12 / 10.28 vs the 10.09
      anchor), t48, uniform IQ4_XS, placement 23.5 GB × 4: **a 97.32 ms token = 73.75 ms thread-0 compute
      + 22.52 ms barrier-and-straggler wait (23.4%)**; **5,410 measured sync events/token** = 4,409 graph
      barriers + 797 `mul_mat` + 144 `mul_mat_id` + 36 `gated_delta_net` + 24 `flash_attn_ext` internal
      barriers (offline census derives 5,410, residual 0) → **10.3 ms/token at 1.9 µs**, not the ~15 ms
      estimate. **1,208 of 4,493 executed nodes (26.9%) run on one thread.** D2 candidates: 432
      single-task pairs + 147 same-shape elementwise pairs = 579 barriers ≈ **1.1 ms** — D2 is demoted.
      Σ per-node wall reconciles with `graph_compute` to +0.9% (C2). Top of the wall table: MUL_MAT 797
      nodes 41.9 ms (7.2 wait), MUL_MAT_ID 144 / 21.0 (3.9 wait), **GET_ROWS 175 / 9.3 ms, all
      single-task**, UNARY 510 / 5.8, CPY 162 / 3.7 (2.2 wait), GATED_DELTA_NET 36 / 3.0 (0.8 compute —
      3.8× wait), ADD 689 / 1.7. Evidence `/mnt/raid0/llm/tmp/inf70/agents/prof/` (TABLES.md, node table,
      per-node table).
- [x] **D1 — remove the internal `mul_mat` / `mul_mat_id` barrier at batch 1.** ✅ 2026-09-02 — implemented
      and **proven bit-exact** (3 prompts × 128 steps bitwise-identical logits; 2,280 `test-backend-ops -b CPU`
      cases with receipts identical to a same-commit control; `test-iqk-ser`, `test-llama-archs`), but **no
      measurable speedup: 96.06 vs 96.11 ms/token at t48 (+0.05%, inside the base build's own 0.5% spread);
      t96 −0.7%**. Branch `inf70/d1` (`1ba448e74`, +328/−39 in `ggml-cpu.c` and `iqk/iqk_dispatch.cpp`), not
      merged — keep, land only if D2 proceeds. Two findings that outrank the null result: **(a) under
      `GGML_IQK=1` the iqk dispatch hooks own the activation quantization and the barrier and return before
      the generic code — the generic `ggml-cpu.c` matmul path is dead on this model, so any barrier or
      chunking work (B3-k included) must patch `iqk_dispatch.cpp`**; (b) deleting ~940 sync events/token is
      invisible in the token, so the barrier-count levers D2/D3 are re-priced to ~zero — the 22.5 ms of
      wait the profiler sees is straggler/imbalance, not the primitive. Report:
      `/mnt/raid0/llm/tmp/inf70/agents/d1/REPORT.md`.
- [ ] **D2 — barrier elision between nodes that do not need one (re-priced to ~zero: D0 counts 579 eligible
      pairs ≈ 1.1 ms and D1 showed 940 removed sync events are invisible in the token; do not run unless a
      later measurement reopens it).** Two safe classes, both decided at
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
      ~1.5–2 µs at 48 threads, a **hierarchical barrier patch** in `ggml_barrier`. **Measured 2026-09-02:
      libgomp is already at 1.9 µs at 48T and the hierarchical prototype does not beat it (2.1 µs); the
      primitive only becomes a lever at 96+ threads (3.2 µs → ~2 µs ≈ 9 ms/token).** Demoted: run (a)
      only if D4 moves the operating point to 96 threads or more.
- [x] **D4 — thread count × placement sweep.** ✅ closed 2026-09-02 by measurement, not run further: with
      clean placement t48 10.09 / t64 9.69 / t96 9.67 t/s (C5), and B2's `-t 8,24,48` arm gives 9.57 / 9.53 /
      10.26 — the decode floor is saturated at 8 threads and more threads do not buy bandwidth. Re-open only
      if D1/D2/B3-k or Axis A change the floor. Original text: t ∈ {48, 64, 96, 192} with
      `OMP_PLACES=cores OMP_PROC_BIND=spread` versus explicit masks (`--cpu-mask` works in OpenMP builds;
      4 threads per CCD across all 12 CCDs vs 8 per CCD on 6, which decides how many GMI links carry the
      weight stream). Measured 2026-09-02 with clean placement: t48 10.09, t64 9.69, t96 9.67 — more threads
      do not help today because the floor is not bandwidth; re-sweep only after D1/D2 or Axis A move the
      floor. Same build, same window, same artifact.
- [ ] **D5 — huge pages (demoted to verify-only).** Measured 2026-09-02: with free memory on the nodes the
      weight buffers are **100% `AnonHugePages`** (96.3 of 96.4 GB) with no code change — THP `always` does
      it at fault time; only the as-is/cache-full regime showed 68%. Nothing to gain once C7 is in place;
      keep the in-window `AnonHugePages` line as a check. Original: measure `AnonHugePages` in
      `/proc/<pid>/smaps_rollup` during a C5
      run. If the weight buffers are not ~100% huge, add `MADV_HUGEPAGE` with 2 MB alignment in
      `ggml_backend_cpu_buffer_type_alloc_buffer` (`ggml-backend.cpp:2314` → `ggml_aligned_malloc`) —
      one self-contained change; the 2026-05-28 record shows khugepaged alone (~26 MB/s) cannot
      coalesce a 98 GB buffer inside a bench window. Stake: page-walk overhead on a 4.16 GB/token stream
      through 4 KB pages, 0–8%; decisive either way in one run.
- [x] **D8 — parallelise GET_ROWS (and the other single-task copy ops).** ✅ implemented 2026-09-02
      (`inf70/d8`, `bc2834a9b`; subagent `d8`), **bit-identical** (198-case multi-thread memcmp verifier, 0
      failures; `test-backend-ops -o GET_ROWS -b CPU` 111/111 with the threshold forced to 0 — without that
      the suite is vacuous because every built-in case is under 64 KB; greedy identity 3 × 128) — **but the
      lever was ~10× smaller than the profile said**: the four `get_rows` kernels already split by
      `ith/nth` over ROWS and the hot nodes gather one row of 786,432 f32, so the kernels now split
      (row, column-chunk) pairs, block-aligned, `n_tasks = n_threads` above 64 KB of dst
      (`GGML_GET_ROWS_MIN_BYTES`). Same-binary ABA at t48: **+0.115 t/s (+0.97%), inside the 0.17 t/s
      drift — neutral-to-slightly-positive, not a claim.** Why: GET_ROWS cost **2.59 ms/token in this
      window, not the 9.34 ms the profiler saw 2.5 h earlier** — the 36 big PLE gathers took 37 µs each
      (cache-served, ~162 GB/s) vs 233 µs then, same command, recipe, placement and THP: **a
      state-dependent cost, not a structural one; D6's "start with GET_ROWS" ranking is retracted.**
      SET_ROWS deliberately left serial (source rows can share a destination index — a write race, for
      0.011 ms/token); CPY needs nothing (its single-task nodes are the empty `ne1 = 0` ones). A cold-source
      probe shows the split does work when there is DRAM traffic (1T 105 µs → 48T 12–61 µs). **Side
      finding under bisect (D8x, running): the anchor binary 10196 measures 10.37–10.47 t/s while the d8
      tree's build measures 11.82–12.02 with the patch disabled — a reproducible +14% whose cause is not
      the patch by the agent's protocol, with cmake cache, flags, gcc, stale objects, library resolution,
      base delta, placement and THP ruled out; a fresh pristine build (d1-base) is NOT faster, so it is
      something in the d8 tree or its arm protocol.** If real, the 10.09 anchor and every Δ against it are
      understated ~14%. **D8x static verdict (2026-09-02, bench arms pending): the +14% IS the GET_ROWS
      patch.** `GGML_GET_ROWS_MIN_BYTES` only changes the *planned* `n_tasks`, which this tree's compute
      loop never consults (`params.nth = n_threads` for every node; `n_tasks` only sizes the work buffer),
      so D8's "OFF" arm ran the parallel kernel too — the A/B was on/on, and the "37 µs vs 233 µs,
      state-dependent" reading was parallel-vs-serial. `nm -S` shows the only functions that differ between
      the pristine and d8 libraries are `get_rows`, `get_rows_back`, `graph_plan` and the env cache; ISA
      counts identical. The cross-binary greedy check (unpatched prof binary vs patched, 70 tokens) is
      byte-identical. **So D8's real effect is ≈ 95.5 → 83.4 ms/token (10.4 → 12.0 t/s, −12%) at t48 —
      the largest single gain of the day — and D6's GET_ROWS ranking stands; the "retracted" line above is
      itself retracted.** Per-op attribution from the two profiled runs (same command and recipe): GET_ROWS
      9.34 → 2.59 ms, **CPY 3.65 → 0.50, GATED_DELTA_NET 3.00 → 0.49, MUL_MAT 41.9 → 40.1**, MUL_MAT_ID
      +0.9; total profiled wall 96.0 → 82.2 ms (−13.8) — the parallel gather leaves each 3 MB row spread
      across the 48 threads' caches, so its consumers stop pulling everything from one CCD. The node table's
      `n_tasks = 1` count for GET_ROWS is 175 in BOTH runs while its wall fell 3.6× — direct proof that the
      planned task count does not gate execution in this tree. Confirmation arms (anchor / pristine /
      prof-only / d8, plus a cross-binary greedy pair) running as D8x — the first four arms confirmed: anchor 10.43, pristine 10.15, committed d8 tip 11.87, d8 with the inert "off" knob 11.88. **`inf70/d8` merged into `exp/cpu-fusion-qwen4exp-20260829` on 2026-09-03 (operator direction; merge commit `bb5bec310`, then `9e75132e3` with D7b), verification running.**
- [ ] **D6 — the 796 small dense gemvs run at 40% of read bandwidth while the one big gemv runs at 94%.**
      B1 measured dense `mul_mat` 61.1 GB/s and `mul_mat_id` 61.8 GB/s against `lm_head` 143.9 GB/s — same
      op, same kernel, only the size differs, so per-call ramp/imbalance is the cost; the worst single node
      is the F32 router `ffn_moe_logits` (48 × f32 2560×512: 4.20 ms wall for 2.10 ms compute; one at
      1,118 µs wall for 32 µs compute) — B4's router requant now has 4.2 ms/token at stake. Bucket them by weight bytes from the D0-b node dump (the
      4-stream hyper-connection loras at 2560×320, the F32 router, indexer projections, shared expert).
      Levers in order: cap `nchunk0` so a thread never gets fewer than ~64 rows (idle threads still hit
      the graph barrier, so this only helps once D2 elides it); concatenate the per-stream lora weights
      at load into one `mul_mat` per hc site (fewer nodes, same math, bit-exact if accumulation order is
      preserved); quantize the F32 router (B4). Measure the dense-path in-function median before and after.
- [x] **D7 — upstream CPU-side fusion sync.** ✅ 2026-09-02, research only (subagent report
      `/mnt/raid0/llm/tmp/inf70/agents/d7/REPORT.md`). Fork point: upstream `a8dc0e326` (**b10045**,
      2026-07-16, #25076); upstream HEAD `0f3a71be1` (b10760) — 715 commits of divergence, 28 touching
      `ggml/src/ggml-cpu/`, 6 that are not ARM/kleidiai/PowerPC/SpacemiT. **Result: upstream has added
      nothing to the CPU backend that cuts this graph's batch-1 node count or per-node cost.** Master still
      performs exactly one CPU fusion (RMS_NORM+MUL) with the same `ggml_graph_plan` TODO; `ggml_can_fuse`,
      `ggml_barrier`, the graph loop, `mul_mat`/`mul_mat_id` chunking and every x86 kernel file have zero
      upstream commits since the fork. Four upstream items measure exactly zero here (#27402 iqp is gated to
      batch ≥ 8; #27930 SWIGLU_CLAMP is arch-gated and `swiglu_clamp_exp` = 0; #27880's PLE hoist is a
      graph-split change and the artifact has one PLE layer; #27877 is a no-op on CPU) and #24575 must not
      be ported. Two things the survey did find: **D7a** below, and an **Axis E prerequisite** — the
      recurrent-state rollback chain `1692f9e50` (#26623) + `0eadefebd` (#28123) + `9d817213a` (#28159)
      (without it the server serializes the whole recurrent state per draft round; upstream measured
      108 → 183 t/s with MTP) plus `36b101543` (#27941) qwen4exp correctness — filed under E2. Upstream's
      CPU `graph_optimize` hook (#27301 plumbing) is the natural home for D2's plan-time barrier bitmap.
- [x] **D7a — enable the CONCAT dim-0 row partition (found by D7).** ✅ measured 2026-09-02 (subagent
      `d7a`, `/mnt/raid0/llm/tmp/inf70/agents/d7a/REPORT.md`). `ggml_compute_forward_concat_f32` shards over
      ne2; the GDN conv concat `[4, 10240, 1]` has ne2 = 1, so thread 0 did all 40,960 copies on 37
      nodes/token. `GGML_CPU_CONCAT_DIM0_ROWS=1` (our `e5dffb4e8`, default OFF), build 10196, uniform
      IQ4_XS, canonical recipe, two same-window OFF/ON pairs with verified 23.5 GB × 4 placement:
      **decode −1.10 ms/token at t48 (10.41 → 10.53 t/s) and −1.29 at t96; reproduced −1.41 / −1.32 in a
      second window; prefill pp512 +28.2% at t48 (184.5 → 236.5 t/s), +22.5% at t96.** `GGML_CPU_PROF`
      CONCAT row 1.318 → 0.112 ms/token over 37 nodes (35.6 → 3.0 µs/node, 11.8×). Greedy output
      bit-identical on 3 prompts × 128 tokens. One OFF arm was excluded because its placement skewed
      (node 3 at 20.1 GB after an eviction that did not reach the target on a cold box — the placement
      proof caught it, which is C7 working). Drift between the two OFF arms 45 min apart was −1.6%, the
      same order as the decode effect; the profiler row is the load-bearing decode evidence and the prefill
      gain stands on its own. **Note for the prefill owners (out of INF-70 scope): +23–28% pp512 from this
      flag alone.**
- [x] **D7b — flip `GGML_CPU_CONCAT_DIM0_ROWS` default-ON in the fusion tree.** ✅ 2026-09-02 — branch
      `inf70/d7a-default`, commit `3026caac` (1 file, +18/−1): default enabled, env is an explicit opt-out
      (`=0`/`false`/empty disables). `test-backend-ops test -o CONCAT -b CPU`: **210/210 OK with the new
      default and 210/210 with the stock kernels** (the 18 `concat_transpose_dim0` cases included; note
      that without `-b CPU` the suite skips the CPU device and passes vacuously with zero cases — the
      0-vs-210 count is the non-vacuity check). **Merged into `exp/cpu-fusion-qwen4exp-20260829` on 2026-09-03 (operator direction; merge commit `9e75132e3`, no conflicts); build + test + bench verification of the merged tree
      running (`merge-verify`).** **VERIFIED ✅ 2026-09-03: merged tree (build 10202, `9e75132e3`) 12.11
      ±0.03 t/s vs anchor 10.19 in the same window (+18.8%), placement even; `test-backend-ops -b CPU`
      GET_ROWS 111/111, CONCAT 210/210, MUL_MAT 1139/1139, MUL_MAT_ID 815/815, `test-llama-archs` rc=0;
      anchor-server-vs-merged-server greedy IDENTICAL on 3 prompts (71/128/128 tokens). Safe to build on.** Rationale for default rather than
      `canonical_recipe.py`: the recipe governs our benches, not the served stack — an env-gated win would
      silently miss `llama-server` in production.

## Axis B — the weight stream: bytes per token and achieved GB/s per path

- [x] **B1 — split the token by path and report achieved GB/s, not just ms — on the C5 build.** ✅
      2026-09-02 (same run as D0): **dense `mul_mat` 796 calls / 38.29 ms / 2.338 GB → 61.1 GB/s (40.0% of
      the measured 152.6); expert `mul_mat_id` 144 / 20.96 ms / 1.296 GB → 61.8 GB/s (40.5%); `lm_head`
      (Q6_K 2560×248320) 1 call / 3.62 ms / 0.522 GB → 143.9 GB/s (94.3%).** Weight paths total 62.87 ms
      for **4.1558 GB/token** (the live graph independently reproduces the tensor-table 4.16 GB); **3,468
      non-weight nodes cost 33.39 ms — 35% of the token — and move no weights.** The retracted "5.6–17 GB/s"
      and the pre-fix "100–130 GB/s" expert figures are both superseded by 61.8 GB/s at proven placement;
      B2's N-sweep (64.8 GB/s marginal) agrees. **The one big gemv is not the problem; the 940 small ones
      and the 3,468 non-weight nodes are.**
- [x] **B2 — decide what binds the expert path: per-call fixed cost or bandwidth.** ✅ 2026-09-02 —
      **both hypotheses refuted; the path is bytes-proportional at ~43–54% of achievable bandwidth.**
      `--override-kv qwen4exp.expert_used_count=int:N` for N ∈ {10, 5, 2, 1} via `llama-server` (build
      10196, uniform IQ4_XS, C5 recipe + eviction, placement proven per arm, N=10 controls at both ends of
      the window 98.8 / 98.3 ms reproducing the 99.1 ms anchor): **98.81 / 90.64 / 82.45 / 80.92 ms/token**.
      Fit ms/token = 34.9 + 15.44 × bytes(GB), R² 0.984 → **1/slope = 64.8 GB/s, 42% of the measured 153**;
      the confound-free N=10→5 step gives 81.8 GB/s (53%). Extrapolated to N=0 the **expert path is
      ~19.7 ms/token (20% of the token): ~8.5 ms is its bytes at 153 GB/s and ~11 ms is overhead**; the
      N-invariant per-call floor (144 × 2 barriers × 1.9 µs) is ≤ 0.6 ms, so per-call fixed cost does not
      bind. Thread arm (`-t 8,24,48`, N=10): **9.57 / 9.53 / 10.26 t/s — +7% for 6× the threads**; whatever
      binds the op is saturated at 8 threads (each thread gets 14–54 rows = 19–26 KB per expert, ten short
      streams per op). Evidence: `/mnt/raid0/llm/tmp/inf70/agents/b2/`. **Consequences: B3 (joint
      expert×row chunking + gate-up fusion) is the highest-ROI lever on this path; B4 pays proportionally
      and at ~1.5× its roofline value; D1's barrier removal has ≤ 0.6 ms at stake here and must earn itself
      on the 797 dense `mul_mat` calls; D4 is refuted as a decode lever.**
- [ ] **B3 — restructure `mul_mat_id` for batch 1.** Beyond D1's barrier removal: chunk across
      (expert × rows) jointly so each thread streams ≥ ~100 KB of one contiguous expert slab instead of
      14 rows of each (B2 measured the cost of the current split: ~11 ms/token of overhead on a 19.7 ms
      path, saturated at 8 threads) — **B3-k, the kernel half**, to be built on top of D1's branch; and
      **fuse up+gate** into one op — **B3-a, the artifact half**. The two tensors are both IQ4_XS `[2560,640,512]`,
      so a `[2560,1280,512]` `ffn_gate_up_exps` is a per-expert byte-level concatenation — producible
      offline with `gguf-py` from the existing GGUF, no requant and no HF source (the 2026-08-28
      `--fuse-gate-up-exps` re-conversion attempt was never reported). Halves the expert-path op count
      (144 → 96 calls/token). **Verified 2026-09-02 (D7): this tree already handles it end to end** —
      tensor `blk.{bid}.ffn_gate_up_exps` `[2560,1280,512]` (`llama-arch.cpp:413/850`), loaded by
      `create_tensor_gate_up_exps` (`llama-model.cpp:2874`, optional with fallback) which qwen4exp calls at
      `qwen4exp.cpp:203`, consumed by the merged branch of `build_moe_ffn` (`llama-graph.cpp:2095–2112`: one
      `mul_mat_id` then two views), passed at `qwen4exp.cpp:911`; landed upstream pre-fork (`b68d75165`,
      #19139). **Concat order: gate rows first, then up, along ne[1].** One gate: the merged branch leaves
      `gate_exps` null and the SILU clamp arm tests `if (gate_exps)` — harmless only because qwen4exp's
      `swiglu_clamp_exp` is 0. **B3-a is DONE ✅ 2026-09-02** (subagent `b3`): artifact
      `models/unsloth/Qwen3.8-Flash-Next-GGUF/IQ4_XS-uniform-gateup/Qwen3.8-Flash-Next-IQ4_XS-uniform-gateup.gguf`,
      98,392,908,896 B, SHA-256 `b991107bb72a496ad0aeb135e1bd62401aeccc7ff64e512a5ef684d961db891d`, 1,176
      tensors, 48 × `ffn_gate_up_exps` IQ4_XS `[2560,1280,512]`, produced offline by
      `tools/inf70/gguf_fuse_gate_up.py` (branch `inf70/b3`, `dd27ec3bb`) — no requant, no HF source; a
      successful load proves the merged path (the fallback would demand the dropped tensors). Greedy output
      **bit-identical** (token ids) to the uniform file on 3 prompts × 128 tokens. ABA on build 10196, clean
      placement (~24 GB × 4), one window: t48 tg128 **10.44 ±0.04** vs uniform 10.33 / 10.27 → **−1.30
      ms/token (+1.36%)**, B's ±1σ disjoint from both A arms; t96 9.91 vs 9.83 (−0.82 ms, weaker); pp512
      unchanged within error. Inside D7's predicted −0.5…−1.5 ms band. **Recommendation adopted: the
      gate-up file is the comparison baseline for Axis B/D decode work from here** (new artifact per the
      artifact rule; the uniform file stays the era anchor); B4's `--tensor-type` overrides apply on top of
      it in one `llama-quantize` pass since they touch none of the fused tensors. **B3-4 combined ✅ 2026-09-02** (subagent `b34`, first Fable-low agent):
      `IQ4_XS-uniform-gateup-r16` = the gate-up file + `ffn_gate_inp` F32→F16 only, via B4's patched
      quantizer (48 s); 98,267,079,776 B, SHA-256
      `6468558b42579664af5a4551292828264905109f9a8d3fea4d8e10e3c7ce47d7`; GGUFReader diff exactly 48 type
      changes, routers exactly `float16(F32)`; bytes/token 4.1656 → 4.0397 GB (−3.02%). ABA + bracket at
      t48, build 10196, placement proven: gate-up 10.33 → **r16 10.49 ±0.02 t/s (95.33 ms, −1.48 ms,
      +1.55%)**; t96 9.76 → 10.21 (one arm each, non-claim); prefill-only ABAB **neutral (200.3 vs
      200.2)**. Greedy agreement 82.6% (p2/p3 identical; p1 diverges at a low-confidence branch —
      expected, the router precision changed; C9 is what would prove equivalence). **`IQ4_XS-uniform-gateup-r16`
      is the Axis B/D comparison baseline from here** (prefill equal within noise, decode and bytes better;
      the uniform file stays the era anchor, UD stays the served file). B3-k (the kernel half) stays open.
- [x] **B4 — the bytes budget: requantize what is streamed for no reason.** ✅ 2026-09-02 (subagent `b4`,
      `/mnt/raid0/llm/tmp/inf70/agents/b4/`) — three artifacts vs the uniform control, build 10196, t48, r5,
      placement proven in-window on every arm. Full override set `IQ4_XS-uniform-b4` (router F16 +
      `output.weight` Q5_K + `ffn_down_exps` IQ4_NL; bytes/token 4.1656 → 3.9369, −5.49%; SHA
      `bcddc62b…`): decode **10.385 → 10.515 t/s (+1.25%, −1.19 ms; −1.49 ms predicted at 153 GB/s)** but
      **prefill −15.1% (177.4 → 150.6)**. Separation arms invert the naive reading: **`ffn_gate_inp`
      F32→F16 is decode-neutral (+0.05%) and read as +11.9% prefill (198.5) — take it** (the prefill part did NOT reproduce in B34's prefill-only ABAB, 200.3 vs 200.2 pp512, so it is decode- and prefill-neutral; the +11.9% was one arm against a drifting control); `output.weight`
      Q6_K→Q5_K −84 MB/token with no measured effect — optional; **`ffn_down_exps` Q5_1→IQ4_NL is the
      whole regression, −21.7% prefill for 0.44% of the stream — do not take it.** Correction to the
      ledger: only **6 of 48** `ffn_down_exps` were Q5_1 (layers 0–5, `use_more_bits`); 42 were already
      IQ4_NL, so that lever was worth 18 MB/token, not ~590 MB. Requires a quantizer patch (`inf70/b4`
      `49a1255`, +14 lines): stock `llama-quantize` accepts a `--tensor-type` on `ffn_gate_inp` and
      **silently ignores it** (`tensor_allows_quantization()` rejects the router before the pattern list;
      anchor the regexes — `output\.weight` unanchored also matches `attn_output`). Quality: **no PPL/KL
      possible — see C9**; greedy-generation gate only: 33.5% prefix agreement over 5 × 128 tokens,
      median |Δ logprob| 0.0014 nats on agreed tokens, all continuations coherent — no visible regression,
      equivalence not proven. One arm discarded for placement skew (44.6/23.5/23.5/2.4 GB) **despite
      eviction inside the lock — C7 recurs; the in-window sampler is what caught it.** Open question for
      B1/D6: −21.7% prefill from IQ4_NL on six 640-wide expert tensors is backwards from the naive
      prediction (`llamafile_sgemm` covers IQ4_NL, not Q5_1) — point the per-path profile at `mul_mat_id`
      for those two types before anyone uses IQ4_NL on a 640-wide expert tensor. Artifacts kept:
      `IQ4_XS-uniform-b4` and `IQ4_XS-uniform-b4r` (router-only, 98,267,083,136 B); `-b4b` deleted.
- [ ] **B5 — a quality-representative uniform artifact without the FP8 conversion.** The OP-32 uniform
      file is a quant-from-quant of the unsloth UD shards ("speed control only — not quality-representative",
      INF-68). Operator direction 2026-09-02: skip the FP8 download and converter run. The route is the
      unsloth `Q8_0/` GGUF (6 shards, ~175 GB) → `llama-quantize` to uniform IQ4_XS — the same Q8_0→IQ4_XS
      path the destroyed 08-28 original took — or the `BF16/` GGUF (8 shards, ~330 GB) for a true
      from-source quant. One download at a time, never inside a measurement window; apply the B4 tensor
      overrides in the same pass so one artifact carries both. Same recipe, same window, old vs new, before
      either becomes the served artifact.
- [ ] **B6 — interleave striping vs expert-local placement (deprioritized).** Expert weights are
      per-expert contiguous slabs (expert is the outermost GGUF dimension) — the pre-audit
      "interleaved rows / page-scatter" hypothesis is dead on arrival. The residual question is whether
      `--interleave=all` page-striping *inside* a 2.7 MB slab costs anything versus node-local
      placement. Only worth a run if B2 says the path is bandwidth-bound.
- [ ] **B7 — EXL3 `mul1` trellis experts (filed as INF-71).** turboderp published EXL3 weights for this
      model on 2026-08-31 (`turboderp/Qwen3.8-Flash-Next-exl3`, 2.05–6.05 bpw, MTP head at 4 bits,
      `mul1` codebook), and exllamav3 ships an AVX-512/VNNI CPU GEMV for exactly that codebook whose decode
      fuses into the `vpdpbusd` the gemv already needs (~4 vector uops per 16 weights — IQ4_XS-class, unlike
      ik_llama.cpp's slow 3INST trellis types). At 3.05 bpw the expert stream drops ~0.4 GB/token. Spec,
      phases, gates and hazards: [`exl3-trellis-cpu-kernel.md`](exl3-trellis-cpu-kernel.md). Do not start it
      before C0/C5/B1/D0 rank the levers.

## Axis A — finish the fused decoder's viability test (INF-67)

The go/no-go was answered 2026-09-01: the batched `mul_mat` is callable on staged tensors, so the per-row
`vec_dot` in `FusedMM::dot` is a fixable implementation error, not a structural one. INF-67 remains the
design record; this is the live task list.

- [x] **A1 — batched `mul_mat` substitution in `lora_mm`/`FusedMM`.** ✅ implemented 2026-09-02
      (`380278b40`, branch `inf70/fused`, subagent `fused`) — every per-row `vec_dot` loop replaced by
      `ggml_compute_forward_mul_mat` (via `ggml_cpu_extra_compute_forward` first). **Measured at 1T, same
      build (Release + OpenMP, commit `740d0cfea`), same process, same window, uniform artifact,
      clean placement: fused gemv column = 232 ms after the census fix (810 ms before it — 598 ms was the
      un-migrated repacked-down-expert path), against a whole graph token of 195 ms.** The success criterion
      (→ ~300 ms) is met for the column; the census says the residual is structural (4.1× the calls, the
      double MoE), not mechanical — per-call time is ordinary (36.6 µs per 640×2560 expert slice). The pre-A1 per-row path could not
      be timed in the same build: it aborts with `double free or corruption` on its first token — and the
      abort reproduces on the pristine `c035bbf3d` tree in Release, so the heap corruption pre-dates this
      work and was masked by the debug build the INF-67 campaign measured on.
- [x] **A2 — scratch arena.** ✅ implemented 2026-09-02 (`5d2d27510` + `672c5e9e5`) — one arena per
      nesting slot plus one staging buffer for the recurrent state. **Churn measured (replaces the retired
      "~2.5 GB" estimate): 73 `ggml_init`/`ggml_free` pairs per token asking for 3,520 MB/token before A2,
      223.7 MB actually needed, plus 112.6 MB/token of state-staging allocations; after A2 the four arenas
      hold 12.2 MB total.** With both A1 and A2 in, the fused "other" column is still **150.6 ms at 1T —
      77% of the graph's entire 197 ms token** — so the non-gemv machinery of the fused design costs more
      than the whole graph does, at a thread count where the graph pays no barrier at all.
- [x] **A3 — strip the debug I/O.** ✅ 2026-09-02 (`e02ddbdff`) — ~70 `getenv` and ~114 `fprintf`/`fopen`
      sites behind the compile-time `QWEN4EXP_FUSED_DEBUG` (OFF by default); the worst were ~2.5 M
      `getenv` calls per token inside the expert row loops, two of them inside the `FUSED_PROF` gemv window,
      and five `GGML_FUSED_DUMP_GLAYERS` getenv sites in `process_ubatch` that ran on the GRAPH arm of
      every A/B too.
- [x] **A4 — the safety contract.** ✅ 2026-09-02 (`bf56cf94e` + `07d980e5e`) — hook is OPT-IN
      (`GGML_FUSED_DECODE=1`); `supports_fused_decode()` checks CPU-device residency, repack layout and the
      hparams it assumes; a preflight validates the memory context, cache views/types and the logits
      carrier before any work; PLE and GDN recurrent state staged and committed in one pass at
      end-of-token. The logits carrier remains the previous graph's tensor under a checked contract; the
      owned-buffer form (`decode()` taking the fused result's own buffer) is **A4b**, moot unless the gate
      below is overruled. Three fused-path correctness bugs found and fixed on the way: the GDN state
      copy-back read at a byte offset where the state starts at a float offset (`a188b2f70`), repacked
      IQ4_NL hc loras read as plain rows, and F16 `ple_conv1d` read as F32 — 81 KB past the tensor
      (`b1439ce59`). The INF-67 residual (0.684 / 1.7e-2) was measured with all three present.

**⚠ The measurement trap on A1.** With the churn still present, a *perfect* gemv fix reads fused ≈ 300
(gemv) + 215 (other) = **~515 ms at 1T vs the graph's 350** — still 1.5× slower, because the graph's own
1T non-gemv cost is only ~50 ms. A1 and A2 are individually fatal; the design needs both. With both, the
ambition is the weight stream at the machine's rate (~32 ms for 4.16 GB at 130 GB/s, less as Axis B/D4
raise the rate) plus a fused-path overhead that has to be measured — **≈ 25–30 t/s if that overhead is
≤ 10 ms**. That is the ambition to test, not a predicted result. The fused/graph ratio (3.86× at 1T) is
the honest interim metric; it is same-build and roughly stable across thread counts.

- [x] **A-GATE**: fused ≤ graph at 1T on BOTH the gemv column and the other column, same build. ✅ run
      2026-09-02, three iterations in one session, each driven by the call census naming a defect:
      **4.70× → 1.51× → 1.10×.** Final: **fused 214.3 ms/token vs graph 195.1 ms at `-t 1`, steady state
      (steps 2–6; step 1 is the arena first-touch outlier at 316 ms)**, same process, same model load, same
      window, placement proven; commit `06f916224` on branch `inf70/fused` (self-reported build number 1274
      is a shallow-clone artifact; hashes are the ids). Column split: gemv 170.5 ms, other 41.7 ms — both
      inside the graph's own 1T band, but the side-by-side token is 10% slower, so **the gate is not met.**
      What the census removed: (1) 598 ms of an un-migrated hand-rolled path for the 42 CPU_REPACK
      `ffn_down_exps` (2.15 M scalar dots/token) — routed through the dispatcher; (2) a transcription
      error that ran the routed MoE **twice per layer** (attention side and ffn side; the graph runs it
      once at `qwen4exp.cpp:356`) — removed; after it the census matches the ledger exactly (1,440 expert
      calls = 48 × 10 × 3, 1,236 MB vs the ledger's 1,296 MB). **What remains is structural: 2,213
      `mul_mat` calls vs the graph's 941** (one call per expert per lora where the graph issues one
      `mul_mat_id` per layer and fuses the hc streams), at an ordinary 76.9 µs mean — closing it means
      rebuilding `mul_mat_id` inside the fused path. Logit gate still fails by four orders of magnitude
      (max_abs 1.2–2.7, NMSE 4e-2–2.4e-1 per step; greedy agreed 6/6 on every run). **Operator decision
      package** (report §6b): (a) read the columns as within noise of passing → the 48-thread question
      is a project, not a measurement — the path is single-threaded by construction (`ith=0, nth=1` on a
      private pool; arenas, staging and tensor headers assume one caller), so INF-67 Phase 4 threading is
      one to two focused sessions before any 48T number exists; (b) the literal reading: given its batched
      matmuls, its arena, clean instrumentation, a safety contract and two real defects removed, at one
      thread where it has no dispatch disadvantage the design still costs 10% more than the graph while
      failing numerics — close, with this report as the refutation. **Recommendation from the audit: (b)**;
      the diagnosis is complete enough to choose knowingly, which is what the gate was for. The branch
      keeps the safety contract (A4), the debug strip (A3), the batched kernels (A1), the arenas (A2), the
      three bug fixes and the census instrument as the record; A4b (owned logits buffer, call sites in the
      report) precedes any serving exposure if (a) is chosen. Every arm held the bench lock 80–84 s.

## Axis E — restore the MTP head (speculative decoding), LAST

**Facts (2026-09-02).** unsloth published the MTP heads on 2026-09-01 (repo revision `5d16c055`,
`MTP/` folder of `unsloth/Qwen3.8-Flash-Next-GGUF`): `mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf` (2.60 GB,
**their recommendation**), `shared-Q4_K_M` (1.78 GB, ~2 points less acceptance), `shared-BF16` (4.87 GB,
slower), and self-contained `Q8_0` / `Q4_K_M` / `BF16` (3.85 / 2.60 / 7.24 GB). `shared-` heads borrow the
token embedding and output projection from the running trunk; the self-contained files carry their own
copies and are for builds without cross-model borrowing. **So no FP8 re-download and no converter run is
needed for MTP** (our converter's `no_mtp` opt-out in `conversion/qwen4exp.py` is now moot unless a
from-source conversion is ever run). Their README states the heads do **not** work on mainline
`ggml-org/llama.cpp` (as of upstream `0eadefebd`: no MTP graph for `qwen4exp`, no cross-model tensor
borrowing, no `--spec-type draft-mtp`); they run on `unslothai/llama.cpp` PR #144 (branch `mtp`, prebuilt
tag `b10715-mix-86bd2d3`). Invocation: `-md <head> --spec-type draft-mtp --spec-draft-n-max 2`; the log line
`draft acceptance = … mean len = …` is the proof it is live. Their measurement (B200, greedy, shared-Q8_0,
concurrency 1): UD-Q4_K_XL 83.2 → 138.8 t/s (**1.67×**), UD-IQ1_S 1.34×; acceptance shared-BF16 66.5% /
shared-Q8_0 66.1% / shared-Q4_K_M 64.4%; a net *loss* (0.81–0.87×) at concurrency 8. Our production v9
already ships the generic `--spec-type draft-mtp` driver (`common/speculative.cpp:1702`, from INF-46); what
it lacks for this model is the `qwen4exp` MTP graph (`t_h_nextn` export + the head's decoder graph, precedent
`src/models/qwen35moe.cpp:110-137`) and tensor borrowing for the `shared-` heads.

- [x] **E1 — download the heads.** ✅ 2026-09-02 — `mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf`
      (2,786,568,256 B) and self-contained `mtp-Qwen3.8-Flash-Next-Q8_0.gguf` (4,137,429,120 B) in
      `models/unsloth/Qwen3.8-Flash-Next-GGUF/MTP/` with the README; both `SHA-OK` against the repo's LFS
      oids (`download.log` there, 10:21–10:35Z, at the operator's direction).
- [x] **E2 — port the `qwen4exp` MTP path into the experimental tree.** ✅ 2026-09-02 — branch `inf70/mtp`
      (`d6d175d09`, 15 files, +401/−47; subagent `e2`): `t_h_nextn` export from the trunk graph, MTP tensor
      loading under `mparams.load_mtp` (`n_layer_all` = 49, the head is `blk.48`), the qwen4exp
      `LLM_GRAPH_TYPE_DECODER_MTP` graph, **cross-model borrowing for the `shared-` head** (`model_shared` +
      `borrow_shared_tensor`; log: `tensor token_embd.weight taken from the target model`, 1.27 GB saved,
      outputs identical to the self-contained head), and one fix beyond the PR (the fused fast path yields
      when `cparams.embeddings_nextn` is set). Our tree already had the whole generic `draft-mtp` driver;
      only the arch side was missing. **Proven live on CPU** (`llama-server` + `/completion`, uniform trunk,
      canonical recipe, placement 24.6 GB × 4): `draft acceptance = 1.00000 / 0.90909 / 0.88889, mean len =
      3.00 / 2.82 / 2.74` on three toy prompts, identical for both heads. Trunk-only path byte-identical to
      the unpatched build on 3/3 prompts. **Non-claim speed, 64 tokens, greedy: 10.2–10.4 t/s without a
      head → 14.3–17.7 t/s with one (1.39–1.70×)**, the same range unsloth measured on a B200. Head facts:
      the MTP block is an attention block (not GDN) with its own hc mixing and `nextn.hc_head_*` final
      mixer, no PLE tensors, a full 512-expert MoE and the LM head. Evidence
      `/mnt/raid0/llm/tmp/inf70/agents/e2/`. (The build self-reports a small build number because the
      fusion repo was briefly made shallow by a `--depth` fetch that afternoon, since repaired with
      `--unshallow`; commit hashes are the ids for every branch built in that window.)
- [ ] **E2a — the greedy-identity gate failed on 1 of 3 prompts; find out whether batched verification is
      exact on this architecture.** Prompt 1 diverges at generated token 28: the MTP arm accepted
      `' Lisbon'` where the trunk alone puts `'\n\n'` first by **0.79 nats** (not a rounding tie); both heads
      diverge identically and the trunk-only path is unchanged, so it is neither the head nor the port's
      effect on the trunk. Live hypothesis: qwen4exp's **multi-token verification forward is not equivalent
      to its single-token forward** (GDN chunked vs per-token kernel, PLE conv, QSA indexer) — which would
      make MTP's "verification is exact" premise false for this model independently of the port. The
      discriminating controls ran 2026-09-02: `ngram-mod` on the UNPATCHED build with real drafts
      (`n-match 4`: acceptance 2/2 at positions 53–59) leaves greedy output **byte-identical**; the MTP
      arm at `--spec-draft-n-max 1` (same 2-token verify depth) **still flips** at token 28, byte-identical
      to the `n-max 2` run, with 31/31 drafts accepted. **Verdict: the divergence is in the MTP path, not
      in batched verification per se** (caveat: the ngram control never batched at position 28, so it
      proves a 2-token verify batch *can* be exact here, not that it always is; the default-`n-match 24`
      ngram arm was vacuous — it never drafted). Bisect (running, two arms): the one target-side
      difference between the arms is `cparams.embeddings_nextn = true, masked = false` — **bisected
      2026-09-02 (env-gated diagnostics, `5497d7864`)**: forcing `masked = true` cannot even start (the
      driver reads the target's hidden state at every prompt position — the ungathered export is its
      contract), so the deferred-gather hypothesis is refuted; the acceptance comparison is exact
      token-id equality and does reject (2 genuine rejections in 33 steps). **The divergent token is the
      BONUS token**: `common_sampler_sample_and_accept_n`'s `i == draft.size()` branch
      (`common/sampling.cpp:657-663`) reads it from the last row of the verification batch and compares it
      against nothing. Underneath: **the target's logits at rows ≥ 1 of a multi-token decode differ from
      the same position decoded singly on this hybrid** (GDN chunked path / PLE conv / QSA indexer) — which
      also means the "verified" tokens are checked against slightly non-exact logits, and **acceptance rate
      is not evidence of exactness on this architecture** (p1 reported 1.00 and diverged). Options: (a) an
      extra single-token decode per round for the bonus token — correct, costs most of the win; **(b) make
      qwen4exp's multi-token path row-exact vs the single-token path — the real fix; **its cheapest shot,
      upstream `36b101543` (#27941), was ported (`inf70/mtp-27941`, `7ab0a0fe4`, 444 lines of
      `llama-memory-hybrid-idx` + kv-cache + 7/8 `qwen4exp.cpp` hunks; a provable no-op for
      non-speculative output) and the flip survives byte for byte**; (c) accept non-exactness — MTP as
      *approximate* speculation for research measurement, exactness claim dropped. **E2c (running, first
      Fable-low agent): does the trunk's forward depend on batch size at all?** Same prompt through
      `-b 1 -ub 1` vs default batching vs `-b 8 -ub 8` on the unpatched build, greedy ids and top-5
      logprobs compared — if they differ, every prefill-vs-decode comparison in this campaign inherits
      the finding, not just speculation. Then (a)/(b)/(c) is the operator's decision; the E2 agent's
      recommendation is (c) with no serving exposure, and to keep `inf70/mtp-27941` as a correctness
      rider regardless. E-GATE depends on it.
- [ ] **E2b — recurrent-state checkpoints per draft round (measured).** Every verification round writes a
      **112.571 MiB** speculative checkpoint and restores it on rejection: 66 created / 18 restored per
      three 64-token requests (0 / 0 without a head) ≈ **9.4 GiB of serialized memcpy per 192 tokens,
      ~49 MiB/token**, on top of the weight stream; no re-prefill observed. Rollback itself works (p2/p3
      stayed identical); it is paid with a copy instead of an in-place rewind. **E2b-1 ✅ done 2026-09-02:
      `36b101543` (#27941) ported on `inf70/mtp-27941` — no regression, checkpoints unchanged (31/2), not the
      E2a fix.** E2b-2 open: the rollback trio `1692f9e50` (#26623) + `0eadefebd` (#28123) + `9d817213a`
      (#28159) — the throughput lever (upstream: 108 → 183 t/s with MTP once landed), to be ported the same
      way (patch files, never a `--depth` fetch into the shared repo).
- [ ] **E3 — measure α before tuning anything** (`feedback_measure_alpha_before_specdec_investment`):
      acceptance per draft position and mean accepted length on the production prompt mix, greedy AND the
      production sampler (temp + seed 42), `--spec-draft-n-max` ∈ {1, 2, 3, 4}, both heads, on the C5
      recipe and the C5 build with the C5 trunk. The B200 figures (66% acceptance, 1.67×) are the reference;
      the CPU multiplier will differ because a dispatch-bound trunk verifies n+1 tokens for nearly the
      cost of one — measure, do not extrapolate.
- [ ] **E4 — the comparison arms, one `--spec-type` at a time**: plain, `ngram-mod` (free, no head — but
      the recorded 2.8× n-gram win was a warm-context self-copy artifact, true gain ≤ +1.7%), `draft-mtp`
      with each head. **No DFlash or DFlash2 drafter exists for this model as of 2026-09-02** (z-lab and
      incoai inventories and a 320-repo HF search checked; the publishers shipped a GLM-5.3 DFlash2 on
      08-27 but nothing for `qwen4_exp`), so the INF-62 arm is excluded until one appears. Same build,
      same window, same trunk artifact. Concurrency 1 only, per unsloth's own loss at 8.
- [ ] **E-GATE**: acceptance-weighted t/s against the non-speculative C5 number for the same trunk,
      reported per the artifact rule and with the sampler named. Note the PLE regime: under `--no-mmap`
      the 51B table is resident and every draft token pays its own PLE gather and hc stream mixing; that
      cost is part of the measured number, not something to subtract.

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
8. **Axis E added** (operator direction): MTP restoration, sequenced last. Rewritten the same day once
   unsloth's published heads were found (2026-09-01 upload): no FP8 download, no converter run; the work
   is porting the `qwen4exp` MTP graph and borrowing from `unslothai/llama.cpp#144`.
9. Recipe made explicit (the `canonical_recipe.py` prefix + OMP stack; INF-68 used it, the 08-28 bandwidth
   run did not), C5 gained the OMP on/off arm and the box-state capture, C6 wires the belief kernel.
10. INF-68 path fixed (`../completed/`), INF-67 given a pointer to this task list, wiki
    `benchmark-methodology.md` correction 1 rewritten as the fifth correction.
11. **Measured the same day (operator granted the CPU):** C0 read bandwidth 67–77 GB/s as-is vs 153/166 GB/s
    after per-node eviction; C5 anchor 10.14 / 10.09 t/s at t48 (as-is 7.65), t1 5.04; barrier primitive
    1.9 µs at 48T; tiny-node cost 3.7 µs at 48T; 100% THP when memory is free. The **placement mechanism**
    (page-cache-full nodes defeat `--interleave=all`) explains the 08-28→08-31 −32% and became task C7.
12. SMBIOS read: 12 × Samsung 96 GB DDR5-5600 RDIMMs configured at 4800 MT/s (one per channel); the BIOS
    change to 5600 is queued by the operator for the next reboot — re-run C0/C5 after it.
13. Operator direction folded in: unsloth heads downloaded (E1 ✅); no DFlash2 drafter exists for this
    model; EXL3 weights exist with a fused VNNI CPU decode → INF-71.
14. Follow-up arms: UD under clean placement 9.18 t/s (13.46 retired for good); C0-c four node-local
    streams total 171 GB/s with each node dropping from 66 to ~40 → a global uncore cap → task C8 (BIOS
    checklist for the operator's reboot: 5600 MT/s, UCLK 1:1, APBDIS/DF P0, DF C-states, power-down).
