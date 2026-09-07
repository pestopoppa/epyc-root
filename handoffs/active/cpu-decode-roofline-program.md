# CPU Decode Roofline Program — Qwen3.8-Flash-Next (qwen4exp) at the machine ceiling

**CURRENT STATE (2026-09-07) — read this before the 2026-09-02 framing below.**
**CHAMPION: `inf70/champion3` @ `9c4f73e29`, build 10241** (full record at *CHAMPION-3*, and the standing
rule *the champion is always current*). **+4.27% over champion-1 (117/120 paired per-prompt wins),
1.4993× over pristine (120/120), 1.7151× plain, bit-identical in 16 arm-pairs.** Quote the **ratios**: the
in-window absolute is 33.370 t/s / 29.967 ms and the ≈36.9 t/s / ≈27.1 ms anchor-referred figure is a
**projection, not a measurement** (WRAP-7). Production untouched at `0db32c06e`. **The 98.6 ms / ~95 ms
token, the "27% of roofline" fraction and the Sept-2 ordering below are the AUDIT-DAY baseline, retained
because every ledger row is sourced — they are not the current state.** In flight: SYNC-16, HARNESS-1.

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
- [x] **C7 — make the placement fix permanent, everywhere a CPU model is loaded.** ✅ 2026-09-03 *(a) ✅ ADOPTED-FORCING
      2026-09-03 — research main `0458de88`: `numa_evict.py` allocates TARGET+2 whenever free < TARGET, verifies per
      node, 2 passes (the 2026-09-02 `TARGET − free` sizing freed nothing — D8x); mutation-tested (weak form fails
      14/20). (b) ✅ done — no CPU server was live; the fix is in the launch path. (c) ✅ durable form = launch-path
      pre-evict, ENABLED: orchestrator main `5f20e23c` sets `numa_pre_evict_gib: 40` on frontdoor,
      eval_batch_frontdoor, architect_critic, ingest_long_context, worker_general (never on gpu_host_lane roles —
      refused in code), forcing form, `[numa-placement]` per-node fold logged after health; priors recompiled.
      `vm.zone_reclaim_mode=1` rejected (system-wide); BIOS NPS1 → C8 reboot session (C0-c decides). **The orchestrator launch-path half is production-plane work and its ACTIVATION is NOT
      INF-70's** — an experimental-kernel session had no business enabling it on a live stack (scope creep,
      corrected 2026-09-03 on operator challenge). The merged-but-inert activation step is now filed where its
      owner will see it: [`numa-placement-defect-20260730.md`](numa-placement-defect-20260730.md) → *The permanent
      fix is MERGED and awaiting activation by the stack owner*. **INF-70's own half — the forcing eviction in the
      measurement recipe — is DONE and is what every number in this campaign depends on.** Operator "proceed"
      2026-09-03; agent `c7-finish`, report `/mnt/raid0/llm/tmp/inf70/agents/c7-finish/REPORT.md`. Memory:
      `feedback_page_cache_defeats_numa_interleave`.* Measured 2026-09-02: when a
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
      only a durable form closes it. **Root cause found 2026-09-03 (D8x): the `evict_nodes.sh` helper used
      all session under-evicts — it allocates `TARGET − free` GiB, freeing nothing useful when a node's
      free is near TARGET but the model needs more than that per node, so interleave still spills to node
      0. The forcing form (`/mnt/raid0/llm/tmp/inf70/evict_nodes_force.sh`) allocates `TARGET + 2` GiB
      whenever `free < TARGET` and verifies; C7(a) should adopt it. This is why placement kept skewing
      "even after in-lock eviction" — the eviction was too weak.** (c) Decide the durable form with the operator: `vm.zone_reclaim_mode=1` (reclaim on
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
- [x] **C9 — `llama-perplexity` returns NaN for qwen4exp; there is no PPL/KL gate for this model.** ✅ 2026-09-04 — stale binary; verified to the same-binary standard, see the C9 block below.
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
      (cache-served, ~162 GB/s) vs 233 µs then, same command. **Correction 2026-09-03 (D8x): this "state-dependent" reading was itself wrong — D8's
      "serial" arm was secretly parallel (the `GGML_GET_ROWS_MIN_BYTES` knob is inert at execution), so
      the 2.59 ms it saw was the PARALLEL cost and the 9.34 ms is the genuine SERIAL cost; the
      parallelization is real (9.34 → 2.59 ms) and D6's "start with GET_ROWS" ranking STANDS.**
      SET_ROWS deliberately left serial (source rows can share a destination index — a write race, for
      0.011 ms/token); CPY needs nothing (its single-task nodes are the empty `ne1 = 0` ones). A cold-source
      probe shows the split does work when there is DRAM traffic (1T 105 µs → 48T 12–61 µs). **Side
      finding under bisect (D8x, running): the anchor binary 10196 measures 10.37–10.47 t/s while the d8
      tree's build measures 11.82–12.02 with the patch disabled — a reproducible +14% whose cause is not
      the patch by the agent's protocol, with cmake cache, flags, gcc, stale objects, library resolution,
      base delta, placement and THP ruled out; a fresh pristine build (d1-base) is NOT faster, so it is
      something in the d8 tree or its arm protocol.** If real, the 10.09 anchor and every Δ against it are
      understated ~14%. **D8 follow-up (D8x): `GGML_GET_ROWS_MIN_BYTES` is dead at execution** — it gates
      only the planned `n_tasks`, which the compute loop ignores; delete it or move the byte-threshold gate
      into the kernel, and isolate GET_ROWS in future with a build lacking `bc2834a9b`, never the env var.
      **D8x static verdict (2026-09-02, bench arms then confirmed): the +14% IS the GET_ROWS
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
      anchor-server-vs-merged-server greedy IDENTICAL on 3 prompts (71/128/128 tokens). Safe to build on.**
      **Attribution resolved 2026-09-03 (merge-verify raised a counter-claim; refuted from the code):
      the +18.8% decode is the parallel GET_ROWS (`bc2834a9b`), confirming D8x.** merge-verify read its
      opt-out arm (12.05 t/s with `GGML_GET_ROWS_MIN_BYTES=1e12` + CONCAT off) as "GET_ROWS ≈ 0.5%, the
      rest is the prof commit `e9d9d288a`" — both halves are wrong: (1) `GGML_GET_ROWS_MIN_BYTES` only
      sets the *planned* `n_tasks`, which the compute loop ignores (D8x), so that arm still ran the
      parallel gather — it disabled only CONCAT, which is why pp512 fell to anchor level while tg128 held;
      (2) every line `e9d9d288a` touches is inside `#ifdef GGML_CPU_PROF` and the shipped build has no
      `-DGGML_CPU_PROF`, so it compiles to nothing. Pristine (no GET_ROWS) 10.15 → merged tip 12.11 with
      only GET_ROWS + CONCAT compiled-in and CONCAT worth ~0.5% decode ⇒ GET_ROWS ≈ +18%. Methodology
      note carried to D8: the env knob is an inert A/B handle; isolating GET_ROWS needs a build without
      `bc2834a9b`, not the knob. Rationale for default rather than
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
- [x] **B3 — restructure `mul_mat_id` for batch 1.** ✅ 2026-09-03 (both halves). Beyond D1's barrier removal: chunk across
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
      the uniform file stays the era anchor, UD stays the served file). **B3-k DONE ✅ 2026-09-03** (subagent `b3k`, branch `inf70/b3k` `5eb7d5f05` on D1 `664096408`, build 10203): thread `ith` streams the contiguous range `[total·ith/nth, total·(ith+1)/nth)` of the flat (used-expert, row) space (~133 rows/181 KB of IQ4_XS gate-up, ~533 rows/256 KB of Q5_1 down, ≤ 2 adjacent slabs) instead of ten 14–54-row stripes; patches the iqk hooks (`iqk_dispatch.cpp`, `iqk_mul_mat.{cpp,h}`) that `GGML_IQK=1` actually runs, gated by `GGML_MMID_SLAB`. **Round-2 ABA, placement proven per arm, coherence-checked: slab-on 12.59/12.61 t/s (79.43/79.30 ms) vs merged tip 12.24/12.21 t/s (81.70/81.90 ms) = +3.07% decode (−2.43 ms/token), 12× the 0.25% baseline spread.** Same-binary flip attributes the whole gain to the slab partition (D1 alone −0.37%, null). Bit-identical logits on 3 prompts × 128 steps vs slab-off and the merged tip; `test-backend-ops -o MUL_MAT_ID -b CPU` 815/815 (six runs), `test-iqk-ser`, `test-llama-archs` pass. **Merged into `exp/cpu-fusion-qwen4exp-20260829` on 2026-09-03 (operator direction — "merge b3k if the round 2 confirms"; `--no-ff` merge commit `0d2af8194`; merged tree SHA `9e43dcbc8` bit-identical to the gated `inf70/b3k` tree, so the gates transfer verbatim — no combined-tree reverification needed). Carries D1 (`664096408`, cherry-pick of `1ba448e74`) as its bit-exact, null-on-its-own base.** Evidence: `/mnt/raid0/llm/tmp/inf70/agents/b3k/`.
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
## ★ OPERATOR DECISION 2026-09-05 — OP-35 RESOLVED: MTP GOES TO PRODUCTION, AND THE RECIPE OWNS IT

Operator, verbatim in substance: *"yes, of course it would. Ultimately we will fold this cpu kernel work into
the autokernel champion when we're done, and establish a canonical recipe for this qwen3.8 model to always
include its mtp head."*

Three things follow, and they change the END STATE of this campaign — it no longer terminates in an
experimental branch:

**⚠ RECIPE DEFECT FIXED 2026-09-05 — the campaign's documented `--fa 1` DOES NOT EXIST.** Verified against
the binary: the option is **`-fa, --flash-attn [on|off|auto]`, default `auto`** (`LLAMA_ARG_FLASH_ATTN`).
**⚠ CORRECTED 2026-09-06 — I OVER-CLAIMED THIS.** Tested against the binary with the dry-run trick:
**`-fa 1` is VALID** (the short form accepts `1`), `-fa on` is valid, `--flash-attn on` is valid, and **only
`--fa 1` is invalid** — the *long* form must be spelled `--flash-attn`. So it was the **name alone**, not the
value form. **`MEASUREMENT_POLICY.md:37`'s "`-fa 1` explicit" is CORRECT** and I was one step from "fixing" a
correct governance doc on a false premise; the dry-run trick caught it in about a second, which is the whole
argument for the trick. Any launcher using `--fa 1` **dies at startup before loading the model**. **Two agents lost arms to it in one session** (B12 lost its first preflight; SYNC-10 lost
all seven MTP arms of a hard-won lock turn). The campaign's own arms therefore never passed an FA flag at all
— they ran on `auto`, which resolves to enabled (`resolve_fused_ops: Flash Attention enabled`), so the
MEASUREMENTS are unaffected; only the written recipe was wrong. **Corrected to `-fa on` throughout
(10 occurrences).** This is precisely the failure PROD-1 exists to prevent: a recipe carried in prose that
nobody had executed verbatim. **Codify it as constants that launchers import, and validate the string by
dry-running against a nonexistent model** — the parse either reaches model load or reports an invalid
argument, and it costs about a second.

- [x] **★ PROD-1 — THE CANONICAL RECIPE. Operator-flagged 2026-09-06 as the thing not to forget; with PROD-2
      deferred it is the ONLY live PROD task.** The MTP head is part of the MODEL, not an experiment. Write the canonical recipe for
      Qwen3.8-Flash-Next so that **every** serving path for this model carries its MTP head by default.
      Settled config: head `shared-Q8_0`, `--spec-type draft-mtp --spec-draft-n-max 4 --spec-draft-p-min 0.5`
      (fleet default n-max 3, **4 for coding roles**, per the 2026-09-04 operator ruling), `GGML_ROWEXACT_N`
      unset, **KV f16 — do NOT quantise (B9)**, `-t 48`, `-fa on` + `GGML_FA_SPLIT_KV=0`, canonical env +
      `taskset -c 0-95 numactl --interleave=all`. Measured **23.16 t/s, 1.876× plain** (ABA-confirmed).
      Codify it per [MEASUREMENT_POLICY](../../agents/shared/MEASUREMENT_POLICY.md) so sessions import the
      constants instead of remembering them — the standing rule is *use codified recipes, not memory*.
      **Dependency**: B12 may change the head artifact (IQ4_XS requant); do not freeze the recipe's head
      choice until B12 reports.
      **★ THE RECIPE MUST CARRY G2-CONC.** Any canonical recipe for Qwen3.8-Flash-Next that admits concurrent
      requests inherits the `nrc_y >= 32` row-count trigger. Codify: (a) the `-np` value the recipe is validated
      at, (b) that G2-CONC was run **on the binary the recipe names**, never inherited from an ancestor commit,
      and (c) the reproducibility policy chosen under OP-39 — the recipe is where "which routes are row-exact"
      becomes importable constants rather than a remembered convention. A recipe that pins flags but not the
      concurrency gate reproduces the failure PROD-1 exists to prevent.
      **✅ COMPLETE 2026-09-07 — the recipe is now DATA, validated against the real binary and the real host.**
      Drafts in `/mnt/raid0/llm/tmp/inf70/agents/prod1/draft/`: `lib/qwen38_flash_next_recipe.py` (657 lines,
      `preflight` passes here), `lib/test_qwen38_flash_next_recipe.py` (**38 tests, all pass**),
      `benchmark/serve_qwen38_flash_next.sh`. Follows the EXISTING convention (`scripts/lib/canonical_recipe.py`)
      as a **sibling, not a replacement** — that file is the bare `llama-bench` CPU baseline (`-t 96`, no MTP);
      this is the served `llama-server` champion (`-t 48`, MTP mandatory). **Proof of equivalence**: the emitted
      command is **byte-identical** to CHAMPION-3's expanded arm, and the emitted env is **set-identical** to the
      live `/proc/PID/environ` readback (`champion3/runs/Q_C3_r1.env`).
      **Three defects it found in our own record:**
      1. **The PROD-1 prose recipe was a HYBRID NOBODY EVER EXECUTED** — it claimed `-fa on` *and*
         `GGML_FA_SPLIT_KV=0`; the live readback shows **neither**.
      2. **`23.16 t/s` / `1.876×` is a build-10221 number, NOT a champion-3 number.** Do not quote it as the champion.
      3. **B12's dependency on PROD-1 is DISCHARGED** — any row still reading as blocked on PROD-1 is stale.
- [ ] **PROD-2 — ⚠ THE 09-06 DEFERRAL WAS REVERSED BY THE OPERATOR ON 2026-09-07. Read the FOLD block
      below before acting on the deferral text that follows.**

      **★ REVERSAL, recorded here 2026-09-07 at the wrap-up sweep (this handoff did not know about it).**
      `handoffs/active/autokernel-champion-aggregate.md` → **FOLD** carries operator decision **FOLD-OP
      2026-09-07**: *the fold IS wanted*, no reversal ceremony needed, and **the trigger is the run-29 /
      reboot boundary** — the operator will stop run 29 to reboot, and that boundary is when the fold
      happens. Plan: [`../../docs/design/inf70-cpu-fold-into-champion-20260907.md`]
      (../../docs/design/inf70-cpu-fold-into-champion-20260907.md). Same lineage (fork `270b48ed6`),
      merge-tree **0 conflicts**, two default-ON blockers on the CPU side to fix first.
      **`FOLD-0` is assigned to `inf70-audit` — this session — but is deliberately NOT handed over yet**
      ("surface FOLD-0 to `inf70-audit` when the run-29 / reboot boundary approaches"). Do not start it;
      **do watch for that boundary.**
      **⚠ FOLD-0 is written against `6f032c48d` (champion-1). The champion is now `9c4f73e29`
      (champion-3).** Under the standing rule *the champion is always current*, the fold-ready commit must
      be re-based on the current champion or the fold ships a two-generations-old kernel. **Surface this to
      the champion owner before the boundary, not at it.**
      **⚠ `inf70/champion` is still a private clone — FOLD-0's own text says "push".** Ten INF-70 branches
      exist locally only; a devcontainer rebuild already happened once this week and missed them by luck.

      **Superseded deferral text, retained for the record:** *"we're not folding into autokernel champion
      just yet."*
      **Do not start it, and do not let a later session infer that it is ready** because the levers are
      merged. The merge into `exp/cpu-fusion-qwen4exp-20260829` is EXPERIMENTAL integration; the champion fold
      is a separate operator-gated step. Original scope retained below for when it is called.
      **★ PROD-1 IS THE LIVE ITEM AND MUST NOT BE LOST BEHIND THIS DEFERRAL** — operator, same message:
      *"make sure we don't forget the canonical recipe."* See PROD-1 above; it is now the only PROD task in
      flight.
      **Original scope — fold the INF-70 CPU kernel work into the AUTOKERNEL CHAMPION.** The merged-and-validated
      levers on `exp/cpu-fusion-qwen4exp-20260829` (b3k expert slabs +3.07%, the iqk IQ4_XS repack fix that
      closed the long-prompt P0, D8's GET_ROWS parallelisation +15.4% same-binary-verified, the MTP stack with
      E2b-2, BE-1/BE-2) become champion input rather than a branch. **The single-champion invariant applies**:
      ONE champion aggregates ALL work between promotions, and anchor == champion tip is enforced. Sequence
      against the four-step kernel workflow in `CLAUDE.md` — pull fresh production → build → validate no
      regressions (GPU + CPU) → deploy as a NEW production version, with the full candidate benched as a
      whole, never reconciled by cherry-pick at promotion time.
- [ ] **PROD-3 — promote a CHAMPION artifact and retire the anchor** (this is what remains of OP-37).
      `-gateup-r16` is the best measured (12.73 vs 12.61).
      **⚠ RECONCILE BEFORE ANSWERING OP-37 (flagged 2026-09-07):** B4 measured **`IQ4_XS-uniform-r16` with
      the F16 router** at +1.69% MTP / +0.63% plain, PPL null with a stated MDE of 1.041%, α up 0.8209 →
      0.8227 — an **artifact-axis** GO that is deliberately *not* folded into the champion kernel (it is the
      only non-bit-identical lever, and folding it would silently retire the property that makes the champion
      promotable on a digest match). **So "the champion artifact" and "the champion kernel" are now two
      different objects, and this row names only the older of the two candidates.** Decide which artifact
      OP-37 is about before the 92 GB deletion is authorised. Once a champion exists the comparison basis is
      transitive — future deltas bench against the champion, exactly as autokernel already operates — and
      `IQ4_XS-uniform` (92 GB) becomes deletable. Precondition: confirm unsloth still publishes it (~2.8 h
      re-download, recoverable, not a one-way door).
      **★ G2-CONC gates this too.** A champion *artifact* promotion ships the same serving path as a kernel
      promotion; the coherence evidence must be on the candidate pair (kernel + artifact) actually being
      promoted. Do not close it by citing champion-3's own G2-CONC run if the artifact changes.

**★ SEQUENCING SETTLED BY THE OPERATOR 2026-09-05: "I'm not promoting to production any time soon —
certainly not before we finish this optimization study thoroughly."** So there is **no promotion window to
race**, and the earlier worry (that in-flight levers would miss it) is void. The consequence runs the other
way: levers accumulate into ONE properly-validated candidate, which is what the four-step kernel workflow
wants anyway — the full candidate benched as a whole, never reconciled by cherry-pick at promotion time.
**Do not re-raise promotion timing as a constraint on any Axis S or B-axis work.**

## Axis S — SYNCHRONIZATION. Opened 2026-09-05. The 23.4% of the token that is not compute.

**Why this axis exists.** Three byte-shrinking levers in a row underdelivered — B7 (PLE precision) null,
B10 (vocab slice) +3% ceiling, B11's premise dissolved entirely. That is not bad luck; it is the roofline
saying bytes are not the constraint. Decode runs at ~36% of the 152.6 GB/s ceiling, and the per-node census
says where the rest goes.

**⚠⚠ TWO CORRECTIONS THAT DEGRADE THE TABLE BELOW — READ BEFORE CITING ANY NUMBER IN IT.**

**(1) The profile is PRE-D8 and off the base's history** (`inf70/prof` @ `8b578bc57` is not an ancestor of
`exp/cpu-fusion-qwen4exp-20260829`). Pre/post-D8: GET_ROWS −7.40, CPY −1.31, CONT −1.07, GDN −0.28 ms/token.

**(2) It has UNQUANTIFIED STALL CONTAMINATION throughout.** Every per-node figure is a **mean over 69 evals
with no dispersion reported**, so any node may be carrying a discrete host stall divided by 69.
**Pre-registered 2026-09-05 by SYNC-1, before the confirming run**: the two "systematic stragglers" this axis
was partly opened on are very likely artefacts, and the arithmetic nearly settles it without new data —
`node_872` (MUL_MAT `iq4_nl [320,10240]`) has **97 same-shape siblings that compute in 47–59 µs** while it
computes **772 µs, 15×**, and *thread-0 compute cannot be inflated by a barrier or by imbalance* — whatever
hit it hit it INSIDE the kernel. `ffn_moe_logits-11` has the **opposite** signature: compute normal at
31.9 µs, only the wait exploded. Two unrelated mechanisms — yet both land **within 1 µs of each other in
total wall** (1117.0 / 1118.4) and each sits ~1,055 µs over its sibling median, which over 69 evals is
**~73 ms each, on a token of 96 ms.** That is two discrete multi-tens-of-ms host stalls (THP compaction,
reclaim, a scheduler event) landing on whichever node was executing, not a structural straggler — a
structural one would show on all 97 siblings, not on exactly one.
**Discriminator, pre-registered**: `wall_max ≈ 73,000 µs` at a single eval index with `spikes = 1` ⇒ artefact;
`wall_max ≈ 1,200 µs` with `spikes ≈ 69` ⇒ real. Anything in between (2–5 spikes) is still artefact, just
multiple stalls. **Cross-node check added by the coordinator**: if the argmax eval indices of the two nodes
coincide with each other and with a cluster of unrelated nodes, a host event is near-conclusive.
**★ DE-LUMPED 2026-09-05 (SYNC-1, offline — no lock needed): the contamination is WORSE than the two nodes
and the barrier estimate SURVIVES it.** Sweeping the handed-over profile for the stall signature finds
**4 contaminated nodes carrying 2.39 ms/token** — not the ~1.4 ms from the two I had spotted. After removing
them, the **arrive-together node class shows 2.32 µs/node dead**, which matches BOTH barrier instruments (the
2.16 µs OMP primitive and the 2.478 µs/node through the real threadpool) **to 8%**. So: the census was dirtier
than assumed, and the congestion model's central constant is now confirmed from a **third** independent
direction — on de-lumped in-situ data rather than a microbenchmark.
**If the discriminator confirms: drop 2.39 ms from the addressable envelope** (and MUL_MAT's dead from
7.19 → 6.10 ms for the two MUL_MAT-class nodes) — and
note this contaminates SYNC-5's ~4.2 ms MUL_MAT imbalance figure, which contains that 1.09 ms, and one of the
three pillars of this axis's original framing. **Treat every Sept-2 per-node number as an UPPER BOUND.** The
tip census reports max / argmax-eval / spike count per node; the Sept-2 data cannot be cleaned retroactively.

**⚠ DENOMINATOR CORRECTION 2026-09-05: the token is now ~84.2 ms post-D8, not 96.3 ms** (`agents/d8x/REPORT.md`); the census below is build 10197, PRE-D8. Price every lever against 84.2 ms.

**Measured, plain decode, build 10197** (`agents/prof/results-20260902T135356Z/pernode.tsv`, 4,409 node
evals): **22.516 ms dead of 96.267 ms wall = 23.4%.**

| op | wall ms | compute ms | dead ms | dead % | nodes |
|---|---|---|---|---|---|
| MUL_MAT | 41.911 | 34.723 | 7.188 | 17.2% | 797 |
| MUL_MAT_ID | 20.962 | 17.116 | 3.846 | 18.3% | 144 |
| **GATED_DELTA_NET** | 2.999 | 0.785 | **2.214** | **73.8%** | 36 |
| **CPY** | 3.648 | 1.440 | **2.208** | **60.5%** | 162 |
| **ADD** | 1.718 | 0.225 | **1.494** | **86.9%** | 689 |
| **SCALE** | 0.918 | 0.037 | **0.881** | **96.0%** | 375 |
| CONT | 0.843 | 0.106 | 0.737 | 87.5% | 166 |
| MEAN_D1 | 0.470 | 0.032 | 0.438 | 93.2% | 97 |
| RMS_NORM | 0.588 | 0.245 | 0.343 | 58.3% | 184 |
| SET_ROWS | 0.278 | 0.011 | 0.266 | 95.9% | 48 |
| L2_NORM | 0.201 | 0.023 | 0.179 | 88.7% | 72 |
| **GET_ROWS** | 9.338 | 9.000 | 0.338 | **3.6%** | 175 |

**Two readings that set the whole axis:**
- **The small-op family is a BARRIER TAX** — ADD/SCALE/CONT/MEAN_D1/SET_ROWS/L2_NORM/RMS_NORM total
  **~4.34 ms dead across 1,631 nodes at 87–96% dead**. They compute almost nothing and appear to pay a full
  thread-pool barrier each.
- **`GET_ROWS` is the exception and it is NOT a barrier problem — only 3.6% dead.** Its 9.0 ms is real
  compute stuck on too few cores (prior D6 note: unconditionally single-task, 113 MB at **13.1 GB/s on one
  core**). Against a 152.6 GB/s machine this is the largest single lever identified in the campaign.
  **Correction to the framing used when this axis was opened: D6 is a serialization defect, not dead time.**
- **Outlier**: `ffn_moe_logits-11` runs **1118.4 µs wall for 31.9 µs compute (35.1×)** — 1.09 ms in ONE node
  — while the other 47 `ffn_moe_logits-*` nodes are unremarkable. Smells like first-touch / pool wake-up
  rather than the router itself; must be discriminated, not assumed.

**Amdahl bound, stated up front so nobody oversells this axis:** 22.5 ms of a 96 ms token. A clean sweep of
every seam is ~10–15% realistically, ~23% at the theoretical limit — **not** the 2× that separates us from a
DGX Spark GB10 running the same model. That gap is ~1.78× memory bandwidth (273 vs 153 GB/s) and the rest is
a GPU paying no per-node barrier at all. Tuning does not close it; a coarser graph might (SYNC-5).

- [x] **SYNC-1 — COMPLETE ✅ 2026-09-07 (ranked envelope + per-(node,thread) census; see the tip-census block). authoritative census + outlier diagnosis + barrier-cost baseline.** Dispatched 2026-09-05.
      Re-census on current tip `10221`/`c51e4dabf` in BOTH plain and **the MTP config, which has never been
      profiled** (the draft graph is ~144 nodes and may look nothing like this). Discriminate the
      `ffn_moe_logits-11` outlier: same node every run (real defect) or whichever node is first after an idle
      gap (artefact)? **Measure what one barrier actually costs at `-t 48`** — every sibling's saving is
      priced against that number, so it must be measured, not estimated. Also: is the dead time spin-wait,
      futex sleep, or work imbalance? Different fixes.
- [x] **SYNC-2 — GO on all three levers. ★ GRAPH BARRIERS DO CONVERT TO WALL TIME — AXIS S IS ALIVE.** ✅
      2026-09-05. 4 paired same-window rounds, **4/4 wins each**, bit-identical. Base **12.922 t/s / 77.384
      ms/token** measured on its own `c51e4dabf` (not 96.267, not 84.2), base spread 1.86%.

      | lever | removes | end-to-end | ms/token | barriers |
      |---|---|---:|---:|---:|
      | `GGML_ELEM_COLSPLIT` | nothing — redistributes work | **+8.19% ± 1.12%** | −5.86 | 0 |
      | `GGML_TINY_SOLO` | **915 barriers, 0 nodes, 0 compute** | **+3.86% ± 1.20%** | −2.87 | −915 |
      | `GGML_EMPTY_SKIP` | 217 zero-element nodes + their barriers | +0.87% (r2–r4) | −0.67 | −217 |
      | **all three** | | | **77.374 → 69.750 (−9.85%)** | |

      **★ THE DECIDER, AND IT OVERTURNS THE COORDINATOR'S WORKING CONCLUSION.** `TINY_SOLO` **breaks the
      "one graph barrier per node" identity**: it elides **915 graph barriers while removing zero nodes and
      changing zero arithmetic**, recovering **3.14 µs per barrier**. `EMPTY_SKIP` recovers **3.09 µs per
      barrier** over a **disjoint** population. **Two independent levers agreeing to 2%, both just above
      SYNC-1's 2.72 µs in-situ residual.** So the ~12 ms barrier budget is **not** a gross unrecoverable
      number, Axis S is **not** economically dead, and **SYNC-5's fusion pricing should be REDONE at
      3.1 µs/barrier rather than written off.**
      **D1's null is not in tension**: it removed *internal* `mul_mat` barriers, whose waits land inside
      compute — exactly SYNC-1's disjoint-populations result.
      **Mechanism, both halves of the brief refuted**: `ggml_get_n_tasks()` is advisory
      (`ggml-cpu.c:3861` sets `params.nth` to the full count for every node), so **lever (a) as briefed could
      not have removed a single barrier**. SCALE *is* single-threaded, but because
      `ggml_compute_forward_scale_f32` splits over rows and every decode SCALE is `[2560,1,1,1]`.
      **⚠ DUPLICATE EFFORT — MY COORDINATION FAILURE, but it bought corroboration.** SYNC-2's census
      independently found **the same row-split defect as SYNC-10**: 7.375 ms/token of row-partitioned
      elementwise work on ONE thread of 48 because `ggml_nrows(dst) == 1` at batch 1, of which 4.665 ms is
      134 `UNARY [10240,1]` nodes — the hyper-connection sigmoids, scalar libm `expf`, 10,240 per node.
      `ELEM_COLSPLIT` is D8's shape; UNARY wall **6.644 → 1.589 ms**. **Two independent implementations, two
      independent measurements: +8.19% vs SYNC-10's +8.57%, agreeing within 0.4 pp.** I should have caught the
      overlap when I told SYNC-2 its nodes were `hc_mix` chains.
      **Correctness**: full-logit fnv1a over all **248,320** logits, 83- and 186-token prompts × 48 greedy
      steps — **bit-identical on all 96 step lines** with all three on; 1.7B smoke bit-identical per lever.
      Knobs `strings`-proven in both binaries before any arm (the harness hard-fails otherwise); own worktree,
      fresh configure, no shared build dir. `EMPTY_SKIP` r1 had unproven placement (19.3 GB resident) so the
      **conservative r2–r4 figure is reported**. Commits `1150140fe` `3713f02a0` `25597fc97` `226847752`
      `20db1a5ab` on `inf70/sync2`, all knobs default OFF, nothing merged.

- [x] **SYNC-10 COMPLETE 2026-09-05 — GO on the split, NO-GO on the vectorisation.** ✅ Lock released,
      nothing orphaned, `/workspace` untouched. Two commits on `inf70/sync10`, **not pushed, not merged**.

      | | verdict |
      |---|---|
      | **`GGML_ROWCOL_SPLIT`** (`2af8669ce`) | **GO** — **+3.05% ± 0.52 serving (MTP)**, +8.42% ± 0.80 plain. **Bit-identical.** One env flag, default OFF. |
      | **`GGML_VEC_SIGMOID`** (`086b5b9c9`) | **NO-GO here** — +0.0 pp on top of the split, costs a top-1 flip at ~19 tokens. **No KLD window needed.** Keep as an **upstream PR** (UP-1). |

      **LEAD WITH +3.05%, NOT +8.42%.** Quoting 9.9% / 7.79 ms / +8.4% as *serving* value overstates it ~2.8×.
      **Threshold MEASURED, not guessed**: `MIN_ELEMS=4096` gives **+5.5% vs +8.42% at 512**, so **a third of
      the win lives in rows under 4096 elements** — the threshold is a real tuning parameter, not a formality.
      **Bit-identity proven FIVE ways**: 50-shape × 8-op digest (mutation-tested — and its first mutant was
      benign by construction, which it declared rather than counted); greedy streams byte-identical at
      40/90/200-token prompts; `test-backend-ops -b CPU` 8/8 × 4 arms; **`M1A ≡ M1S` under spec decoding**; and
      `W ≡ V`, showing the split adds zero numerical change.
      **⚠ THP CAVEAT THAT LIMITS D6-PLACE — the step is NOT localised to exactly 2 MB.** SYNC-10 corroborates
      the effect (hc gemvs 1.74/1.84 MB at **33–39 GB/s** vs **124–147** for ≥2 MB, with a size-controlled
      series at fixed inner dim ruling out shape) **but its shapes jump 1.84 → 5.24 MB, so it cannot place the
      boundary.** SYNC-2's pair brackets it more tightly (1.741 MB → 28.0 GB/s; 2.253 MB → 41.6). **Together
      they bracket the step between ~1.84 and ~2.25 MB — consistent with THP but NOT proof of the THP
      mechanism.** D6-PLACE must sample that gap rather than assume it.
      **Three of its own instruments were defective and each was fixed** (vacuous sha over a timing footer;
      `rfind` mis-anchoring; a comparator racing its producer). **All three verified as its own alone** —
      siblings redirect `> .out 2> .err` and are unaffected, no shared harness implicated — and **none changed
      a timing number**, though mid-flight divergence-depth figures did move and §4.4 records that.
      **Two self-inflicted costs, disclosed rather than buried**: a task-manager kill lost window 1 (contained
      — it proved no process survived, so SYNC-2's concurrent window was uncontaminated), and the `--fa 1`
      typo killed all seven MTP arms, costing half a lock turn.
      Report: `/mnt/raid0/llm/tmp/inf70/agents/sync10/REPORT.md`, **6,339 words against a 900-word brief —
      flagged by the agent rather than hidden**; §6 carries ready-to-apply handoff rows.

- [x] **SYNC-16 — COMPLETE ✅ 2026-09-07: the lever WORKS and does NOT PAY. NO-GO.** Branch
      `inf70/sync16` @ `6d8592fb8`, default OFF, not merged; report
      `/mnt/raid0/llm/tmp/inf70/agents/sync16/REPORT.md`.
      Kernel row loop **10.36× faster** (20.28 → 2.01 µs/row), bit-identical. But knob-isolated on a
      SINGLE binary, plain decode is **0.9968×, 95% CI [0.9945, 1.0004], 24/60 pairs faster — no gain,
      bounded at ≤ +0.04%.** The projected +1.5% / +0.8% did not materialise. The 10.36× is
      **mechanism sizing, a NON-CLAIM**, and was not scaled into a served number.
      **★ BOTH APPARENT WINS WERE ARTEFACTS, AND THE PRE-REGISTERED A/A CONTROL CAUGHT ONE.**
      The **+2.91% plain** was **the BINARY, not the knob**: plain arms cluster cleanly by binary
      (`bin-base` 18.99–19.34, `bin-s16` 19.61–19.86) *regardless of knob state*, with no overlap and
      no position ordering — and knob-OFF on the sync16 binary was the FASTEST arm in the block. The
      A/A rule (written 16:03Z, 21 min before the window opened) said "C must match A, or any delta is
      a build artefact." It didn't.
      The **+4.9% MTP** was **CO-RESIDENCY**: r(foreign %CPU, tw_tps) = **−0.825**, A arms carried 63%
      more foreign load than B. It also exceeded the lever's entire ~1.02% MTP budget by 5×, so it was
      physically impossible regardless.
      Gates that stand as claims: bit-identity 16/16 stream digests (plain + MTP, full 256-token
      streams at 41/109/240 prompt tokens), 24/24 production rows, α = 0.8209 identical across all MTP
      arms, `test-backend-ops -b CPU` failure sets unchanged. Coherence {COHERENT 20, SHORT 4} in all
      14 arms; the 4 SHORT rows are the same four every time and are **exactly** the `pred_n < 16` set,
      so the pre-registered floor excludes them consistently — prompt set behaving as designed.
      **Caveat the agent flagged rather than buried:** it named a profiler-overhead hypothesis for the
      null but did NOT prove it → SYNC-21.

- [ ] **★★ MEAS-1 — EVERY ABA IN THIS CAMPAIGN RAN WITH UNFENCED TOOLING INSIDE THE MEASURED REGION.**
      Filed 2026-09-07 from SYNC-16. `claude`, `codex` and `python3` processes, all with
      `cpus_allowed=0-191`, ran at **100–600 summed %CPU inside cores 0-95 in every arm**.
      `region-lock` excludes other bench ROLES but does not fence unpinned tooling. The co-residency
      logger's `27 of 11` is not a broken counter — it is 27 foreign-process OBSERVATIONS over 11
      SAMPLES, a label bug; the co-residency itself is genuine. **The same defect sits in
      `champion1/arm.sh`, the copy source for the campaign's harness** — flagged by SYNC-16, not
      silently patched. Until this is decided, every sub-5% delta in this campaign carries an
      uncontrolled variable.
      **★★★ THE FRAMING THAT DECIDES THIS IS A HARDWARE FACT, NOT A SCHEDULING ONE.** This is a
      **96-physical-core box presenting 192 logical CPUs**. Every logical CPU in 96-191 is the SMT sibling of
      one in 0-95 (96↔0 … 191↔95, **exhaustive**, verified against `thread_siblings_list`). Therefore any
      second tenant doing real work is *necessarily* on the bench cores' siblings. **On this host, isolation
      between two CPU-heavy campaigns is not achievable by placement at all — only by time.** That sentence is
      the decision: this is not "should we tidy up our tooling", it is **"two campaigns cannot both run
      CPU-heavy work and both trust their sub-5% numbers."**
      **⚠ CORRECTION 2026-09-07 — THE "FENCE IT" OPTION CANNOT BE BUILT AND HAS BEEN REMOVED.** The
      original filing offered *fence via cgroup/cpuset vs log-and-regress*. Challenged by the autokernel
      session and **verified directly against the kernel** by reading `thread_siblings_list` for all 192
      logical CPUs: **not one logical CPU in 96-191 lacks a sibling inside 0-95** — the pairing is
      exhaustive (96↔0, 183↔87, 184↔88, 191↔95). **There is no disjoint region to move tooling to.** Any
      process on this host, pinned anywhere, lands on a physical core our bench range is timing.
      **The dominant contention is BUILDS, not bench threads.** autokernel's `gates.compiles` runs
      `jobs=64` pinned to `cpu_list="96-183"` — the sibling set of **88 of our 96** bench cores — and its
      bench on `184-191` covers the other 8: **96 of 96**. Sampled live during their run 30 while we were
      measuring: **9 concurrent `cc1plus` at 100% CPU each.** That is a far better candidate for our
      **16.8% A/A spread** than the 8 GPU host threads originally flagged.
      **A nuance recorded rather than smoothed over — and recorded AS THE PEER MADE IT.** The autokernel
      session wrote the 16.8% attribution up as **SHARED SUSPICION, not settled on them**: the `cc1plus` we
      caught at 1200% had `cpus_allowed=0-191` (**unpinned**), while theirs are pinned to `96-183`, so the
      process we sampled was most likely **one of our own** unlocked builds. Their defect is still real —
      pinned-but-unlocked contends whenever a build overlaps an arm; it just does so on a predictable 88
      cores. **Two separate defects**: ours is unpinned AND unlocked, theirs is pinned but unlocked.
      *A peer correcting their own overreach is worth preserving accurately; do not re-simplify this to
      "it was their builds".*
      **Context, theirs alone, no decision needed:** their `serving.py` pins nothing — the `llama-server`
      at their serving gate has no `taskset` in its Popen argv, so it can land **directly on 0-95** rather
      than merely on siblings. They are fixing it; it is recorded here only because their own serving
      measurements inherit the same hazard.
      **★★ CROSS-REFERENCE — MEAS-1 AND AUTOKERNEL'S `R23-49` / THEIR `OP-39` ARE ONE DECISION, NOT TWO.**
      They have queued the **identical** serialize-vs-regress tradeoff, cross-referencing ours, because
      option (A) costs **them** throughput (their builds queue behind our arms) while it buys **us**
      resolution. **Neither session can decide it alone and neither should.** The two rows must be ruled on
      together, **or one campaign's answer silently sets the other's default.**
      *(Note: this is a different OP-39 from INF-70's own resolved per-route row-exact item.)*
      **Also recorded, theirs, no decision needed:** they have made `llama-server` pinnable
      (`Recipe.cpu_list`) but are **deliberately leaving the default `None`** — setting it changes the
      measured condition and would invalidate their 3.536% serving floor, so the pin and its re-calibration
      must land **in one window**. A clean instance of this campaign's own rule that a lever's value is a
      property of the configuration it was measured in.
      **⏳ IN PROGRESS (coordinator, not an open task): our own build-script bypass** — `build3.sh` runs
      `cmake --build -j 40` with no `region-lock` wrapper.
- [ ] **★★ MEAS-1-DECIDE — OPERATOR DECISION. Three options; fencing is not among them.** Requested for
      the master index operator queue, `Open since 2026-09-07`.
      **★ THE DISCRIMINATOR IS THE PEAK, NOT THE TOTAL FOREIGN LOAD — SO (A) NEED ONLY COVER BUILDS.**
      HARNESS-1 quantified three A/A arms (same binary, same config, **bit-identical output — purely timing**):

      | arm | tw t/s | foreign CPU p50 | foreign CPU max | heaviest foreign |
      |---|---:|---:|---:|---|
      | `A_OLD1` | 19.313 | 399.9 | **3218.0** | `cc1plus` 1200, `test-backend-ops` 363 |
      | `A_OLD2` | 22.860 | 621.2 | 1214.6 | `python` 840 |
      | `A_OLD3` | 22.421 | 477.8 | 1458.0 | `python` 600 |

      **All three: 16.47% spread. Excluding the compiler-contended arm: 1.94%.** Note `A_OLD1` has the
      **lowest** median foreign CPU yet is **15% slower** — unpinned noise (`ps`, `htop`) dominates the median
      and moves nothing; what hurts is a **burst of 3218% = 32 cores, a third of the bench region.**
      **⚠ The existing `loadavg < 10` PRE-LOAD gate cannot protect an arm**: it passes, and then the burst
      arrives *during* the measurement. Only **in-window** sampling catches it — which is precisely why the
      sampler's `184-191` mislabel (WRAP-4) mattered as much as it did.
      **(A) SERIALIZE — and it is CHEAPER than first stated: serializing COMPILES ALONE plausibly takes the
      A/A floor from 16.47% to ~1.94%**, i.e. the difference between a 3–5% effect being unresolvable and
      being measurable. It does **not** require fencing or serializing all tooling. Builds and other heavy
      work take the region lock and queue against bench arms. *Removes the confound at the source; costs the
      other campaigns throughput directly* — autokernel's builds would queue behind our CPU arms. That cost is
      why it is an operator call.
      **(B) PUBLISH A SCHEDULE** — heavy work advertises its windows and sub-5% timing avoids them.
      *Cheaper, weaker, relies on compliance.*
      **(C) ACCEPT AND REGRESS** — keep measuring through the noise, log foreign load per arm, treat it as
      a known variance term. *No host change; prices the confound rather than removing it, and cannot
      rescue runs already taken.*
      **No recommendation yet, deliberately** — SYNC-19/20's numbers under a quiet window come first.
      **⚠ THE QUIET WINDOW IS REQUESTED, NOT ARRANGED. Do not record it as secured.** autokernel accepted the
      protocol (hold run 30 at a task boundary when SYNC-19/20 acquire) but **cannot deliver it unilaterally
      — run starts and stops are operator-gated on their side.** If their operator has not ruled by the time
      SYNC-19/20 are ready, they will surface it as a live request rather than let the default take effect.
      **On current evidence SYNC-19/20 may well run CONTENDED, in which case their headline is a NON-CLAIM
      and must say so in advance** — decided now, not after the numbers are in.
- [ ] **★ MEAS-3 — RETENTION ROW: `/mnt/raid0/llm/tmp/inf70/agents/sync16/` IS A CROSS-CAMPAIGN DEPENDENCY.
      DO NOT RECLAIM.** Marked in place at `agents/sync16/DO-NOT-RECLAIM.md`. The autokernel session is
      **reusing its sibling-expanded `cpus_allowed` residency check** in their serving gate rather than
      rebuilding it, and has filed that path as the source. The directory also holds the **pre-registered A/A
      control that caught SYNC-16's build artefact** and the long-stream identity harness. **It looks exactly
      like spent scratch and is not** — the last sweep removed 185 GB, and this is the class of thing that
      sweep would have taken. Carry this row until the dependency is vendored somewhere durable.
- [ ] **★ MEAS-2 — ADOPT `build_locked.sh` AS THE STANDING BUILD IDIOM, AND PROMOTE IT OUT OF SCRATCH.**
      Filed 2026-09-07. **The build bypass is SYSTEMIC, not one script.** Audit of every INF-70 build script:
      **19 of 21 take no region lock at all** — only `harness1/build.sh` and `b7-ple/build.sh` do.
      `champion3/build3.sh` was merely the one we happened to catch, so patching that single script would have
      fixed nothing and manufactured a false sense of closure. **This is a CONVENTION gap, not a slip.**
      **The fix is written**: `/mnt/raid0/llm/tmp/inf70/build_locked.sh` — a wrapper running `cmake --build`
      under `region-lock` with `--role build --timeout-s 0` (fair queue, **never polls**).
      **Verified to actually exclude rather than merely appear to**: the lock module's occupancy registry
      computes blockers from **region overlap regardless of role** (`cpu_region_lock.py`, the `overlaps` set);
      role is attribution only, and only a `shared=True` same-role request can join a cohort — so `role=build`
      genuinely queues behind `role=bench`. Checked deliberately, because the CLI help calls it a "per-role
      lock" and the lock FILES are per-role (`cpu_region.{role}.{region}.lock`), which would have made a
      role-labelled wrapper **vacuous** had the cross-role mutex not existed.
      **Task**: adopt it as the campaign's standing build idiom, and **promote it into the research repo
      alongside PROD-1's recipe module** so it outlives scratch and PROD-1 can import it.
      **Explicit decline recorded, not a drop: do NOT edit the 19 scratch build scripts** — they are one-shot
      artifacts and mostly spent; the value is in the convention and in PROD-1 importing it.
- [ ] **SYNC-21 — prove or kill the profiler-overhead hypothesis for SYNC-16's null.** Needs a
      profiled A/B on a NON-prof build in one window. If the nodes shrink while the token does not,
      the lever is dead for good. Also tests the wider risk SYNC-16 raised: **the per-node census may
      systematically overprice cheap single-threaded nodes** — SYNC-16 is the first lever to test a
      census line item end-to-end and find nothing there, and every lever sized off `*_pernode.tsv`
      inherits that risk.

**Superseded — the settled-serving-number block:**

**★★★ SETTLED — THE SERVING NUMBER IS `+3.05% ± 0.52 pp`, REPLICATED, AND IT IS THE WHOLE EFFECT, NOT A
FLOOR.** MTP R1 **+3.11%**, R2 **+2.98%**, pooled **+3.05% ± 0.52 pp, 10/10 prompts positive, −1.42
ms/token**, base drift 0.1% between rounds.
**SYNC-10's guard is `nr < nth`, NOT `nrows == 1`** (`common.h:162`), and its work unit is **already a
(row, column-chunk) pair** — D8's exact shape. **The relaxed-guard follow-up SYNC-2 identified as the
highest-value item is ALREADY IMPLEMENTED on `inf70/sync10`.** Occupancy at the real shapes:

| graph | shape | nr | ncc | tasks over 48 thr |
|---|---|---:|---:|---:|
| plain decode | [10240,1] | 1 | 46 | 46 |
| **MTP trunk (census)** | **[10240,2]** | 2 | 24 | **48** |
| **MTP trunk (n_max=4)** | **[10240,4]** | 4 | 12 | **48** |
| batch 47 | [10240,47] | 47 | 2 | 94 |
| batch 48 | [10240,48] | 48 | 1 | row split already fills |

**Full 48-thread occupancy on the trunk at every batch from 1 to 47.**
**And the measurement settles it independently of the code**: the saving is **5.84 ms/eval** at ~4.1
tokens/eval against a trunk seam of **6.04 ms/eval**. A draft-only effect is bounded at ~0.76 ms/token =
**+1.6%** and cannot produce +3.05%. **So the ÷3 framing was right for this branch** (⚠ *for this branch
only* — see **★ COROLLARY THAT SUPERSEDES THE ÷3 RULE ENTIRELY** below: the haircut is a property of a lever
IN A GIVEN KERNEL, never portable; re-measure, never re-scale) — SYNC-10 said so
plainly rather than letting the hopeful reading stand.
**Two consequences, both actionable:**
1. **Do NOT schedule the relaxed guard as new work — ADOPT SYNC-10's.** Its `nr < nth` supersedes SYNC-2's
   `nrows == 1` `ELEM_COLSPLIT`; it is the cheap route to the batch-4 behaviour SYNC-2 wanted and it is
   already measured, bit-identical and gated.
2. **★ SYNC-2's `TINY_SOLO` HEADROOM IS REAL AND UNTOUCHED — a genuinely open lever on a different axis.**
   It elides **barriers**, is gated `nrows == 1`, and therefore **still does not fire on the trunk**, while
   SYNC-10's change removes **zero** barriers. **Trunk barrier headroom remains uncaptured by either branch**
   — and at the measured 3.14 µs/barrier that is worth quantifying. **This is the next lever.**
**`M2W` and `M1V` will produce NO MTP number**, per the numerics-under-speculation rule.

**Superseded — the open question this resolves:**

**★★★ THE ÷3 MAY BE THE WRONG CORRECTION — THE PREDICATES ARE GATED ON `nrows == 1`, WHICH IS THE BATCH-1
CONDITION (SYNC-2, 2026-09-05).** Verified in its own code rather than inferred:
`ggml_elem_colsplit_applies()` requires `ggml_nrows(src0) == 1` (`common.h:142`); `ggml_cpu_node_is_solo()`
requires `ggml_nrows(node) == 1` **and** `ggml_nrows(src[0]) == 1` (`ggml-cpu.c:2688`, `:2691`);
`GGML_EMPTY_SKIP` is `ggml_nelements(node) == 0` and batch-independent.
**On an MTP verify pass the trunk graph carries ~4 tokens**, so those tensors are `[n_embd, 4]` and
**neither `ELEM_COLSPLIT` nor `TINY_SOLO` fires on the trunk at all — yet the trunk is where the 6 ms lives.**
They fire fully on the draft model's batch-1 steps. **SYNC-2 therefore refused to publish a scaled
+3.02% / +1.42% and says its two large levers must be MEASURED, not divided.** Only `EMPTY_SKIP` scales
cleanly: **~+0.32% served.**
**⚠ OPEN QUESTION THIS RAISES ABOUT THE HEADLINE, routed to SYNC-10**: if `GGML_ROWCOL_SPLIT` carries the same
`nrows == 1` guard, then its **+3.11% comes ENTIRELY from the draft model's batch-1 steps** (~4.27 draft evals
per trunk eval — plenty to explain it), and **the trunk's 6 ms is untouched, meaning the serving number is a
FLOOR, not a ceiling.** If instead its guard already handles `nrows < nth`, +3.11% is the whole effect.
SYNC-10's graph-shape filter already separates the 144-node draft graph from the 7481-node trunk, so this
should be answerable from data in hand rather than a new arm.
**★ THE HIGHEST-VALUE FOLLOW-UP ON EITHER BRANCH — relax `nrows == 1` to `nrows < nth` and split by
(row, column-chunk) PAIRS instead of column-only.** D8's exact shape; bit-identity holds for the same reason.
It makes the lever fire at **every batch below 48**, not only at 1 — which is where the trunk's 6 ms becomes
reachable. The defect is milder at batch 4 but far from gone: **the hyper-connection sigmoids would still run
4-way on a 48-thread box.** Filed as item 5 of SYNC-2's go/no-go, to be measured under MTP where the paired
ratio is clean.
**The barrier finding is unaffected by any of this**: 3.14 µs/barrier (`TINY_SOLO`) and 3.09 µs/barrier
(`EMPTY_SKIP`) are **per-eval structural measurements**, and Axis S's re-pricing should use that rate.
**THP hand-off re-labelled**: ~9.1 ms is plain decode, expect nearer 3 ms served — still the largest single
item on either denominator.

**★★ METHODOLOGY RULE ADOPTED 2026-09-05 (SYNC-10) — A NUMERICS-CHANGING ARM CANNOT BE A/B'd ON ms/token
UNDER SPECULATIVE DECODING.**
**★ THE RULE IS NOW DEMONSTRATED, NOT JUST ARGUED (2026-09-05).** `M2W` reproduces `M1W` to **0.6% per
prompt** (ratios 1.007, 1.006, 1.001, 1.009, 1.007) — while **W-vs-A scatters −9.7% to +19.4%.** So W is a
**highly repeatable measurement of a DIFFERENT WORKLOAD**, not a noisy measurement of the same one. The
scatter is entirely the changed token stream altering draft acceptance. **A numerics-changing arm under
speculative decoding gives you PRECISION WITHOUT COMPARABILITY** — and precision is exactly what would
otherwise make such a number look trustworthy. That is what makes the confound diagnosis airtight rather
than merely plausible. A different token stream produces a different acceptance pattern, and
acceptance dominates ms/token, so the arm measures **acceptance-rate luck confounded with kernel speed** — at
five prompts the luck wins. **SYNC-10 declined to report ANY MTP number for its V and W arms on these
grounds.** Requirements: a **fixed-token-stream harness** or **plain-decode measurement**, with quality judged
separately. **Only bit-identical arms yield a clean paired MTP ratio** — which is a second reason, beyond
shipping cost, to prefer them.
**The precise form, so it is not over-applied**: for a numerics change the total MTP delta is still the right
number for a **ship/don't-ship** decision, because an acceptance change is a *real consequence* and not an
artefact. What cannot be done is **attributing that delta to kernel speed**. **B9's KV-quant work is the
pattern to copy** — it measured α directly (0.8274 → 0.8166) and attributed through
`LLAMA_ATTN_ROT_DISABLE`, which is what made its conclusion sound.
**★ FOURTH INDEPENDENT BIT-IDENTITY CONFIRMATION**: `M1A ≡ M1S` **byte-for-byte on all five prompts, in the
FULL SERVING CONFIG** — speculative decoding, f16 KV, flash attention, 192 tokens. The strongest of the four
because it is the configuration that ships.

**★★★ THE SERVING NUMBER — +3.11%, NOT +8.42%. QUOTE THIS ONE.** (round 1 of 2, MTP config, 5 prompts)

| prompt | A base | S split | speedup |
|---|---:|---:|---:|
| p0 | 53.11 | 51.25 | +3.62% |
| p1 | 39.13 | 38.21 | +2.41% |
| p2 | 45.96 | 44.71 | +2.79% |
| p3 | 52.12 | 50.42 | +3.38% |
| p4 | 49.39 | 47.79 | +3.35% |
| **mean** | **47.94** | **46.48** | **+3.11%** (sd 0.44 pp, **5/5 positive**) |

**−1.47 ms/token.** Mechanism is the amortisation, exactly as pre-registered: the seam is **6.04 ms per
EVAL**, and the trunk graph amortises over **~4.1 tokens/eval** here (the MTP census assumed 3.23), so the
plain win does not carry across. The agent predicted ~4% before running it and measured 3.11%.
**⚠ THE BRIEF'S NUMBER SHRANK TWICE UNDER MEASUREMENT: 7.79 ms → 6.59 ms addressable once ARGSORT was ruled
unreachable, then +8.42% → +3.11% once priced against the config that SERVES rather than plain decode.
ANYONE QUOTING 9.9%, 7.79 ms, OR +8.4% AS THE SERVING VALUE IS OVERSTATING IT BY 2.7–3×** — including this
coordinator's own reports before the MTP arm existed.
**Still clearly worth taking**: +3.11% ± 0.44 with every prompt positive, **bit-identical**, behind a single
env flag. But it is a **3% lever, not a 9% one**, and the campaign's ranked envelope must be re-priced on
that basis — the plain-decode figures in SYNC-1's table are all subject to the same ÷~3.
**Round 1 of 2**; the `W` and `V` MTP arms and round 2 are still running.

**★★★ SYNC-10 PLAIN PATH SETTLED — THREE COMPLETE PAIRED ROUNDS, ALL ARMS SAME BINARY.**

| arm | R1 | R2 | R3 | **mean** | sd |
|---|---:|---:|---:|---:|---:|
| **S** `GGML_ROWCOL_SPLIT` (bit-identical) | +9.53% | +7.60% | +8.12% | **+8.42%** | 0.80 pp |
| V `GGML_VEC_SIGMOID` | +6.33% | +4.37% | +5.54% | +5.41% | 0.80 pp |
| W both | +9.53% | +6.63% | +8.66% | +8.27% | 1.22 pp |
| **W/S ratio** | 1.000 | 0.991 | 1.005 | **0.999** | ±0.007 |

**★ INDEPENDENTLY CORROBORATED: SYNC-2's separately written implementation measured +8.19% ± 1.12% over four
paired rounds. The two agree to 0.23 pp.** Seven paired rounds across two implementations, on a host that
drifts 3% over hours, converging inside a quarter of a percentage point.
**★ PROMOTION SETTLED ON THE PLAIN PATH: ship `GGML_ROWCOL_SPLIT` ALONE.** `W/S = 0.999 ± 0.007` — the
vectorisation contributes **nothing** on top of the split, three times over, and S is if anything marginally
the fastest. **Do NOT ship `GGML_VEC_SIGMOID` here**: it buys **0.0 pp** and costs a **top-1 flip at ~19
tokens**. **No KLD window is needed** — the accuracy question never has to be answered, because we never have
to ship the ulp change to get the win. Its value is **upstream only** (UP-1), where a 48-thread split is not
available to hide the scalar `expf`.
**Remaining**: the `MIN_ELEMS=4096` threshold probe closes this window; **the MTP serving arms are queued
behind it and remain the ONLY missing evidence.** No MTP claim until they land.

**SYNC-10 WINDOW 2 (2026-09-05) — everything except the MTP arms is now in.**

| evidence | status |
|---|---|
| census confirmed on its own base | done |
| plain wall-time, 2 paired rounds | done — **S +8.57%**, V +5.35%, W +8.08% |
| pristine-base control | done — `PBase` **13.06 ± 0.04** vs knobs-off 13.19, **no OFF-path regression**, so the S-vs-A gap is not an artefact of a slowed baseline |
| bit-identity: kernel digest + mutation test | done |
| greedy gates, 3 prompt lengths | done — **S identical; V and W DIVERGE at ~19–68 tokens** |
| `test-backend-ops test -b CPU` | done — **8/8 on all four arms** |
| THP corroboration for D6-PLACE | done (bonus — **second independent confirmation**) |
| **MTP serving arms** | **re-queued — still the one missing piece; no MTP claim will be made** |
| plain round 3 + threshold probe | running |

**★ THE GREEDY GATES SETTLE THE PROMOTION CHOICE INDEPENDENTLY OF SPEED.** `S` is byte-identical to base at
all three prompt lengths; **`V` and `W` diverge within 19–68 tokens.** For a ~2.3 ulp change that is *early* —
it is a real behavioural change on production-length output, not a theoretical one. Combined with W ≈ S on
speed, there is **no configuration in which shipping the vectorisation is worth it here**: it buys nothing
measurable and changes the output stream inside 20 tokens.
**⚠ Seven MTP arms lost to the `--fa 1` recipe defect** (see the PROD-1 note above) — an agent flag error, not
a code defect, and the second time this session that **instrumentation rather than kernel work** was the
failure. The fix is now applied ahead of the re-run: **dry-run the invocation against a nonexistent model**,
which parses through to model load or reports an invalid argument, and costs about a second.

**★★★ SYNC-15 COMPLETE 2026-09-07 — TWO GOs, ONE NO-GO, AND THE STACK MEASURED IN ITS OWN WINDOW.**
Branch `inf70/sync15` @ `56fe8ef0a`, not merged.

| lever | knob | **MTP served** (3 rounds, 60 paired) | plain | bit-identical | verdict |
|---|---|---|---|---|---|
| **V** vectorised Q8_K quantizer | `GGML_VEC_Q8K` | **+3.12%** CI[+2.50,+3.67], **57/60** | +4.39%, 20/20 | YES | **GO** |
| **Q** activation-quant grain split | `GGML_QSPLIT` | **+3.04%** CI[+2.64,+3.42], **58/60** | +6.95%, 20/20 | YES | **GO** |
| **S** solo predicate widened | `GGML_TINY_SOLO_ROWS` | −0.16% CI[−0.60,+0.27], 28/60 | −1.04%, 3/20 | YES | **NO-GO** |
| **V + Q (multi-row only), S off** | — | **+5.24%** CI[+4.82,+5.67], **59/60** | +4.87%, 20/20 | YES | **SHIP** |

**The stack figure is its OWN ABA window (`inf70-sync15-aba2`) — measured, not inferred.** α = 0.8209 / dpt
0.8961 in all 21 MTP arms.
**★ THE MECHANISM, and the brief's premise was wrong**: `hc_inject` is **not** thread starvation
(`thr_mean/thr_max = 0.92`). All 48 threads are busy **quantizing the SAME activation row**, because on x86
`quantize_row_q8_K` **is the scalar reference** (12.27 µs/row vs 2.18 for its SIMD `q8_2_x4` sibling) and D1's
batch-1 path **replicates it `nth` times**. New `GGML_IQK_PROF` instrumentation times the phase in situ:
**activation quantization was 3.93 ms of a 48.47 ms plain token (8.1%)**, and on the skinny nodes
**quantization is 6× the entire GEMM** (1.28 vs 0.21 ms/token). The brief's 1.83 ms resolves to 1.28
replicated-quant + 0.21 GEMM — **there was never idle capacity there.**
**S survives but is 4.5× smaller than the agent's own offline model predicted** — measured −79.6
barriers/trunk eval, not ~355, = 0.27% gross, under the noise floor. **It reported its model's failure rather
than only its output.**
**Bit-identity four ways**: unit test vs the reference (1,400 seeded rows, 7 input classes, poisoned buffers)
**0 mismatches** — and it **caught a real bug**, FMA contraction fusing the `iscale` multiply into
`nearest_int`'s magic add (4 bad rows/140×10240), so **`-ffp-contract=off` is load-bearing**. Greedy
256-token streams **5/5 sha256** per arm, plain + MTP. **384 + 72 ABA completions, zero divergence.** HYG-3
failure sets **byte-identical to the seeded control** once `LIGHTNING_INDEXER` churn is excluded.
**⚠ CONFIG DECISION THAT IS EASY TO GET WRONG: once V ships, `GGML_QSPLIT_MIN` must default ABOVE every
`ne00`** — Q's single-row branch buys a 3.1 µs barrier (+241/plain eval) that only pays at 12 µs/row, **not at
2**; its multi-row branch buys nothing extra and stays profitable.
**Caveat flagged rather than smoothed**: window 1's **plain** phase ran one round, sequential not alternating,
and its arms **do not reconcile** (+8.05% stack-with-S vs +4.87% adjacent-pair vs −1.04% S alone). **MTP
reconciles cleanly. Take +4.87% as the plain figure**; a 3-round alternating plain ABA would close it.
**Co-residency checked per arm**: window 1 had the GPU lane present **7/7 in every arm** (uniform, nothing to
exclude on); window 2's one asymmetry favoured the **control**, so it can only understate — **no round
dropped.** Consequence: **its champion arm reads 32.8 t/s against the 35.407 anchor** because CHAMP-1's window
had that GPU session stopped — **quote its ratios, never its absolutes.**
**★ FALSIFIABLE PREDICTION LEFT FOR THE REBUILD, at no extra arm cost**: CHAMP-2 and V+Q should be **partly,
not fully, additive** — CHAMP-2 makes `wdata` cheaper while V and Q make there be **less `wdata` traffic**
(Q at batch 1 cuts the footprint from `nth × row_size` to `row_size`). **If CHAMP-2's +1.0% holds
undiminished after V+Q, its win is mostly non-`wdata`.**

**→ CHAMPION-3 DISPATCHED 2026-09-07**: fold CHAMP-2 + V + Q into `inf70/champion2` off `6f032c48d`, S kept
inert at default 1, `VEC_SIGMOID` off, and **re-measure the headline claim-grade**. Per the standing rule the
new number is the deliverable, not arithmetic on the parts.

**★★★ CHAMP-2 — GO, BIT-IDENTICAL, FOLD IT IN. 2026-09-07.** Branch `inf70/champ2` @ `df0f37c62` (base
champion `6f032c48d`, build 10235). Committed, not pushed, not merged. Frozen tree untouched.

**★ THE COORDINATOR'S ATTRIBUTION WAS WRONG: the champion's knob was NOT missing the KV cache or compute
buffers.** Both are allocated by `ggml_backend_cpu_buffer_type_alloc_buffer()`
(`ggml/src/ggml-backend.cpp:2315`), whose body **is** `ggml_aligned_malloc(size)` — already madvised.
Measured per-VMA on the live 92 GB server, the residual is **the glibc brk heap**: **100% `[heap]`, 41 brk
VMAs, 0.0996 GiB AnonHugePages**, with all 99.7 GB of anon mmaps (weights + KV + compute) at **0**. That heap
holds **the CPU backend graph work buffer** (`new uint8_t[cplan.work_size]`, `ggml-cpu.cpp:177` — `wdata`,
**touched by every `mul_mat`/`mul_mat_id`**), llama.cpp's `std::vector` state, and server slot/JSON
allocations. `numa_maps` confirms at page level: THP heap VMAs sit at `maxfrac` **0.274–0.407**, and with the
shim **every heap VMA is at 0.250–0.255**. *The same table explains why the prize is small* — D6-PLACE's
penalised weight tensors were at `maxfrac` **0.97**; these 13–84 MB heap regions already average out.

**The change**: `common/common.cpp`, **+44 lines, one file** — an `__attribute__((constructor))` calling
`prctl(PR_SET_THP_DISABLE)`. It lives in `libllama-common`, **which only the tools link**, so no external
`libllama`/`libggml` embedder inherits it — the condition the brief set. You **cannot** madvise the brk heap
per-allocation without hooking malloc, so the process shim is genuinely the narrowest fix. Champion idiom
kept: `GGML_NOHUGEPAGE=0` master off, `GGML_NOHUGEPAGE_PROCESS=0` disables only the shim, so **every
comparison is same-binary**. Gate **mutation-tested 7/7** via `LD_PRELOAD` into `sleep`, zero inference,
before any timing.

| vs champion (26 arms, 3 lock windows) | plain | **MTP served** |
|---|---:|---:|
| paired per-prompt ratio | **1.0108** CI95 [1.0074, 1.0141] | **1.0100** CI95 [1.0061, 1.0141] |
| wins | **86/120**, sign p = 2.3e-6 | **71/100**, p = 3.2e-5 |
| round medians ≥ 1 | **6/6** | 3/5 (others 0.9995, 0.9999) |
| ms/token | 50.715 → 50.146 (−0.569) | 29.472 → **29.229 (−0.243)** |

**★ THE GAP CLOSES AS THE SAME ABSOLUTE QUANTITY**: D6-PLACE's knob-vs-shim residual was **0.225 ms/token**;
here it reproduces at **0.243 ms/token**. It reads as +0.83% rather than +0.90 pp only because the champion
base is faster. **Nothing measurable remains** — the shim arm shows **0** AnonHugePages process-wide.
**Two caveats the agent refused to bury.** (a) MTP **excludes round 3**, whose outlier arm was the only one
in 26 whose co-residency sampler saw the GPU lane in **7/7 samples vs 3/7** for its paired control —
**★ those `llama-bench` processes are pinned 184-191, the SMT SIBLINGS of physical cores 88-95, which are
INSIDE our 0-95 bench region. They are NOT disjoint from us, contrary to this campaign's earlier
conclusion.** *Including* r3 the MTP pooled ratio is **0.9903**. Plain needs no exclusion. (b) A single
cross-check on the champion's own binary **DISSENTS** — `M_V_champ` 36.5795 vs d6place's `thpoff` 36.4002,
shim **0.49% slower**, 2/20. n=1, NON-CLAIM, but an honest warning about effect size.
Host drifted **~7% between windows** (MTP C 36.1 → 32.5); all comparisons are within-round/within-window and
**no absolute headline is quoted.**
**Bit-identity**: 3 prompts at 41/109/240 tokens × 256 greedy, sha256 — champion = champ2-X = champ2-C,
**3/3 plain, 3/3 MTP**. 24-prompt harness `content_sha` **identical across all 26 arms** in both modes;
α 0.8209 / drafted-per-token 0.8961 in every MTP arm, **matching CHAMPION-1 to 4 dp**. Coherence 20+4 in all
26; placement within 0.1% in all 26. `test-backend-ops -b CPU` paired: identical `EXP`/`EXPM1`/`DIAG_MASK_INF`,
`LIGHTNING_INDEXER` 52 vs 50 churning across `type_K` — **pure HYG-3 signature, no new failure class**.
**Verdict: GO, fold it in, do not re-order the campaign for it** — a ~1% / 0.24 ms lever, not a champion-class
one. **Implied re-measure target 28.24 → ~28.00 ms/token is ARITHMETIC on the measured −0.243, NOT a claim:
re-measure inside the rebuilt champion.**

**★★★ B4 — GO, BUT AS AN ARTIFACT CHANGE, NOT A CHAMPION KERNEL LEVER. 2026-09-07.** Branch `inf70/b4r2` @
`a0907a8bc` = champion `6f032c48d` + B4's quantizer patch `49a1255` (**still required**:
`tensor_allows_quantization()` hard-excludes `ffn_gate_inp`, so stock `llama-quantize` **accepts the override
and silently ignores it**). Build 10236, committed, not pushed. Artifact `IQ4_XS-uniform-r16`,
98,267,083,136 B, SHA `f9aa401f…`. Disk 389 → 291 GB.

**★ WHY IT IS NOT A CHAMPION LEVER, and this is the right call**: **every champion lever is bit-identical;
this one is not.** Folding it in would **silently retire that property** — the thing that makes the champion
promotable on a digest match. The champion **kernel** stays bit-identical; the **artifact** is a separate
axis (see PROD-3).

**Both brief premises were pre-champion and both moved:**
- Re-census: the 48 `ffn_moe_logits` nodes cost **1,685 µs wall / 1,315 µs compute — ratio 1.28, not 2.00**;
  worst node **41 µs, not 1,118 µs**. **The champion already fixed the straggler.** The router is **6.04% of
  the bytes but only 3.88% of the wall** — *not bandwidth-bound.*
- **The coordinator's "~62.9 MB after quantising" was an arithmetic slip.** F16 saves **125,829,120 B/token =
  3.02%**, confirmed exactly in the artifact.

**Bytes vs wall, measured separately — and they diverge:** bytes −3.02%; wall **MTP +1.69% (−0.513
ms/token)**, **plain +0.63% (−0.315 ms, paired 95% CI [+0.22%, +1.01%], 15/20 wins, sign p = 0.021)**.
**A pure-bandwidth model predicts −1.53 ms; the machine returns ~20% of the byte saving**, and the node-level
census (−0.678 ms) predicts it far better. **MTP's paired CI straddles zero** — `P_A_r3` came in +3% over its
sibling arms, a real mid-window drift the agent **could not discard on hygiene grounds, so it stays in and
costs MTP its significance.**
**Quality gate — a null WITH a stated floor**: `Mean ln(PPL(Q)/PPL(base)) = +0.003763 ± 0.003697`, **t =
1.02σ, MDE 1.041% PPL**, resolved against a **37.5σ** mean KLD (0.046951 ± 0.001252) and **93.078 ± 0.251%
same-top-1**. **The stream changes; the quality does not.** **α RISES 0.8209 → 0.8227** (identical to 4 dp
across all 3 rounds of each arm) — **B9's α-collapse does not recur.**
**Tie-breaking is NOT the risk** (the coordinator's main worry): `ggml_argsort_top_k` → `std::sort` with a
strict `>` and no index tie-break *is* implementation-defined on a tie, but there were **0 exact F32 ties in
40.9 M adjacent-pair comparisons** and 0 at the k=8 boundary in 80,000 rows; the top-8/top-9 gap is
**200–370× the perturbation**, and F16 does not make ties likelier since logits stay F32 dot products over
2560 terms.
**★ THE FINDING WORTH KEEPING: the F32 router is 100.0000% exactly-BF16** — the converter upcast a BF16
tensor, so the container stores **16 bits of zero per weight**, and the F16 *weight* cast is **bit-exact for
99.97%**. The real precision cost is elsewhere: **ggml gives `GGML_TYPE_F16` `vec_dot_type = F16`, so the
lever also rounds the HIDDEN STATE to F16** — and *that*, not the weight, causes the 6.9% top-1 flips. It
also **kills Q8_0 on mechanism** (worse on both terms for +58.7 MB ≈ 0.06 ms); that probe was queued, sat 70
min behind a sibling, and was **cancelled cleanly** (own PID, verified dead), with `chain2.sh` left ready.

**⚠ B4's ABSOLUTE NUMBERS DO NOT REPRODUCE THE CHAMPION BASELINE — ratios usable, absolutes not.** Its A arm
reads **32.292 t/s MTP / 19.750 plain** against the champion's measured **35.407 / 21.638** — ~9% low on
both. Cross-day host drift is the likely cause, but it is unexplained. **Do not update the champion headline
from B4's arms**, and treat this as a live instance of the campaign's standing rule that absolute numbers are
only comparable within a harness and window.

- [x] **B4-b — CLOSED/REFUTED ✅ 2026-09-07 (there is no second B4; see the B4-b close block below). sweep EVERY artifact's F32 tensors for the same BF16-padding test.** Filed 2026-09-07. If the
      router was silently upcast from BF16, others may be too — **including the MTP head's untouched
      `blk.48.ffn_gate_inp`.** Each such tensor stores 16 bits of zero per weight and is a free F16 cast.
      Cheap, read-only, and it generalises past this model.

**★★★ B4-b CLOSED 2026-09-07 — THERE IS NO SECOND B4.** Scanned **1,869 F32 tensors across six GGUFs
(396 GB) in 2.2 s**: *every* one is BF16-derived — the converter upcast everything — with a single
exception, `ssm_a`, which is `-exp(A_log)` and therefore computed rather than converted. **The
confirmation is what kills the lever: B4 already took the only tensor large enough to matter.** Everything
else is blocked hard — `ssm_conv1d` trips `GGML_ASSERT(src1->nb[0] == sizeof(float))`, and the remainder are
1-D, which **B4's patch cannot reach by design** (its override loop sits below the `ggml_n_dims < 2` check).

**The MTP head's `blk.48.ffn_gate_inp` is 100.0000% padded exactly as predicted — and still does not pay.**
It saves **2.622 MB/token = 0.0625% end-to-end**, predicting **+0.035%**. The agent caught that the
flattering 1.702% figure uses the MTP head's *own* tensors as denominator while ignoring that the draft pass
must also drive the shared 675 MB output projection, and verified the shared file is the served one before
making the correction.

**★ ONE MECHANISM WORTH KEEPING FOR ANY FUTURE PADDING AUDIT: norms are stored as `1.0f + bf16_residual`.**
`hc_attn_norm` reads **26.6% BF16-exact in `v` but 100.0000% in `v − 1.0`**. Naively they look like
mixed-precision tensors and invite the wrong conclusion. **Any future padding audit must test `v − 1.0`
alongside `v`.**

Detector validated before use (injected 37.5% recovered as 37.5097%; random control 0.014%) and B4's
published 125.8 MB/token reproduced to the digit before its model was trusted.

**★★★ SYNC-14 CLOSED 2026-09-07 — IMBALANCE ON A MEMORY-BOUND MATMUL IS NOT RECOVERABLE CAPACITY. Axis
closed at ~0.** Branch `inf70/sync14` @ `f91c49a9e`, committed, not merged. Production untouched.

**Re-census on the champion**: MUL_MAT + MUL_MAT_ID imbalance is **2.86 ms/token MTP** (trunk 2.39 + draft
0.47) against SYNC-1's 4.83; plain **5.57** against 9.20. **It did NOT largely close** — as a share of the
token it went 10.0% → 8.7% (MTP) and **11.7% → 12.2% (plain)**. *The absolute drop is almost entirely the
token getting shorter around it.*
**The entanglement hypothesis is CONFIRMED AND QUANTIFIED**: toggling the champion's own placement lever back
off (`GGML_NOHUGEPAGE=0`, AnonHugePages 0.1 → 99.9 GB) restores the seam to **4.16 ms/token** and the trunk
eval to 127.9 ms, reproducing SYNC-1's era exactly. **Placement owns ~1.4 ms/token of this seam, and that is
the whole of the reduction.**
**Mechanism, from per-(node,thread) data — two components:** **static partition 0.51 ms/token** + **rate skew
1.88 ms/token** (trunk).
- **Static partition**: iqk's `nrc_x = ceil(U/nth); first_x = ith*nrc_x`. At the dominant expert shape
  (U=640, nth=48) threads 0–44 take 14 rows, thread 45 takes 10, and **threads 46 and 47 take NONE** — on 96
  `MUL_MAT_ID` nodes per token, visible directly in the 48-value dump.
- **★ RATE SKEW — SYNC-11's PER-CCX RESIDENCY HYPOTHESIS IS REFUTED.** Equal rows, up to **2.1× unequal
  time**, but **88–96% of the per-thread variance lies BETWEEN NUMA NODES and only 3–11% between the three
  32 MiB L3 CCXs inside a node.** It is reproducible across process restarts (Pearson **r = 0.79**;
  slowest-group agreement 56% vs 25% chance), its direction **varies per graph node**, and it **survives
  4 KiB interleaving with placement uniform to 0.1%**. **No named cause — that needs a PMU, not this
  profiler.**
**Lever built, bit-exact, and a MEASURED NULL.** `GGML_IQK_EVENSPLIT` (default OFF) replaces the ceiling with
`[U*ith/nth, U*(ith+1)/nth)` at all six sites. **It works structurally — starved (thread,node) pairs
249 → 12.** ABA ×3 on the 24-prompt production harness: **35.697 → 35.613 t/s, −0.24%**, against a **±1.2%
A/A control** whose win counts (18/20, 3/20) **track the round, not the lever**. Token stream bit-identical,
24/24 SHA matches every round; α 0.8209 and coherence unchanged; **the A arms reproduce the champion baseline
(35.70 vs 35.407).**
**★ THE CAMPAIGN CONCLUSION, AND IT RE-PRICES SYNC-1's WHOLE IMBALANCE COLUMN: `max − mean` on a matmul is
NOT recoverable capacity here — these nodes are MEMORY-BOUND, so handing two cores back buys nothing.**
Seam 2 goes from "~1.0–1.9 ms recoverable, LOW confidence" to **~0, axis closed.** By extension, the 10.66 ms
of MTP "imbalance" in SYNC-1's census should not be read as a lever pool without first asking whether each
node is compute- or memory-bound.

**★★★ SYNC-15 INTERIM 2026-09-07 — THE "4 OF 48 THREADS" MODEL IS REFUTED, AND THE REAL DEFECT IS A MISSING
SIMD KERNEL.** Levers committed at `56fe8ef0a`, all default OFF, `strings`-proven; measurement queued.

**Seam 1 — `hc_inject` is NOT thread starvation.** Read with the occupancy predicate, SYNC-1's own
per-`(node,thread)` table gives **`thr_mean/thr_max = 0.92`** on `MUL_MAT hc_inject [10240,4]` (15.11 / 16.48
µs, `thr_min` 13.84). **Every thread is busy.** What all 48 are doing is quantizing the **same** 10,240-element
activation row into private copies — D1's batch-1 fast path — and **on x86 `quantize_row_q8_K` IS THE SCALAR
REFERENCE IMPLEMENTATION**: measured standalone at **12.27 µs/row (1.20 ns/element)** against **2.18 µs
(0.21 ns)** for the SIMD `quantize_row_q8_2_x4` **one type away**. **IQ4_XS maps to Q8_K, so this model pays
the scalar path on every wide-reduction node.** In the MTP trunk it appears as `thr_min ≈ thr_mean ≈ 18 µs` —
the whole team parked in an intra-op barrier while two threads quantize.
*(The "4 of 48 threads" characterisation came from SYNC-2's report and was propagated by the coordinator into
SYNC-15's brief. It was wrong; the per-thread data always said otherwise.)*
**Seam 2 — `TINY_SOLO` widening is real but marginal.** Offline reconstruction, **validated by reproducing
SYNC-2's measured 915 elided barriers on plain decode exactly**: widening `nrows == 1` → `nrows <= 2` takes
the trunk from 89 to **444 elided barriers/eval**, i.e. **+355 × 3.14 µs = 1.11 ms/eval ≈ 0.35 ms/token ≈
1.2% gross**, before netting off serialization `ROWCOL_SPLIT` already avoids.

**Three levers built:**
- **`GGML_VEC_Q8K`** — AVX-512 `quantize_row_q8_K`, **bit-identical, 6.3× (12.27 → 1.96 µs)**.
  **★ `-ffp-contract=off` is LOAD-BEARING**: with contraction GCC fuses the `iscale` multiply into
  `nearest_int`'s magic-number add, **rounding once instead of twice** — 4 mismatching rows in 140×10240 with
  it on, **0 with it off.** Verified byte-identical against the library reference at 256/2560/6144/10240 over
  **1,400 seeded trials** including tie and all-zero classes.
- **`GGML_QSPLIT` / `GGML_QSPLIT_MIN`** — split activation quantization over the (row, block) space when
  rows < threads; **block-local for both Q8_K and Q8_2_X4, so bit-identical by construction.** The threshold
  applies only to the single-row case, where the split must buy back the barrier D1 avoids.
- **`GGML_TINY_SOLO_ROWS` / `_MAX`** — the widened solo predicate.

**★★★ SYNC-7 / SYNC-8 / SYNC-13 COMPLETE 2026-09-07 — zero compute. Three champion-relevant findings, one
invalidated result, two upstream bugs, and one of my premises inverted.**

**★ CHAMPION-RELEVANT #1 — `GGML_ROWCOL_SPLIT` DOES NOT REACH `SCALE`.** `scale_f32` does **not** route
through `get_rowcol_split`, so its **375 nodes/token stay thread-0-only EVEN UNDER `GGML_ROWCOL_SPLIT=1`.**
The census reading of SCALE was correct, and *stronger* than assumed — but it means a live gap remains in the
shipped champion. **Candidate for the next rebuild.**
**★ CHAMPION-RELEVANT #2 — `TINY_SOLO` whitelists `GGML_OP_CLAMP` on a FALSE PREMISE** (`ggml-cpu.c:2705`):
the justification is that thread 0 already owns the whole row, but `clamp_f32` strides **columns**
(`ops.cpp:6059`), so thread 0 owns **1/48**. Still bit-identical, but it **serialises parallel work.** Zero
CLAMP nodes in the qwen4exp census, so **no measured result is affected** — drop the case anyway.
**★ CHAMPION-RELEVANT #3 — `TINY_SOLO` and `ROWCOL_SPLIT` COLLIDE.** With `ROWCOL_SPLIT=1` the same
"thread 0 owns the row" premise fails for **the whole whitelist** in the **512–4096-element band, where both
levers claim the same node.** Both ship ON in the champion. **Audit before the next rebuild.**
**★ INVALIDATED: D8's +0.97%.** `ggml_get_rows_min_bytes()` is referenced at **exactly one line — the
planner** (`ggml-cpu.c:2872`), while the three kernels (`ops.cpp:5246/5290/5334`) unconditionally build
`ggml_get_rows_split_init(...)`. **Both arms ran the identical parallel kernel; the number is noise, and
"small gathers should stay single-task" is UNTESTED.** *(D8's real win is unaffected — SYNC-4 re-measured it
same-binary at +15.4%.)* Nothing else rested on an `n_tasks` reading; SYNC-2's TINY_SOLO argument rests on
`ggml_nrows(dst)==1`, not the planner.
**Classification (b) — planner says 1, kernel actually splits**: `SUB`, `SQR/SQRT/LOG/SIN/COS`, the **17
scalar `UNARY` cases (376 nodes/token)**, `MEAN`, `SET`, `CLAMP`, `SET_ROWS`. And
**`WIN_PART`/`WIN_UNPART`/`GET_REL_POS` ignore `ith`/`nth` outright — all 48 threads write the same
destination.** `ROPE` and `DIAG_MASK_INF` were a **false alarm**: both return `n_threads` and were never
capped.

**SYNC-8 — the rule is sharper than the brief's.** The governing condition is not "does the plan use
`n_tasks`" but **`n_tasks >= D`, where `D` is the count of threads that actually dereference `wdata`.**
Sweeping all 16 `n_tasks`-sized sites: **exactly one real hit.**
- **`SET_ROWS` — REAL.** Plan `4*ne00*1` vs kernel `wdata + (nc+CACHE_LINE_SIZE_F32)*ith` with
  `D = min(nr,nth)`; **`nr >= nth` overflows for any `nc`, and `nr=2, nc=1024` already does.** Reached on the
  F16-src → non-F16-dst branch — a **quantised KV cache written from F16**, so any prefill of N tokens gives
  `nr=N`. Not reachable from qwen4exp decode. **Fix is to size by `n_threads`, NOT to clamp `ith`** — clamping
  would drop rows that threads `ith>=1` genuinely own, **turning an overflow into wrong output.**
- **`SOFT_MAX` — FALSE POSITIVE**, provably in-bounds for every shape; the pointer is merely *formed* out of
  range on work-less threads. **`TOP_K` is safe with exactly zero slack** — it breaks first if the global pad
  ever goes.
- **NEW HIT — `MAP_CUSTOM1/2/3` and `CUSTOM`**: they honour the caller's `n_tasks` in the planner
  (`:2960-2993`) but pass `params->ith, params->nth` **verbatim** to the kernel (`ops.cpp:11819`, `:11862`).
  **A custom op registered `n_tasks=1` — the documented way to ask for serial — runs on all 48 threads.**
  Public-API contract violation. §2.6 of the report has ready-to-lift upstream issue text for all four.

**SYNC-13 — MY PREMISE WAS INVERTED, and the flag is disqualified for a different reason than I gave.**
Sites 1–5 are `disable_chunking = ggml_is_numa()`: **`false` gives fine chunks plus atomic stealing; `true`
gives STATIC one-chunk-per-thread.** So enabling NUMA would make those paths **MORE static, not less** — the
opposite of what I briefed. **And the residency claim is safe either way**: `iqk_mul_mat` partitions
statically as `first_x = ith*nrc_x` and there is **no reference to `ggml_is_numa()` anywhere under `iqk/`**,
so the 244 GB/s draft head is **structurally immune to the flag.**
**What actually disqualifies it is the AFFINITY family**: `set_numa_thread_affinity` (`:2553`, called per
worker at `:4052`) issues `pthread_setaffinity_np` that **overwrites the external `taskset`/`numactl` mask the
entire placement result rests on.** Plus the loader's `MADV_RANDOM`, which suppresses THP as a side effect —
the same end as `GGML_NOHUGEPAGE` but bundled with losing prefetch.
**Recommendation: keep it false, never pass `--numa`.** But **the chunker subset IS cleanly separable** — a
`GGML_STATIC_CHUNKS` knob at `ops.cpp:9501` (FA_EXT prefill) and `:11256` (GATED_DELTA_NET), **two lines, no
affinity, no loader change.** That is the single arm worth running if anyone wants it.

- [x] **SYNC-17 — COMPLETE ✅ 2026-09-07: three fixes built and measured as ONE combined lever vs
      champion-3. NO-GO on a CHAMPION-4 fold; headline NON-CLAIM. The collision is real and the
      champion was resolving it the RIGHT way by accident.** Branch `inf70/sync17` @ `10ff9be0d`;
      report `/mnt/raid0/llm/tmp/inf70/agents/sync17/REPORT.md`.
      **★ THE COLLISION ANSWER — `TINY_SOLO` wins UNCONDITIONALLY, and `ROWCOL_SPLIT` does not run
      at all in the 512–4096 band.** The contest is in the DISPATCH, not the kernels: the solo path
      (`ggml-cpu.c:4177`) re-dispatches with `sp.nth = 1`, so `get_rowcol_split` fails both its
      guards (`nth > 1`, `nr < nth`), returns `ncc = 1`, and degenerates to the identity.
      **~469 nodes/token in plain decode** (census: 426 ADD ne0=2560 + 42.6 MUL) get nothing from a
      lever adopted at +8.42%. **Invisible to speed measurement** — both levers ship ON and no arm
      ever existed where they disagreed; only reading the dispatch found it.
      **★ BUT FIXING IT COSTS −3.08% plain**, predicted to 0.05 pp by barrier count alone (468.6
      nodes × 3.14 µs / 48.46 ms). At 2560 elements a barrier-eliding solo run beats a 48-way split
      handing each thread 213 bytes. **The fix is to raise `GGML_ROWCOL_MIN_ELEMS`, not to flip the
      winner.** Bit-identity PASSED at production prompt length (6/6 full 256-token streams, plain
      + MTP, plus 20/20 per speed arm). Knobs, auditable via `strings`: `GGML_SCALE_SPLIT`,
      `GGML_SOLO_YIELD_ROWCOL`, `GGML_TINY_SOLO_CLAMP`.
      **★ CORRECTION to SYNC-7's premise:** of the "375 SCALE nodes/token thread-0-only", ~323 are
      below the 512 floor and correctly solo, 67 are zero-element and already elided; only **~6.3
      genuinely lose parallelism — but they carry ~20 MB/token on one thread of 48.**
      **FIX-2 is provably inert here (zero CLAMP nodes) but correct — ship it.** FIX-1 is untested
      in isolation, its value masked by bundling with FIX-3 → SYNC-19.
- [ ] **SYNC-19 — measure FIX-1 alone, unbundled from the −3% lever.**
      `GGML_SCALE_SPLIT=1 GGML_SOLO_YIELD_ROWCOL=0 GGML_TINY_SOLO_CLAMP=0` on
      `/mnt/raid0/llm/tmp/inf70/agents/sync17/bin-s17` — NO REBUILD, that binary carries every knob.
      Targets the ~6.3 SCALE nodes/token at 30 720 / 786 432 elements, which exceed
      `GGML_TINY_SOLO_MAX` and so are reachable WITHOUT FIX-3. If neutral-or-better, the CHAMPION-4
      candidate is FIX-1 + FIX-2 with FIX-3 shipped INERT (`GGML_SOLO_YIELD_ROWCOL` default 0).
- [ ] **SYNC-20 — sweep the yield floor.** `GGML_SOLO_YIELD_ROWCOL=1` ×
      `GGML_ROWCOL_MIN_ELEMS ∈ {4096, 16384, 65536}`: find where a column split starts to out-earn
      a barrier-eliding solo run. SYNC-17 proves 512 is far too low. Same binary, no rebuild.
- [ ] **METH-2 — register the A/A control as two A arms run BACK-TO-BACK.** SYNC-17's pre-registered
      G3/G4 compared NON-adjacent arms (A1 vs A3 ≈ 20 min, A1 vs C1 ≈ 45 min), which measure host
      DRIFT rather than measurement error and are guaranteed to blow out on a drifting host — they
      did, in BOTH directions in one session (MTP −4.9%, plain +11.3%), tracked by a lever-insensitive
      prefill probe. SYNC-17 applied the rule as written rather than revising it post-hoc, which is
      why its headline is NON-CLAIM. Adopt back-to-back A/A campaign-wide.
- [ ] **SYNC-18 — re-test "small gathers should stay single-task."** D8's +0.97% was measured with both arms
      running the identical parallel kernel, so the hypothesis is **untested**, not refuted. Cheap now that
      `GGML_GET_ROWS_MIN_BYTES` is known inert at the kernel.
- [x] **UP-2 — upstream the two ggml contract bugs**: the `SET_ROWS` `wdata` overflow (size by `n_threads`)
      and the `MAP_CUSTOM*`/`CUSTOM` `n_tasks` violation. Issue text ready in `sync7-8-13/REPORT.md` §2.6.
      **✅ COMPLETE 2026-09-07 — folded into the same UP-1/UP-2 pass.** Both contract bugs confirmed still
      present on upstream `master` @ `e71b805`: the `SET_ROWS` `wdata` overflow (planner sizes by `n_tasks`,
      fixed at 1, while the kernel splits over `n_threads`; ASan-confirmed by `repro_set_rows_overflow.c`) and
      `MAP_CUSTOM*`/`CUSTOM` ignoring the requested `n_tasks` (forwards in `ops.cpp` still pass `params->ith/nth`
      straight through; `repro_map_custom_ntasks.c` + `regression_check.c`). Presented as a defect class plus a
      fix — **no aliasing write-primitive or extraction path was written.** Not submitted; operator's call.

**★ CROSS-CAMPAIGN EXCHANGE WITH AUTOKERNEL 2026-09-07 — the leave-one-out gap is CONFIRMED and filed there
as R23-48.** Autokernel's own answer, verbatim in substance: *"no — autokernel never re-tests an accumulated
lever."* Each **new** keep is paired-A/B'd against the accumulated tip, so it is measured on top of everything
before it — **but a PRIOR keep is never re-measured after later keeps land**, and a grep of its loop for
leave-one-out / re-test / ablation returns nothing. Their fix: on every champion-of-record promotion, one arm
per accumulated keep with that keep reverted in a detached worktree, paired A/B at the calibrated floor; a
keep whose removal is neutral-or-better becomes a candidate drop, recorded as `retracted_by_loo` with both
sample vectors. **Cost is n_keeps arms per PROMOTION, not per iteration** — which is the right granularity and
is the shape we should adopt too.
**They already do "measure the stack" at the gate**, with one labelled exception worth knowing: their
accumulator's `compounded_bench_pct` (**+3.01% over 2 keeps**) **is** a product of solo deltas, used only to
decide *when* to fire the serving gate — **never as a claim** — and R23-48 pins that it stays labelled an
estimate on the dashboard. That is a defensible use of a product-of-solos, and a distinction this campaign did
not draw when it quoted one.
**Page-cache eviction is not in their loop** (VRAM-resident models, cheap reload) — nothing to win, and they
agree hot-server switching does not transfer for the same reason. So of the three items passed over: **one
real transfer, one already-covered, one N/A.**
**★ WHAT COMES BACK TO US: their "incremental build via the object-digest path makes each arm cheap."** Our
leave-one-out arms currently need a fresh build each — the champion's own leave-one-out cost a full rebuild
per lever. **An object-digest incremental build would make per-lever ablation cheap enough to run on every
champion rebuild rather than occasionally**, which is exactly what the standing champion-currency rule needs
to be affordable. Filed below.

**★★★ THE SAMPLER DEFECT IS MUCH WIDER THAN REPORTED — IT MISLABELLED THE ENTIRE SMT HALF (HARNESS-1,
2026-09-07, FIXED).** I reported it as "184-191 mislabelled as disjoint". Wrong scope: **the predicate tests
logical CPU ids against `<= 95`, so ALL of 96-191 was reported `disjoint-from-0-95`.** **Any agent that pinned
a background job anywhere on 96-191 and consulted the sampler was told the bench window was clean.**

**⚠ CONCRETE CONSEQUENCE FOR CHAMPION-3, and it is not hypothetical.** SYNC-16 ran `test-backend-ops`
**off-lock on cores 96-183** while `inf70-champion3-confirm` held the region. **96-183 are the SMT siblings of
physical cores 0-87 — inside CHAMPION-3's 0-95 bench region — and its sampler would have reported them
disjoint.** CHAMPION-3's **ratios survive**: every comparison is same-window paired, so contention common to
both arms cancels. Its **absolutes do not**, and it already flagged them as GPU-lane-depressed — the true
depression had **at least two sources, only one of which it could see.** This strengthens rather than weakens
its own instruction to **quote its ratios and never its absolutes.**
**The fix** (`tools/cpuoverlap.py`): **three-valued** — `DIRECT-OVERLAP` / `SMT-SIBLING-CONTENTION` /
`DISJOINT-FROM-BENCH-CORES`, where *disjoint* now means disjoint **in physical cores**. The sibling relation is
**read from `/sys/.../thread_siblings_list`, not assumed to be `+96`** — the agent's reasoning being that
**"an assumed offset would be the same class of error as the label it replaces."** Verified `cpu184
siblings=88,184`, `cpu191 siblings=95,191`. Six-case selftest **plus an end-to-end positive control**: it
started a process pinned to 184-191, sampled it live, and got `SMT-SIBLING-CONTENTION: 184-191 are the SMT
siblings of bench cores 88-95`. Control and sampler both confirmed dead with `ps -p`.
**Landed before any arm ran, so no arm in the HARNESS-1 campaign inherits the wrong label.**
**Two of its own bugs caught by a smoke test before any arm**: `grep -c` **exits 1 on zero matches**, so
`|| echo 0` emitted a second line and corrupted the summary arithmetic; and the cold sampler ran **in a
function subshell**, so the captured PID was the subshell — **the inner `bash` would have been orphaned to
append forever across 10+ arms.**
**Two structural consequences worth keeping**: the sampler is now **one shared implementation** used by both
`arm_cold.sh` and `arm_hot.sh`, **so they cannot drift the way champion1 → champion3 did** — which is how this
defect propagated in the first place. And **`arm_hot.sh` samples PER ARM, not per session**: the agent had
originally omitted the sampler from the hot script entirely, and with 10 arms inside one process that was a
real gap, since **knowing WHICH arm was contended is exactly what a hot session buys.**

# ★★★★★ CHAMPION-3 — THE CURRENT CHAMPION. `inf70/champion3` @ `9c4f73e29`, build 10241. 2026-09-07.

Committed, not pushed. Frozen tree untouched at `0db32c06e`.

| MTP served | value |
|---|---|
| **in-window (shipped binary, window 3)** | **33.370 t/s · 29.967 ms/token** — and **34.433 t/s · 29.042 ms** in window 1, same config via the hatch |
| **vs champion-1, paired same-window** | **1.0427 (+4.27%), 117/120 per-prompt wins** — **HARNESS-1 backward assessment 2026-09-07: NOT exposed** to eviction skew (every arm on both sides evicted in 0 s); independent recompute **+4.50%** |
| **vs pristine `c51e4dabf`** | **1.4993, 120/120 wins** — **HARNESS-1 2026-09-07: computed from the 0 s rounds only this is `1.5149`.** The multiplier we have been quoting is **understated**, not inflated |
| referred to the 35.407 anchor | ≈36.9 t/s · ≈27.1 ms — **A PROJECTION, NOT A MEASUREMENT. Quote the RATIOS (1.4993 / 1.5149) or the in-window `33.370 t/s`; never this absolute.** (WRAP-1) |

Plain: **20.589 t/s · 48.569 ms**, 1.0568 over champion-1, **1.7151** over pristine. **α = 0.8209 and
drafted/token 0.8961 in EVERY MTP arm of every binary**; coherence 20 COHERENT + 4 SHORT in **all 48 arms**.
**No round and no arm excluded anywhere.**

**★ CHAMP-2 WAS NOT SHIPPED, AND THE EVIDENCE IS STRONGER THAN THE HYPOTHESIS.** Two independent same-window
ABAs **disagree in sign** on the shim: window 1 says shim-off **+1.48%** (CI [1.0104, 1.0191], 48/60), window
3 says shim-off **−1.15%** (CI [0.9816, 0.9952], 25/60). **Pooled over 120 paired observations: +0.16%,
73/120 — zero.** So CHAMP-2's +1.0% does not merely shrink after V+Q, **it does not survive.**
**★ THE MECHANISM ARM IS THE CLEAN CONFIRMATION OF SYNC-15's FALSIFIABLE PREDICTION.** Same binary with
`GGML_VEC_Q8K=0 GGML_QSPLIT=0`, the shim the only difference: **+0.94%, CI [1.0043, 1.0149], 42/60** —
**CHAMP-2's original claim reproduced exactly, in a different agent's window.** **The shim's value scales with
`wdata` traffic; V and Q remove the traffic, and what remains is a TLB-reach cost that cancels it. CHAMP-2 was
never wrong — just not additive.** Code and evidence stay in the tree; polarity inverted so
`GGML_NOHUGEPAGE_PROCESS=1` now opts **in**.
**⚠ THE DISTINCTION THAT MATTERS: `GGML_NOHUGEPAGE` (the `ggml_aligned_malloc` madvise in `libggml-base`)
STAYS ON** — proven live, champion-3 runs at **AnonHugePages 0.057% against pristine's 99.888%**. Only the
process-wide `PR_SET_THP_DISABLE` in `libllama-common` went default-OFF. Conflating the two would discard
**86.4% of the champion**.

**Gates, and note how each was proven rather than asserted:**
- **`GGML_QSPLIT_MIN` = `INT64_MAX`** (multi-row branch only) — **verified in MACHINE CODE**: `movabs
  0x7fffffffffffffff` present in champion-3's `ggml_iqk_try_mul_mat`, **absent from champion-1's**.
- **`-ffp-contract=off` carried** — **0 FMA, 16 `vmulps` + 16 `vaddps`** in the AVX-512 quantizer. Default-ON
  proven by **timing the dispatch entry point**: 7.72× unset, 7.43× empty, **1.00× at `=0`**. 1200 adversarial
  row trials, 0 mismatches.
- **Bit-identity**: **16 arm-pairs, 5/5 sha256 identical over 689 tokens each**, plain and MTP; all-hatches-off
  reproduces pristine **in tokens AND throughput**.
- **`test-backend-ops -b CPU`**: comparable failure sets **identical** across pristine / champion-1 /
  champion-3 (7 signatures), churn confined to `LIGHTNING_INDEXER` (49/50/50), per HYG-3.

**Two things for the record:**
1. **Quote its RATIOS, never its absolutes.** The GPU lane was live throughout — champion-1 read 32.930 /
   32.115 against its own 35.407 anchor. **And the lane STOPPED mid-way through window 3's plain phase**
   (`R_P` 17/52 samples, `R_C1`/`R_C3` zero), so **those plain rounds straddle a contention change**; window
   1's plain arms are better conditioned.
2. **★ THE CO-RESIDENCY SAMPLER MISLABELS 184-191 AS "disjoint-from-0-95". They are SMT SIBLINGS of 88-95.**
   The label is inherited from `champion1/arm.sh` and is **wrong in every report that used it.** One-line fix,
   routed to HARNESS-1 so the new harness does not inherit it.

**★★ COORDINATION BUG FOUND 2026-09-07 (SYNC-16) — POLLING FOR A FREE LOCK IS NOT QUEUEING FOR IT, AND CAN
STARVE FOREVER.** Its first chain used a **30-second polling loop** to detect a free region. The holder
**released and immediately re-took the region under a new tag** (`champion3-confirm` → `champion3-mech`) —
a pattern a poller can starve behind **indefinitely**, because it only ever samples the gaps. **`region-lock
run` already blocks in a FAIR QUEUE by default (`--timeout-s 0`)**; the poller was killed and the work
re-queued properly. **Anyone writing a chain that waits for the bench region must queue, never poll** — and
this is not hypothetical, it happened while four agents contended for one region.
**★ THE HOT-SERVER MECHANISM IS FREE (HARNESS-1, measured off-lock)**: per-graph knob refresh costs **under
2 ns/graph** — 199.3 ns with the control page vs **201.2 ns without**, min of 7 on a tiny-graph loop that
isolates per-graph cost. **The sign is negative** because the refactor also replaced C++ guard-variable checks
with plain global loads in the per-node path. Against a ~99 ms token that is nothing, so **the design carries
no runtime cost to weigh against its benefit.** Proof table (all without bench time): the knob page reaches
`ggml_cpu_knobs_cur` in both env modes; refresh is **per-`graph_compute`, not per-process and not per-node**
(one refresh site, before dispatch); values are stable across graphs when unchanged; **an absent key reverts
to the ENV baseline, not a hardcoded default**; switching is reversible exactly; ADD checksum correct in all
six knob states.
**Disclosed perturbation, and the distinction it drew is worth adopting**: HARNESS-1 ran two microsecond-scale
unit tests on **core 2** during CHAMPION-3's hold — ~4 core-seconds of 96 — and **disclosed it rather than
letting the sampler surface it**. It explicitly **did not touch the page cache**, noting that is the shared
state which would actually corrupt an arm. **A few core-seconds perturbs a SAMPLER; page-cache state perturbs
a MEASUREMENT.** Relayed to CHAMPION-3 so it does not mis-exclude a round.

**★★★ SYNC-16 INTERIM 2026-09-07 — built at `inf70/sync16` @ `6d8592fb8`; measurement blocked on the lock.
It caught a real correctness bug in its own first version, before any measurement.**

**The lever**: `ggml_argsort_top_k` now records `k` in the ARGSORT node's `op_params[1]` as a **hint**; the CPU
kernel satisfies it with `std::partial_sort` over a **k+1** prefix plus a per-row tie guard falling back to the
full `std::sort`. Op contract, DESC ordering, the view, `n_tasks` and all other backends untouched.
`GGML_ARGSORT_K=1`, **default OFF**. `nth_element` avoided (unordered top-k would permute experts);
`ggml_top_k` avoided (its deliberate `swap(dst[0],dst[1])`).

**★ THE BUG IT CAUGHT IN ITSELF — a guard that claimed uniqueness while ties hid where it could not see.** The
first version sorted a **k-wide** prefix, but **`partial_sort` does not make `dst[k]` the (k+1)-th largest**,
so a tie against the k-th element **can hide anywhere in the 502-element tail** and the guard misses it. An
adversarial unit test found **2,363 of 200,000 tie-rich rows diverging from `std::sort` while the guard
claimed uniqueness.** With a **k+1** prefix: **0 divergences in 1.26 M rows** across six distributions from
continuous to all-tied, plus ASC edge shapes at k=1/10/511. **Bit-identity is now a contract, not an
observation** — and a spot-check would have shipped the broken version, since ties are rare in real data
(b4r2 measured 0 in 40.9 M pairs) and the defect only surfaces under adversarial construction.
**Activation proven three ways, not assumed**: `strings` shows the marker in `bin-s16` only; a real-graph probe
on the full 512-wide ARGSORT node shows knob-unset → full sort, knob-set → partial selection, and **champion
binary with the knob set → `op_params[1]=0, inert**; the k-prefix is identical in all three.
**★ THE OBJECT-DIGEST MACHINERY PAID FOR ITSELF WITHIN HOURS OF BEING LIFTED.** First identity attempt was
confounded — **two worktrees embed different paths, so all 291 objects differed.** Rebuilt both arms from the
**same directory**: exactly **2 of 291** differ (`ggml.c.o`, `ops.cpp.o`), 289 byte-identical. And separately,
**an index-vs-HEAD trap made one rebuild silently produce the BASE binary under the s16 name — caught only by
the object diff showing 0 differences.** That is precisely the class of error `.so` hashing cannot see.
**Mechanism sizing (off-lock microbenchmark)**: the champion arm **independently reproduces the in-situ
census** (20.3–20.9 µs/row here vs `thr_max` 19.33 µs/node in-model), and partial selection runs at **2.01
µs/row — 10.4×, above the 4–7× projection** — saving ~907 µs of the 928.5 µs ARGSORT budget. **Caps the
plain-token prize at ~1.8–2.0%.**
**All four `ggml_argsort_top_k` call sites audited**: every one consumes only the returned k-wide view, so the
hint is **safe tree-wide**, not merely for this router.
**Blocked on one named external event**: the bench lock, held by `inf70-champion3-confirm`. `test-backend-ops`
is running off-lock on cores 96-183; the bit-identity window and the claim-grade ABA (3 rounds × {champion,
sync16+knob}, MTP first, **plus a knob-off control on the sync16 binary to separate the knob from the
binary**) are queued. **No go/no-go — the measured delta is the deliverable and it does not exist yet.**

**★★ HARNESS-1 INTERIM 2026-09-07 — implementation complete at `inf70/harness1` @ `eae02f2dc`; measurement
queued.** Three things worth recording before its results land.

**★ ENV VARS CANNOT SWITCH A LIVE PROCESS — the hot-server design needed a different mechanism than I
specified.** A running process's `environ` cannot be rewritten from outside, so "read the knob once per
`graph_compute`" is necessary but **not sufficient**. It moved all compute-path knobs from first-use latches
to a **snapshot refreshed once per `ggml_graph_compute` on the calling thread**, fed by an **mmapped control
page (`GGML_KNOB_FILE`)** rather than the environment. `GGML_NOHUGEPAGE` and the THP shim untouched.
**★ CORRECTION TO MY BRIEF: `GGML_VEC_Q8K` and `GGML_QSPLIT` DO NOT EXIST at `6f032c48d`.** I named five
compute-path knobs and told it to base on the champion; two of them exist only on **CHAMPION-3's tip,
`9c4f73e29`** (build 10241). It branched from `6f032c48d`, then fast-forwarded to `9c4f73e29` with
`6f032c48d` still in ancestry — the right call, and it flagged rather than silently retargeting.
**★ THE FADVISE PREMISE IS PROVEN, with the right instrument**: `tools/pagecache` does an fadvise drop with
**`mincore`-based re-measurement**, and has already established that the **91.636 GiB GGUF is 100% resident,
measured in 1.4 s** — versus the 140 s the allocation-pressure path costs. Verified by page residency, **not
by the syscall's return**, as required.
**Object-digest work taken**: `object_digest`/`object_manifest`/`object_diff` lifted from `b808e2d6` into
`tools/objidentity.py`, with `post_build.sh` recording the object digest alongside the substitution record.
Its own exposure was the **sound** kind — `binaries.sha256` compares a copied binary against the same build's
output — and it had no rebuild-and-compare-`.so` check anywhere.
**★ AND IT IMPROVED THE ABLATION RECIPE**: `ablate.sh` mutates, builds incrementally, `object_diff`s against
the champion manifest, and checks the diff names **only the lever's TUs** — plus a new **`diffm` mode**,
because *"an ablation compares champion-state to mutated-state across TIME in one incremental build dir, not
two dirs."* Autokernel's `object_diff` compares two directories; ablation in a single incremental dir needs a
**temporal** comparison. That distinction is the agent's, not autokernel's or mine.

**★★ BINDING RULE FROM AUTOKERNEL 2026-09-07 — DIGEST THE OBJECTS, NEVER THE LINKED `.so`.** Measured on
this host: the **compiler is byte-reproducible** (**0 of 379 objects** ever differed across rebuilds) but the
**LINKER is not** — **one commit produced four distinct `libggml-hip.so` digests.** So build identity must be
asserted on **object files**.
**Our exposure, checked**: several INF-70 harnesses hash `.so` files. CHAMPION-1's *"`libggml-cpu.so.0.16.0`
sha matches the build tree's byte for byte"* **is sound** — it compares a copied binary against the same
build's output, a *substitution* check. **What is unsound is any "rebuild and confirm the `.so` still matches"
check**, which will false-fail on linker non-determinism alone. Relayed to HARNESS-1 as binding.
**Verified pointer**: `epyc-inference-research` @ **`b808e2d6`** (2026-09-06), *"Anchor guard: digest the
OBJECTS, not the linked .so — resolves the recurring keep aborts"*. Two dependency-free Python functions over
`pathlib`/`hashlib`, **liftable as-is** (read via `git show b808e2d6:<path>`; the shared checkout is behind):
`controller/anchor_integrity.py::object_digest(build_dir)` — sha256 over the sha256s of every **library** `.o`
under the CMake build dir (`tools/`/`examples/`/`tests/`/`pocs/` excluded via `_IDENTITY_EXCLUDE`) — plus
`object_diff()`, returning differing objects, one-side-only objects, and a **`linker_only`** flag; and
`loop/anchor.py::verify()`, whose scratch build is **incremental with no clean at start**, so a change
touching one TU recompiles one object and **arm cost becomes proportional to touched TUs, not to the tree.**

- [ ] **HARNESS-2 — object-digest incremental builds, so leave-one-out is cheap enough to run every time.**
      **Offered to HARNESS-1 as an optional third part** (it is already in the build/arm machinery, and two
      agents editing it concurrently is the larger risk); dispatch separately only if it declines.
      **Their recipe for our case, and the last clause is the part worth having**: `git revert --no-commit
      <lever>` in a detached worktree sharing the champion's build-dir layout, incremental build, then
      `object_diff` against the champion **tells you exactly which TUs the revert touched — and the sanity
      check is that it should be ONLY the lever's.** That turns an ablation arm into a self-verifying one.
      Filed 2026-09-07 from autokernel's R23-48 exchange. Our per-lever ablation currently needs a full rebuild
      per arm; autokernel reports an object-digest path that makes each arm cheap. **This is the enabler for
      the standing rule**: "fold in a validated lever and re-measure the champion" is only sustainable if
      leave-one-out on every accumulated lever is affordable at each rebuild — and leave-one-out is the ONLY
      thing that catches a lever gone sign-negative (measured: a lever at +1.0% in a 26-arm study read −1.39%
      in the stack it shipped in). Ask autokernel's owner for the mechanism rather than reinventing it.

**DISPATCH NOTE 2026-09-07 — the bench lock is the campaign's bottleneck, so the zero-compute queue was
opened in parallel.** CHAMPION-3 holds it and HARNESS-1 queues behind it; every remaining read-only item was
dispatched instead of waiting, since none can contend:
- **`b4b-sync16`**: B4-b (sweep every artifact's F32 tensors for exact-BF16 padding, ranked by **bytes/token**
  not tensor size, each carrying the caveat that `vec_dot_type = F16` rounds the **hidden state** so no
  candidate is free) + SYNC-16 (MoE `partial_sort`, starting from SYNC-14's measured "unreachable" rather than
  re-deriving it).
- **`sync7-8-13`**: SYNC-7 (classify every op as genuinely single-task at the KERNEL vs falsely believed so
  from the PLANNER — and re-check which INF-70 conclusions rested on the difference), SYNC-8 (sweep for the
  bug **shape**: any op that caps `n_tasks` *and* sizes `wdata` by it — upstream-reportable), SYNC-13
  (enumerate what `ggml_is_numa()` gates without flipping it, since `false` is load-bearing in our favour by
  accident).

- [ ] **HARNESS-1 — make the measurement harness 3–5× faster and tighten its noise floor.** Dispatched
      2026-09-07 from an operator question ("why load and reload the same model over and over?").
      **Measured: every arm costs ~370 s, of which ~170 s is SETUP** — `evict_nodes_force.sh` **140 s**
      (it allocates ~58 GiB **per node** to pressure page cache out), server start → health 30 s, actual
      measurement ~200 s. **Across a 41-arm window that is ~95 minutes of pure eviction.**
      **Part 1 — targeted eviction**: replace the allocation pressure with
      `posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED)` on the GGUF. **The eviction is LOAD-BEARING, not
      hygiene** — page-cache-full NUMA nodes silently defeat `--interleave=all`, and the current harness
      demonstrably delivers **23.04 / 23.05 / 23.04 / 23.04 GB** placement. The replacement must reproduce
      that, and must **prove the pages dropped via `mincore()` or the file's `Cached` contribution — NOT by
      the syscall's return**, since `DONTNEED` is advisory and only evicts clean pages.
      **Part 2 — hot-server arm switching**: compute-path knobs (`VEC_Q8K`, `QSPLIT`, `ROWCOL_SPLIT`,
      `TINY_SOLO`, `EMPTY_SKIP`) need no fresh process; only **allocation-time** ones (`NOHUGEPAGE`, the shim)
      do. Read them **once per `graph_compute`** — not cached at init, and **not per node**, since a knob
      changing mid-graph breaks barrier pairing (SYNC-12: matchers must be pure functions of the graph).
      **This is a BETTER experiment, not just a faster one: it removes load-to-load variance from the pairing,
      because arms are compared within one process instead of across two 92 GB loads.**
      **★ The deliverable is the A/A NOISE FLOOR, old harness vs new** — borrowing autokernel's discipline of
      deriving arm counts from a measured floor rather than a convention (its `n≥5` comes from a measured p95
      of 2.175% prefill / 3.452% decode at n=20 pairs). This campaign has repeatedly spent rounds it did not
      need and reported effects it could not resolve.
      **Note what autokernel does NOT do**: it does not hot-switch either — it beats noise with repetition.
      Its models sit in VRAM, so reload was never its bottleneck. This lever is specific to a 92 GB CPU model.
      **Failure mode to respect: if targeted eviction cannot reproduce even placement, keep the slow path.**
      A fast harness that measures the wrong thing would poison every result after it.
      **⏳ PARTIAL 2026-09-07 — the chain is STILL RUNNING; the BACKWARD ASSESSMENT is done and consequential.**
      Artifacts: `/mnt/raid0/llm/tmp/inf70/agents/harness1/` (`BACKWARD-ASSESSMENT.md`, `CONTENTION-FINDING.md`,
      `EVICTION-NOTE.md`, `SAMPLER-FIX.md`).
      - **The +4.27% headline is NOT exposed** — every arm on both sides evicted in **0 s**; independent
        recompute **+4.50%**.
      - **But `1.4993×` over pristine should be `1.5149×`** using only the 0 s rounds. **The champion
        multiplier we quote is UNDERSTATED, not inflated.**
      - **★ Phase R IS materially exposed**: `R_C1` averaged **125 s** of eviction against `R_C3`'s **74 s**,
        inflating `R_C3`'s **+8.60%** by an estimated **1–3 points**. Phase R must be re-derived (WRAP-9).
      - **★★ A METHOD TRAP WORTH MORE THAN THE ARM**: pooling all nine phase-R arms gives **r = +0.420** —
        **the OPPOSITE sign** to the within-arm relationship. **Simpson's paradox**: pristine runs slow with
        cheap evictions and champions run fast with expensive ones, so the pooled correlation inverts. Any
        future eviction-cost-vs-throughput read on this harness **must be computed WITHIN-ARM.**
      - It also produced the A/A contention quantification now folded into **MEAS-1** (peak, not median).

# ★ STANDING RULE — RECLAIM A NO-GO ARTIFACT AS SOON AS IT IS PROVEN (operator, 2026-09-07)

**Operator: "keep reclaiming space when artifacts are proven as NO-GO."** Do not accumulate multi-GB
artifacts behind closed investigations, and do not wait to be asked.

**The precondition, which is the whole safety of it: the REGENERATION RECIPE MUST BE IN GIT before the
artifact is deleted.** A tool sitting in `/mnt/raid0/llm/tmp/` is not a recipe, it is a coincidence — scratch
is exactly what a container cleanup removes. Verify with `git cat-file -s <ref>:<path>`, against the **branch**
rather than a possibly-lagging working tree.
**Applied 2026-09-07**: B12's two spliced 3 GB head artifacts plus their 665 MB of intermediates deleted
(**6.6 GB, 354 → 361 GB free**) — its verdict is NO-GO with the mechanism understood, and the finding *"a
private draft head is anti-cache regardless of quant, because it ADDS to the trunk's slab rather than
replacing it"* **binds the whole family**, so no successor needs them. Recipe verified present:
`scripts/inf70/gguf_swap_ple.py` on `origin/main` @ `34cf1022`, 6,679 B.
**Still retained deliberately, and why**: `IQ4_XS-uniform` (era anchor), `-gateup-r16` (Axis B artifact, **not
yet re-measured on the champion**), `-r16` (B4's GO), `UD-IQ4_XS` (the served file), `MTP/` (in the serving
config). None of these is a closed NO-GO.

# WRAP-1..WRAP-8 — derived actionables filed at the 2026-09-07 wrap-up sweep

Each of these was **stated as a conclusion in this session's own output and never converted to a task**.
They are filed here rather than described in prose so the dashboard can see them.

- [ ] **WRAP-1 — purge the two retracted framings from this handoff, the sibling reports and the wiki.**
      (a) **"the 2 MB THP boundary" does not exist** — D6-PLACE's 37-point sweep shows a smooth monotone
      ramp; the mechanism is THP raising `--interleave=all` granularity to 2 MiB. The phrase still stands in
      the D6-PLACE-ORIGINAL brief, in SYNC-2 §8 and in SYNC-10's backlog note. (b) **the ÷3 / ÷2.71
      plain→served haircut is not universal** — it is a property of *barrier-class* levers only; a bandwidth
      lever has nothing to amortise away (D6-PLACE measured served **above** plain). Seven occurrences
      remain in this file. The handoff already records both corrections in situ (`⚠ LANGUAGE CORRECTION
      REQUIRED ELSEWHERE`, `★ COROLLARY THAT SUPERSEDES THE ÷3 RULE`) — **this is the task that acts on
      them.** Anyone inheriting either phrasing hunts a step that is not there, or mis-scales a lever by ~2.7×.
- [ ] **WRAP-2 — re-price SYNC-5's fusion ceiling at 3.1 µs/barrier.** SYNC-5 closed "don't pursue the
      megakernel" on a barrier model **SYNC-2 later reversed**: `TINY_SOLO` elided 915 graph barriers while
      removing zero nodes and zero arithmetic, recovering **3.14 µs/barrier**, and `EMPTY_SKIP` recovered
      3.09 µs over a disjoint population. The session's own text says *"SYNC-5's fusion pricing should be
      redone at 3.1 µs/barrier rather than written off"* and it never became a task. Zero compute — an
      arithmetic re-price of an existing report against the champion's node/barrier census.
- [ ] **WRAP-3 — classify every node compute-bound vs memory-bound before any imbalance figure is treated as
      a lever pool.** SYNC-14's closing finding: `max − mean` on a *memory-bound* matmul is not recoverable
      capacity, so **SYNC-1's 10.66 ms MTP "imbalance" column cannot be read as available** until each node
      is classified. Until this exists, the ranked envelope's second-largest line is uninterpretable. Zero
      compute (the per-(node,thread) census already carries the inputs).
- [ ] **WRAP-4 — fix the co-residency sampler's "disjoint-from-0-95" label AND re-open every conclusion that
      rested on it.** Cores **184-191 are the SMT siblings of physical cores 88-95**, which are inside the
      0-95 bench region. The label is inherited from `champion1/arm.sh` and is wrong in **every report that
      used it** — including a contention escalation retracted on its authority. The relabel was routed to
      HARNESS-1; **the re-examination half has no owner.**
- [ ] **WRAP-5 — report the llama.cpp GGUF C reader segfault upstream (fold into UP-2).** B12 found
      llama.cpp's own C reader segfaults dumping these files — **on the pristine source too**, established
      only because it ran the control. A reproducible upstream crash with a control arm, filed nowhere.
- [ ] **WRAP-6 — give two cross-campaign rules a durable home outside this handoff.** (a) *"digest the
      OBJECTS, never the linked `.so`"* — the compiler is byte-reproducible on this host (0 of 379 objects
      differed) and **the linker is not** (one commit, four `libggml-hip.so` digests). The session calls this
      **binding** and it lives only in this handoff and a progress log. (b) *"queue, never poll"* for the
      bench region — `region-lock run` already blocks in a fair queue; a poller can starve **forever** behind
      a holder that releases and immediately re-takes under a new tag (observed, not hypothetical). Candidate
      homes: `agents/shared/MEASUREMENT_POLICY.md` (a), the region-lock/bus protocol docs (b).
- [ ] **WRAP-7 — re-measure the champion-3 headline in a GPU-quiet window.** In-window champion-3 reads
      **33.370 t/s / 29.967 ms**; the **≈36.9 t/s / ≈27.1 ms** figure referred to the 35.407 anchor is
      **labelled a projection, not a measurement**, and the GPU lane was live on 184-191 throughout its
      windows (see WRAP-4). The campaign's public headline should be a measurement. Ratios (+4.27% over
      champion-1, 1.4993× pristine) are unaffected and are what to quote until this lands.
- [ ] **WRAP-8 — `GGML_STATIC_CHUNKS`: the one separable arm SYNC-13 left on the table.** Two lines at
      `ops.cpp:9501` (FA_EXT prefill) and `:11256` (GATED_DELTA_NET), no affinity change, no loader change —
      the chunker subset of `ggml_is_numa()` without the affinity family that disqualifies `--numa`. Named in
      SYNC-13's result as *"the single arm worth running if anyone wants it"* and never filed. LOW priority.
- [ ] **WRAP-9 — re-derive phase R WITHIN-ARM, and restate the champion multiplier as `1.5149×`.**
      Filed 2026-09-07 from HARNESS-1's backward assessment. Two separate jobs: (a) `R_C3`'s `+8.60%` is
      inflated by ~1–3 points by an eviction imbalance (`R_C1` 125 s vs `R_C3` 74 s) and must be recomputed
      from comparable rounds; (b) the pristine multiplier computed on 0 s rounds only is **1.5149×**, not
      1.4993× — the champion table has been annotated but every downstream quotation still carries the old
      figure. **Do NOT pool arms when regressing eviction cost against throughput — the pooled sign inverts.**
- [ ] **WRAP-10 — land PROD-1's recipe module in `epyc-inference-research`.** Three new files
      (`scripts/lib/qwen38_flash_next_recipe.py`, `scripts/lib/test_qwen38_flash_next_recipe.py`,
      `scripts/benchmark/serve_qwen38_flash_next.sh`) plus **one line** adding the test to the Makefile's
      `PYTEST_SMOKE` list. Drafts are validated and 38/38 green but **PREPARED, NOT APPLIED**; they live in
      scratch (`/mnt/raid0/llm/tmp/inf70/agents/prod1/draft/`) and are lost with it. Land MEAS-2's
      `build_locked.sh` in the same pass so the two conventions arrive together.
- [ ] **WRAP-11 — decide the fate of the 21 branches carrying unique work.** `inf70/champion3` is pushed to
      the `fork` remote as **`experimental-inf70-champion3`**. Of 44 branches, **22 are fully contained in
      champion-3** and need no push; **21 carry unique work** and a push command for them is **pending with
      the operator**. Until it runs, that work exists only in local clones on this host.
- [ ] **WRAP-12 — correct the PROD-1 hybrid recipe and the build-10221 figure wherever they were propagated.**
      Two of PROD-1's three findings are record defects with reach beyond this file: the prose recipe claimed
      `-fa on` **and** `GGML_FA_SPLIT_KV=0` and the live `/proc/PID/environ` readback shows **neither** (a
      configuration nobody ever executed), and **`23.16 t/s` / `1.876×` is a build-10221 number quoted as a
      champion-3 number**. Sweep the handoff, the wiki and the progress record; the third finding (B12's
      PROD-1 dependency is discharged) is closed by this wrap-up.

**Explicitly declined at the 2026-09-07 operator wrap-up (decisions, not drops):**
- **Editing the 19 unlocked INF-70 scratch build scripts** — one-shot artifacts, mostly spent. The value is
  in the convention (`build_locked.sh`, MEAS-2) and in PROD-1 importing it, not in retrofitting dead scripts.
- **Purging the retracted "2 MB THP boundary" and ÷3 phrasings wholesale (WRAP-1)** — roughly half the
  remaining occurrences ARE the retraction text; deleting them would remove the correction and leave the
  record silent about a claim propagated fleet-wide. The three sites that still ASSERT the ÷3 framing now
  carry supersession pointers, and the ≈36.9 t/s row now names the ratios to quote instead. `wiki/`
  needs no purge: `wiki/hardware-optimization.md` §THP (2026-09-06) already quotes the phrase only to debunk
  it, and `wiki/` contains **zero** `36.9` and **zero** `÷3` INF-70 hits.
- **Rewriting the `progress/` occurrences** — the daily record is history, not a live claim surface. 21 of
  the 46 hits are there, including the retraction narrative itself. Left verbatim by design.
- **Pre-filing SYNC-19 / SYNC-20 outcomes** — dispatched and queued on the bench lock; an outcome must not be
  inferred from a dispatch.

**Explicitly declined at this sweep (decisions, not drops):**

- **SYNC-11** (48-value per-thread dump on `result_output`) — **not re-filed as new work; recommend closing
  it.** It existed to test the per-CCX residency hypothesis, and **SYNC-14 answered that question with a
  better instrument**: 88–96% of per-thread variance is *between NUMA nodes*, only 3–11% between the three
  L3 CCXs inside a node. The dump would now confirm a refuted hypothesis.
- **The `-fa` recipe sweep** — no action. The correction self-corrected the same day: only the *long* form
  `--fa 1` is invalid; `-fa 1` and `-fa on` are both valid, so `MEASUREMENT_POLICY.md` was correct and was
  not changed.

# ★ STANDING RULE — THE CHAMPION IS ALWAYS CURRENT (operator, 2026-09-07)

**Operator, verbatim:** *"always build on top of the latest champion and rebuild the champion when new
performance unlocks are achieved. It's what guarantees we always have the best kernel for our machine."*
And: *"as performance keys are unlocked, upgrade the champion and update the performance numbers. I don't
want to ask you about it. It should just be part of the results you report."*

**The loop, which is not optional and does not wait for a decision:**
1. **Every lever is based on the CURRENT champion**, never on pristine and never on the experimental tip.
   A brief that names an older base is stale and must be corrected before dispatch.
2. **Every lever is measured AGAINST the champion's current headline**, not against pristine. A delta over a
   superseded base is not a result.
3. **When a lever validates, it is folded into the champion immediately and the champion's headline is
   re-measured** — claim-grade, 24-prompt production harness, ABA ≥3 rounds, plain and MTP, leading with MTP.
4. **The new headline is reported as part of the result.** Not held for a decision, not reported as a delta
   awaiting integration.
5. **Promotion to PRODUCTION remains separately operator-gated** (PROD-2 deferred, CHAMP-1) — *champion*
   currency and *production* promotion are different things and must not be conflated.

**Why this rule exists, measured:** four validated bit-identical levers sat default-OFF on two branches and
were never measured together. Combining them was **super-additive (1.5017 predicted, 1.6934 measured)** and
the campaign spent a day quoting solo numbers that were wrong in both directions — `ROWCOL_SPLIT` understated
(+3.05% → +5.3%), `TINY_SOLO` and `EMPTY_SKIP` overstated (+3.86%/+0.87% → below the noise floor).
**A lever's value is a property of the kernel it is measured in. Re-measure, never re-scale.**

**CURRENT CHAMPION: `inf70/champion3` @ `9c4f73e29` (build 10241) — +4.27% over champion-1 (117/120 wins),
1.4993× over pristine, bit-identical. In-window 33.370 t/s; ~36.9 t/s referred to the 35.407 anchor is a
PROJECTION, not a measurement.** *(Superseded: `inf70/champion` @ `6f032c48d`, 35.407 t/s / 28.24 ms, 1.4834×.)*

# ★★★★★ THE CHAMPION KERNEL — `35.407 t/s` SERVED, `1.4834×`, BIT-IDENTICAL. 2026-09-06.

**Branch `inf70/champion` @ `6f032c48d`** (build **10234**), `/mnt/raid0/llm/worktrees/inf70/champion`.
`inf70/d6place` merged cleanly at `77b704e5d`. **Committed, not pushed.** Production `/mnt/raid0/llm/llama.cpp`
untouched at `0db32c06e`; no branch switched in a shared clone.

**Claim-grade ABA — 24-prompt production harness, 3 rounds, same-window alternating, 3 arms:**

| | pristine `c51e4dabf` | **CHAMPION** | ratio | wins |
|---|---:|---:|---:|---|
| **MTP served** | 23.870 t/s · 41.90 ms (sd 0.13, spread 1.22%) | **35.407 t/s · 28.24 ms** (sd 0.17, spread 1.14%) | **1.4834** | **60/60** |
| plain decode | 12.778 t/s · 78.26 ms | **21.638 t/s · 46.22 ms** | **1.6934** | **60/60** |
| prefill (MTP) | 137.8 pp t/s | 179.9 pp t/s | 1.305 | |

**What is ON by default**: `GGML_NOHUGEPAGE`, `GGML_ROWCOL_SPLIT`, `GGML_TINY_SOLO`, `GGML_EMPTY_SKIP`.
`GGML_VEC_SIGMOID` stays **OFF** (not bit-identical, +0.0 pp, upstream only). Idiom on all four:
**unset or empty = ON, explicit `0` = OFF** — and for `TINY_SOLO`/`EMPTY_SKIP` both the static initialiser
*and* the `ggml_cpu_init()` parse were flipped, so a process that never reaches init still gets champion
behaviour. Two `__attribute__((used))` markers make the defaults auditable with `strings`.

**CORRECTNESS — the combination is bit-identical, proven.** **1,457 greedy tokens, 7 of 7 comparisons
byte-identical**: 5 production prompts (59–329 prompt tokens) plus 3 engineered full-256-token streams at
41/109/240, sha256-compared across pristine / champion / champion-all-hatches-engaged, in **plain and MTP**.
Corroborated without hashes: **α = 0.8209 and drafted/token = 0.8961 in all 15 MTP arms of BOTH binaries**.
Coherence 20 COHERENT + 4 SHORT in all 28 arms.
**`test-backend-ops -b CPU`**: champion **16704/16762**, pristine **16704/16762**, same classes (the HYG-3 set).
`LIGHTNING_INDEXER` membership churns, so a **third pristine sweep was run as a seeded control**:
pristine-vs-pristine differs by **13 lines** (count moving 47→48) while pristine-vs-champion differs by
**14 lines** with the count unchanged — **the champion sits inside the instrument's own churn.**
**Escape hatches verified**: all four set to `0` lands on pristine (1.007× served, 1.009× plain) and THP
backing returns to **99.83% from 0.10%**, measured in every one of the 28 arms. Placement within 0.1% across
four nodes on every arm.

**★ SUPER-ADDITIVE, AND THE VALUE IS CONCENTRATED IN TWO LEVERS.** Product of the four individually measured
plain gains = **1.5017**; measured combination = **1.6934** (**×1.128 excess**). Served: 1.3933 predicted vs
**1.4834** measured. Leave-one-out (2 rounds, MTP), marginal contribution *in the presence of the other
three*:

| lever | marginal | ms/token | share of log-gain |
|---|---:|---:|---:|
| **`GGML_NOHUGEPAGE`** | **×1.4315 (+43.2%), 40/40 wins** | **11.89** | **86.4%** |
| **`GGML_ROWCOL_SPLIT`** | ×1.0532 (+5.3%), 40/40 wins | 1.47 | 12.5% |
| `GGML_TINY_SOLO` | ×1.0053 | 0.15 | 1.3% |
| `GGML_EMPTY_SKIP` | ×0.9992 | −0.02 | −0.2% |

**Two levers are 99% of the win.** `TINY_SOLO` and `EMPTY_SKIP` fall **below the 1.1% in-window noise floor
once placement is fixed** — their +3.86% / +0.87% were measured against a base whose small tensors sat on one
memory controller. **They stay ON (bit-identical, free, may matter at other shapes) but MUST NOT be quoted in
the headline.**
**★ COROLLARY THAT SUPERSEDES THE ÷3 RULE ENTIRELY: the plain→served haircut is a property of a lever IN A
GIVEN KERNEL, not of the lever.** `ROWCOL_SPLIT` measured +3.05% served alone and **+5.3% served here.**
A lever's value is not portable across kernels; re-measure, never re-scale.

- [ ] **CHAMP-1 — decide promotion.** `inf70/champion` is forked from `exp/cpu-fusion-qwen4exp-20260829`, **not
      the production tip**, so the four-step kernel workflow **starts over from fresh production**: pull fresh
      production → build → validate no regressions (GPU + CPU) → deploy as a NEW production version, full
      candidate benched as a whole. **Operator-gated** (PROD-2 is deferred).
- [x] **CHAMP-2 — RESOLVED ✅ 2026-09-07: measured GO (+1.0%) solo, then DID NOT SURVIVE in the champion-3 stack (pooled +0.16%, 73/120); shim shipped opt-in as `GGML_NOHUGEPAGE_PROCESS=1`. extend `MADV_NOHUGEPAGE` past `ggml_aligned_malloc` to KV/compute buffers.** d6place's
      whole-process shim still beats the knob by **+0.90 pp served**, and this is **the same lever class that
      just paid 86% of the result** — the highest-confidence remaining item on the board.

**★★★★ D6-PLACE MEASURED 2026-09-06 — `+35.21%` SERVED. THE LARGEST RESULT OF THE CAMPAIGN BY AN ORDER OF
MAGNITUDE, AND IT IS BIT-IDENTICAL.**

| | plain | **MTP served** |
|---|---:|---:|
| **`GGML_NOHUGEPAGE=1`** (in-tree knob) | **+32.21%** · 3/3 | **+35.21% ± 0.0205** · **15/15** |
| `thpoff` shim (zero-code) | +34.97% · 3/3 | +36.11% ± 0.0226 · 15/15 |

**Served 49.11 → 36.32 ms/token = 12.79 ms/token saved. Bit-identical in all 9 arm pairs.** Base spread
1.82%, so the effect is **~18× the spread**. THP verified per arm (99.8% → 0.1%); placement verified
24/24/24/24 GB. **The knob captures 97% of the shim's win** — ship the knob (one env var, default OFF,
CPU-only); extending `MADV_NOHUGEPAGE` to non-`ggml_aligned_malloc` buffers is a ~0.9 pp follow-up.

**★ THREE THINGS THAT CHANGE HOW THE WHOLE CAMPAIGN IS PRICED:**

1. **It is WHOLE-MODEL, not the 194 gemvs.** The agent's own pre-registered seam-only prediction (+2.9%
   served) was **low by 12×**, and it scored that miss explicitly: the microbenchmark established *what* was
   happening but was a poor instrument for *how much*.
2. **★ THE ÷2.71 PLAIN→SERVED HAIRCUT MUST NOT BE APPLIED HERE — served (+35.2%) EXCEEDS plain (+32.2%).**
   That calibration is a property of **barrier-class** levers, which MTP amortises over ~4.1 tokens/eval;
   **a bandwidth lever has nothing to amortise away.** Applying ÷2.71 would have understated this by ~2.7×.
   **The coordinator propagated the ÷3 rule to every agent as though it were universal. It is not — it is
   lever-class-dependent, and the class must be named before the correction is applied.**
3. **★ RE-PRICE EVERY OTHER INF-70 LEVER BEFORE MERGING ANY MORE.** They were all measured against a base
   **running at quarter memory bandwidth on its small tensors.** Their **absolute ms/token savings should
   survive; their PERCENTAGES are against the wrong base.** That includes the already-merged
   `GGML_ROWCOL_SPLIT` at "+3.05% served" — the 1.42 ms/token it saves is real, but the percentage was taken
   against a crippled denominator.

- [x] **PLACE-1 — DONE by CHAMPION-1 2026-09-06.** ✅ Knob merged (`77b704e5d`) and the merged levers re-priced on the corrected base via leave-one-out: `ROWCOL_SPLIT` +5.3% (not +3.05%), `TINY_SOLO` +0.5%, `EMPTY_SKIP` −0.1% — the last two now below the noise floor. **Original scope:** merge `GGML_NOHUGEPAGE` and re-price the merged levers against the corrected base.
      Filed 2026-09-06. Branch `inf70/d6place` @ `29a5857ac`, not merged. Two parts: (a) merge the knob —
      bit-identical, default OFF, 97% of the available win; (b) **re-measure `GGML_ROWCOL_SPLIT` and SYNC-2's
      `TINY_SOLO`/`EMPTY_SKIP` with `GGML_NOHUGEPAGE=1` as the base**, because their percentages are currently
      quoted against a memory-starved denominator and their interaction is unmeasured — a barrier lever and a
      bandwidth lever need not compose additively.

- [x] **D6-PLACE — ★★ THE "2 MB THP BOUNDARY" DOES NOT EXIST. The mechanism is real and BIGGER than the
      seam it came from. 2026-09-06.** Branch `inf70/d6place` @ `29a5857ac`, not merged, not pushed.
      **★ THERE IS NO STEP.** A 37-point ABA sweep (3 rounds, THP backing proven per arm at 100.0% vs 0.0%)
      shows effective bandwidth under THP is a **smooth monotone ramp** — 10 GB/s at 0.25 MB to 161 GB/s at
      64 MB, **no discontinuity anywhere.** Through the exact 1.84–2.25 MB gap SYNC-10 could not localise, the
      numbers run **36.2 → 35.6 → 38.3 → 38.7 GB/s: continuation, not a step.** Both prior agents'
      *magnitudes* reproduce (microbench predicts 34.8 GB/s at 1.75 MB; SYNC-2 measured 28.0–29.0, SYNC-10
      33–39) — **the measurements were right, the interpretation was wrong, and the interpretation was
      mine.**
      **★ THE MECHANISM, ESTABLISHED NOT INFERRED — it IS THP, but not promotion cost.** THP is `always` here
      and llama.cpp runs `--no-mmap`, so the weight buffer is anonymous and — measured on the real 92 GB
      process — **99.8% THP-backed. That raises `numactl --interleave=all` granularity from 4 KiB to 2 MiB, so
      a sub-2 MiB tensor is served by ONE memory controller.** Three confirmations: `move_pages(2)` gives
      `maxfrac` **1.00 at ≤2 MB decaying to 0.25 by 8 MB**, tracking the bandwidth ratio; fitted marginal
      bandwidth below 2.25 MB is **53 GB/s against one node's 57 GB/s share (R²=0.98)** versus **362 GB/s on
      4 KiB pages**; and the lever restores exactly **0.250** at every size. **Ruled out**: promotion cost,
      tensor shape, L3, first-touch, TLB (which runs the *other* way), and the agent's own
      per-thread-binding hypothesis.
      **★ TWO FINDINGS THAT CHANGE THE FRAMING — in opposite directions.** **4 KiB wins at EVERY size up to
      64 MB** (1.38× residual at 8–64 MB with placement already balanced), so **this is WHOLE-MODEL placement,
      not 194 small gemvs** — much larger scope than filed. But **at 1.75 MB placement recovers only ~14% of
      the gap to peak**, so the ceiling is well short of "small gemvs at peak".
      **Lever follows from the mechanism**: restore 4 KiB interleave. Implemented two ways, mutation-verified —
      `GGML_NOHUGEPAGE=1` (29 lines, default OFF, 99.8% → 0.0% → 99.8%) and a **zero-code
      `PR_SET_THP_DISABLE` shim**. **Bit-identity is structural**: `madvise`/`prctl` move pages, never
      contents.
      **⚠ SERVED PRICING NOT DELIVERED — NON-CLAIM.** MERGE-1 held all four regions continuously from when
      this window was ready; **the coordinator told D6-PLACE to yield to a window described as short, and it
      was not** (coordination error, mine). §4 is a **pre-registered prediction — ~+7.8% plain / ~+2.9% served
      from the gemv seam alone, possibly more whole-model — explicitly not a result.** The three-arm window
      (B/K/P × 3 rounds, plain + MTP, immutable binary snapshot, per-arm `numastat` / AnonHugePages /
      `content_sha`) is **queued as PID 2860235, tag `inf70-d6place-arms2`, and starts itself when the lock
      frees**; then `python3 analyze2.py`. It holds nothing while waiting.
      **Process note**: the agent **aborted its own first window** after rebuilding the shared library mid-run
      (mixed binaries, indefensible pairing) — all PIDs verified dead, lock released.

- [x] **MERGE-1 DONE 2026-09-06 — `exp/cpu-fusion-qwen4exp-20260829` advanced `c51e4dabf` → `13907877d`.** ✅
      Both merges real `--no-ff`, **neither conflicted**; fast-forwarded in place by the coordinator after
      verifying the tree clean and `c51e4dabf` an ancestor. **Production `/mnt/raid0/llm/llama.cpp` untouched
      at `0db32c06e`.** Nothing pushed to `origin`.
      **The duplicate split, resolved cleanly**: SYNC-10's `GGML_ROWCOL_SPLIT` ships; SYNC-2's
      `GGML_ELEM_COLSPLIT` is **reverted** (`1402d348b`) on a throwaway branch off `inf70/sync2` — **sync2's
      own branch is untouched so UP-1's history survives.** Removal proven **at the binary**
      (`strings … | grep -x GGML_ELEM_COLSPLIT` absent in both builds), not by reading the diff. One
      deliberate exception, documented in the revert message: `ggml_cpu_tiny_solo_max` stays at **4096** rather
      than reverting to 65536, because that cap's purpose — stopping `TINY_SOLO` swallowing large single-row
      nodes the column split wants — is unchanged; only the consumer's name changed.
      **`TINY_SOLO` / `EMPTY_SKIP` untouched**, their `nrows == 1` gate left as **known headroom, deliberately
      not widened** in a merge.
      **`086b5b9c9` (vec-sigmoid) carried with its knob default OFF** — reachable only via
      `getenv("GGML_VEC_SIGMOID")`, no CMake option, and a grep across orchestrator/research/scripts finds **no
      launcher or recipe setting it** (same for the other new knobs). Flagged must-not-enable in the merge
      message.
      **★ KNOBS-OFF BIT-IDENTITY PROVEN — the load-bearing check.** Three fresh builds (merged plain, merged
      `-DGGML_CPU_PROF`, pristine `c51e4dabf`); greedy 256-token streams at 40/90/200-token prompts give
      **identical sha256 at all three lengths** for base, merged-knobs-off **and**
      merged-`GGML_ROWCOL_SPLIT=1`. **The merge is inert until switched on, and the split is bit-identical when
      on.** Knobs proven present/absent by `strings`.
      **`test-backend-ops test -b CPU`: 1950/1950** across three knob states over every op family the merge
      touches. **Speed sanity**: MTP ABAB with `-fa on`, merged binary, knob toggled — **+2.86%** (per-prompt
      +2.35% to +3.63%, split wins all ten pairings). Reproduces ~+3%; a sanity check, not a claim.
      **★ PROFILER PATCH LANDED** as `13907877d` — **the D9 hook refused nothing across all three commits and
      no `D9-ack` was invented.** METH-1's blocked deliverable is now closed: three agents will not rebuild it
      a fourth time.
      **Process note**: the agent killed its own first lock window after ~25 min on measuring that the
      unfiltered single-threaded `test-backend-ops` was multi-hour, relaunched with `-j 12` and cheap checks
      first, and ran the final 20-second controls **outside** the lock at `nice -n 19` on 8 cores. All kills by
      captured PID, verified with `ps -p`.

- [x] **HYG-3 — PRE-EXISTING test failures in the fusion branch, NOT merge-induced.** Filed 2026-09-06 from
      MERGE-1. The unfiltered `test-backend-ops` sweep gives **16703/16762, rc=1**; the 59 failures are only
      `EXP`, `EXPM1`, `DIAG_MASK_INF`, `LIGHTNING_INDEXER`. A seeded control (`--suite-seed 42`) on the
      **pristine `c51e4dabf`** build versus merged in both knob states yields an **identical 62-case failure
      set in all three** — so this predates all INF-70 work on the branch. **Anyone running the unfiltered
      sweep will see rc=1 and must not read it as a regression.** Diagnose or document as accepted.
      **✅ COMPLETE 2026-09-07.** Full findings in the session record (`progress/2026-09/2026-09-07-inf70-audit.md`).

**⚠ LANGUAGE CORRECTION REQUIRED ELSEWHERE — "the 2 MB THP boundary" is wrong and I propagated it.**
SYNC-2 §8 and SYNC-10's backlog note both assert a boundary at 2 MB, as did this handoff and my reports.
**There is no threshold. There is a smooth ramp, and a granularity effect that makes sub-2 MiB tensors
single-controller.** Anyone inheriting the old phrasing will hunt a step that does not exist.

- [x] ✅ **D6-PLACE-ORIGINAL (superseded, retained for the record) — the largest remaining lever: ~9.1 ms/token at the 2 MB THP boundary.** Filed 2026-09-05,
      **placement hypothesis CONFIRMED by SYNC-2 on its own nodes**: the 194 hc rank-320 gemvs run at
      **29.0 GB/s against 109.1 GB/s for ≥2 MB weights**, and the rate **steps exactly at the 2 MB THP
      boundary** — `iq4_xs` at 1.741 MB → 28.0 GB/s, `q5_K` at 2.253 MB → 41.6. **Larger than all three
      SYNC-2 levers combined.** Next window goes here: D6's `MADV_NOHUGEPAGE` / 4 KB interleave, measured
      penalty-free for streaming. Interacts with **SYNC-13** (`ggml_is_numa()` is false, so iqk's static
      partition — not ggml's chunker — is what makes residency possible; do not disturb it blindly).

- [x] **SYNC-15 — COMPLETE ✅ 2026-09-07: premise refuted; `GGML_VEC_Q8K` + `GGML_QSPLIT` GO (+5.24% served as a stack), `TINY_SOLO_ROWS` NO-GO. `hc_inject` `MUL_MAT [10240,4]` moves 21,760 bytes in 19.0 µs = 1.1 GB/s, 1.83 ms/token**,
      because **only 4 of 48 threads get a row**. Filed 2026-09-05 from SYNC-2, unclaimed. Same defect family
      as the row-split (degenerate row partition at batch 1) but a different shape — 4 rows, not 1 — so
      `ELEM_COLSPLIT` does not cover it.

- [ ] **SYNC-2 — the tiny-op barrier tax** (~4.34 ms, 1,631 nodes). Dispatched 2026-09-05. Confirm from
      `ggml_get_n_tasks` that a 32 µs SCALE is really handed to 48 threads. Levers, cheapest first: cap
      `n_tasks` below a work threshold; fuse trivial chains; last resort the barrier primitive itself.
      **Correctness is the risk, not speed** — bit-identical output required.
- [x] **SYNC-3 — NO-GO 2026-09-05. The seam had already closed; the subsystem is 3.8% of the token.** ✅
      **★ THE CENSUS IS WRONG BY 26%, MEASURED ON THE ACTUAL BASE.** Re-censused at `c51e4dabf`
      (`agents/sync3/results-run1/pernode-off.tsv`):

      | | my brief | **measured on base** |
      |---|---|---|
      | graph wall / token | 96.267 ms | **76.371 ms** |
      | `GATED_DELTA_NET` wall / dead | 2.999 / 2.214 (73.8%) | **0.510 / 0.071 (14.0%)** |
      | `CPY new_state→cache_s_l*` (36) | part of 2.208 dead | **0.171 wall / 0.050 compute** |
      | `GET_ROWS` state read | 8.4 ms | **2.068 ms** |

      The brief's "~4.4 ms dead in the two worst ops" is **0.19 ms** here. Note three different token figures
      have now circulated (96.3 / 84.2 / 76.4) — **only a measurement on your own base is safe.**
      **★ THE LOAD-BEARING FINDING — THE RECURRENT STATE IS CACHE-RESIDENT, so the byte ledger is moot.** The
      state is moved three times (**678 MB/token**) in 2.922 ms = an effective **234 GB/s, 1.5× the 152.6 GB/s
      DRAM ceiling**; individual 3.0 MiB `CPY` nodes run at **~1.2 TB/s aggregate**. The 113 MB state lives in
      cache across tokens. **B11's "226 MB/token omitted from the ledger" is arithmetically true and
      economically irrelevant** — and this is the THIRD cache-residency finding today (draft head 260 GB/s,
      GDN state 234 GB/s, PLE table 1.44 KB/token). **A byte ledger is systematically wrong on this box for
      anything re-read per token that fits in 384 MiB of L3.**
      **Mechanism, named from `ops.cpp:ggml_compute_forward_gated_delta_net_f32`**: not single-tasked and not
      serialized on state — `nr = H × n_seqs = 48` against `nth = 48`, so **exactly one head per thread,
      `dr = 1`, work-stealing never steals, and the wall is the max of 48 tiles with zero slack.** Plus a
      **redundant second 48-way barrier inside the op**, provably unnecessary when `nchunk ≤ nth`. Confirms
      SYNC-5: the recurrence forces no barriers at batch-1.
      **Is the state CPY required? NO — and this tree's CUDA backend already fuses it away**
      (`ggml_cuda_try_gdn_cache_fusion`) but bails at `if (K <= 1) return 0;`, covering only the K>1 rollback
      path. **CPU decode runs K == 1, where it is fused on no backend.**
      **Result**: `GGML_GDN_STATE_DIRECT` (cache slot as GDN `src[6]`, CPY node never built) +
      `GGML_GDN_NO_INNER_BARRIER`, both default OFF, both `strings`-verified in the right libs before any
      result was read. Per-node **2.922 → 2.615 ms = −0.307 ms, −0.40% of the token**. ABA (tg128 r3, evict
      per arm, one lock session): base 12.77/13.11/12.89, both 12.87/13.04/13.05 → **+0.49% mean, 2/3 wins,
      while the three BASE arms alone span 2.6%. NON-CLAIM.**
      **Bit-identity: all EIGHT streams byte-identical** — 288 greedy tokens, prompts ~40/90/200, arms base /
      both / direct-only / nobar-only. Knob proven to fire (0 `copy of new_state-*` nodes on vs 36 off). QSA
      layers untouched. `test-backend-ops -b CPU` 38/38 at 4 and 48 threads.
      **⚠ IF EVER MERGED**: `src[6]` is CPU-only; CUDA/Metal/SYCL would ignore it and **silently skip the
      state write-back**. Needs `GGML_ASSERT(dst->src[6] == nullptr)` in those three entry points, or better,
      reshape as a backend-local `ggml_cpu_try_fuse_ops` fusion mirroring the CUDA one. Branch `inf70/sync3` @
      `00d79415a`, **not merged**.
      **Amdahl: this subsystem is CLOSED.** Perfect elimination of every copy leaves ~3.2% of the token, and
      the traffic is cache-served, so even that is optimistic.

- [x] **SYNC-9 — DONE ✅ 2026-09-07: implemented by SYNC-12 (nine lines, bit-identical, `skip_barrier` load-bearing), shipped as `GGML_EMPTY_SKIP` in the champion. 72 zero-sized `build_rs` nodes cost 0.173 ms/token for ZERO work** (98.8% dead, pure
      barrier). `ggml_nelements(dst) == 0`, so a skip in the node loop removes them; a node producing no
      elements cannot affect output, so there is no correctness surface. Same magnitude as the entire
      write-side state copy SYNC-3 eliminated, for a one-line guard. **Routed to SYNC-2** — it is the purest
      co-arrival case in the graph.

**⚠ METHODOLOGICAL CORRECTION — dead% IS NOT A TARGET.** SYNC-3 removed a redundant internal barrier and the
op's **dead% rose 14.0% → 38.3% while its wall FELL 0.510 → 0.373 ms**: the fix moved thread-0's wait out of
`compute` and into `wall − compute`. **Judge every change on WALL TIME; use dead% only to locate candidates.**
This axis was opened on a dead%-ranked table, so the ranking was a search heuristic, never a value estimate.

- [ ] **SYNC-3 — the GDN path** (GATED_DELTA_NET 73.8% dead + `cache_s_l*` CPY 60.5% dead, ~4.4 ms).
      Dispatched 2026-09-05. Name the mechanism from code. Is the recurrent-state copy structurally required,
      or a defensive copy that could be an in-place update or buffer rotation? **State is carried across
      tokens, so correctness must be gated over ≥256-token generations** — an error may not appear on token 1.
- [x] **SYNC-4 — CLOSED 2026-09-05. The premise was STALE: GET_ROWS was already parallelised at D8.** ✅
      **★ THE CENSUS I BRIEFED FOUR AGENTS FROM IS OFF THE BASE'S HISTORY.**
      `agents/prof/results-20260902T135356Z/` was taken on branch `inf70/prof` @ `8b578bc57`, which
      `git merge-base --is-ancestor` proves is **NOT an ancestor** of `exp/cpu-fusion-qwen4exp-20260829`; the
      base already carries `bc2834a9b` (D8, 2026-09-02 15:55Z — two hours AFTER that profile at 13:53Z).
      **Every per-op ranking taken from it is pre-D8**: GET_ROWS **−7.40**, CPY **−1.31**, CONT **−1.07**,
      GATED_DELTA_NET **−0.28** ms/token. D8 alone is the whole 95.9 → **84.2 ms/token** step. Upstream has no
      fix to adopt — its newest ref (2026-07-04) still carries the `n_tasks = 1` FIXME and a row-only split.
      **★ THE REAL DEFECT SYNC-4 FOUND AND FIXED: `ggml_get_n_tasks()` IS ADVISORY ON THIS BACKEND.**
      `ggml_graph_compute_thread()` sets `params.nth = n_graph & N_THREADS_MASK` for **every** node, so
      `n_tasks` only sizes the work buffer and never reaches the kernel. The `n_tasks = 1` branch and
      `GGML_GET_ROWS_MIN_BYTES` were dead code — **which is why D8's own A/B ran parallel on BOTH arms and read
      just +0.97%, and why `test-backend-ops -o GET_ROWS` could only ever exercise one path.** Corollary with
      campaign-wide reach: **SET_ROWS, SCALE, ROPE and DIAG are NOT serialised at runtime** despite their
      source saying `n_tasks = 1`. Any lever expressed as a `n_tasks` change is a **vacuous null**.
      `inf70/sync4` @ `eeecb3745` moves the threshold into `ggml_get_rows_split_init()`; default 0 = today's
      behaviour, so it is a **no-op unless the knob is set**.
      **★ FIRST GENUINE SAME-BINARY VERIFICATION OF THE D8 WIN** (D8x could only compare different binaries):

      | arm | knob | tg128 | ms/tok | GB/s (÷153) |
      |---|---|---:|---:|---:|
      | A1 | parallel | **12.78 ±0.36** | 78.2 | 53.1 (34.7%) |
      | B1 | serial | 11.01 ±0.08 | 90.8 | 45.8 (29.9%) |
      | A2 | parallel | **12.78 ±0.05** | 78.2 | 53.1 (34.7%) |
      | B2 | serial | 11.14 ±0.03 | 89.8 | 46.3 (30.3%) |

      **+15.4%, per-round 1.161 / 1.147, 2/2 rounds** — ~11× the 1.1% in-window repeat. Placement 23.52 GB × 4
      every arm, THP 99.9%. On the 36 hot nodes: **13.9 → 85.1 GB/s**. Gates: `test-backend-ops` 111/111 on
      both paths (serial reachable for the FIRST time), mutation evidence that the knob bites, and 3 prompts of
      41/141/237 tokens × 255 greedy steps **all sha256-identical** — which IS the recurrent-state gate, since
      the hot nodes are the GDN state reads.
      **Byte breakdown, which reframes SYNC-3's seam**: 93% of the old 8.86 ms was **36 nodes each gathering
      ONE row of 786,432 f32 = 3.145 MB → 113 MB/token of GDN recurrent state**. `nr = 1`, so row-sharding was
      structurally impossible; the win came from splitting *within* a row. The PLE gather is **8.4 µs** — a
      rounding error, as B11 predicted. Residual GET_ROWS: 1.46 ms compute / 2.60 ms wall, the 1.15 ms gap
      being barrier (SYNC-2's seam). `MIN_BYTES=65536` deliberately not measured: the 91 small gathers carry
      16.9 µs/token, not worth a lock turn.
      Evidence: `/mnt/raid0/llm/tmp/inf70/agents/sync4/REPORT.md`.

**★★★ THE TIP CENSUS LANDED 2026-09-05 (SYNC-1) — AND IT REFUTES THE CONGESTION MODEL, RESTATES THE BUDGET,
AND DEFLATES THE WHOLE AXIS. Read this before any other number on this page.**

**(a) The congestion/arrival model is REFUTED.** It predicted the barrier residual would collapse after
heavy staggered nodes. It does not: **MUL_MAT's residual is 2.25 µs/node, statistically level with SCALE's
2.44 and ADD's 2.39.** The toll is paid roughly **uniformly** — 12.00 ms / 4,409 barriers = **2.72 µs**,
right on the 2.16/2.48 µs primitives. *(The model was the coordinator's, propagated into this handoff, the
wiki and four sibling briefs. It is dead. **D1's null therefore still wants an explanation.**)*

**(b) "23.4% dead" UNDERSTATES COORDINATION BY ABOUT HALF — it is a THREAD-0 artefact.** Thread 0 does
**57.6 ms** where the mean thread does **46.9 ms**, because it is the one thread that works on every
single-task node. Tip 10221, plain, `-t 48`, 128 evals, placement 23.9 GB × 4:

| | ms/token | % |
|---|---:|---:|
| mean-thread compute (useful work) | 46.87 | 59.4 |
| **IMBALANCE** (Σ per-node max−mean over 48 threads) | **20.00** | **25.4** |
| **BARRIER + dispatch** (Σ wall − max) | **12.00** | **15.2** |
| total wall | 78.87 | |

**True coordination at tip is 32.0 ms of 78.9 = 40.6%, not 23.4%.** Every dead-time figure this campaign has
quoted — including the table Axis S was opened on — is a thread-0 measurement.
**Caveat that must travel with the split**: `thr_max` absorbs *intra-op* barrier waits, so the
imbalance/barrier division is exact only for ops with no internal barrier. For **MUL_MAT, MUL_MAT_ID, GDN and
FLASH_ATTN_EXT** it blurs (MUL_MAT even shows a small negative residual). **The 32.0 ms total is robust; its
two halves are approximate for those four ops.**

**(c) ★ THE ÷3 RULE — THE MTP CONFIG WE ACTUALLY SERVE HAS A DIFFERENT PROFILE, AND IT PRICES AXIS S DOWN.**
⚠ **SUPERSEDED AS A GENERAL RULE** by **★ COROLLARY THAT SUPERSEDES THE ÷3 RULE ENTIRELY** — the plain→served
haircut belongs to a lever IN A GIVEN KERNEL, not to the lever. `ROWCOL_SPLIT` measured **+3.05% served alone
and +5.3% served in champion-3**. The profile below still holds for THIS config; it must not be applied as a
universal divisor. (WRAP-1)
Graph shapes: 508 draft evals @144 nodes, 119 trunk evals @7,481, for 384 tokens = **3.23 tokens per trunk
eval**, 4.27 draft evals per trunk eval.

| per token | plain | **MTP (settled config)** |
|---|---:|---:|
| wall | 78.87 ms | **48.03 ms** |
| imbalance | 20.00 | **10.66** |
| barrier + dispatch | **12.00** | **3.89** |
| coordination total | 40.6% | **30.3%** |

**The barrier toll is 3.1× smaller in serving** — the trunk graph amortises its 4,400 barriers over 3.23
tokens and the 144-node draft graph is nearly barrier-free (0.315 ms). **EVERY barrier-elision estimate in
this campaign must be divided by ~3 before being priced as serving value**: SYNC-2's ~4.3 ms → **~1.4 ms**;
SYNC-5's ~11 ms ceiling → **~3.5 ms**; the D2(i) 579-barrier candidate likewise. **This may end Axis S on
economics alone.**

**(d) D1's arms are STALE — confirmed by `strings`, not mtime** (`GGML_FA_SPLIT_KV=0 GGML_ROWEXACT_N=0
GGML_IQK_DEQUANT=0 GGML_MMID_SLAB=0 GGML_GET_ROWS_MIN_BYTES=0`; `git merge-base --is-ancestor 99425578d` =
NO for both `1ba448e74` and `c035bbf3d`; both also predate D8 and b3k, decoding at ~96 ms vs tip's 77).
**Deliberately NOT rebuilt, and the reasoning is the important part: rebuilding would mean RE-INSERTING a
barrier that b3k has since rewritten around — a new code change on the critical path, not a re-measure.**
Both arms share every defect and differ by exactly the barrier commit, so the A/B stays **internally valid**;
only the absolutes are non-comparable to tip. D1 is now **corroboration, not the decider** — the in-situ
per-(node,thread) census measures the same quantity at tip with ~4,400 observations per token.

**★★★ SYNC-1 COMPLETE 2026-09-05 — THE GAP WAS NEVER A GAP, AND THE AXIS HAS A RANKED ENVELOPE.**

**(a) THE D1 PUZZLE DISSOLVES: TWO DISJOINT BARRIER POPULATIONS.** Counted separately in
`agents/prof/.../census.txt`:

| population | count/token | in the 12.00 ms residual? |
|---|---:|---|
| **graph** barriers — one per executed node | **4,409** | **yes, all of it** |
| **internal** — inside `mul_mat` (797), `mul_mat_id` (144), GDN (36), FA (24) | **1,001** | **no** |

**D1 removed 940 of the INTERNAL ones** — its own report says "940 sync events", and 797 + 144 = 941 is
exactly the `mul_mat` + `mul_mat_id` internal population. A thread waiting at an internal barrier is still
inside its own `ggml_compute_forward`, so that wait lands in `thr_max` — **inside compute, not in the
residual.** Disjoint domains. **The 2.72 µs was never a prediction about what D1 removed; D1's null means
only that INTERNAL barriers are cheap.** No congestion story survives, and none is needed.
**(b) THE COORDINATOR'S DISPATCH MECHANISM IS RULED OUT — right conclusion, wrong reason.** There is **no
per-node dispatch** in ggml's OpenMP path: the whole graph runs inside a single `#pragma omp parallel`
(`ggml-cpu.c:4357`) and each thread walks the node loop itself, so per-node non-barrier overhead is loop
bookkeeping — tens of ns. Decisive evidence: **SCALE nodes, where 47 of 48 threads have literally zero work
to distribute, still pay the full 2.44 µs residual.** The 2.72 µs is the barrier, essentially all of it.
**But the conclusion stands and is now an IDENTITY, not a model**: there is exactly **one graph barrier per
executed node**, so graph-barrier count **≡ node count** — **you cannot remove a graph barrier without
removing a node.** Re-pricing the axis on node count is correct *by construction*.
**(c) OUTLIER: ARTEFACT, CONFIRMED.** `spikes = 1`, `wall_max` 9,300–49,163 µs at a **single eval index**,
and **different nodes every run** — whichever node is executing when a host stall lands, divided by the eval
count. **~0 ms recoverable.** The pre-registered discriminator returned the pre-registered answer.
**(d) BARRIER COST, FOUR INSTRUMENTS AGREEING**: 2.16 µs (`active`) / 23.83 µs (`passive`) / 2.478 µs per
trivial node through the real threadpool / **2.72 µs in situ**. **Spin, not futex**, confirmed twice
including `voluntary_ctxt_switches = 231` across 48 threads over minutes. **Hierarchical barrier: no win at
48T. No implementation win exists** — do not spend a window looking for one.

**★ RANKED ENVELOPE — MTP ms/token, the config that serves (wall 48.08; mean-thread compute 33.52
+ imbalance 10.67 + barrier 3.89 = 48.08, closes exactly):**

| rank | seam | MTP ms | recoverable | confidence | owner |
|---|---|---:|---|---|---|
| 1 | **single-threaded row-split kernels** | **2.84** | **~2.3** | **HIGH** | SYNC-10 |
| 2 | **matmul imbalance** | **4.83** | ? | **LOW — no mechanism** | **SYNC-14 (new)** |
| 3 | tiny-op barrier toll | 1.97 | ~0.5–0.7 | MEDIUM | SYNC-2 |
| 4 | GDN + CPY | 1.70 | ~0.1 | closed | SYNC-3 |
| 5 | GET_ROWS | 0.33 | 0 | **closed by D8** | — |

**⚠ CORRECTION 2026-09-05 — `hc_gate` DOES NOT COLLAPSE TO A SCALAR. The coordinator's stated mechanism was
wrong and was propagated to SYNC-10.** Read from `src/models/qwen4exp.cpp:246-278`:

```
xn    = mul(rms_norm(x), w_norm)                        // [hc_dim = 4*2560 = 10240, T]
gate  = sigmoid(w_up @ silu(scale(w_down @ xn, 1/hc)))  // [10240, T]  <- hc_gate
gated = mul(xn, gate)                                   // ELEMENTWISE over all 10240
mixed = mean_d1(reshape(gated, n_embd, hc, T))          // [2560, T]
```

It is a **full 10240-element vector gate**, one multiplier per (stream, channel), applied elementwise to the
whole hyper-connection state. **The collapse happens in `mean_d1` AFTER the gate, not in it.** Two
consequences pulling opposite ways — which is exactly why precedent cannot settle the vectorisation question:
**worse** than the scalar picture (not one perturbed multiplier but **10240 independently perturbed ones**,
each scaling a residual channel feeding the rest of the layer), and **better** (the following `mean_d1`
averages `hc=4` streams, attenuating independent errors by ~1/√4 = 0.5 into `hc_mixed`). Net ~1.4e-07
relative perturbation, 48 layers deep, on a quantity with measured top-1 leverage. **The conclusion — gate on
KLD, not on the silu precedent — survives; the reasoning behind it does not.** It matters because **a probe
designed around "one scalar per layer" would measure the wrong object**; the right one is per-channel gate
perturbation into `hc_mixed`, which a paired full-distribution KLD already captures. (B7's ~8% top-1 figure
is NOT re-verified by SYNC-10 and is not restated as its finding.)

**★★★ B12 IQ4_XS DRAFT HEAD — HYPOTHESIS REFUTED AND INVERTED 2026-09-05. THE SHARED HEAD WAS ALREADY THE
CACHE-EFFICIENT DESIGN, AND THIS EXPLAINS B10's 1.6× PHENOMENON.**
Bytes fell to **0.648×** but time per head call **ROSE to 1.097×**; effective bandwidth went
**244.4 → 144.3 GB/s**. The baseline reproduces B10 independently (**244.4 GB/s measured off a printed
`PATHROW`** vs their derived 260), so this is not an instrument artefact.

| | measured |
|---|---|
| bytes | 0.648× |
| compute | 1876 → 1682 µs (**−10.3% for −35.2% of bytes**) |
| dead time | 258 → **658 µs (2.5×)** — exceeds the entire compute saving |
| effective rate | **244.4 → 144.3 GB/s** |
| **α** | **0.8209 → 0.8249 (+0.0040)** — coherence identical |

**Mechanism 1 — the head is not bandwidth-bound at this size.** Cutting 35.2% of bytes bought 10.3% of
compute; on compute alone the rate *drops* 278 → 201 GB/s, because **IQ4_XS is the only one of the three
candidate quants requiring Q8_K activations**, so its kernel is less efficient per byte.
**Mechanism 2 — dead time rose 2.5×**, more than erasing the compute win.
**★ THE STRUCTURAL FINDING, AND IT REVERSES THE PREMISE: the shared head is a FEATURE.** The draft graph
reuses **the trunk's** `output.weight` — **one 521.5 MB slab, two consumers**, where each verification step
re-warms exactly the bytes the next draft step reads. **That mutual re-warming is very likely WHY B10
measured 1.6× the DRAM ceiling in the first place.** Giving the draft its own head does not replace the slab,
it **ADDS** to it: 521.5 (trunk) + 337.7 (draft) = **859.2 MB, +64.8%** against ~402 MB of L3.
**★ THE COORDINATOR'S ERROR, NAMED: my per-CCX arithmetic counted the head ONCE when the change makes it
count TWICE.** I was right about the slab and wrong about the *working set*. **Generalisable rule: when
evaluating a change that gives a consumer its OWN copy of a shared tensor, cost the WORKING SET, not the
tensor.** This is the fourth time this week byte-based reasoning has erred in the same direction
(B7 dilution, B10 byte model, B11's premise, now this) — and every correction has come from measuring a rate
rather than counting bytes.
**α was NOT the binding constraint.** The B9-shaped risk was real to check and did not bite: a 7.85%-RMSE
head with no imatrix cost **nothing** in acceptance (it gained 0.004). The kernel and the footprint arithmetic
were what killed it. **Checking α was still correct** — it was the cheapest way to be wrong safely.
**Consequence for PROD-1**: the settled recipe's use of the **shared** MTP head is now *understood*, not
merely inherited — **lock it with the reason.** Any future change that gives the draft path a private copy of
a large tensor is anti-cache by this mechanism and must clear the working-set arithmetic first.
**★ RESOLVED 2026-09-05 — CONFIGURATION, NOT INSTRUMENT. The non-reproduction is EVIDENCE FOR the finding.**
Settled from B10's own on-disk artifacts with no lock time: B10's plain arm ran **the same commit**
(`10221 / c51e4dabf`), same `n_threads = 48`, same profiler accumulate site, and its `lm_head` PATHROW shows
`compute 3.7422 / wall 3.7423` — no barrier component, and plain decode has no speculative catch-ups, so the
empty-eval hazard never touched it either. **B10's 139.35 is sound for what it measured.** What it measured
is a different object: B10's headline varied **two** things at once, graph shape *and* the presence of MTP.
Ordered by how recently the 521.5 MB slab was last touched:

| configuration | between two head calls | µs/call | GB/s | ×ceiling |
|---|---|---:|---:|---:|
| trunk head, **plain** (B10) | a whole trunk token; slab fully evicted | 3742.2 | 139.4 | **0.91×** |
| trunk head, **in MTP** (B12 P0) | ~4.45 draft steps just re-read the slab | 2537.7 | 205.5 | 1.35× |
| draft head, **in MTP** (B12 P1) | ~144-node graph, ~105 MB of other weights | 2133.6 | 244.4 | 1.60× |

**Monotone, with the endpoints behaving correctly** — plain sits *below* the DRAM ceiling at 0.91×, which is
what a fully evicted slab must do. **The shared-slab mechanism PREDICTS that adding MTP speeds up the trunk's
own head call, and 139 → 205.5 is exactly that.** So 244.4 does not inherit doubt.
**But it RETIRES the framing**: holding MTP constant, the draft head's advantage is **1.19×, not 1.87×**.
Residual uncertainty stated in-report: B10 used one prompt, B12 used 24 — cannot explain a 47% gap, but is
the one thing not eliminable from existing data.

**★★ Q4_K REFUTED B12's OWN MECHANISM — the most useful result of the run.**

| arm | slab | compute µs | dead µs | wall µs | vs base |
|---|---|---:|---:|---:|---:|
| q6_K | 521.5 MB | 1875.6 | 258 | 2133.6 | 1.000× |
| **Q4_K** | 357.6 MB (−31.4%) | **1867.8 (−0.4%)** | 430 | 2298.1 | 1.077× |
| IQ4_XS | 337.7 MB (−35.2%) | 1681.9 (−10.3%) | 658 | 2340.1 | 1.097× |

B12 predicted Q4_K near 278 GB/s on compute because it alone avoids **Q8_K activations**; it came in at
**191.4 — the worst of the three** — while IQ4_XS, the quant it blamed, saved the *most* compute.
**The Q8_K story is WITHDRAWN.** Two of three predictions right (loses, loses less); the one it got wrong
carried the mechanism, and it said so.
**★ WHAT REPLACES IT IS STRONGER AND GENERALISES: cutting 31.4% of the head's bytes changed its compute time
by 0.4%.** The head is **not bandwidth-bound at batch 1** — it is bound by something paid **per call**
regardless of slab size, which corroborates the per-node/per-call picture from an independent direction.
**This is the FIFTH byte-model failure this week and the sharpest statement of it: on this machine a byte
estimate is a hypothesis awaiting a rate measurement, not an estimate.**
**Honest residual**: the falsifier did not trigger (Q4_K was not faster), so the footprint argument stands —
but **dead time does NOT order by footprint** (IQ4_XS has the smaller footprint *and* the worse dead time),
so §8b explains why both lose without explaining their ordering, and that cannot be separated from this data.
**Verdict unchanged: NO-GO.** α cleared in both candidates (+0.0040 IQ4_XS, +0.0018 Q4_K, coherence identical
across all three) — **B9 does not generalise to head precision.** t/s remains NON-CLAIM. Both artifacts kept
with digests so the deferred ABA needs no rebuild. Lock released 21:15:05, never held past the yield.

**Superseded note — the validation criterion as originally flagged:** B12 set up a
trunk-graph arm specifically to reproduce B10's **printed** 139 GB/s before any draft number was trusted. It
measured **205.5 GB/s**. Two readings, not yet distinguished: either the configurations genuinely differ
(B10's 139 is the trunk graph in PLAIN decode; B12's is the trunk graph inside an MTP run, where draft steps
re-warm the head — under B12's own shared-slab mechanism those *should* differ, and in the direction
observed, which would make the non-reproduction a **prediction of the finding** rather than a failure of it),
or the instruments differ, in which case 244.4 inherits the doubt and its agreement with B10's derived 260 is
coincidence. **The verdict does not depend on it**: the refutation rests on a WITHIN-ARM comparison (bytes
−35.2%, wall per call +9.7%, α flat), which needs no external baseline. But no cross-agent rate comparison
should be made until this is resolved. **Second time in one day a "before" number turned out to be measuring
a different object than the "after" it was compared against.**
**★ STRUCTURAL COROLLARY (B12) — this binds every future proposal in the family:** a private draft head is
anti-cache regardless of quant, because it *adds* to the trunk's slab rather than replacing it. **The only
way to shrink the resident head is to requantise the one the TRUNK uses — which is a CORRECTNESS change, not
an α change**, and therefore gated on KLD/PPL rather than on acceptance.
**DEFERRED, NOT DROPPED — 8 ABA arms**, resumable as their own window; the driver skips completed arms, both
artifacts kept with digests. **Q4_K prediction recorded BEFORE its result was read**: it should lose too, but
less and for a different reason — no Q8_K activations, so its compute-side rate should land near q6_K's 278
GB/s rather than IQ4_XS's 201, while paying the footprint penalty *harder* (357.6 → 879.1 MB, **+68.6%**).
**Falsifier, stated in advance: if Q4_K comes back FASTER than baseline, the footprint argument is wrong and
reopens.** No t/s claim is made — the ABA did not run, so throughput is **NON-CLAIM**, stated rather than
inferred; 9.7% slower per call with α flat is neutral-to-worse and could not have overturned the verdict.
**Original text**: `Q4_K` (P3), the interesting arm rather than a contingency — it is the one candidate
that does **not** use Q8_K activations, so it isolates mechanism 1 from mechanism 2. It still pays the +64.8%
duplication, so it is expected to lose too, **but less, and for a different reason** — which is what makes it
worth the arm.

**✅ OP-38 RESOLVED 2026-09-05 — operator acked, fix committed `1e4924b1`.** Both defects closed; policy
untouched (guarded prefixes, ack mechanism and refusal text unchanged); 5-case regression test added,
mutation-proven both directions. **⚠ Deployment: the hook that EXECUTES is the copy in `/workspace`'s working
tree, which the commit does not update — it takes effect there on the next pull.** METH-1's blocked
deliverable (committing SYNC-1's profiler patch from a llama.cpp worktree) unblocks once that lands.

**Original decision request, retained — TWO DEFECTS IN THE D9 HOOK, ONE OF THEM A BYPASS. Fix prepared and
mutation-proven; I did NOT commit it, because `scripts/hooks/` is itself D9-guarded and inventing an ack is
exactly what the control exists to prevent.**

1. **FALSE POSITIVES — the hook probes the wrong repository.** `_run()` invokes git with no `cwd`, so it
   inherits `$CLAUDE_PROJECT_DIR` (`/workspace`) regardless of which repo the commit targets. It therefore
   refuses legitimate commits in `/mnt/raid0/llm/**` worktrees on the strength of **a peer session's** dirty
   `scripts/coordination/**`. **Hit independently by SYNC-1 and SYNC-10 on 2026-09-05; both correctly
   declined to invent a `D9-ack` to get past it.** It will refuse every llama.cpp-worktree commit for as long
   as `/workspace` carries dirty coordination files — which is most of the time.
2. **★ FALSE NEGATIVE — `git commit -a` BYPASSES D9 ENTIRELY.** Found while testing (1). `-a` stages tracked
   files *itself*, so with nothing staged `git diff --cached` returns empty and `commit_targets()` reports no
   guarded paths. **Measured: `git commit -am` on a dirty `scripts/coordination/` file passes cleanly, rc=0.**
   Only a staged-then-plain commit is caught. The hook's own refusal text reads *"a control with an unguarded
   path is not a control"* — and it has one. **This is the more serious of the two: D9 has been advisory
   against anyone using the most common commit idiom since it was ratified 2026-08-15.**

**The fix** (`/mnt/raid0/llm/tmp/inf70/operator/d9_hook_two_defects.patch`, 112 lines, + a 5-case regression
test `test_d9_hook_probes_target_repo.py`, 85 lines): run the probes in the commit's own `cwd` from the hook
payload; skip only where the target repo does not CONTAIN the guarded tree (`git cat-file -e HEAD:<prefix>`,
**failing closed** if git cannot answer, so it can only ever exempt repos lacking the prefix and never weakens
enforcement where it exists); and treat `-a`/`--all` as recording the working tree.
**Mutation-proven, both directions**: reverting the `-a` fix fails exactly the two enforcement tests;
reverting the `cwd` fix fails exactly the two false-positive tests; restored, all five pass. Policy is
untouched — guarded prefixes, ack mechanism and refusal text are unchanged.
**To apply** (from a clean `/workspace`, operator ack required by the control itself):
`git apply /mnt/raid0/llm/tmp/inf70/operator/d9_hook_two_defects.patch && cp
/mnt/raid0/llm/tmp/inf70/operator/test_d9_hook_probes_target_repo.py tests/` then commit with a
`D9-ack:` line. **Note the patch tightens the control more than it loosens it.**

- [x] **SYNC-14 — CLOSED ✅ 2026-09-07: measured null (`GGML_IQK_EVENSPLIT` −0.24%); imbalance on a memory-bound matmul is not recoverable capacity. diagnose matmul imbalance (4.83 MTP ms/token, the LARGEST single item, and nobody knows
      why).** Filed 2026-09-05 from SYNC-1's envelope. It is ranked second only because its confidence is LOW:
      **there is no named mechanism.** Candidates to discriminate, not assume: per-CCX residency straddling
      (SYNC-11's 48-value dump on `result_output` bears directly — that node has the graph's largest absolute
      imbalance at 359 µs, 1.48× fast-to-slow); NUMA placement of specific tensors; expert-gather row-count
      variance under `mul_mat_id`; iqk's static partition dividing unevenly for particular shapes.
      **⚠ Note the measurement caveat that applies to exactly this seam**: `thr_max` absorbs intra-op barrier
      waits, so the imbalance/barrier split is **approximate for MUL_MAT and MUL_MAT_ID** — the 32.0 ms total
      is robust but this 4.83 ms is the least certain number in the table. **Establish the mechanism before
      anyone proposes a fix.**

**★★ D1 A/B RESULT 2026-09-05 — AND THE HYPOTHESIS THAT RECONCILES IT WITH THE 2.72 µs RESIDUAL.**
ABABAB round 1, `-p 0 -n 128 -r 25`, placement 25.5 GB × 4, same window:

| arm | tg128 | ms/token |
|---|---:|---:|
| `G1_base` (`c035bbf3d`, unpatched) | **10.28 ± 0.16** | 97.28 |
| `G1_d1` (`1ba448e74`, 940 barriers removed) | **10.10 ± 0.39** | 99.01 |

**The patched arm is 1.73 ms/token SLOWER against a primitive-model prediction of ~2.56 ms FASTER** — wrong
sign, comparable magnitude. Second in-situ null for barrier elision after INF-10. **Cut after round 1
(coordinator's call) and reported single-round NON-CLAIM**: the instrument cannot reach ±0.2 ms (SEM of the
difference is 0.81 ms at one round, ~0.47 ms at three, bound by the d1 arm's own 2.4× dispersion), and the
binary predates `99425578d`, D8 and b3k while taking **21.2 min against base's 5.5 for the same 25 reps** —
a 4× wall anomaly outside the timed decode. **50 min of a contended lock could not change any decision.**

**★ THE RECONCILING HYPOTHESIS (coordinator, from SYNC-1's own label — testable, not yet confirmed):** the
measured quantity is "**barrier + dispatch**", and the two are NOT equally removable.

> **Removing a barrier between two nodes does not remove either NODE.** Each node still has its work
> distributed to 48 threads, and **dispatch is paid per node, not per barrier.** If dispatch dominates the
> 2.72 µs, D1 eliminated 940 barriers while leaving all 4,409 dispatches intact — buying nothing, as measured
> — while the in-situ per-node residual remains a genuine 2.72 µs, also as measured. **Both facts hold with
> no congestion story required.**

It predicts the live seams diverge sharply, which is what makes it worth testing rather than believing:
**SYNC-2's fusion removes NODES** ⇒ recovers dispatch *and* barrier; **D1-style elision removes barriers but
no nodes** ⇒ recovers only the barrier part ⇒ null, observed twice; **SYNC-10 removes neither** ⇒ its win
comes wholly from the 7.79 ms idle-thread critical path, independent of both. **If it holds, the axis must be
re-priced on NODE COUNT, not barrier count.**
**★ SYNC-9 IS NOW THE DECISIVE EXPERIMENT, NOT A FREEBIE** (routed to SYNC-2, to be run FIRST). The 72
zero-sized `build_rs` nodes do **literally zero work**, so removing them has **no compute confound** and the
entire saving must be dispatch + barrier. 72 × 2.72 µs = **0.196 ms** against the profile's **0.173 ms** —
close enough to discriminate. **Recovers ~0.173 ms ⇒ dispatch is recoverable by node removal, SYNC-2's
fusion seam is real, re-price the axis on node count. Recovers ~nothing ⇒ even node removal does not convert,
and Axis S is finished** — including the fusion, before a week is spent building it.
**Also settled, with a second independent instrument: the pool SPINS, it does not sleep.**
`voluntary_ctxt_switches = 231` across all 48 threads over minutes of decode; a futex pool would show
~5,400 × 48 per token. Costs nothing and forecloses an entire branch of speculation.

**★★★ SYNC-10 ROUND 1 (2026-09-05) — NON-CLAIM, one round, but the arms agree with the census to <2% and
the composition result CANCELS a planned KLD window.** Base measured on its own tip: **13.12 ± 0.06 t/s =
76.22 ms/token** (±0.5%) — near SYNC-1's 78.87 and nowhere near the 96.3 / 84.2 figures from the pre-D8
profile that was never on this base's history.

| arm | t/s | ms/token | Δ vs A | vs S | bit-identical |
|---|---:|---:|---:|---:|---|
| A base | 13.12 | 76.22 | — | | — |
| **S** split | **14.37 ± 0.10** | **69.59** | **+9.5% (−6.63 ms)** | — | **YES** |
| V vec-sigmoid | 13.95 ± 0.10 | 71.68 | +6.3% (−4.54 ms) | −2.9% | no |
| **W** vec+split | **14.37 ± 0.07** | **69.59** | **+9.5%** | **±0.0%** | no |

**Predictions matched**: S saved 6.63 ms against a census prediction of **6.59** (0.6%); V saved 4.54 against
**4.46** (<2%). A placement artefact or drift excursion has no reason to land on the census's numbers, so the
mechanism is confirmed, not just the effect.
**★ THE COMPOSITION RESULT: W ≡ S. The vectorisation contributes NOTHING once the split exists.** Mechanism
exactly: the split threads the sigmoid 48 ways, 50 µs → ~1.1 µs; vectorising then takes 4 µs → ~0.1 µs, worth
~1 µs × 97 nodes = **0.1 ms on a 70 ms token (0.14%)** — below the noise floor. **The two levers fix the SAME
node by different routes and do not add**, and the cheaper-to-justify one captures nearly all of it. Note
this **inverts the coordinator's framing**, which flagged the vectorisation as "possibly a larger and much
cheaper lever": the magnitude estimate (~4.5 ms) was right, "larger" was wrong — the split also fixes the
sigmoid *and* picks up MUL and REPEAT.
**★ CONSEQUENCES IF IT REPLICATES:**
1. **Promote S ALONE** — `GGML_ROWCOL_SPLIT=1`, **bit-identical**, gated by a digest match that already
   passes. No accuracy argument, no correctness debate.
2. **NO KLD TURN NEEDED FOR THIS STACK.** The `hc_gate` leverage question stays real but becomes **moot
   here**, because we never have to ship the ulp change to get the win. *(A window the coordinator had
   already committed to funding is cancelled by an experimental design choice, not by an argument.)*
3. The sigmoid vectorisation remains valuable as an **upstream contribution** — it helps every model that
   lacks a 48-thread split to hide the scalar `expf` — which is where §7.1 already puts it.
**Why this outcome existed at all**: the agent gated the two knobs **independently**, against a brief that
had them bundled. Three arms answered more than four arms of split-only would have.
**★★ ROUND 2 COMPLETE — REPLICATED. Window 1 then KILLED BY THE TASK MANAGER mid-`P3S` (not by the agent).**
Two complete paired rounds, all four arms the same binary separated only by env:

| arm | R1 Δ | R2 Δ | **mean** | bit-identical |
|---|---:|---:|---:|---|
| **S** split | **+9.53%** | **+7.60%** | **+8.57%** | **YES** |
| V vec | +6.33% | +4.37% | +5.35% | no |
| W both | +9.53% | +6.63% | +8.08% | no |
| **W/S ratio** | 1.000 | 0.991 | **0.996** | |

Base arms **13.12 / 13.28 / 13.17 t/s — 1.2% spread over 40 minutes**, so the host held through the window
and the effect is **~7× the noise**. Measured denominator **76.22 ms/token**.
**★ THE CENSUS PREDICTED THE WALL CLOCK TO WITHIN 1%** — S predicted 6.59 ms vs **measured 6.63**; V
predicted 4.46 vs **measured 4.54**. That is the strongest available evidence the mechanism is real rather
than a placement artefact: drift has no reason to land on the census's numbers.
**★ W ≈ S REPLICATES ⇒ PROMOTE `S` ALONE, AND THE KLD WINDOW IS NOT NEEDED.** Post-split the sigmoid node is
~1.1 µs; vectorising then saves ~0.1 ms/token = 0.14%, under the noise, while its scalar tail and per-chunk
setup are real. The levers fix the **same node by different routes** and the **bit-identical one already gets
all of it**. `GGML_VEC_SIGMOID` need not ship here; its value is **upstream**, for models without a 48-thread
split to hide the scalar `expf`.
**⚠ NOT MEASURED, AND NO CLAIM MADE: the MTP arms.** The brief said lead with MTP; there is no MTP number.
Also outstanding: greedy gates, `test-backend-ops` ×4, pristine-base control, threshold probe, round 3.
**Plain result stands as MEASURED BUT UNDER-REPLICATED** — 2 rounds against a protocol asking ≥4.
**Containment on the kill, done before anything else**: scanned every `/proc/*/environ` for the agent's unique
worktree `LD_LIBRARY_PATH` (**zero survivors**), confirmed no listener on port 18531, verified **SYNC-2's
window is uncontaminated**, and **discarded `P3S` rather than read a partial arm** (no `tg128` line).
**Window 2 rebuilt from the failure**: **resumable** (each arm skips if its result exists) and **reordered so
the cheap required evidence runs first** — greedy gates → `test-backend-ops` → MTP → plain leftovers — so a
further interruption costs least. Launched **detached** (`setsid`, own session leader, PID in `window2.pid`)
so a task-manager kill cannot take it down again, with the PID recorded so it can still be stopped precisely.

**Superseded — round 1 outstanding list:**

- [ ] **SYNC-10 — AT BATCH 1, EVERY ROW-SPLITTING KERNEL IN ggml IS SINGLE-THREADED. 7.79 ms/token (9.9%),
      one thread working and 47 idle.** Dispatched 2026-09-05, **the largest single lever identified in the
      campaign.** Nodes with `thr_mean/thr_max < 0.1`, tip plain:

      | op | n | critical path | mean work | wasted |
      |---|---:|---:|---:|---:|
      | UNARY | 145 | 5.170 ms | 0.131 | **5.039** |
      | MUL | 144 | 1.116 | 0.065 | 1.051 |
      | ARGSORT | 48 | 0.985 | 0.026 | 0.958 |
      | REPEAT | 95 | 0.528 | 0.026 | 0.502 |
      | **total** | **453** | | | **7.790 ms/token** |

      **Mechanism verified at the kernel**: `ggml_compute_forward_silu_f32` and siblings split over ROWS
      (`dr = (nr+nth-1)/nth`), and every one of these tensors is `[10240,1,1]` ⇒ `nr = 1`, so only `ith = 0`
      gets a range while 47 threads enter, do nothing, and park. **Not a barrier problem and not imbalance — a
      missing parallelisation.** Precisely the defect **D8 fixed for GET_ROWS** with a (row, column-chunk)
      split, bit-identical, +13.8% (re-verified same-binary at +15.4% by SYNC-4) — so the template exists
      (`bc2834a9b`, `inf70/sync4`'s `ggml_get_rows_split_init`).
      **★ It survives the ÷3 rule** (⚠ superseded as a general rule — see the COROLLARY; the ranking below
      stands on its own measured served numbers, not on the divisor), which is why it outranks every barrier
      lever: **6.04 ms is still wasted
      in the MTP trunk graph** (UNARY 4.11 + REPEAT 1.62). ARGSORT is not elementwise and may be unreachable —
      triage honestly rather than forcing it.

- [x] **SYNC-12 — DONE 2026-09-05. Entry point built; CUDA's `K<=1` bail is SCOPE, not soundness.** ✅
      Branch `inf70/sync12` @ `f5908e76c`, **not merged**. Lock released 21:19Z.
      **★ THE SAFETY QUESTION ANSWERED FROM THE CODE — SYNC-3's behaviour is SAFE, not lucky.** The CUDA
      *kernel* at K==1 is already the fused form; only the *matcher* refuses. Three proofs:
      `gated_delta_net.cu:329` — `if (cache != nullptr) { state_d = cache->data; }` is **unconditional on K**;
      `gated_delta_net.cu:170-178` — the `if constexpr (!keep_rs_t)` epilogue writes `state[col*S_v + i]` after
      the token loop at an offset already advanced by `(sequence*H + h_idx)*S_v*S_v`, so with `cache` set and
      K==1 it **writes the final state straight into the cache slot, correctly**, using code exercised on every
      non-rollback GPU decode. Two tells the author considered K==1 and dropped it: `gated_delta_net.cuh:8`
      documents `slot_stride` as *"0 when K==1"*, and `ggml-cuda.cu:2762`'s `K > 1 ? … : 0` ternary is **dead
      code** under the early return above it. **Why gated off**: the K==1 destination is a `ggml_view_2d`
      (`delta-net-base.cpp:551`) vs the K>1 `ggml_view_3d` the matcher's shape checks assume — a second shape
      to validate for **zero GPU payoff** (one 3 MiB D2D copy per layer on HBM).
      **The real soundness question is ALIASING, and it resolves identically at both K**: `src[5]` comes from a
      `GET_ROWS` gather, never the cache tensor, so read source and write target are disjoint. The pass checks
      that explicitly — **one check more than CUDA's own matcher makes.**
      **★ `ggml_cpu_try_fuse_ops()` ALREADY EXISTED** (`ggml-cpu.c:3812`) with CUDA's exact shape and one
      hardcoded RMS_NORM+MUL clause; turned into a registry. **Backend safety is STRUCTURAL, not defensive** —
      the pass lives only in `ggml-cpu.c` and the graph is never mutated, so CUDA/Metal/SYCL see a
      byte-identical *unfused* graph. Of the three options offered this is the third and best: **the fused form
      is UNREPRESENTABLE for a backend that cannot execute it** — no asserts to remember in three files, no
      capability check to get wrong, no ABI change. Contract: `run` returns handled/not-handled plus `n_extra`
      (nodes consumed) and **`skip_barrier`** — splitting those is what lets the entry point host node
      **DELETION** as well as merging. Load-bearing invariant of five in the source header: **matchers must be
      pure functions of the graph**, since all `nth` threads decide independently and a disagreement unmatches
      the barriers.
      **Correctness: all EIGHT streams byte-identical** — 288 greedy tokens at ~40/~90/~200, base vs both at
      each length plus gdn-only and empty-only at 200. **Hit counts prove firing: `gdn_state_cache` = 10368 =
      36 layers × 288 tokens exactly**; `rms_norm_mul` = 24192 in all eight arms (refactor behaviour-neutral).
      `test-backend-ops -b CPU` OK on `GATED_DELTA_NET`/`RMS_NORM` at nth 4 and 48 both ways; `EXP`/`EXPM1`
      fail **pre-existing** (they also fail under `GGML_CPU_DISABLE_FUSION=1`, so no pass can reach them).
      **OWED and not claimed**: the full `test-backend-ops -b CPU` sweep — started, then **killed (PID 441478,
      death verified) because it was running UNLOCKED while siblings were timing 1% effects.**
      **★ SECOND CONSUMER IMPLEMENTED, NOT SKETCHED — and it found the trap in SYNC-9.** Nine lines,
      bit-identical over 288 tokens, **62,999 elisions per process**. The insight: those nodes'
      `ggml_compute_forward` is **already a no-op**, so their 0.173 ms is **pure barrier** — **eliding the node
      WITHOUT the barrier recovers nothing.** A naive early-return would have measured zero and been read as
      "node removal does not convert", when no barrier had been removed at all. Measurement and disposition
      routed to SYNC-2/SYNC-9.
      **No speed claim, by design.** An encoding change cannot make a kernel faster; value is that SYNC-3's
      `src[6]` **cannot ship** (silent write-back skip on three backends) and this can, and that the next lever
      writes a matcher and adds a row instead of another `GGML_*` flag.

- [x] ✅ **SYNC-12-ORIGINAL (superseded, retained for the record)** — port the CUDA GDN fusion. Dispatched
      2026-09-05 from an operator question ("can't we reverse engineer it and adapt it to our hardware?").
      **Framed deliberately as INFRASTRUCTURE, not a speed lever** — SYNC-3 already achieved the functional
      outcome and measured it honestly at −0.307 ms plain / **~0.1 ms per token in serving** (the copy is in
      the trunk graph, which amortises over 3.23 tokens), which is below the noise floor. Two reasons it is
      still worth doing:
      1. **SYNC-3's version cannot ship.** `src[6]` is CPU-only; CUDA/Metal/SYCL would ignore it and
         **silently skip the state write-back** — a silent wrong-answer path on three backends.
      2. **The campaign needs a fusion MECHANISM, not more env knobs.** Every fusion here is currently a
         bespoke `GGML_*` flag. A `ggml_cpu_try_fuse_ops` mirroring the CUDA pass is the entry point that
         SYNC-2's HC_MIX compound op and the 72 zero-sized `build_rs` skip (SYNC-9) both need.
      **The question that decides safety**: CUDA bails at `if (K <= 1) return 0;`, and CPU decode runs K == 1
      — is that guard there because the fusion is UNSOUND at K==1, or merely because it was not worth it on a
      GPU? Must be answered from the code, not assumed. Design gate: if the entry point cannot trivially host
      the zero-node skip as a second consumer, it is the wrong design.

**★★ `GGML_IQK=1` IS LOAD-BEARING FOR THE ENTIRE CACHE-RESIDENCY STORY (B12, 2026-09-05).** The per-CCX
residency mechanism requires a **static per-thread row partition** — and that comes from **iqk, not ggml's
chunker.** `ggml_is_numa()` is **false** on this host (we run `numactl --interleave=all` externally but never
pass llama.cpp's own `--numa` flag), so the generic path would use **atomic work-stealing over 15,520
chunks**, under which **no thread sees the same rows twice** and nothing can stay resident in its CCX's L3.
**So every above-DRAM-ceiling rate this campaign has measured — the 260 GB/s draft head, SYNC-3's 234 GB/s
GDN state — is contingent on `GGML_IQK=1` giving a stable partition.** All three candidate head types are
iqk-supported, so B12's arms are not confounded by scheduling; but the finding generalises well beyond B12.

- [x] **SYNC-13 — COMPLETE ✅ 2026-09-07: premise was inverted; keep `ggml_is_numa()` false, never pass `--numa` (affinity, not chunking, is the disqualifier). what does `ggml_is_numa()` gate, and is `false` the right value for us?** Filed 2026-09-05
      from B12. We run `numactl --interleave=all` externally but never pass llama.cpp's `--numa`, so ggml
      believes it is on a non-NUMA box and takes the work-stealing chunker. That is currently **load-bearing
      in our favour by accident** — static iqk partitioning is what makes L3 residency possible. Enumerate
      every path `ggml_is_numa()` gates, and determine whether enabling ggml's NUMA awareness would help
      (better placement) or **destroy the residency effect** (work-stealing partitions). **Do not flip it to
      find out** — read the paths first. Interacts with D6 (placement) and B2, which are now the campaign's
      largest remaining levers.

- [ ] **METH-1 — make the per-`(node,thread)` OCCUPANCY census the standing FIRST step for kernel work.**
      Filed 2026-09-05 from the campaign retrospective. **The instrument we used all campaign made the winning
      defect invisible by construction**: per-node `wall`/`compute` was recorded **from thread 0**, and in a
      node where only `ith = 0` has work, thread 0 *is* the working thread — so 453 single-task nodes looked
      like honest compute. And the **ranking metric actively deprioritised the winner**: we ranked by dead%
      (`wall − compute`, an OVERHEAD metric), under which `GET_ROWS` scored **3.6% dead** while being the
      largest lever in the graph, and SCALE scored 96% while being worth ~0.5 ms.
      **The right first question is OCCUPANCY — "what fraction of the machine is doing useful work during this
      node?" — not overhead.** One per-`(node,thread)` pass yields all of it: `mean/max` across threads finds
      **idle threads** (the row-split defect, `thr_mean/thr_max < 0.1`); `max − mean` gives imbalance;
      `wall − max` gives the true barrier residual; variance across evals catches **host stalls** (2.39 ms of
      ours hid in 4 nodes' means); and bytes ÷ time per node gives the **effective rate**, which is what
      exposed cache residency after five byte-model failures. Every correction this campaign made falls out of
      that single instrument; we assembled it piecemeal across four investigations.
      Deliverables: fold SYNC-1's `sync1_profiler_instrumentation.patch` into the tree so it is a one-flag run
      (**three agents rebuilt it independently this session** — SYNC-1, SYNC-10, B12); a wiki page stating the
      occupancy-not-overhead rule; and two supporting habits — **census the config you SERVE** (the MTP graph
      was uncensused until 2026-09-05 and gave the ÷3 rule) and **never report a per-node mean without
      dispersion**. **Blocked on OP-38** for the patch commit.

- [x] **UP-1 — upstream the two ggml contributions this campaign produced.** Filed 2026-09-05.
      (a) **`ggml-cpu: vectorise sigmoid`** — `ggml_vec_sigmoid_f32` existed in `vec.h` as a **dead scalar loop
      with zero callers** while `ggml_compute_forward_sigmoid` went per-element, and `ggml_v_sigmoid` is
      `ggml_v_silu` with the numerator `1`. A **12.5× gap on identically shaped nodes** from a function written
      and never wired. SYNC-10's §7.1 is already drafted as a liftable PR description, with the accuracy table
      (74.2% bitwise exact, 92.1% within 1 ulp, max ~2.3 ulp) and a note that the PR must **NOT** carry the
      `GGML_VEC_SIGMOID` gate — that knob exists only for our attribution; upstream should take the fast path
      unconditionally, as silu does.
      (b) **the (row, column-chunk) split for elementwise kernels at batch 1** — `apply_unary_op`,
      `apply_unary_op_functor`, `apply_binary_op`, `ggml_compute_forward_repeat_f32` (which was
      `if (ith != 0) return;` outright). Bit-identical, and worth **+8.57% measured** on this stack.
      Note upstream value differs from ours: (a) helps anyone lacking a 48-thread split; (b) helps anyone
      running batch-1 decode on many cores.
      **✅ COMPLETE 2026-09-07.** Verified against a **fresh clone of upstream `ggml-org/llama.cpp`, `master` @
      `e71b805`** (ggml 0.23.0) — not our vendored/frozen tree, not a README. All FOUR defects confirmed still
      present. Patches `git apply --check` clean against pristine master, independently and together.
      Patches, reproducers and ready-to-paste PR bodies: `/mnt/raid0/llm/tmp/inf70/agents/up/` (`REPORT.md`).
      **Nothing opened, pushed or posted — submission is the operator's call.**
      **⚠ CORRECTION TO OUR OWN RECORD: the `SET_ROWS` write-up quoted a "duplicate-destination race guard"
      comment that DOES NOT EXIST UPSTREAM — it was our own fork's added comment.** Real upstream documents the
      aliasing precondition at the `ggml_set_rows()` **API** level. Never cite that comment as upstream intent.
      **⚠ The (row, column-chunk) patch needed a hand fix for `ggml_compute_forward_repeat_f16`**, a variant
      added upstream since our commit — a naive reapplication would have **silently mis-patched** it.
      **Sigmoid accuracy re-measured here at 60.3% exact / 94.3% within 1 ulp vs 74.2% / 92.1% downstream**
      (libm/compiler difference). **Both are shown and labelled in the PR body**, neither is quoted as *the* number.

- [x] **HYG-1b — rebuild or remove EVERY stale build dir in the shared tree.** Escalated 2026-09-05: it is not
      one directory. **None** contain `GGML_FA_SPLIT_KV`, `GGML_ROWEXACT_N` or `GGML_IQK_DEQUANT`, and **all
      predate `99425578d`**, so setting any of those against them is a **silent no-op** and any result measured
      there is **vacuous rather than wrong** — the more dangerous kind. Cost B12 a rebuild and is the third
      incident of this class in a week. Either refresh them at tip or delete them so nobody can reach for one.
      **✅ COMPLETE 2026-09-07.** Audit found the "none of the build dirs contain the knobs" defect is now
      confined to **5 directories**, all of which were **deleted today**. Scan script and output retained at
      `/mnt/raid0/llm/tmp/inf70/agents/hyg/` (`scan_builds.sh`, `scan_builds_output.txt`). This is the standing
      stale-build-artifact failure mode, and it is exactly why **G2-CONC must run on the promotion-candidate
      binary and not on an ancestor.**

- [x] **HYG-2 — `check_commit_hygiene.py` parses the COMMIT MESSAGE as shell text.** Filed 2026-09-05 (was
      "noted, not filed" — filing it). It splits the command string on newlines and reads message lines as
      commands, so a message that merely **quotes** a git invocation is misread as a pathspec commit and
      refused. Cost three attempts in this session; worked around with `-F <file>`. Same family as OP-38 —
      a hook whose parser is wrong about which text is a command. Low severity, trivially reproducible.
      **✅ COMPLETE 2026-09-07 — fix committed at `29d340ad` with a MUTATION-PROVEN regression test** (the
      mutation was made visible AND counted, not merely asserted absent).
- [ ] **★ HYG-2b — THE COMMIT-HYGIENE HOOK DOES NOT SEGMENT A COMPOUND SHELL COMMAND, AND IT BLOCKS ITS OWN
      PRESCRIBED IDIOM.** Found and **reproduced deliberately** at the 2026-09-07 operator wrap-up, with
      `29d340ad` (HYG-2's fix) present in the tree — so this is a **second, residual defect, not a
      regression of the first.**
      **Repro (2 arms, one variable):** `git diff --stat -- <file> && git commit --dry-run -m "probe"` is
      **BLOCKED** as *"`git commit -- <pathspec>` on a shared repo"*; the identical `git commit` issued
      **alone** succeeds. The `--` belongs to the sibling `git diff`, not to the commit.
      **Proof it is reading the whole line as one command**: the block message renders the offending path as
      `git diff -- 2>&1` — it has taken the LAST token of the entire shell line as the "race" path.
      **Why it matters more than a nuisance**: the pattern it blocks — `git add -- <my files> && git commit
      -m "..."` with **no pathspec on the commit** — is *exactly the safe idiom the hook's own remediation
      text prescribes*. A guard that forbids its own idiom trains sessions to bypass it
      (`EPYC_ALLOW_COMMIT_HYGIENE_BYPASS=1`), which is strictly worse than the defect it prevents.
      **Fix**: split the command string on `&&`/`||`/`;`/newline and evaluate each segment independently;
      only a `--` appearing **after** `git commit` within the SAME segment is a pathspec commit. Extend the
      regression test with a compound-command arm — the existing test passes because it only ever feeds one
      command at a time, which is the same vacuity class HYG-2 itself was filed for.

- [x] **SYNC-11 — CLOSED ✅ 2026-09-07: ANSWERED, not run. Both of its justifications are gone.** Its
      question — is `result_output`'s 1.48× spread a per-CCX residency effect? — was answered by a better
      instrument. **SYNC-15's per-(node,thread) census refutes the per-CCX residency hypothesis: 88–96% of
      per-thread variance is BETWEEN NUMA NODES, only 3–11% between the three 32 MiB L3 CCXs inside a
      node**; it reproduces across process restarts at Pearson **r = 0.79**, its direction varies per graph
      node, and it **survives 4 KiB interleaving with placement uniform to 0.1%**. That refutation is
      written at the *RATE SKEW* block above; this row was simply never updated to match, and was left
      reading as an open unconfirmable hypothesis. Its second justification — corroborating B12's per-CCX
      step-change mechanism on `result_output` — died with B12 (closed NO-GO; the shared head was already
      optimal). **The 48-value dump remains one line in the summariser and one arm if a PMU-class question
      ever needs it** (SYNC-14 named a PMU as the only way to attribute the residual skew); it is not
      outstanding work. **Original row retained below for the record.**
      *Original:* full 48-value per-thread dump on `result_output` — three order statistics cannot show a
      GAP, and bimodality is a claim about a gap, so the per-CCX hypothesis is unconfirmable from
      `thr_min`/`thr_mean`/`thr_max` alone. Known: `result_output` has the graph's largest absolute
      imbalance (359 µs, 2653/1789, 1.48×), **but 18 MB q5_K nodes at 1.5 MB per CCX — far under threshold
      — reach 3.5×, so spread alone does NOT require a residency explanation.**

**★★ HYG-1 ESCALATED 2026-09-05 — EVERY BUILD DIR IN THE SHARED TREE IS STALE, NOT JUST ONE.**
B12 reports that **none** of them contain `GGML_FA_SPLIT_KV`, `GGML_ROWEXACT_N` or `GGML_IQK_DEQUANT`, and
**all predate `99425578d`** (the IQ4_XS iqk repack fix that closed the long-prompt P0). **Setting any of those
env vars against any shared build dir is a SILENT NO-OP.** This is C9's failure recurring at scale — the
third time this class has bitten the campaign in a week — and it is why the standing rule is now doctrine in
`CLAUDE.md`: **`strings <lib> | grep <KNOB>` before trusting a knob's null; an mtime check proves freshness
against source, only `strings` proves the symbol is in the binary you are running.** Every agent has been
warned; B12 built fresh at `c51e4dabf` (`build-b12`, `build-b12-prof`) and proved the knobs in.
**Any INF-70 result measured against a shared build dir is VACUOUS, not merely wrong** — and a vacuous result
is more dangerous, because it presents as a clean null.

**★ L3 IS PER-CCX, NOT A SHARED POOL — 384 MiB across 12 instances, 32 MiB per CCX** (B12, 2026-09-05). This
CORRECTS the coordinator's framing (I wrote "384 MiB ≈ 402 MB, the head doesn't fit"). The aggregate
threshold still lands near 402 MB, because ggml partitions by row range across threads and each thread's
slice stays in its own CCX — **but only if the partition is stable across steps.** Per-CCX at 48 threads over
12 CCDs: the q6_K head is **~43.5 MB per CCX (over 32 MiB — thrashes)**, IQ4_XS is **~28.2 MB per CCX
(under)**. So the B12 step-change hypothesis is **sharper, not weaker**: a real threshold crossing between
exactly these two artifacts.
**Consequence for the whole axis**: residency is per-CCX, so a tensor straddling the threshold is resident
for some threads and not others — producing **systematic straggle that is neither barrier cost nor ordinary
load imbalance**, and which a dead-time column cannot distinguish from either. **Signature to look for:
bimodal thread times on a single node.** Routed to SYNC-1 and SYNC-2.

**★ AXIS S RECONCILED 2026-09-05 — THE BARRIER BUDGET IS GROSS, NOT RECOVERABLE IN BULK.**
The apparent contradiction (2,478 ns/node measured on two instruments, pricing 5,410 barriers at ~13 ms, vs
D1 removing 940 barriers bit-exact for **−0.05 ± 0.5 ms** against a predicted 2.33 ms) resolves into one
mechanism, stated by SYNC-1 as a falsifiable model:

> The ~2.2–2.5 µs is **not a fixed toll per barrier**. It is the CONGESTION cost of 48 cores doing a
> simultaneous atomic RMW on one cache line plus the release round-trip, and it is paid in full **only when
> threads arrive at the barrier TOGETHER**. When arrival is staggered — which heavy, imbalanced matmul work
> guarantees — the late arriver finds 47 threads already spinning and the marginal cost collapses toward
> release latency alone (a few hundred ns). The straggler wait that remains is **not the barrier's, it is the
> imbalance**, and it would persist if the barrier were deleted, because the consumer needs all the data.

It predicts the entire record with no special pleading: D1's null (940 barriers sitting right after staggered
work), INF-10's −50 barriers, and the hierarchical-barrier prototype's flatness — while predicting that
**tiny-op chains DO pay**, because every thread arrives simultaneously with nothing to do.
**Therefore the correct target is not 5,410 barriers but "barriers at nodes where threads arrive together"**
≈ SYNC-2's tiny-op set (~3.6 ms) + D2(i)'s 579 consecutive-single-task elision candidates (~1.3 ms), against
an 84.2 ms token. **Axis S as originally framed was too broad; the imbalance half plus placement is where the
rest of the budget lives.**
**The estimator survives, and for a reason worth recording**: `ggml_compute_forward_scale_f32` splits over
ROWS (`dr = (nr+nth-1)/nth`), and every decode SCALE here is `ne = [2560,1,1,1]` ⇒ `nr = 1`, so only `ith=0`
gets work while threads 1–47 enter, do nothing, and park. The 375 SCALE nodes are genuinely single-task **at
the kernel, not the planner** — so the advisory-`n_tasks` finding does not invalidate them. Falsification
test, one run of SYNC-1's per-(node,thread) instrument: residual ≈2.2 µs on tiny/single-task nodes and a few
hundred ns after heavy nodes confirms; ~2.2 µs uniformly refutes.

- [x] **SYNC-8 — COMPLETE ✅ 2026-09-07: swept as a shape; both bugs written up in UP-2. two latent HEAP OVERFLOWS in the `n_tasks`-is-advisory class (not on our critical path).**
      Filed 2026-09-05 from SYNC-1. Neither is hit by qwen4exp decode; both are real for other graphs and
      probably upstream, so they want reporting as well as fixing.
      1. **`SET_ROWS`** — the planner sizes wdata as `ne0 * n_tasks` with `n_tasks = 1` (the "NOT parallelised"
         case in `ggml-cpu.c`), but the kernel indexes `params->wdata + (nc + CACHE_LINE_SIZE_F32) * ith` for
         `ith` up to 47 (`ops.cpp:5457`, F16-src → non-F16-dst branch). **Any quantised KV cache with an F16
         source overruns the work buffer**, and the sizing also omits the `CACHE_LINE_SIZE_F32` padding the
         kernel adds. That same `n_tasks = 1` carries a comment claiming serialisation prevents the
         destination-index write race — **the guard is inert**, since the kernel row-splits with nth=48. Our
         graph is safe only because `nr` is 1–4 there.
      2. **`SOFT_MAX`** — planned `n_tasks = MIN(n_threads, nrows)`, so 1 at single-row decode, while the
         kernel indexes wdata by `ith` up to 47 (`ops.cpp:5802`). qwen4exp uses FLASH_ATTN_EXT and has zero
         SOFT_MAX nodes. `ROPE` is fine (`n_tasks = n_threads`).
      **General rule this yields: every `n_tasks = 1` case that ALSO sizes wdata by `n_tasks` is a candidate.**
      Sweep for the pattern rather than fixing these two in isolation.

- [x] **SYNC-7 — COMPLETE ✅ 2026-09-07: kernel-vs-planner classification done; invalidated D8's +0.97% (filed SYNC-18). audit every `n_tasks`-based assumption in the campaign.** Filed 2026-09-05 from SYNC-4.
      `ggml_get_n_tasks()` is advisory; `params.nth` is overwritten per node. Sweep the tree for ops whose
      source implies serialisation (`SET_ROWS`, `SCALE`, `ROPE`, `DIAG`, and any others) and record what they
      ACTUALLY do at runtime, then re-check every INF-70 conclusion that rested on a `n_tasks` reading —
      including D8's own +0.97% and any null a sibling reports from a thread-count knob. Same failure shape as
      C9's stale binary: **a knob that does not reach the code produces a null that looks like evidence.**

- [x] ✅ **SYNC-4-ORIGINAL (superseded, retained for the record) — GET_ROWS serialization.** Dispatched 2026-09-05.
      Verify the single-task claim against the CURRENT tip before optimising — the tree has moved, and
      upstream may have fixed it already (adopting beats writing). Break the 9.0 ms down across the 175 nodes
      first: one hot node or a long tail changes the fix entirely.
- [x] **SYNC-5 — ANSWERED 2026-09-05: DO NOT pursue the fused-decoder / megakernel axis. And INF-67 never
      tested coarsening at all.** ✅
      **★ INF-67's 4× regression was NOT intrinsic to coarsening — it was four implementation defects.**
      1. A **per-row generic `vec_dot`** in `FusedMM::dot` (`src/models/qwen4exp-fused.cpp:66-104`) bypassed
         the iqk hooks (`ggml-cpu.c:1296`, `:1575`) AND CPU_REPACK (`:1743`), and misread IQ4_NL 8×8-interleaved
         rows as plain rows. Routing it through `ggml_compute_forward_mul_mat` (agent `fused`, branch
         `inf70/fused` @ `06f916224`): **923 → 295 ms/token. That is the entire "4×".**
      2. Scratch churn: 3,520 MB/token of `ggml_init/free` + 112.6 MB/token of state vectors — real, an
         implementation property, now replaced by 12.2 MB of arenas.
      3. A dead duplicated MoE (295 → 214 ms) and ~2.5M `getenv` calls per token inside the profiled window.
      4. **Single-threaded by construction** (`ith=0, nth=1`, private pool, `qwen4exp-fused.cpp:629-675`), and
         `ggml_barrier()` returns immediately at `n_threads==1` (`ggml-cpu.c:575-579`) — **so the 1T-vs-1T
         control arm could not, even in principle, have measured the barrier-removal hypothesis it was cited
         for.** With the artefacts removed, fused-1T is **×1.10 of the graph** (214.3 vs 195.1 ms, same
         build/process/window). The residual is intrinsic to hand-rewriting a layer outside the graph: 2,213
         `mul_mat` calls vs the graph's 941, loss of ggml's own fusions, and ≥10 correctness defects across
         two campaigns with the ≤1e-4 gate still failing by four orders of magnitude.
      **★ THE DEAD TIME SPLITS IN TWO, AND ONLY ONE HALF LOOKS RECOVERABLE.** ~**12 ms barrier primitives**
      (5,410 × ~2.2 µs; the 375 single-task SCALE nodes cannot have imbalance and show exactly 2.3 µs dead
      each — a clean estimator) and ~**10.5 ms imbalance** (MUL_MAT ~4.2, MUL_MAT_ID ~3.3, GDN 2.2, state CPY
      ~1.7). The forced all-to-all sync floor is ~8 per GDN layer / ~9 per attention layer = **~400 syncs/token
      against the 5,410 actually executed**, so a perfect per-layer fusion ceilings at **9–11 ms (11–13%)** and
      **touches none of the imbalance**.
      **⚠ BUT EVERY IN-SITU BARRIER-REMOVAL TEST TO DATE IS NULL.** **D1 removed 940 barriers, bit-exact, and
      measured −0.05 ± 0.5 ms against a predicted ~0.9 ms.** INF-10 (−50 barriers): −2.1% / +0.25%. A
      hierarchical-barrier prototype: no gain. A 2026-08-28 fused HC_MIX op: 785 µs vs 150 µs — per-row dots
      again, the same defect as (1). **The marginal realised value of a removed barrier is bounded ≤ ~1 µs and
      has not been shown positive.**
      **The 1,631 "small ops" are two `build_hc_mix` chains** (`qwen4exp.cpp:245-284`, 16 × 2 sites × 48 =
      1,536) plus the 9-ADD expert sum (432), ~3.6 ms dead — but their compute is two rank-320 gemvs per site
      at **27–30 GB/s, i.e. D6's sub-2 MB NUMA placement effect, not coordination.**
      **Ranked options against the corrected 84.2 ms token** (ceiling / realistic): (1) `HC_MIX` compound op
      calling the BATCHED `mul_mat` kernels internally, 1,536 → 96 nodes — 3.0 / 1–2.5 ms, ~300 lines,
      bit-exact by construction; (2) expert-sum op, 9 ADDs → 1 — 0.85 / 0.3–0.8, ~80 lines; (3)
      dependency-aware barrier elision (579 pairs) — 1.1–2.2 / 0.5–1.5, silent-race risk; (4) one op per layer
      DRIVING existing kernels with the real threadpool (~8 syncs) — 10–11 / 4–8, or **0 if D1's null is real**;
      (5) INF-67 revisited — already killed on its own terms. Work-stealing and cross-layer wavefront are 0 at
      batch-1: no independent work in the chain.
      **★ RECOMMENDATION: the structural lever is COARSER MEMORY STREAMS, not coarser graph nodes.** D6's
      placement-granularity fix (sub-2 MB tensors pinned to one NUMA node; `MADV_NOHUGEPAGE` / 4 KB interleave,
      measured penalty-free for streaming) is worth **~15 ms** and B2's per-expert split ~11 ms — both larger
      than the entire barrier budget. The SYNC siblings' options are **substitutes, not additive**, drawing on
      the same ~11 ms.
      **Close INF-67 Axis A on its own §6b(b).** Evidence: `/mnt/raid0/llm/tmp/inf70/agents/sync5/REPORT.md`.

- [ ] **SYNC-6 — THE DECIDER for the whole coordination axis: re-measure the existing D1 arms to ±0.2 ms.**
      Filed 2026-09-05 from SYNC-5. Zero new code, one bench window: `/mnt/raid0/llm/worktrees/inf70/d1` vs
      `d1-base`, 940 barriers removed, bit-exact. **≥0.5 ms ⇒ the primitive model holds, green-light the
      HC_MIX op (expect 1.5–3 ms) and let it decide option 4. ≤0.2 ms ⇒ barrier count is NOT the cost on this
      box: stop D2/D3/SYNC-1/SYNC-2 and this axis, and spend the coordination budget on imbalance (the two
      systematic stragglers `ffn_moe_logits-11` at 1,087 µs dead and `node_872` at 13× its siblings are
      1.4 ms/token on their own) and on placement.** Routed to SYNC-1, which owns the barrier-cost baseline.

- [x] ✅ **SYNC-5-ORIGINAL (superseded, retained for the record) — is there a COARSER graph?** Dispatched 2026-09-05.
      The structural question the four seams above cannot answer. **Must start from INF-67, which already
      tried a fused decoder block and FAILED — control arm graph-1T 350 ms vs fused-1T 1350 ms, ~4× slower,
      with "scratch churn" the named liability.** The deliverable is a correct diagnosis of WHY it failed and
      whether that cause is intrinsic to coarsening or an artefact of that implementation. "Do not pursue this
      axis" is an acceptable and valuable verdict.

- [x] **B10 — NO-GO 2026-09-05. Reduced-vocabulary drafting does not pay HERE, and the reason is L3.** ✅
      Measured with an own `-DGGML_CPU_PROF` build of `10221`/`c51e4dabf` (worktree `/mnt/raid0/llm/worktrees/
      inf70/b10`, knob proven compiled in), two region-locked arms, placement 0.1% dev, both COHERENT at a
      72-token production prompt.
      **★ THE FINDING THAT OUTLIVES THE TASK: the campaign's byte-based roofline OVER-PRICES DRAFT-SIDE WEIGHTS
      BY ~2×.** The draft head is the TRUNK's `output.weight` q6_K `[2560, 248320]`, 521.472 MB (the shared MTP
      GGUF carries no head of its own):

      | | ms/call | effective GB/s |
      |---|---|---|
      | `lm_head`, trunk graph (plain arm) | 3.742 | 139 — 94% of the 153 ceiling |
      | `lm_head`, MTP draft graph | ~2.0 wall / 1.55 compute | **260 — 1.7× the DRAM ceiling** (DERIVED) |

      **⚠ PROVENANCE, recorded 2026-09-05 before this hardens into a measured fact: only the 139 GB/s trunk
      figure is a printed `PATHROW` value. The 260 GB/s is B10's DERIVATION** from the MTP arm (386 evals =
      78 trunk + 308 MTP, with the 78 `process()` catch-ups excluded because they add with `logits=0` and
      stream no head bytes — `dst ne[1]=0` in the meta). B10 derived it two independent ways and the
      conclusion is corroborated from a second direction by SYNC-3's GDN state at 234 GB/s (also above the
      DRAM ceiling, also cache-resident), so the L3-residency finding does not rest on this one number. But
      **a derived rate is not an instrument reading**, and B12 is currently being asked to test a residency
      step change against it — so B12 must report the head node's rate from its OWN measurement rather than
      inheriting 260.

      Derived two independent ways from the MTP arm (386 evals = 78 trunk + 308 MTP; 78 MTP evals are
      `process()` catch-ups adding with `logits=0` and streaming no head bytes, confirmed by `dst ne[1]=0`).
      **260 GB/s is impossible from DRAM** — the MTP graph is only 144 nodes / ~105 MB of other weights, so the
      521 MB head substantially SURVIVES IN THIS BOX'S 384 MiB L3 between draft steps.
      **Cost future "shrink the drafter" levers against the measured 260 GB/s, never against 153 GB/s.**
      **Consequence for B10**: the head is **~4–5% of the settled 43.17 ms token**, not the 8.6% the byte model
      predicts. A K=65,536 slice ceilings at **+3.0–3.9%**; even a FREE head is only +5%.
      **α side (zero compute)**: rebuilt the model's BPE from the GGUF and tokenised all 97,858 tokens of
      COHERENT output from `speed-claim`. A contiguous id-prefix 64k slice — the only variant needing no new
      artifact and no remap — covers **97.95%**, because **Qwen's vocab is NOT frequency-ordered above 65k**
      (`'```'` = 71093, `'.**'` = 159029). That is **Δα ≈ −0.017 ≈ −2.6 to −3.4% — exactly break-even.** A
      frequency-ranked top-64k reaches 100% coverage on our mix but needs the offline builder, a new GGUF, a
      loader shape relaxation and a draft→target id map, for ~+3%. Upstream `#25187` independently measured
      **+1.4%** on a 5090.
      **Sub-questions all answered, and none of them is what killed it:**
      - **Correctness — output-lossless.** `server-context.cpp:3876` compares the TARGET's sampled id against
        the draft, so an out-of-slice truth is a REJECTED DRAFT, never a wrongly accepted token. α is the only
        currency at risk.
      - **Shared-head safety — SAFE, not a no-go.** The trunk builds its own full `mul_mat` in a SEPARATE graph;
        a `ggml_view_2d` row prefix used only in the MTP graph is a read-only alias.
      - **q6_K alignment — exact.** `QK_K=256`, `sizeof(block_q6_K)=210 B`, row = 10 blocks = **2100 B**
        (521,472,000 / 248,320 = 2100 ✓). A row slice is a contiguous byte prefix; no requantisation.
      - **★ CORRECTS the coordinator's own break-even correction** (which was itself wrong): our config runs
        `--spec-draft-n-max 4` AUTOREGRESSIVELY on the single head, so tokens/step is `Σα^i ≈ 3.79`, **not
        `1+α`**. Sensitivity is ≈1.5–2.0% throughput per 0.01 α, and break-even for the 64k slice is
        **α′ ≈ 0.79** — headroom exists, but the lever shrank to meet it.
      **Cheapest remaining probe in this family, needing NO CODE** (candidate, not filed as committed work):
      requantise the head to IQ4_XS into a new MTP GGUF's `blk.48.nextn.shared_head_head` — the graph already
      prefers that slot — 521 → 338 MB, expected **+1.4–1.8%**.
      Evidence: `/mnt/raid0/llm/tmp/inf70/agents/b10/REPORT.md`. No code changed, worktree clean, no commits,
      both servers verified dead.

- [x] ✅ **B10-ORIGINAL (superseded, retained for the record) — REDUCED-VOCABULARY DRAFTING for the MTP head.** Filed 2026-09-05 from an operator question
      ("how are people getting 2× this on a single DGX Spark?"). Source: `MiaAI-Lab/Qwen3.8-Flash-Next-Single-
      DGX-Spark`, which reports 46.3 tok/s single-stream on GB10 using vLLM + **MTP-3 with the draft head
      projecting over a REDUCED VOCABULARY of 65,536** instead of the model's full 248,320.
      **Why this is the one transferable item in that repo** (NVFP4 needs Blackwell; FP8 KV loses on our stack
      per B9; PLE offload is a GPU-memory concern and we have 1.1 TB): the draft head's output projection is a
      248,320-row GEMV on EVERY draft step, and **we are no longer bandwidth-bound under MTP** — 25.4 GB/s
      actual, 16.6% of the 153 ceiling — so we are dispatch/compute-bound, precisely the regime where cutting
      that matrix ~3.8× should pay. Cheap to falsify: restrict the draft head's logits to a top-K vocabulary
      slice and measure α plus decode t/s. **The gate is α**: a smaller vocab that costs acceptance is a loss
      (B9's lesson — the metric that pays under speculation is α, not bytes).
      **Scope note:** the 2.00× headline gap is NOT evidence we are leaving 2× on the table — GB10 has 273 GB/s
      unified vs our 153 GB/s achievable (1.78×) plus far more compute, so the gap is close to the hardware
      null. File this on its own merits, not as a chase.

- [x] **B11 — CLOSED 2026-09-05 AS A NON-QUESTION. There is no missing 38%; the premise was wrong.** ✅
      The coordinator's arithmetic used two wrong inputs. Ground truth from a from-scratch GGUF reader (no
      binary involved, so build-freshness does not bind it): **4.1656 GB/token**, agreeing with the live-graph
      ledger to **+0.24%**.
      - **6.671 B active params, not 6.0** (+11.2%)
      - **4.995 effective bpw, not 4.0** (+24.9%) — **`IQ4_XS-uniform` IS NOT UNIFORM**: lm_head q6_K,
        `attn_qkv` q5_K, `ffn_down_exps`/`hc_*_up` iq4_nl, and the router `ffn_gate_inp` is **F32**.
      - **1.112 × 1.249 = 1.389** — the "missing 38%", exactly and entirely.
      **Provenance of the original number is clean**: 51.3 GB/s was DERIVED as `12.349 t/s × 4.156 GB/token`
      (`agents/speed-claim/REPORT.md:87`), and the 4.156 came from `agents/prof/` instrumenting the LIVE decode
      graph (`GGML_CPU_PROF`) — summing `ggml_nbytes(src0)` per MUL_MAT and `n_expert_used × nb02` per
      MUL_MAT_ID, re-derived independently from `pernode.tsv` at 4.1558 GB. Not file-size division (that would
      have given 98.4 GB). **So the number was right and the interpretation was mine.**
      **★ Three structural findings worth more than the question was:**
      1. **The GatedDeltaNet stack is 30.3% of the token (1.261 GB) — as large as ALL expert traffic**, and
         `attn_qkv` alone (648.8 MB) exceeds lm_head. **"6B active, mostly experts" is the wrong mental model**;
         experts are under a third of the bytes.
      2. **The F32 router costs 251.7 MB/token — 6.0% of the budget for 0.25% of the active params.**
      3. The ledger is weights-only and omits **~226 MB/token of GDN recurrent state** (113 MB `GET_ROWS` +
         113 MB `CPY`) plus ≤100 MB KV. Honest total **~4.40 GB/token → 54.3 GB/s = 35.6% of the 152.6 ceiling**
         (not 33.5%). **This strengthens the campaign's thesis**: still only ~36% of ceiling, so the deficit is
         latency/sync, not bytes. (NON-CLAIM — arithmetic, not a counter.)
      **Hypotheses refuted, both structurally rather than by measurement:** `GGML_MMID_SLAB` partitions
      `n_groups × ne01` rows where `n_groups` is the distinct-used-expert count, and only when `cne1 == 1`
      (`ggml-cpu.c:1840-1900`) — it changes which thread reads which run, not the row set; both methods give
      1.2964 GB identically. The **PLE table is off by three orders of magnitude**: one gather site
      (`ple.layers=[1]`), 16 rows × 90 B = **1.44 KB/token**; even charging a full 2 MB THP per row gives 32 MB,
      and DRAM is 64 B-line granular so the real cost is ~2 KB. **The 28.8 GB PLE table is a TLB/latency object,
      not a bandwidth object** — which retrospectively explains B7's null from a second direction.
      **Levers this hands us (both already on the board):** quantising the F32 router (**B4**) saves 251.7 → 62.9
      MB = 4.5% of the token AND hits the worst straggler in the graph (those 48 nodes: 4.197 ms wall for 2.102
      ms compute, containing the token's single worst node at 1118 µs wall / 32 µs compute) — bytes and
      imbalance in one change. Runner-up on ms/effort is **D6**: `GET_ROWS` is unconditionally single-task,
      moving 113 MB at 13.1 GB/s on one core for **8.4 ms = 8.7% of the token**.
      **Optional hardware confirmation** (not run, not needed for the verdict): one locked `llama-bench tg128`
      under `perf stat` on the DF/UMC read counters; predicted delta 6% vs the 1.1% in-window repeat.
      Evidence: `/mnt/raid0/llm/tmp/inf70/agents/b11/` (`REPORT.md`, `gguf_inv.py`, `inv.json`).

- [x] ✅ **B11-ORIGINAL (superseded, retained for the record) — where does 4.15 GB/token go?** Plain decode moves 51.3 GB/s at 12.35 t/s = **4.15 GB/token** for a
      model with ~6B active parameters at ~4 bits (~3 GB). That is ~38% more traffic per token than the active
      weights account for. Candidates: expert-gather read amplification (we touch whole slabs, not just used
      rows), the PLE table gather, or a scope error in the bandwidth accounting itself. **Rule out the
      measurement first** — confirm what the 51.3 GB/s counter includes before attributing it to the kernel
      ([[feedback_verify_test_method_before_calling_it_a_bug]]). If real, it is a larger lever than anything
      remaining on Axis B: a 38% traffic reduction on the plain path is worth more than every merged kernel
      change in this campaign combined.

- [x] **INF-71 — EXL3 `mul1` trellis experts.** ⚠ **RENAMED 2026-09-07 from "B7" — that label COLLIDED with the CLOSED PLE-precision B7** (ANSWERED NO 2026-09-04: higher PLE precision buys no quality; BF16 would cost **+25.6 GB resident for nothing**). Two different items carried one ID and the closed one could shadow the live one. **This is the live item, and the operator has just prioritized it; every "B7" elsewhere in this file resolves to the CLOSED PLE item.** turboderp published EXL3 weights for this
      model on 2026-08-31 (`turboderp/Qwen3.8-Flash-Next-exl3`, 2.05–6.05 bpw, MTP head at 4 bits,
      `mul1` codebook), and exllamav3 ships an AVX-512/VNNI CPU GEMV for exactly that codebook whose decode
      fuses into the `vpdpbusd` the gemv already needs (~4 vector uops per 16 weights — IQ4_XS-class, unlike
      ik_llama.cpp's slow 3INST trellis types). At 3.05 bpw the expert stream drops ~0.4 GB/token. Spec,
      phases, gates and hazards: [`exl3-trellis-cpu-kernel.md`](../completed/exl3-trellis-cpu-kernel.md). Do not start it
      before C0/C5/B1/D0 rank the levers.
      **❌ NO-GO 2026-09-07, OPERATOR-CONFIRMED. Artifacts reclaimed (180 GB).** Report:
      `/mnt/raid0/llm/tmp/inf70/agents/inf71/REPORT.md`. Phase 1 as briefed **had already been executed
      2026-09-02** (X-DL, X0, reference half of X1; committed `15c4af65`) — re-running it would have been
      duplicated work. What decided it is new: the lever **re-priced against the CURRENT champion, 1.50× faster
      than the token X1 priced against.** Our own serving mode (MTP) now runs at **16.6% of the DRAM bandwidth
      ceiling** — a bytes-per-weight lever cannot pay there, and champion-3 moved the operating point **further
      from bytes-bound**. The written reopen trigger ("reopen when Axis D has moved the floor enough that the
      expert stream binds") has moved **away**, not toward.
      **★★ FOUR FACTUAL CORRECTIONS TO OUR RECORD THAT MUST SURVIVE THE NO-GO** (all applied in
      [`exl3-trellis-cpu-kernel.md`](../completed/exl3-trellis-cpu-kernel.md)):
      1. **There is NO separate MTP head in the EXL3 weights** — zero `mtp.*head*` tensors. **X5's premise is
         VOID**, and Axis E would inherit **MORE** head bytes, not fewer.
      2. **The 3.05 branch is `mtp_bits: 3`, not 4.**
      3. **Vision is on the 3.05 branch, NOT 4.05 — the handoff had it INVERTED.**
      4. **`byte_pair_ok` pairs fully at K=4 but only on rows 8–15 at K=3** — that is the mechanism behind the
         measured **17.3 vs 9.4 GB/s per core**, previously recorded as an unexplained gap.
      **Counter-proposal recorded, not dropped (the reopen precondition):** the port's gate ordering is
      **INVERTED** — the 3.05 bpw *quality* question, the largest variance source and the one that can kill the
      lever outright, is gated **behind** 5–7 sessions of porting. It can be answered for **~2–5 GB of targeted
      download and one zero-inference session, no bench lock.** If INF-71 is ever reopened, that is FIRST.

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

**Sequencing after the operator's 2026-09-03 "proceed" (recorded by the coordinator):** every MTP branch
(`inf70/mtp` → `mtp-27941` → `mtp-exact`) is based on the OLD `c035bbf3d`, eight commits behind the fast tip, so
no MTP number has yet been measured on the 12.55 t/s kernel. In flight, disjoint: (1) `mtp-tip` — rebase the
stack onto `0d2af8194` and port the E2b-2 rollback trio (the throughput lever); (2) `e3-alpha` — E3 on the
existing build (α is head-vs-trunk, speed-independent, so it need not wait); (3) `gdn-rowexact` — the lossless
gate. Integration order once they land: GDN fix onto the tip → MTP stack on top → **lossless gate**
(`LLAMA_SPEC_EXACT=serial` ≡ MTP ≡ concurrent-prefill ≡ plain, token-for-token) → E-GATE with the sampler
named. MTP is not a serving option until that gate passes.

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
- [x] **E2a — CLOSED negative 2026-09-03: the divergence is the batched target forward, not the bonus token; no driver-side fix exists.** Prompt 1 diverges at generated token 28: the MTP arm accepted
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
      *approximate* speculation for research measurement, exactness claim dropped. **E2c settled (2026-09-02, first Fable-low agent): the qwen4exp forward IS batch-size dependent, in the stock path — see E2a's E2c note above.** Same prompt through
      `-b 1 -ub 1` vs default batching vs `-b 8 -ub 8` on the unpatched build, greedy ids and top-5
      logprobs compared — if they differ, every prefill-vs-decode comparison in this campaign inherits
      the finding, not just speculation. Then (a)/(b)/(c) is the operator's decision; the E2 agent's
      recommendation is (c) with no serving exposure, and to keep `inf70/mtp-27941` as a correctness
      rider regardless. **E2c settled where the non-exactness lives (2026-09-02, report reconstructed
      from its `runs/` data): it is in the STOCK qwen4exp path, not the iqk kernels** — with `GGML_IQK=0`
      the ub512-vs-ub1 greedy streams still diverge, just later (byte ~2157 / ~token 400 instead of token
      28); a dense Qwen3-32B is bitwise batch-invariant on the same build and every MoE tried is not. The
      non-exactness is a property of the hybrid operators (GDN scan / PLE conv / QSA indexer); iqk only
      brings the first flip earlier. **The fix belongs in the qwen4exp multi-token kernels (an
      INF-67/kernel task), not the MTP driver.** E-GATE depends on it. **RESOLVED 2026-09-03 (mtp-exact, measured):
      both driver-side option-(a) shapes FAIL the 3×128 greedy-identity gate — `drop` the bonus token 2/3
      FAIL, `redecode` it single-token 0/3 FAIL — because every failure is at a VERIFIED row, not the bonus:
      the verified tokens themselves ran the chunked GDN kernel and are already non-exact. The exact-by-
      construction control `Mserial` (re-decode every token single-token, no batched verification) is
      byte-identical 3/3 but runs at 9.8–10.1 t/s = plain-decode speed (no speedup). Root cause pinned to
      `src/models/delta-net-base.cpp:435`: `n_seq_tokens == 1 → build_delta_net_autoregressive`, else
      `build_delta_net_chunking` (CS=64) — the two are not row-exact, and this ONE divergence is the common
      cause of E2a, E2c AND X-CONC (concurrent prefill). **Lossless MTP is therefore impossible at the driver
      level; the only lossless path is option (b): make `build_delta_net_chunking` bit-equal to k
      autoregressive steps for small n — a kernel task that ALSO fixes X-CONC and E2c.** Branch
      `inf70/mtp-exact`; evidence `/mnt/raid0/llm/tmp/inf70/agents/mtp-exact/`. **Operator decision 2026-09-03: option (b) FUNDED (task GDN-ROWEXACT below, in flight).** Until it
      lands, MTP stays approximate and the merged non-MTP kernel (`0d2af8194`, 12.55 / 13.06 t/s) is the
      lossless serving path.
- [ ] **E2b — recurrent-state checkpoints per draft round (measured).** Every verification round writes a
      **112.571 MiB** speculative checkpoint and restores it on rejection: 66 created / 18 restored per
      three 64-token requests (0 / 0 without a head) ≈ **9.4 GiB of serialized memcpy per 192 tokens,
      ~49 MiB/token**, on top of the weight stream; no re-prefill observed. Rollback itself works (p2/p3
      stayed identical); it is paid with a copy instead of an in-place rewind. **E2b-1 ✅ done 2026-09-02:
      `36b101543` (#27941) ported on `inf70/mtp-27941` — no regression, checkpoints unchanged (31/2), not the
      E2a fix.** **E2b-2 ✅ PORTED AND VALIDATED on the fast tip 2026-09-03** (agents `mtp-tip` + `mtp-tip-report`,
      branch `inf70/mtp-tip` @ `08f087e87`, not merged/pushed): the rollback trio `b1c1c99c6` (upstream `1692f9e50`
      #26623, ggml `ssm_scan` rollback snapshots) · `ea3f50dda` (`0eadefebd` #28123, qwen4exp rollback) ·
      `3a00401d1` (`9d817213a` #28159, load `n_layer_nextn` before `n_layer()`) · plus companion fix `08f087e87`
      (NextN/MTP layers inherit the trunk's per-layer head/ff counts — REQUIRED in this tree: without it, build
      10211 read the per-layer arrays over 48 not 49 so `n_head_kv_arr[48]=0`, giving a NULL K/V alloc with the
      shared head and a `ggml_set_rows` shape assert in the server's no-alloc dry run with the self-contained one —
      one defect, both symptoms; provably trunk-side perf-neutral, T0b 12.509 on 10211 vs 12.570 on 10212,
      bit-identical output). **Result: speculative checkpointing ELIMINATED — 407 created / 113 restored → 0/0 over
      the same workload** (112.571 MiB each = 44.7 GiB, 4.97 GiB/request, ~39.8 MiB/token of avoided traffic on a
      4.16 GB/token model); `n_rs_seq=2` survives instead of being clamped to 0. **MTP decode 17.582 → 18.125 t/s
      (+3.09%); multiplier over trunk 1.391× → 1.442× — NON-CLAIM, MTP remains APPROXIMATE.** **SUPERSEDED 2026-09-03 by the production-length measurement: the multiplier is 1.380x, NOT 1.442x**
      (`mtp-tip2` Task C, NON-CLAIM): 12.505 -> 17.254 t/s against the SAME-BUILD MTP-off control, **12/12 COHERENT
      at 54-441 prompt tokens**, on the corrected kernel. **The 1.442x was a 12-token-prompt artefact and must not
      be quoted as production.** The scope note below is retained because it is what forced this measurement.
      **SCOPE OF THOSE
      NUMBERS (verified from the run JSONs 2026-09-03, after an operator challenge): the timed reps used a
      12-token prompt and their full 128-token output is COHERENT on 5/5 reps in every arm (word uniq 0.742, top
      share 0.086, max repeat run 1) — the speeds are NOT decode-of-garbage. The 101-token probe on the same builds
      is degenerate (uniq 0.025, top 0.988, run 77), so the two regimes are cleanly separated. Two limits follow:
      (i) MTP output still DIFFERS from plain at 12 tokens on 2 of 3 gate prompts (p1/p3 DIFF, p2 SAME — the E2a
      flips, unchanged by rebase and by E2b-2): coherent, but not what the trunk alone would say; (ii) **the 1.442×
      is demonstrated ONLY in the short-prompt regime, because every longer prompt is currently broken — speculative
      acceptance varies with context length and content, so the multiplier at PRODUCTION prompt lengths is UNKNOWN,
      not assumed.** State it as "1.442× on short prompts; production-length figure pending the iqk fix" (that
      measurement is exactly the blocked E3). The +3.09% E2b-2 delta is the most robust number here: identical
      coherent workload, checkpointing on vs off, mechanism independently visible as 407/113 → 0/0.** Rebase itself was
      trunk-invisible (REF 12.513 → T0 12.643). Gates: (a) trunk-only byte-identical to plain `0d2af8194` PASS short,
      **BLOCKED long** — `T0b ≡ REFL` byte-for-byte, and REFL is the PLAIN tip with no MTP code, which proves the
      long-prompt garbage is not ours; (b) MTP live PASS; (c) `LLAMA_SPEC_EXACT=serial` ≡ plain PASS short AND long;
      (d) `ARCHS_RC=0`, `test-backend-ops -o SSM_SCAN` 6/6; (e) rollback correctness M1 ≡ M1b token-identical and
      M1bself ≡ M1b. **Caveat recorded by the agent: M1b's better-looking long output is NOT evidence MTP fixes
      anything — both streams are degenerate, MTP merely perturbs which attractor the corrupt logits fall into; the
      long-probe 1.59× must not be quoted.** **No exact-and-fast configuration exists today: `serial` is byte-exact
      but SLOWER than trunk (11.69 vs 12.57 t/s), and the approximate-mode flips sit on a build with a known-wrong
      GEMM — exactness re-opens after the iqk fix, it is not settled.** Blocked only on LONG-PROMPT-GARBAGE
      (`gdn-fix-validate`); then re-run the long probe, re-characterise exactness, and decide promotion of the trio.
      **Pre-promotion check owed:** upstream `9d817213a` reads those arrays the same way, so either upstream fixed it
      later or its MTP path never allocates that layer's K/V — one upstream-diff check before any promotion.
      Evidence `/mnt/raid0/llm/tmp/inf70/agents/mtp-tip/{REPORT.md,runs/,compare_all.py}`.
- [ ] **LONG-PROMPT-GARBAGE — P0, blocks every serving claim: the fusion tree's qwen4exp path degenerates to
      garbage on SINGLE-sequence prompts above ~23–42 tokens.** Found 2026-09-03 by the coordinator's long-prompt
      check on the deployable tip `0d2af8194` (42/81/233-token prompts all degenerate, placement + linkage proven)
      and independently by E3 on the old base — so it predates every merged lever and the MTP port. Same defect
      family as GDN-ROWEXACT / X-CONC / E2c at a far lower bar: one sequence, no concurrency, no MTP. Clean repro
      `/mnt/raid0/llm/tmp/inf70/longprompt/`. **ROOT CAUSE FOUND 2026-09-03 (`gdn-rowexact`, node-level trace, evidence
      `/mnt/raid0/llm/tmp/inf70/agents/gdn-rowexact/`): iqk's `is_dequant_better()` (`iqk_mul_mat.cpp`) switches
      IQ4_XS to a requantised `Q8_K_R16` repack GEMM when `nrc_y >= 32 && npt >= 16`, and that converter/kernel is
      WRONG on this host** — first gross error `z-0 = mul_mat(blk.0.attn_gate IQ4_XS [2560×6144], 42 rows)`, every
      element off (max 1.2e3) already at row 0; the tree already excludes IQ2/IQ3 from the same path for the same
      reason. **The GDN kernel is NOT involved** (see GDN-ROWEXACT below). This one mechanism explains all three
      symptoms: single prompts ≥ ~32 tokens, X-CONC (4 simultaneous 12-token prompts = a 48-row ubatch; staggered
      = < 32 rows), and `GGML_IQK=0` clean. **It PREDATES the fusion lineage**: pre-fusion build 10128 (which does
      run iqk) is degenerate too — every iqk-build pp/coherence result on this model above ~32 rows was a wrong
      forward. **Serving workarounds today (unpatched tip): `-ub 1`** (coherent on 42/81/233; decode UNCHANGED
      12.5–12.7 t/s; prefill ~10× slower, 13.5 vs 68–140 t/s) **or `GGML_IQK=0`** (coherent; pp 118.9 vs 135–140).
      **Fix committed `99425578d` on `inf70/gdn-rowexact`**: IQ4_XS returns to its direct iqk kernel for every Ny
      (+ `GGML_IQK_DEQUANT=0` knob disabling all Q8 repacks). **FIX VALIDATED 2026-09-03 — PARTIAL BUT SHIPPABLE (`gdn-fix-validate`).**
      **G3 PASS (the gate protecting every merged lever): n=1 greedy decode BYTE-IDENTICAL to control 10203** on
      3×128; `test-backend-ops -o MUL_MAT -b CPU` 1139/1139, `-o MUL_MAT_ID -b CPU` 815/815 (B3-k slab path
      untouched), `test-llama-archs` zero FAIL. **G4: decode 12.69 t/s — no regression** (control 12.64, baseline
      12.55). **pp512 189.3 t/s on the fixed build vs 135.6 for the correct `GGML_IQK=0` fallback (+39.6%).**
      **WITHDRAWN: the control's 231.4 t/s pp512 and its 135–140 t/s at p200 — they timed a salad-producing
      forward.** At 42 rows the broken repack requantised a whole tensor for 42 columns of reuse, so it was slower
      *and* wrong; the correct-repack crossover is between 42 and 512 rows.
      **BLAST RADIUS AND REPAIR, measured on one prompt set (`mtp-tip2` PRE control) — the cleanest single piece
      of evidence for this defect.** Same prompts, pre-fix `0d2af8194` vs fixed `42332502c`:
      | prompt | prefill rows | PRE (pre-fix) | P (fixed) | PRE vs P |
      |---|---|---|---|---|
      | g1 / g2 / g3 | 5–11 | coherent | coherent | **SAME (byte-identical)** |
      | L1_p40 | **42** | `">>\n.>\n.>\n.>…"` pure degeneracy | coherent | DIFF@0 |
      | L2_p90 | **81** | `" The function would\nl\ne\nl\nl…"` | coherent | DIFF@0 |
      | L3_p200 | **236** | degenerate loop, truncated at 39 tok | 128 tok coherent | DIFF@1 |
      | L4_p600 | **429** | **HTTP 500** | 128 tok coherent | n/a |
      **Every prompt below 32 prefill rows is byte-identical across the fix — the defect never touched them, and
      the fix changed nothing it was not supposed to — while every prompt at or above 32 rows was degenerate,
      truncated or fatal before and is coherent after.** The predicted `nrc_y >= 32` boundary confirmed end-to-end
      rather than inferred. L4 is the defect at its worst: not merely wrong text but *unparseable* text
      (`common_chat_peg_parse: full Content-only output triggering error` → a 500), i.e. an availability failure,
      not only a quality one. **Scope: confined to the experimental fusion tree — production serves v9 from a
      different tree that never carried the commit, so there is NO production availability implication.** It also
      retro-justifies the re-run: every production-length measurement taken on the pre-fix build was on a binary
      that could not generate valid text at those lengths.
      **The residual p200 failure is NOT a second kernel defect — it is PROMPT-SPECIFIC, not length-specific.**
      p200 truncated to 120/160/200/220/230 → all COHERENT; full 233 → EARLY-EOS deterministically (margin 0.0169
      nats, 3/3 runs); **9/9 different 107–181-token prompts COHERENT** (margins 2.2–8.0) where the control fails
      0/9; **p200 through the chat template is COHERENT** (the control is broken even there). Node trace at the
      failing shape: worst node deviation **0.949 vs 2.0e+3 pre-fix**, argmax agrees 221/233 rows — no gross error
      remains. Mechanism: every batched 233-row forward deviates from the exact `-ub 1` reference by O(0.3–1.4
      nats) **including stock ggml at `GGML_IQK=0` (+1.4)**; p200's exact top-2 gap is 0.457 nats, the only prompt
      in the set below that envelope, so its argmax flips. **Coordinator's Q5_1/Q6_K + DEQUANT-knob hypothesis
      REFUTED** (my error): `iqk_dequant_enabled()`'s `return type` is at `iqk_mul_mat.cpp:293`, **above** the
      switch, so it covers Q5_1/Q6_K/Q5_K/Q4_K — every branch; empirically `g0m` (`DEQUANT=0`) and `g0k`
      (`ROWEXACT_N=256`, an independent bypass that never calls the function) give identical p200 logprobs to 4
      decimals. GGUF census: IQ4_XS 586, IQ4_NL 182, Q5_K 54, Q5_1 12 (`blk.0-5.ffn_down_exps/shexp`), Q6_K 1
      (`output.weight`); their measured effect at 233 rows is ~0.04 nats — lossy-but-working, worth ~10% prefill,
      **keep them**. **Classifier defect fixed** (coordinator's): `client.py degeneracy()` scored n=1 as degenerate;
      new `classify.py` classifies by REASON (HTTP-ERROR/EMPTY/EARLY-EOS/SHORT/SALAD/COHERENT), stats only at n≥16 —
      every p200 "DEGENERATE" on the fixed build re-reads as **EARLY-EOS (1 token)**, and `g0j`'s 19-length sweep
      (k=8…361) is COHERENT or correct-SHORT at EVERY length. **Verdict: safe at every length measured (8–361 tokens) through the chat template. The fix carries NO
      residual defect — see the RECLASSIFICATION below; what was filed as its residual risk turned out to be a
      property of one raw prompt, not of the fix. **RECLASSIFIED 2026-09-03 — a PROMPT-SHAPE caveat, NOT a fix caveat. This is the settled, final position;
      two earlier ones of mine were wrong and are recorded rather than dropped.** Measured, not inferred:
      | probe | path | n_pred | stop | top-2 gap |
      |---|---|---|---|---|
      | a_raw | default | 1 | eos | **0.01695 nats** |
      | a_raw | `GGML_ROWEXACT_N=512` | 1 | eos | **0.092 nats** — still EOS, **no flip** |
      | b_cue (`\n\nAnswer:`) | default / rowexact | 128 | limit | 2.249 / 2.971 |
      | c_chat | default / rowexact | 128 | length | **4.74 / 4.28** |
      **No argmax flip occurs under either kernel path**, so it is not a residual defect of the iqk fix — and no
      kernel fix could remove an inherent knife-edge anyway. What IS true: p200's first token is a **0.017-nat
      near-tie (27× tighter than the 0.457 originally published)**, and changing only the GEMM batching moves that
      gap by 0.075 nats — about 4× the gap itself — so the decision is demonstrably batch-shape *sensitive* while
      remaining batch-shape *stable* in outcome here. **Templating removes the fragility entirely** (0.017 → 2.25–4.74
      nats), so **production serving through the chat path has no exposure to this at all.**
      My two superseded positions, kept because I stated both: (1) "DISPUTED / leaning-downgrade" — wrong, because
      (b)/(c) generating is evidence FOR a knife-edge, not against it (the cue's winner is exactly the cue-free
      runner-up, i.e. it breaks a real tie); (2) "confirmed and severity RAISED" — wrong, because no flip actually
      occurs. **⚠ Instrument caveat: `.eosprobe.log`'s gap column is UNRELIABLE** — `eosprobe.py` read
      `probs`/`top_probs` where llama.cpp emits `top_logprobs`, so the live log printed `top2_gap_nats=None`;
      `regap.py` recovers every gap from the persisted JSON and is authoritative (except `c_chat`, whose gap is in
      the raw JSON only). Trusting the log line would have reported the question unmeasurable.
      **Gate B4 PASSES**: `test-llama-archs` `ARCHS_RC=0`, qwen4exp CPU MoE OK (0.00e+00), **0 FAIL rows**. Exact fallback `-ub 1` verified
      byte-identical. **MERGED into `exp/cpu-fusion-qwen4exp-20260829` 2026-09-03 (operator direction) — merge commit
      `42332502c`, merged tree SHA `6aaab89c1` bit-identical to the gated `inf70/gdn-rowexact`, so every gate above
      transfers verbatim; production tree untouched.** Includes `aa2aef969` (guard lift above `#ifdef __AVX2__`, so
      the `GGML_IQK_DEQUANT` kill-switch covers both SIMD arms) — **proved a no-op from the COMPILED OBJECT, not
      asserted: 13 of 10,920 disassembly lines differ and every one is a `GGML_ASSERT` `__LINE__` operand shifted
      +2 by the added comments; zero instruction-sequence differences.** G3 three-way byte-identity (lifted ≡
      pre-lift ≡ control b3k 10203), `MUL_MAT` 1139/1139, `MUL_MAT_ID` 815/815, `test-llama-archs` 0 FAIL,
      coherence classifications identical to pre-lift to the digit. **Task closed; the P0 no longer blocks
      serving.** Deployable numbers are being RE-ANCHORED on the merged tip with PRODUCTION-LENGTH prompts (27
      prompts, ~40–600 tokens, 8 coding / 8 reasoning / 8 general + the 3 P0 prompts, chat-completions path with
      thinking disabled, coherence classified by REASON in the same window as the timing) — evidence
      `/mnt/raid0/llm/tmp/inf70/reanchor2/`. **The old short-prompt figures are NOT being restored.** No serving or deployable-speed
      claim on this tree until it passes.
- [x] **BATCH-ENVELOPE — SOLVED 2026-09-04 (`batch-envelope`). MTP on qwen4exp IS LOSSLESS; the divergence was
      never MTP, it was TWO CPU kernels that are not row-exact under batching. Both named with node-level evidence.**
      `TXF vs MXF: SAME on all 7 gate prompts` including the 429-token one, at **1.32–1.53× decode** — **and note what BE-2 later established: the `-fa off` those arms
      used was avoiding an upstream TG optimisation, not a bug. Exactness at depth requires `GGML_FA_SPLIT_KV=0`
      (or `-fa off`) and costs ~5.7% decode at 4k; the DEFAULT split path is the fastest configuration. So the
      accurate statement is "lossless is available at ~5.7% decode cost at depth, and is not the fast option".**
      **⚠ FIRST: retract the standing exclusion — it was a VACUOUS VERIFICATION, not a negative.** I published
      "the flips are NOT the batched mul_mat" three times, resting on `GGML_ROWEXACT_N=512`. **That knob has never
      had any effect on any tinyBLAS mul_mat.** `llamafile_sgemm` hard-refuses `n < 2`
      (`ggml/src/ggml-cpu/llamafile/sgemm.cpp:3713`), so the per-column loop at `ggml-cpu.c:1379` failed on its
      **first** column every call and fell straight through to the full-batch tinyBLAS GEMM immediately below it.
      Proof of inertness (the mutation test I should have demanded before believing the exoneration): knob ON and
      knob OFF produce a **byte-identical node trace** — same first differing node, same max|d|, same 85,390,493
      differing state bytes. Every conclusion that rested on that knob is withdrawn.
      **Carrier 1 — the F32 tinyBLAS `mul_mat`, i.e. the MoE router `ffn_gate_inp`.** It runs a tiled batched GEMM
      at `ne11=3` and the generic `vec_dot` path at `ne11=1` — a 1-ulp difference that MoE top-k selection
      amplifies. With it genuinely made row-exact, a 3-row batch is **bit-identical to 3 single decodes** (logits
      0 of 248,320 differ; recurrent state 0 bytes differ). **That alone converts 5 of 7 prompts to lossless**, and
      kills the two flips that had survived everything else (`g1@28`, `g3@84`).
      **Carrier 2 — `ggml_flash_attn_ext` on CPU is not row-exact once `n_kv > 256`.** Bisected: n_kv **253 exact,
      257 divergent**, and only the boundary-crossing row is wrong (`node_584 FLASH_ATTN_EXT [256,24,3]`). `--fa 0`
      makes the identical shape bit-exact at prefix 254 and 300 while `-fa on` diverges. **It predicted the two
      remaining survivors before they were measured**: L3_p200's 236-token prompt diverges at generated token 24 —
      position **260**. Next discriminator: `test-backend-ops -o FLASH_ATTN_EXT -b CPU` at n_kv=257, n_q=3 vs n_q=1.
      **Why carrier 2 was invisible for so long**: the tracer's default `n_ctx` capped every run at 256 tokens per
      sequence — exactly below the boundary. Fixed in `332f9ef56`.
      **The recurrent/GDN path is EXONERATED — do not fund it.** The fused GDN op is bit-exact at prefix 8, 230,
      250, 254 and 300; nothing in `ggml_ssm_scan` needed changing. Origin is not prefill and not the
      `embeddings_nextn` graph change either: SX (head loaded, same batched prefill, serial verify) is
      byte-identical to TX on all 7.
      **Cost**: trunk decode unaffected (TXF 12.74–12.91 vs P 12.60–12.86); **prefill −15…−20%** at 236/429 tokens.
      Note the serial oracle costs −7% on DECODE, so **lossless MTP is +55% over the previously recommended
      exactness path** — the exactness/speed trade we thought we faced does not exist.
      **⚠ The kernel commit is a DIAGNOSTIC, NOT MERGE-READY**: `f7f2d4708` (`GGML_MM_TRACE` + `GGML_ROWEXACT_GENERIC`)
      and `332f9ef56` on `inf70/batch-envelope`, not merged, not pushed, **no static tests**. A shipping version
      should either **bound `GGML_ROWEXACT_N` to ~8** — enough for a 3-row verify batch at **zero prefill cost** —
      or make the tinyBLAS tiling row-invariant. That bounded form is the obvious next task.
      Evidence: `/mnt/raid0/llm/tmp/inf70/agents/batch-envelope/REPORT.md`.
- [x] **INSTR-1 ✅ 2026-09-04 (`instr-b7`) — co-residency attribution shipped to 22 harness scripts** via one
      shared helper `/mnt/raid0/llm/tmp/inf70/lib/coresidency.sh` (9-line additive block after `set -u`; log format
      extended, not restructured; all pass `bash -n`). **Four refinements the live box forced, each of which would
      otherwise have RECREATED the false alarm:**
      1. **Thread-UNION affinity, not the main thread** — `llama-server`'s main thread reads `cpus_allowed=0` while
         the union reads `0-94/n=48`; main-thread-only would misread a GPU-side server (main on cpu 0, workers on
         184-191) as a CPU squatter — precisely today's error.
      2. **`gpu_fd=yes/no`** (`/dev/kfd`, `/dev/dri`) — **this is what actually cleared today's process**: the
         autokernel `llama-bench` runs with an UNCONSTRAINED `0-191` mask and self-places on the GPU host threads,
         so affinity alone returns UNCLASSIFIED.
      3. **`sched_in_region=k/n`** (`/proc/<tid>/stat` field 39) resolved by **majority, not "any"** — a GPU-side
         `llama-bench` shows `1/2`, and an "any" rule would re-create the false alarm.
      4. **Delta CPU, not `ps %CPU`** — `%CPU` is cumulative, so five idle `opencode` processes read a steady "45%"
         and crowded out the real workload (`feedback_measurement_attribution_hygiene`).
      **Live output positively identifies today's mystery process**: `exe=…/autokernel/loop-memory/anchor-gen-016/
      bin/llama-bench … gpu_fd=yes cpus_allowed=0-191 verdict=UNCLASSIFIED effective=GPU-SIDE-by-fd`, and an earlier
      sample caught the same binary pinned: `cpus_allowed=184-191 verdict=GPU-PEER`. **The operator's hypothesis is
      confirmed by direct evidence: it was the autokernel session's GPU work, not a lock violation.** 0.27 s/sample
      over 2317 processes; parent-death self-exit tested, no orphans. Deliberately NOT applied to
      `agents/speed-claim/arm*.sh` — that agent is executing those files right now
      (`feedback_never_edit_running_shell_script`); a 5-line patch is prepared for its next arm boundary.
- [x] ~~INSTR-1 (original text)~~ — the co-residency sampler records PID + etime only, so it cannot tell a lock violation from
      legitimate concurrent GPU work.** Filed 2026-09-04 after I mis-called exactly that. `be2-fa` flagged a foreign
      `llama-server` in 83 of 147 samples while it held all four CPU bench regions, and I recorded it as a
      coordination violation. **On the operator's challenge that it was probably the autokernel session — which is a
      HIP/MI210 campaign whose handoffs reference HIP graphs, `HIP_MMQ_MFMA` and GPU serving gates — that is the far
      more likely explanation, and it is NOT a violation at all**: the region lock covers the CPU regions q0–q3, a
      GPU-resident serving gate needs none of them, its weights live in VRAM rather than streaming from DRAM, and
      GPU host threads pin to 184-191 rather than our 0-95. Concurrent GPU work alongside a CPU bench is
      by-design (`feedback_concurrent_inference_is_bydesign`). **I could not prove it either way from what was
      captured, and that is the actual defect**: the sampler logs only `comm(pid,etime)`.
      **Fix**: record, per sampled process, the **binary path** (`/proc/<pid>/exe` or `cmdline`) and the **CPU
      affinity mask** (`/proc/<pid>/status` `Cpus_allowed_list`), plus whether it holds any region lock. Then
      "foreign process during my window" resolves immediately into "GPU peer on 184-191, ignore" or "CPU peer on
      0-95, real contention" — which is the difference between a shrug and an incident. Cheap: two extra reads per
      sample in the existing sampler loops (`agents/*/arm.sh`, `reanchor2/arm.sh`).
- [ ] **HYG-1 — the stale shared build dir is a live trap; rebuild it or remove it.**
      `cpu-fusion-20260829/build-cpu` (Sep 1) sat two days behind its source and cost a full investigation — four
      hypotheses raised and retracted across two investigators, none of which source-level reasoning could have
      caught, because the source was correct. The shared tree holds **five** build dirs spanning Aug 30 – Sep 3
      (`build-asan`, `build-cpu-prof`, `build-cpu`, `build-merged-20260903`, `build-o1`), none version-named.
      **Two options, both operator-adjacent because the tree is shared**: (a) **rebuild** `build-cpu` at the current
      tip and keep it current, or (b) **remove** the stale dirs so nobody can reach into them — the per-agent
      worktree pattern means no agent *needs* a shared build, and that pattern is exactly what contained today's
      damage. **Recommend (b) for the stale ones plus (a) for `build-cpu` if anything still references it.** Do not
      act while agents are live: `b7-ple` is probing `build-cpu` right now. **Guard to add regardless**: any brief
      that names a build must require a freshness proof by CONTENT — a symbol introduced by the relevant fix, or
      `--version` compared to `HEAD` — never a directory name or mtime.
- [x] **BE-3 — carrier 3 CLOSED as a well-scoped negative ✅ 2026-09-04 (`be3-dsa`). It never propagates, and the
      source says it cannot. NO FIX WARRANTED — document it, do not repair it.**
      **What it is: a SEMANTIC carrier, not an arithmetic one** — unlike carriers 1 and 2, and **it is ours, not
      upstream.** The DSA indexer pools each block's key as a **mean over the cells present in the cache**, and
      `build_qsa_top_k` (`qwen4exp.cpp:730-812`) writes **all** of the ubatch's indexer keys (`cpy_k`) before reading
      the whole cache back (`get_k`). So for the block containing a row's own position, an n-token batch pools over
      sibling keys that a single-token decode has not yet written. Model facts: `indexer.head_count=4`,
      `key_length=128`, `top_k=2048`, `compress_ratios=[0,0,0,4]×12`; the indexer `mul_mat` is `[128 × n_blocks]`
      with **`ne11 = 4·n_tokens`** — i.e. **the very node family BE-1's bound `N >= 4·(n_max+1)` was derived from.**
      `ROWEXACT_N=512` removes the arithmetic part and leaves this semantic residue.
      **Why it CANNOT propagate**: every block whose membership can differ satisfies `b*r >= tail_start` (siblings
      sit at positions > q), and `set_input_qsa` (`llama-memory-hybrid-idx.cpp:437-447`) gives exactly those blocks
      **`+1e9`** — forced into the top-k whatever their score. `build_attn_qsa` then consumes `top_k` as a **SET**,
      scattered into a `-INFINITY` mask via `ggml_set_rows`, so ordering is irrelevant. **The only propagation
      channel is a changed selected set, and it is closed by construction.**
      **Measured, 5 arms** (`GGML_ROWEXACT_N=512 GGML_FA_SPLIT_KV=0 --fa 1`): at prefix **64 / 300 / 2100 / 2600**,
      `indexer_top_k` never differs and **logits and the FULL recurrent state (120–206 MB) are IDENTICAL**. The node
      trace matches the prediction element for element (`first@525` = block `2100/4`; `SUM_ROWS diff 1/576`;
      `max|d| = 1.000e+09` on cells 2100-2102 is the tail bias itself, killed by the KQ mask). **Control that rules
      out any rounding/tile/thread story: the LAST row of every batch is `DIFFER 0`** — it has no siblings after it.
      A 5-token batch pollutes exactly two blocks, as the mechanism predicts.
      **⚠ THE POSITIVE RESULT — this completes the exactness picture: with `GGML_ROWEXACT_N >= 4·(n_max+1)` AND
      `GGML_FA_SPLIT_KV=0`, an n-token batch is BIT-IDENTICAL to n single-token decodes — logits and full recurrent
      state — verified at 300, 2100 and 2600 tokens.** Concurrent-stream identity and A/B measurement discipline are
      intact. **All three carriers are now closed**: 1 fixed (BE-1), 2 flag-removable (BE-2), 3 non-propagating.
      **The falsifier to guard**: containment rests **entirely** on the `+1e9` tail bias. Remove it, narrow it, or
      make it finite-comparable against real scores and **carrier 3 becomes a live top-k flip risk immediately.**
      Anyone touching `set_input_qsa` must re-run these arms.
      **Also noted**: the fused decode path (`qwen4exp-fused.cpp:1121`) pools only `cell < n_visible` over an **f64**
      accumulator — neither the pollution nor the graph path's f32 slice-sum, a third numeric variant contained by
      the same argument.
      **⚠ INSTRUMENT DEFECT FOUND AND FIXED (`1aceb684b`, not merged): `rowexact.cpp::tokenize` allocated a FIXED
      512-token buffer**, hard-capping `prefix+n` at 512 — below this model's top-k width
      `min(n_kv, indexer_top_k + r - 1) = 2051`. **So EVERY rowexact run ever made on this model had a vacuous
      top-k and could not have detected a flip even if one existed.** `d_p2100_n3` is the first non-vacuous
      selection ever measured here. **This is the SECOND time an instrument default sat below the phenomenon's
      threshold** — the tool's `--n-ctx` default hid carrier 2 the same way.
- [x] **BE-1 — carrier 1 made shippable; MERGED 2026-09-04 into `exp/cpu-fusion-qwen4exp-20260829` at
      `4d9cdf66f` (operator: proceed). MY SUGGESTED BOUND OF 8 WAS REFUTED BY THE GATE.** ✅ 2026-09-04
      (`be1-ship`, commit **`db6b715c9`** on `inf70/be1-ship`, base `10acba0ab`; not merged, not pushed).
      **The Gap-4 gate did exactly its job.** `G_fix0` (N=0) is **byte-identical to `10acba0ab` on 7/7 prompts** —
      the refactor is provably inert, which is what the gate exists to prove. But **`G_fix` at the default N=8
      DIVERGES on 6/7.** **Mechanism, found for free in `batch-envelope`'s saved dispatch trace: this model has 12
      F32 `[128×64]` `mul_mat` nodes per graph whose `ne11` is `4·n_tokens`** (ne11=4 on a single-token decode,
      ne11=12 on a 3-token batch; 456 dispatches = 19 decodes × 24 lines). **So N=8 is the worst of both worlds — it
      catches `ne11=4` at BATCH 1, moving single-token decode numerics, while still missing the `ne11=20` of a 5-row
      MTP verify batch, leaving the batch non-row-exact.** **The correct rule is `N >= 4·(n_max+1)`** — ≥20 for
      n_max 4 — **not 8.** Prefill is untouched at any such value (a 512-row ubatch presents `ne11=2048` there), and
      the cost claim did verify: prefill at N=8 was 165.5/183.0 vs baseline 167.4/180.3, inside the ±7% noise
      `G_fix0` itself shows. **Falsified cleanly on three points: N=0 identical 7/7, N=3 identical 7/7, N=8 divergent 6/7** — the
      N=3 arm sits below the `ne11=4` nodes and its predicted byte-identity held, so the mechanism is confirmed and
      not merely consistent. **Default ships 0** with the rule documented at the knob. Gap 1's *cost* claim did
      verify: prefill 167.4/180.3 → 165.5/183.0 pp t/s, the −15…−20% is gone. Every arm set `GGML_ROWEXACT_N`
      explicitly, so **no measurement depended on the default**.
      Static gates green: `MUL_MAT` 1139/1139, `MUL_MAT_ID` **815/815**, `test-llama-archs` 0 FAIL; the
      `GGML_MM_TRACE` tracer stays on the diagnostic branch.
      **Lesson: a "safe" bound chosen from the verify-batch row count alone is wrong when a graph contains nodes
      whose `ne11` is a MULTIPLE of `n_tokens`.** I proposed 8 from the n+1 verify shape; the gate caught it.
- [x] **BE-1 Phase 2 — THE FASTEST DEPLOYABLE CONFIGURATION.** ✅ 2026-09-04, 24-prompt production mix,
      token-weighted, `pred_n >= 16` floor, coherence by REASON. **All 8 arms: 20 COHERENT + 4 SHORT, zero SALAD,
      zero EARLY-EOS.**
      | arm | tw t/s | × plain | note |
      |---|---|---|---|
      | P0 plain | 12.484 | 1.000 | baseline |
      | P8 plain + row-exact | 12.515 | 1.003 | **row-exactness is FREE on the trunk** |
      | M2_0 / M2_8 | 20.140 / 19.892 | 1.613 / 1.593 | |
      | M3_0 / M3_8 | 21.959 / 21.120 | 1.759 / 1.692 | |
      | **M4_0 (n-max 4, approximate)** | **22.931** | **1.837** | **FASTEST** |
      | M4_8 (n-max 4, lossless) | 21.559 | 1.727 | −6.0% for losslessness |
      **Row-exactness costs −0.3% / −2.6% / −4.6% at n-max 2/3/4** — it buys losslessness and no speed. **Under the
      operator's speed-first ruling the answer is M4_0: n-max 4, approximate, ~22.9 t/s (1.837×).** Note this is
      carrier 1's knob only; carrier 2's (`GGML_FA_SPLIT_KV=0`) is separately **free** under MTP (`be2-fa`), so a
      *partially* exact config costs nothing — full losslessness is what costs 6%.
      **⚠ The n-max tension LARGELY DISSOLVES once `p_min` is on — this is the operationally important refinement.**
      Without p_min, aggregate favoured n-max 4 (1.837× vs 1.759×) while `e3-run`'s tail favoured n-max 3 (paired
      min 1.271 vs 1.136). **With `p_min 0.5`, n-max 4–8 × p_min 0.5–0.6 is ONE INDISTINGUISHABLE BAND** —
      coin-flip paired win rates across it. **The optimum is a plateau, not a peak: the confidence gate sets the
      working depth, so n-max stops mattering.** n-max 4 was chosen for the lowest drafted-per-token, not because it
      measured fastest. The adopted ruling (3 fleet / 4 coding) therefore remains sound; adding `p_min 0.5` makes
      the choice between them largely moot rather than overturning it.
      **`--spec-draft-p-min` RESULT — a free +3.0%, and the new best configuration:**
      | arm | n-max | p_min | tw t/s | × plain | α | drafted/tok |
      |---|---|---|---|---|---|---|
      | M4_0 | 4 | 0 | 22.931 | 1.837 | 0.752 | 0.994 |
      | **B_n4_p05** | **4** | **0.5** | **23.623** | **1.892** | 0.827 | 0.890 |
      | B_n4_p075 | 4 | 0.75 | 23.023 | 1.844 | 0.920 | 0.763 |
      | B_n4_p09 | 4 | 0.9 | 21.993 | 1.762 | 0.963 | 0.693 |
      **Mechanism CONFIRMED, not inferred**: α rises monotonically (0.752 → 0.827 → 0.920 → 0.963) while
      drafted-per-token falls monotonically (0.994 → 0.890 → 0.763 → 0.693) — the drafter bails out of
      low-confidence blocks instead of paying to verify them — and throughput peaks *in between*, at 0.5. It wins on
      **every** prompt class, most on `general` (+5.2%, 18.886 → 19.863), which is precisely the class with the
      worst α and therefore the most wasted verification to recover. **This knob had never been set in any arm of
      this campaign** (default 0.0).
      **⚠ SUPERSEDED 2026-09-04 BY THE CLAIM-GRADE ABA — 23.623 DOES NOT REPRODUCE. Quote 23.16 t/s / 1.876×.**
      ABA (A-plain → B-config, ×3) in ONE lock window: **B = 23.16 t/s (sd 0.14, spread 1.1%, range 23.01–23.26),
      A = 12.35 t/s (sd 0.24), ratio 1.876×** (per-round 1.845 / 1.886 / 1.897; B faster on 20/20 prompts in every
      round). The 23.623 below sits **2.0% above the ABA mean and 2.6 round-sd out**; no round reached 23.4.
      **The CONFIGURATION is confirmed and the MECHANISM reproduces exactly** — α 0.8274 and drafted/token 0.8900,
      identical to 4 dp across all seven n-max-4 arms — so what failed was the number, not the finding: 23.623 was
      the optimistic edge of one unreplicated arm. Original text retained below.
      **FINAL RECOMMENDED CONFIGURATION: n-max 4, `--spec-draft-p-min 0.5`, row-exact off, `-fa on` +
      `GGML_FA_SPLIT_KV=0`** (the last is free under MTP per BE-2). **23.623 t/s token-weighted, 1.892× plain;
      paired median 1.979× (min 1.227, max 2.152); bootstrap CI [21.79, 25.10]. NON-CLAIM — single session, no ABA;
      432 requests across the arm matrix with ZERO garbage outputs. By class: coding 25.36, reasoning
      24.86, general 19.86 t/s.** Coherence 20 COHERENT + 4 SHORT on every arm.
      **Depth beyond 4 without p_min is a dead end** (n-max 6: 22.281, n-max 8: 21.120, α collapsing to 0.620 /
      0.537). Whether depth pays *with* p_min truncation is the one open arm (n-max 5/6/8 at p_min 0.5, then a p_min
      bracket at the winner).
      **The lossless question is settled without appeal to the ruling**: at EVERY n-max, approximate is faster than
      lossless (−0.3% / −2.6% / −4.6% paired at 2/3/4). **Losslessness is not a trade here, it is simply a cost** —
      worth buying only for the concurrency property it also brings (concurrent streams become bit-identical to
      single-stream), and then at `N >= 4·(n_max+1)`, not 8.
      **Process finding disclosed by the agent**: the first depth probe ran at p_min 0 rather than the winning p_min
      because `pick.py` emitted the label `p5` where the driver writes `p05`, so the lookup **silently fell back to
      the default**. The arms are still valid (they are the honest no-p_min n-max 6/8 points) but were not what was
      intended. Recorded because the failure mode — *silent fallback to a default on a label mismatch* — is the same
      shape as the `GGML_ROWEXACT_N` no-op and the `top_logprobs` parse miss: **a lookup that misses should fail
      loudly, not default.** Evidence `/mnt/raid0/llm/tmp/inf70/agents/be1-ship/`.
- [x] **BE-2 — SOLVED and MERGED 2026-09-04 (`be2-fa`; knob cherry-picked as `c51e4dabf` — the branch itself was
      NOT merged, since it carried the superseded diagnostic fix and the `GGML_MM_TRACE` tracer). Carrier 2 is NOT A BUG: it is two algebraically-equal,
      numerically-different parallelisations of flash attention, and the FAST one is the default. RECOMMENDATION:
      keep `-fa on` with the split path ON and accept the non-exactness — that is also the fastest configuration at
      every depth measured.**
      **The mechanism, named from source.** `ops.cpp:9424-9426`: `use_split_kv_path` requires **`neq1 == 1`** (one
      query row) **and `nek1 >= 512`**. `llama-kv-cache.cpp:1270-1275`: **n_kv is padded to a multiple of 256**, so
      `nek1` is 256 for real n_kv 1–256 and **512** for 257–512. The `nek1 >= 512` gate therefore flips at exactly
      real n_kv = 257 — precisely the measured bisect. **The "256 boundary" is not an FA block size; it is the KV
      padding quantum interacting with the split path's 512 gate.** Single-row decode splits KV across threads into
      per-thread partials recombined by an online-softmax rescale; any batch with `neq1 > 1` takes one sequential
      pass over the whole KV with rows split across threads instead. **Algebraically equal, numerically different —
      so a 1-row decode and an n-row verify batch cannot be bit-identical at depth BY CONSTRUCTION. No bug exists.**
      **Provenance: upstream and deliberate** — `9f682fb64` (Aman Gupta, 2026-02-03, "ggml-cpu: FA split across kv
      for faster TG", #19209). It is a token-generation optimisation; "repairing" it means giving it up.
      **Proof (`llama-rowexact`, build 10221, prefix 254, `-fa on`, carrier 1 already removed):** default split ON →
      `node_584 FLASH_ATTN_EXT [256,24,3]` row 2 only, 68,334,110 state bytes differ (reproduces batch-envelope's
      `e7fa1p254` exactly); **`GGML_FA_SPLIT_KV=0` → ALL 3 ROWS IDENTICAL, 0/248320 logits, 0 state bytes.** One
      boolean removes the entire carrier with FA still on.
      **SPEED — and this is what decides it** (llama-bench, build 10221, depth sweep, t48):
      | depth | `-fa on` split ON (default) | `-fa on` `SPLIT_KV=0` (exact) | `--fa 0` |
      |---|---|---|---|
      | tg32 @ d512 | **12.48** | 12.16 | 12.58 |
      | tg32 @ d2048 | **12.01** | 11.78 | 11.85 |
      | tg32 @ d4096 | **11.89** | 11.21 (−5.7%) | 11.19 (−5.9%) |
      | pp512 @ d4096 | **188.12** | 180.39 (−4.1%) | 169.10 (−10.1%) |
      **⚠ THAT READING WAS WRONG AND IS CORRECTED HERE — it came from a `llama-bench` tg32 sweep, which is
      SINGLE-ROW decode, the only regime where the split path is even reachable.** The deciding measurement, in the
      config we actually ship: **`use_split_kv_path` requires `neq1 == 1`, and an MTP verify batch is ≥ 2 rows — so
      the split path is NEVER TAKEN under MTP.** Measured on the 24-prompt production mix with the MTP head:
      **`GGML_FA_SPLIT_KV=0` is free EXACTLY, not approximately — 24/24 byte-identical outputs, 22.292 vs 22.048 t/s,
      identical draft acceptance.**
      **RECOMMENDATION (ranked, and it inverts the earlier note): (a) `-fa on` + `GGML_FA_SPLIT_KV=0`** — the fastest
      EXACT option, **zero cost in the shipping MTP config**, keeps FA's prefill advantage and its small compute
      buffer, and cashes in the lossless-MTP result. **(c) FA-as-is is now STRICTLY DOMINATED** — same bytes, same
      speed under MTP, but not lossless. **(b) `-fa off` is dominated too**, though it is a safe no-rebuild interim:
      free at current serving lengths (12.730 vs 12.525 t/s on the production mix, coherence identical) but at depth
      it costs decode −1.7% @2048 / **−3.5% @4096**, prefill **−5.2% / −8.7%**, and **+359 MiB compute buffer
      (+175%)** at every context (KV itself unchanged at 264 MiB).
      **So lossless MTP is available at ~22.3 t/s for free.** The exactness/speed trade does not exist in the
      shipping configuration — it only appeared in a single-row microbenchmark.
      **⚠ COROLLARY, a real measurement hazard: single-row CPU decode at n_kv > 256 is NOT thread-count invariant** —
      the split path's chunk size depends on `nth`, so **changing `-t` changes the logits**. Any A/B that varies
      thread count at depth is comparing different numerics, not different speeds.
      **Coordinator's `LLAMA_ATTN_ROT_DISABLE` lead: FALSIFIED** (my error). `attn_rot_k/v` require a **quantised**
      KV cache; our arms run f16, so both are already false and the flag is a no-op — confirmed from source AND
      measured (arm x4 is byte-for-byte identical to the default arm; server logs `attn_rot_k = 0, attn_rot_v = 0`).
      It matters only for quantised-KV serving.
      **Upstream test coverage hole, measured and worth reporting**: `test-backend-ops -o FLASH_ATTN_EXT -b CPU`
      passes **1302/1303, 0 FAIL**, *including* the exact shapes that straddle the two paths (`kv=512,nb=1` split vs
      `kv=512,nb=3` one-chunk). It passes because **every case is compared only against `use_ref` within an NMSE
      tolerance, never against another case** — there is no assertion that the op is invariant in the number of
      query rows. That is why this reached production. The natural missing test is
      `assert fa(q_rows=1..n)[i] == fa(q_row=i)` at `kv >= 512`.
      **Third, weaker carrier NAMED not claimed**: at prefix 300 with the split path off, 98–100 *intermediate* nodes
      in the DSA lightning-indexer path differ on 1–4 of 512 elements. They did **not** propagate — logits and the
      full 128 MB recurrent state are identical on all three rows. It could in principle flip an indexer top-k at
      some other prefix. Evidence `/mnt/raid0/llm/tmp/inf70/agents/be2-fa/{MECHANISM.md,REPORT.md,runs/}`.
- [ ] **GDN-ROWEXACT — make `build_delta_net_chunking` row-exact vs `build_delta_net_autoregressive` for small n
      (the one fix that closes E2a-successor, E2c AND X-CONC).** **RE-SCOPED 2026-09-03 — the premise was wrong: the GDN kernel is
      exact.** `build_delta_net()` checks `cparams.fused_gdn_ar/ch` first, so n=1 AND n>1 both run the fused
      token-sequential op `ggml_compute_forward_gated_delta_net_one_chunk` (`ops.cpp:11045`); the chunked graph kernel
      at `delta-net-base.cpp:435` is dead code on this build. Reproducer `llama-rowexact` (every graph node via
      `cb_eval`, n singles vs one n-token batch): at n=3 every node before layer 0's router — including the fused GDN
      op — is bit-identical, IQK on and off; 4 seqs × 3 tokens in one ubatch reproduce each sequence's own forward
      bit-for-bit (0/5450 nodes differ). The GROSS defect is the iqk IQ4_XS repack (LONG-PROMPT-GARBAGE above). The
      RESIDUAL small-batch non-exactness behind E2a/E2c is the **F32 router GEMM `ffn_gate_inp` (stock ggml, not
      iqk), ~1 ulp fp-order**, which perturbs top-k downstream — addressed on the same branch by `GGML_ROWEXACT_N`
      (tinyBLAS per-column router + iqk GEMV-per-column for 1<Ny≤N), env-gated default OFF. **Lossless-MTP gate =
      `LLAMA_SPEC_EXACT=serial` ≡ MTP on the fix + MTP-stack integration** (coordinator sequences after G0/G3). Root cause, confirmed three ways
      2026-09-03 (`mtp-exact`, `mtp-conc`, `e2c`): `src/models/delta-net-base.cpp:435` routes
      `n_seq_tokens == 1` to the autoregressive GDN kernel and any 2+-token batch to the chunked kernel
      (CS 64, padded), and the two are not row-exact, so a verification batch (MTP), a multi-sequence
      prefill (concurrency), and any batched forward write a different recurrent state forward. `serial`
      mode (`LLAMA_SPEC_EXACT=serial`, single-token decodes) is byte-identical 3/3 and is the exactness
      oracle. Two shapes to scope: (i) unroll n ≤ 3 through the autoregressive kernel inside the graph;
      (ii) make the chunked kernel bit-equal for small n. Plus iqk small-N parity (mechanism is
      iqk-independent per E2c, so this is the CPU-graph kernel, not the iqk path). Gate: `serial` output ==
      MTP output == concurrent-prefill output == plain, token-for-token. **FUNDED by the operator 2026-09-03 ("proceed") — in flight as agent `gdn-rowexact`, branch
      `inf70/gdn-rowexact` from the exp tip `0d2af8194` (this is a non-MTP kernel fix and lands on the tip
      directly; MTP merges on top). Gates: G1 batch-invariance (`-ub 1` ≡ default ≡ `-ub 8`), G2 X-CONC
      (4 simultaneous prefills coherent ≡ single-stream), G3 n=1 path byte-identical to the unpatched tip,
      G4 single-stream speed within noise of 12.55 t/s. One kernel task turns MTP into a lossless
      1.4–1.7× serving option and unblocks concurrent serving.** Successor to E2a; supersedes the "MTP driver fix" framing.
**✖ B8 — DECLINED BY THE OPERATOR 2026-09-07: *"this is unnecessary."*** The qwen4exp (125B/A6B) vs live
122B/A10B head-to-head is **not being run**, and its checkbox row is deleted rather than struck through, per
the handoff/index contract. Recorded as a decline rather than dropped silently, per the derived-actionables
gate: it was a filed task with three sub-tasks, and a reader must be able to see that it ended in a decision
and not in neglect.

**What survives the decline, because it was already measured and is cited elsewhere in this file:** plain vs
plain, qwen4exp was already ~12% ahead (12.61 vs the registry's 11.3 t/s); **B8(ii) had already RESOLVED the
MTP-multiplier gap as ARCHITECTURAL, not a tuning gap** — `draft-mtp` and `draft-tree` are separate impl
classes that do not compose, and no `k` parameter exists on the MTP path, so the production 122B's 2.12×
`k: 4` *tree* number is not a target our *linear* MTP path can be tuned toward; and ~20% of the bandwidth gap
is architectural — fewer active parameters spread over more and smaller ops is worse on a bandwidth-bound
CPU. **Un-run and now declined: (i) the like-for-like bytes/token + plain-decode measurement of the 122B, and
(iii) the model-choice conclusion.** Cross-references to "B8" elsewhere in this file resolve to findings
delivered *before* the decline, not to outstanding work.

- [x] **C9 — SOLVED 2026-09-04 (`b7-ple`). `llama-perplexity` returned `nan` on qwen4exp because the Q6_K output
      head hit iqk's broken large-Ny repack — and perplexity is the ONLY caller that reaches it.**
      **Result** (probe 1, region-locked, kernel env the sole variable):
      | env | result |
      |---|---|
      | `GGML_IQK=1` | `nan` |
      | **`GGML_IQK=0`** | **PPL = 4.9043 ± 0.59979** |
      | `GGML_IQK=0` + `-fa 1` | 4.9043 ± 0.59979 (identical to the last digit) |
      | `GGML_IQK=1` + `-fa 1` | `nan` |
      **`GGML_IQK` is the sole determining variable**; `-fa` and `GGML_FUSED_DECODE_OFF` are irrelevant. **b4's
      original probe matrix varied `-b`/`-c`/`-fa` and therefore could not have found this.**
      **Mechanism, closed by four facts** (`iqk_mul_mat.cpp:319`,
      `case GGML_TYPE_Q6_K : return nrc_y >= 64 ? GGML_TYPE_Q8_0_R8 : type;`):
      1. Type histogram over all **1224 tensors: Q6_K appears exactly ONCE**, on `output.weight` — the Q6_K repack
         has exactly one possible call site in this model.
      2. That call site is a **GEMV in every served path** (generation `n_outputs == 1`; MTP verification a small `k`).
      3. `perplexity.cpp:580` sets logits on `pos >= n_ctx/2`, so **`n_outputs == n_ctx/2` exactly** — 256 at `-c 512`.
      4. **Q6_K is the only case in that switch using 64; every other type flips at 32.**
      Already-convicted family: the comment above the switch says these converters "produce incorrect results for
      some large-Ny dense and MoE shapes on Zen 4", and BE-1 excluded IQ4_XS for exactly this. Q6_K survived on a
      `gdn-fix-validate` coherence check of the **served** path — and lossy is not nan.
      **WHY IT SURVIVED — the generalisable lesson**: the defect is **unreachable from any serving workload**. It is
      reachable only from the all-logits path, which is **the quality gate itself**. *The instrument was the one
      caller its own bug disabled.* A defect that only breaks your measuring device is invisible to every test that
      uses the device.
      **Fix**: Q6_K moved into the excluded-families list in the AVX2 arm, mirroring BE-1 (1 file, +11/−1), on
      worktree `inf70/b7-ple` off the merged tip. The **non-AVX2 arm was deliberately left alone and said so** — this
      host takes the AVX2 path and there is no measurement on the other. Built on cores **96–175**, outside the
      0-95 bench region and clear of the GPU host threads, so it contended with nothing and needed no lock.
      **Two disciplines the agent held itself to, both worth keeping**: (a) the source comment asserts a
      `-c 128`/`-c 126` bracket the bisect has not returned yet, so **it will not commit until that is confirmed** —
      no claim written into a comment ahead of its measurement; (b) **every verification arm runs with
      `GGML_IQK=1`**, because an arm that passed only under `GGML_IQK=0` would be testing the workaround rather than
      the fix. **Unblocks B7, B9, B5 and every future quality or artifact decision on this model.** Coordinator
      contributed the type/threshold hypothesis; the agent confirmed it and found facts 1 and 4 independently.
      **★ C10 (fleet exposure) — MEASURED NULL 2026-09-04. NO production exposure, NO escalation.** Probe 3:
      DeepSeek-1.5B Q4_K_M, which carries **a Q6_K head AND 28 body Q6_K tensors**, at Ny=256 gives
      **36.7101 (`GGML_IQK=1`) vs 36.7159 (`GGML_IQK=0`)** — agreement to 0.016%. **Q6_K is definitively fine at
      large Ny**, so the four production-lineup files carrying body Q6_K (`ingest_long_context` 54,
      `worker_vision` 48, `worker_general` 13, `architect_critic` 1) are **not exposed**. The measurement matched
      the agent's own standing counter-evidence rather than overturning it — it declined to escalate on that
      reasoning and was right. **C10 closed; no operator action.**
      **⚠ ATTRIBUTION NOT SETTLED — the agent doubts its own Q6_K call, and is right to.** Its blast-radius scan
      found **four production-lineup files carrying Q6_K on BODY tensors** (`attn_v`, `ffn_down_exps`), which run at
      `ne1` = prefill batch on **every prefill**, not at `ne1 = 1` like an output head: `ingest_long_context` (54),
      `worker_vision` (48), `worker_general` (13), `architect_critic` (1). **It declined to escalate, on sound
      reasoning: those four serve coherently today, and a corrupt `attn_v` at `ne1 = 512` on every prefill could not
      go unnoticed.** So Q6_K is probably NOT broken at large Ny and the defect is elsewhere in the post-gather chain.
      **Coordinator's alternative, and the stronger suspect: `output_hc_up.weight` is IQ4_NL `[320, 10240]`,
      repacking at `nrc_y >= 32` (`iqk_mul_mat.cpp:336`) — and BE-1 excluded IQ4_XS ONLY, leaving its sibling IQ4_NL
      on the path.** Post-gather chain: `output.weight` Q6_K (64) · **`output_hc_up` IQ4_NL (32) — exposed, crossed
      8× at n_outputs 256** · `output_hc_down` IQ4_XS (32) — excluded by BE-1 ✓ · `output_hc_norm` F32. IQ4_NL is
      (a) an **iquant**, the family the source comment convicts, where Q6_K is a k-quant; (b) the nearest neighbour
      to IQ4_XS, which BE-1 *measured* returning ~1e3 errors from that path; (c) lower-threshold, so crossed harder;
      (d) also post-gather, so it sees `n_outputs` (1 in generation, 256 in perplexity) — the "only the instrument
      reaches it" structure the diagnosis rests on. **If IQ4_NL is the culprit, those four production rows are NOT
      exposed and there is no escalation** — where the agent's own evidence already pointed.
      **Decisive test, queued at no extra cost: does the Q6_K-only exclusion make PPL finite under `GGML_IQK=1`?**
      Finite ⇒ Q6_K implicated, probe 3 becomes a genuine production question. Still `nan` ⇒ Q6_K exonerated; then
      IQ4_NL alone, then both, to attribute cleanly rather than shotgunning. **No production claim until settled.**
      **⚠ BOTH HYPOTHESES ARE NOW UNPROVEN, and the agent found the reason before the coordinator did.**
      Its `GGML_IQK_DEQUANT=0` arm — the knob sits at the top of `is_dequant_better` (line 289) and **every** repack
      decision routes through that function (618, 806, 888, 928) or through `iqk_dequant_type`, which calls it — was
      **still `nan`**. If valid, that exonerates the repack path **wholesale**, killing the Q6_K *and* the IQ4_NL
      story at once, and pointing at a **direct iqk kernel at Ny > 1** rather than a threshold or an exclusion-list
      gap.
      **But the agent refuses to assert it, because it cannot show the knob did anything**: per-pass timings
      identical to the centisecond (2.90 s vs 2.90 s) and byte-identical `[iqk] ACTIVE` lines. A repack is a speed
      optimisation; switching it off should move *something*. **That is the shape of a check passing for the wrong
      reason, so its own exoneration is held as unproven.**
      **Direct precedent, supplied by the coordinator**: `GGML_ROWEXACT_N` was exactly this failure — the coordinator
      published "the flips are NOT the batched mul_mat" three times on a knob that had **never affected any tinyBLAS
      mul_mat** (`llamafile_sgemm` refuses `n < 2`), and the proof of inertness was **byte-identical node traces with
      it on and off**. Identical output under a flipped knob is not evidence the knob is irrelevant; it is evidence
      the knob is **inert**, and the two are indistinguishable without instrumenting the dispatcher.
      **Resolution — stop inferring, make the dispatcher speak.** The agent instrumented `is_dequant_better` to log
      every `(type, Ny)` pair with the path actually chosen, deduped. Two arms: **dequant ON** yields the ground-truth
      list of which types take which path at which Ny in the all-logits path (directly testing the IQ4_NL
      prediction); **dequant OFF must show ZERO repacks** — if it does not, the probe-2 exoneration is withdrawn and
      both repack hypotheses return. **This converts "which of three tensors" from a debate into an enumeration**,
      for one small lock window.
      **Coordinator addition**: BE-1 moved IQ4_XS **off** the repack and **onto its direct kernel**, so
      `output_hc_down.weight` (IQ4_XS `[10240, 320]`) is now a **direct-kernel candidate at Ny=256** in the same
      post-gather chain. The tracer should log the chosen path for every pair — direct vs repack vs generic — so one
      dequant-ON arm enumerates all three candidates at once. The cross-build arm also turns "BE-1 cannot have
      introduced this" (b4 found it first) into "did not", and yields a bisectable range if the older tree is also
      `nan`.
      **CROSS-BUILD RESULT — one candidate ELIMINATED, and BE-1 cleared (measured, 2026-09-04).** The 2026-08-28
      bring-up tree: (a) has **no `GGML_IQK_DEQUANT` knob at all** (`grep -c` = 0), so probe 2's dequant arm only
      ever applied to the new tree; (b) still carries `IQ4_XS : nrc_y >= 32 ? q8_k_type : type` — **IQ4_XS ON the
      repack path, BE-1's exclusion absent**; (c) returns **`nan` on the same command**.
      **So IQ4_XS's repack status FLIPS between the two trees while the `nan` does NOT — the IQ4_XS repack is
      eliminated as the cause, and BE-1 neither caused nor fixed C9.** "Cannot have introduced it" is now "did not",
      measured, with no bisectable range. Still live: Q6_K repack, IQ4_NL repack, and any **direct** kernel at
      Ny > 1 (including `output_hc_down`, which BE-1 moved onto its direct path).
      **PROBE 2'S EXONERATION FORMALLY WITHDRAWN** by the agent: both integrity checks on `GGML_IQK_DEQUANT=0` came
      back null (seconds-per-pass 2.90 vs 2.90; `[iqk] ACTIVE` lines byte-identical under `diff`) — the
      `GGML_ROWEXACT_N` signature exactly. **Both hypotheses are unproven on identical grounds.**
      **Probe 4 built and queued**, logging once per `(typeA, Ny, ne00)` the path actually served:
      `[iqk-path] typeA=… Ny=… ne00=… dequant->… rowexact_n=… SERVED=…` with
      `SERVED ∈ {REPACK | iqk-direct | iqk-direct(rowexact) | iqk-direct-smallNx | DECLINE(ggml-fallback)}`.
      One dequant-ON arm enumerates all three post-gather candidates and their paths at once; the dequant-OFF arm is
      **the knob's own integrity test** — zero `SERVED=REPACK` required, and any survivor withdraws probe 2 formally.
      **Both arms print the PPL, so a still-`nan` also proves the instrumentation is non-perturbing.**
      **★ ROOT CAUSE, 2026-09-04: C9 WAS A STALE BINARY, NOT A LIVE KERNEL DEFECT. It needs a REBUILD, not a code
      change.** `cpu-fusion-20260829/build-cpu/libggml-cpu.so` was built **Sep 1 19:40**; its source
      `iqk_mul_mat.cpp` is **Sep 3 19:36** — **two days newer**. The commit between them is **`99425578d`**
      (BE-1: *"IQ4_XS stays on its direct iqk kernel (Q8_K_R16 repack at Ny>=32 is wrong); … GGML_IQK_DEQUANT
      knob"*). **Proven by content, not dates**: `strings` on the stale library finds **0 occurrences of
      `GGML_IQK_DEQUANT`**; the fresh build has it.
      **Everything resolves at once:**
      1. **`GGML_IQK_DEQUANT=0` was inert because the binary has no such knob.** The identical timings and
         byte-identical `[iqk] ACTIVE` lines were *telling the truth all along* — now proven by `strings` rather
         than inferred. (The `GGML_ROWEXACT_N` precedent is what made the agent distrust its own arm.)
      2. **The culprit is `output_hc_down.weight` (IQ4_XS `[10240, 320]`) on the Q8_K_R16 repack** — precisely the
         path that commit calls wrong. **The coordinator's "convicted iquant family, post-gather chain" instinct was
         right and the specific tensor guess was wrong**: it is the IQ4_XS one, not IQ4_NL (`output_hc_up`) and not
         Q6_K (`output.weight`).
      3. **Every threshold observation now fits**: IQ4_XS repacks at **32**, so `c64`(Ny 32), `c126`(63), `c128`(64),
         `c256`, `c512` were *all* corrupt because all are ≥32. **There never was a 64 boundary** — the "graded
         corruption" was severity scaling with Ny, not a second threshold.
      4. **"Not a regression" was right for the wrong reason** — the 2026-08-28 tree also predates the fix.
      5. **b4 filed C9 on 2026-09-02 against this same binary, one day before the fix landed. C9 was REAL when
         filed and has been FIXED since — by BE-1's own commit, which nobody noticed also repaired the quality
         gate.**
      **Blast radius, checked**: `build-cpu` was *current* on Sep 2 and became stale on Sep 3 when B3-k, the merge
      and the iqk fix landed with no rebuild. Agents that used it on Sep 2 (b2, b3, b34, b4, d7a, d8, d8x, e2, e2c,
      mtp-conc, merge-verify) measured the tree state they intended. **Every agent whose results were published
      today built its own worktree and has ZERO references to it** — `gdn-rowexact`, `mtp-tip2`, `be1-ship`,
      `be2-fa`, `be3-dsa` all 0. `speed-claim`'s single reference is its **co-residency log observing** b7-ple's
      process — the INSTR-1 sampler recording an exe path — and its own binary is dated after the source **and
      contains all three post-fix symbols** (`GGML_IQK_DEQUANT`, `GGML_ROWEXACT_N`, `GGML_FA_SPLIT_KV`), verified by
      `strings`. **Today's claim-grade work is unaffected.**
      **NOT YET VERIFIED, correctly**: `4.4798` (fresh, IQK=1) vs `4.9043` (stale, IQK=0) is a **cross-binary**
      comparison, and a 9% PPL gap between two supposedly-correct runs is too large to wave through. Probe 5 is
      rewritten as a **same-binary** test — one binary, `GGML_IQK=1` vs `=0` at `--chunks 20`, plus a now-meaningful
      `DEQUANT=0` arm and a cross-build agreement check.
      **THE HYGIENE LESSON: "the merged tip" named a SOURCE TREE, and everyone — coordinator included — assumed the
      build inside it matched. The shared tree holds FIVE build dirs aged Aug 30 to Sep 3.** Freshness must be
      proven by **content** (symbol presence, `--version` commit) and never by directory name or mtime alone.
      **⚠ THE CORRUPTION IS GRADED, NOT A CLEAN `nan` — and that is worse.** Measured: **~3.3e5 at Ny 63,
      degrading to `nan` at Ny 256.** A `nan` announces itself; **a wrong-but-finite perplexity is quiet** and would
      be recorded as a result. **Consequence: any PPL ever taken on this model with `GGML_IQK=1` at moderate Ny is
      wrong-but-plausible, not obviously broken.** (We are fortunate here: C9 was open, so no PPL was ever recorded
      on this model — but the same defect class on a model where the instrument *did* return a number would have
      silently poisoned the record.)
      **COORDINATOR'S `nrc_y >= 64` THRESHOLD HYPOTHESIS IS REFUTED** by the agent's own `c126`/`c64` arms:
      corruption is present at **Ny 63, below the Q6_K threshold of 64**. The Q6_K-repack story is dead as stated.
      The agent's patch is **reverted; nothing committed** — correct, since the source comment asserted the very
      bracket the arms refuted.
      **C9 IS FUNCTIONALLY SOLVED FOR OUR PURPOSES, INDEPENDENT OF ATTRIBUTION**: `GGML_IQK=0` yields
      **PPL 4.9043 ± 0.59979**, four arms across two probes agreeing to the last digit. **The workaround is validated
      and usable today, so B7, B9 and B5 are unblocked now** — attribution remains scientifically open but is not
      gating. Establish it, then decide whether a fix is worth shipping over the flag.
      **Belief-kernel wiring, flagged by the agent and adopted: `GGML_IQK` state MUST be part of the warrant of any
      PPL claim tuple on this stack.** This defect proves the kernel flag is not incidental to the number — the same
      command, same build, same artifact returns 4.9043 or garbage depending on it. A claim tuple that omits it
      cannot be re-derived. Add to the adapter's projection alongside build id, thread count and recipe.
- [ ] **B9 — KV-cache quantisation: a much SMALLER lever on this model than on a dense one, and it activates an
      untested path. Analysed 2026-09-04 from the artifact; recommend ONE cheap measured arm, not adoption.**
      Filed after an operator question ("should we use a quantized KV cache? won't it improve decode speeds?").
      **The structural answer: only 12 of 48 layers have a KV cache at all** — the other 36 are recurrent
      Gated-DeltaNet and carry none — and `head_count_kv = 2` with key/value length 256. Measured from the GGUF:
      | | f16 | q8_0 |
      |---|---|---|
      | KV per token | **24.0 KiB** | ~12 KiB |
      | KV at ctx 4096 | 0.094 GiB | 0.047 GiB |
      | KV at ctx 8192 | 0.188 GiB | 0.094 GiB |
      | KV read per generated token @ 4096 | 96 MiB = **2.42% of the 4.16 GB byte budget** | ~1.2% |
      | @ 8192 | 192 MiB = **4.84%** | ~2.4% |
      **So q8_0 buys ~1.2% of the per-token byte budget at 4k and ~2.4% at 8k — and the MEMORY saving is
      irrelevant** (0.047 GiB saved on a 1.1 TB box). On a dense model KV is often the dominant term at depth; here
      it is 2.4% at 4k **because the hybrid is 75% recurrent**. Note also that the measured decode drop d0→d4096 is
      −7.8% while KV is only 2.42% of bytes there, so **most of that drop is attention compute and the FA split
      path, not KV bandwidth** — quantising KV cannot recover it.
      **⚠ The risk is specific and known**: quantised KV is exactly what **activates `attn_rot_k`/`attn_rot_v`**
      (`llama-kv-cache.cpp:322-338` — they require `ggml_is_quantized(type_k/v)`). That path is **inert on our f16
      arms and has never been exercised by us**, and a community Flash-Next MTP repo ships
      `LLAMA_ATTN_ROT_DISABLE=1` as a "critical flag", which is strong circumstantial evidence that quantised-KV +
      rotation misbehaves with the MTP draft head. Any KV-quant arm must therefore also run the MTP path and a
      coherence check, not just a speed number.
      **Quality evidence (external, KL-divergence benchmark)**: Qwen-family models tolerate **q8_0 well (KL < 0.04)**;
      **q4_0 concentrates its damage in LONG DOCUMENTS (KL 0.581)** — which is precisely our workload — and the
      asymmetric guidance is to spend bits on the **Key**, not the Value. **q4_0 is contraindicated here.**
      **★ ARTIFACT BUILT AND VERIFIED 2026-09-04.** `123,993,035,136 B`, spliced from the era anchor with a
      **mutation-tested verifier run first**, then applied to the real 124 GB file (not a fixture):
      **67 recipient KV fields verbatim · tensor order preserved, 1224 tensors · PLE `IQ4_NL → Q8_0`, shape
      unchanged `[160, 320001536]` · PLE content byte-identical to the donor (blake2b `ae189b34…`) · 1223 non-PLE
      tensors byte-identical to the recipient, 0 differ · all 1224 data offsets aligned.** Donor SHA-256 matched the
      HF LFS oid before use, and **the donor was deleted only after verification returned 0** — deleting earlier
      would have destroyed the comparison evidence. Disk: 242 → 192 (donor down) → **75 GB at splice peak** →
      **126 GB after deletion**; era anchor and `-gateup-r16` untouched.
      **Methodological cleanup worth copying**: the agent reverted its diagnostic instrumentation, rebuilt pristine
      at `c51e4dabf`, and then **verified that structurally rather than by assertion** — `strings` shows **0
      `iqk-path` symbols** (instrumentation gone) and **1 `GGML_IQK_DEQUANT`** (post-fix source present). That is
      the stale-binary lesson applied to its own build within the hour.
      **Consequence worth stating: B7's quality numbers will be measured at `GGML_IQK=1` — the actual production
      kernel configuration — and that is only trustworthy BECAUSE C9 turned out to be a stale binary rather than a
      live kernel defect.** Had C9 been real, B7 could only have been measured at `GGML_IQK=0`, i.e. in a
      configuration nobody serves, and the result would not have transferred.
      **★ B7 SPEED GUARD-RAIL COMPLETE 2026-09-04** — 24 production prompts per arm: `b7-anchor` **12.4086 t/s**
      vs `b7-pleq8` **12.3606 t/s** token-weighted, both 20 COHERENT + 4 SHORT. The −0.39% comes from two
      SEQUENTIAL lock acquisitions and is therefore **not evidence** under the same-window rule; predicted
      bandwidth cost was +3.1e-5%. B7 closes on both axes: no quality gain, no measurable speed change.

      **★ C9 CLOSED 2026-09-04 — VERIFIED TO THE SAME-BINARY STANDARD.** Four arms, `-c 512 --chunks 20`,
      same corpus and settings, only the BINARY and the kernel flag varying:

      | arm | binary | env | PPL |
      |---|---|---|---|
      | `fresh_iqk1` | fresh `c51e4dabf` | `GGML_IQK=1` | 3.2317 ± 0.09736 |
      | `fresh_iqk0` | fresh | `GGML_IQK=0` | 3.3038 ± 0.10011 |
      | `stale_iqk0` | **stale** | `GGML_IQK=0` | **3.3038 ± 0.10011** ← identical to every digit |
      | `stale_iqk1` | **stale** | `GGML_IQK=1` | **`nan`** |
      | `fresh_c62` / `fresh_c64` (Ny=31/32) | fresh | `GGML_IQK=1` | 10.8592 / 10.4619, both sane |

      **The `stale_iqk0` ≡ `fresh_iqk0` exact match is the load-bearing control**: two different binaries
      reproducing to every digit rules out model, corpus, settings, build configuration and machine state
      together, leaving the kernel flag × binary combination as the only live variable. Only that combination
      produces `nan`. The accelerated path is not corrupting; the remedy was a REBUILD, not a patch.

      **⚠ RESIDUAL — every PPL claim on this model MUST name its `GGML_IQK` state.** `IQK=1` sits 2.2% below
      `IQK=0` (3.2317 vs 3.3038). That is NOT run noise: the exact-digit reproduction above proves these runs
      are deterministic, so the ± is corpus-sampling uncertainty and the paired shift is real — the lossy Q8
      repack at large Ny, behaving as designed. Reading the overlapping error bars as "the paths agree" would
      understate a systematic, reproducible offset. Folded into the belief-kernel wiring note.
      **Why this and not the earlier figure**: the cross-binary comparison (`4.4798` fresh vs `4.9043` stale)
      confounds the kernel flag with every other difference between two builds, so it could not support the
      claim and was correctly refused at the time. Only the one-binary form isolates the variable.
      **Consequence**: the PPL/KL gate for qwen4exp EXISTS again, at `GGML_IQK=1`, so B7's KLD A/B runs in the
      production kernel configuration rather than one nobody serves.
      **Recommended scope: ONE arm** — `-ctk q8_0 -ctv q8_0` vs f16 at ctx 4096 and 8192, plain AND with MTP,
      token-weighted decode + prefill + coherence by REASON, plus an explicit check of whether `attn_rot_k/v` flip to
      1 in the server log and whether output stays coherent when they do. **Predicted gain ~1–2% decode at
      production context; adopt only if measured and if the MTP path stays clean.** Do not pursue q4_0.
- [x] **B7 — ANSWERED 2026-09-04: NO. Higher PLE precision does not buy quality — a null WITH a stated floor.** ✅
      Pristine `c51e4dabf`, `GGML_IQK=1` (the production kernel — measurable only because C9 was stale-binary),
      40 chunks, placement proven on both passes:

      ```
      Mean ln(PPL(Q)/PPL(base)) : 0.004707 ± 0.004380   t = +1.07σ   NOT significant
      95% CI on PPL ratio       : [-0.39%, +1.34%]      MDE = 1.235% PPL
      Mean KLD                  : 0.064860 ± 0.001713   t = 37.9σ
      Same top-1                : 92.020 ± 0.268 %      RMS Δp 8.27%
      ```

      The sign runs slightly AGAINST higher precision. **The instrument is provably not blind**: it resolved the
      distributional change at 38σ in the very same run, so the null is a real bound, not a failure to measure.
      Pairing bought 18× tighter resolution than raw PPLs (Cor 98.06%).
      **BF16 is not worth a second pass**: Q8_0 nearly doubled PLE precision for zero gain against a 1.235% floor;
      BF16 would cost **+25.6 GB resident** for nothing. **The PLE-precision B7 closes with no successor of its own** — unrelated to **INF-71**, the EXL3 trellis item that formerly shared the `B7` label and was renamed 2026-09-07.
      **★ This CORRECTS the structural argument used to pre-judge B7 (mine, twice).** I argued the PLE row is
      diluted (input to two GEMVs averaged over 2560 terms, `ple.layers=[1]`, projections themselves IQ4_XS).
      But **~8% of top-1 tokens flip**: the `key` branch collapses to a SCALAR through a sigmoid gate that
      multiplies the whole value vector, so PLE sensitivity is HIGH. The premise was wrong and the conclusion was
      right for a different reason — sensitivity ≠ headroom. A greedy-identity gate here would have screamed
      "different!" and told us nothing; only the paired KLD/PPL separates "changed" from "improved".
      **Original brief, retained for the record:**
      Filed 2026-09-03 from an operator question, **reframed the same day after operator pushback that corrected the
      premise**: the first draft proposed an *ablation* ("does the PLE earn its keep"). That is a non-question — the
      weights were TRAINED with the PLE, so removing it does not measure its contribution, it just breaks the model,
      and there is no shippable variant without it. The decision-relevant question is **precision, not presence**.
      **⚠ MY MECHANISTIC PREMISE IS REFUTED — established from the graph 2026-09-04 (`b7-ple`), no compute spent.**
      I argued the PLE row is "gathered straight into the residual stream, so its quantisation noise enters
      undiluted". **That is wrong, three ways:**
      1. **The gathered row never reaches the residual stream.** It is the *input vector* to two GEMVs — `ple_key`
         (2560→10240) and `ple_value` (2560→2560) — so its noise **is** averaged over 2560 terms like any other
         activation, then passed through a sigmoid gate. The "undiluted" argument was simply incorrect.
      2. **`qwen4exp.ple.layers = [1]` — the PLE runs in exactly ONE layer of 48.** *(I dumped this key myself and
         failed to draw the inference: whatever it does, it does in 1/48th of the network.)*
      3. **The projections it feeds are themselves IQ4_XS**, so a Q8_0 PLE puts an 8-bit vector through 4-bit
         matrices — it does not move the precision floor of that path.
      The bandwidth half of the case is confirmed exactly (+1,280 B/token = **+3.1e-5%** of the 4.1656 GB/token
      stream), but bandwidth was never the argument for doing it. **Net: the prior is firmly toward a NULL result.**
      **The case as originally written.** `per_layer_token_embd` is IQ4_NL *in this artifact* — unsloth's quantization choice, made on a
      GPU rationale where 27 GB of VRAM is enormous. On this box 27 GB is a rounding error, so we may be inheriting a
      decision whose justification does not apply to us. Mechanistically the stakes are higher than for ordinary
      weights: a GEMM weight's quantization error averages out over hundreds of accumulated terms, whereas a PLE row
      is gathered and mixed **directly into the residual stream** as a feature vector, so its noise enters undiluted —
      a lookup table is plausibly MORE quant-sensitive than the tensors B4 optimised, and 4 bits is exactly where we
      should least want to economise. It is also near-free on the axis that binds us: the PLE contributes ~0 to the
      4.16 GB/token stream (it is a `ggml_get_rows` gather, `qwen4exp.cpp:1115`, not a GEMM), so precision costs RAM
      and gather-latency, not bandwidth.
      **Experiment**: `per_layer_token_embd` at Q8_0 (and BF16 if cheap) vs IQ4_NL, everything else held identical
      (B4's `--tensor-type` override tooling already does this in one `llama-quantize` pass; the r16 artifact is the
      baseline). Measure (i) quality on a real eval — NOT greedy-identity, which only proves they differ; (ii) the
      per-token gather-latency delta (IQ4_NL→Q8_0 roughly doubles table and gathered bytes; D8 put GET_ROWS at
      2.59 ms/token, so price the increase against it); (iii) bytes/token, expected ~unchanged — if it moves, the
      PLE is being streamed and that is its own finding.
      **PREREQUISITE ANSWERED 2026-09-04 (`instr-b7`) — GO, and it is CHEAP. The blocking question dissolved.**
      **The PLE ships as a DEDICATED SINGLE-TENSOR SHARD** (`tensors=1, offset=0`) in unsloth/bartowski/lmstudio, so
      **no trunk pull is needed**: `unsloth/Qwen3.8-Flash-Next-GGUF → Q8_0/…-00003-of-00006.gguf`, **54.400 GB,
      ~1.7 h** at this host's ~9 MB/s (vs 188 GB / 5.8 h for a trunk). BF16 PLE is `BF16/…-00003-of-00008.gguf`,
      102.400 GB / 3.2 h — **BF16 is the highest precision published anywhere; no F16/F32 trunk exists.** Ours is
      `per_layer_token_embd.weight IQ4_NL [160, 320001536] = 28.80 GB`.
      **SPLICE VERDICT: WORKS.** `/mnt/raid0/llm/tmp/inf70/tools/gguf_swap_ple.py` written and tested, modelled on
      `gguf_fuse_gate_up.py`: KV verbatim, tensor order preserved, other tensors byte-identical, PLE type swapped
      with shape unchanged and bytes == donor, offsets aligned — **and MUTATION-TESTED (one flipped byte in the
      spliced PLE is detected, so the PASS is not vacuous).** Loader checked: `get_rows` dispatches Q8_0/F16/BF16 and
      `qwen4exp.cpp` creates the PLE with no type constraint, so a spliced artifact loads unmodified.
      **DISK RESOLVED 2026-09-04 (operator): `IQ4_XS-uniform-b4r` deleted (98,267,083,136 B), freeing 92 GB →
      **243 GB free**, enough for the 178 GB peak. It was the right one to drop: B4 is complete ✅ and its
      `--tensor-type` recipe AND exact byte count are recorded, so it is regenerable in one `llama-quantize` pass —
      a reversible deletion. `IQ4_XS-uniform` (era anchor, OP-32) and `-gateup-r16` (current baseline) protected.
      **B7 dispatched as `b7-ple`**: download the Q8_0 PLE shard, splice into the era anchor with the mutation-tested
      tool, delete the donor immediately, then measure — **quality is the deliverable, speed is the guard-rail**, and
      an evidenced "no measurable difference" closes B7 rather than being a failure. **Do NOT pursue**: the PLE as a free speculative drafter — it maps an n-gram hash to a 160-wide
      *embedding* mixed into each layer, not a next-token distribution, so there is nothing to draft from;
      llama.cpp's `ngram-mod` is unrelated (it mines the current context for repeats, hence its retracted 2.8×).
      **Already settled, do not re-derive**: the PLE gather is not on the broken iqk repack path (it is a gather, not
      a matmul); it is bit-identical at n=3 in the node trace; and its one real cost — single-threaded `GET_ROWS` at
      9.34 ms/token, ~10% of the token — was fixed by D8 to 2.59 ms, the largest single gain of 2026-09-02.
- [x] **E3 — measure α before tuning anything.** ✅ 2026-09-03 (`e3-run`, build 10217 `540b1e697`, shared-Q8_0,
      24 production prompts 59–682 tok, chat path, linear drafting). **Both gating numbers delivered.**
      | n-max | α | mean acc len | ×all | ×coding | ×reasoning | ×general | paired min |
      |---|---|---|---|---|---|---|---|
      | 1 | 0.924 | 1.92 | 1.307 | 1.321 | 1.318 | 1.267 | 1.218 |
      | 2 | 0.870 | 2.74 | **1.607** | 1.660 | 1.649 | 1.471 | 1.265 |
      | 3 | 0.812 | 3.42 | 1.786 | 1.880 | 1.865 | 1.556 | **1.271** |
      | 4 | 0.752 | 3.99 | 1.799 | **1.967** | 1.900 | 1.467 | 1.136 |
      Plain baseline **12.591 t/s**. **Position-1 acceptance is FLAT at ≈0.91 at every depth** — asking the head
      for more does not degrade its first prediction; each further position costs ~0.10. **α differs sharply by
      class and the spread widens with depth** (9pp at n-max 1 → 27pp at n-max 4): coding 0.846 / reasoning 0.805 /
      general 0.572 at n-max 4. **Long prompts accept BETTER than short, monotone at every depth** (n-max 4: α
      0.862 vs 0.707, 1.98× vs 1.72×) — **the 12-token measurements were sampling the worst case.** Speed knee
      between n-max 3 and 4 (+0.7%). A-B-A closed at **−0.08% drift** with identical placement, so the ratios are
      not drift artifacts; `plainB` vs `plain` **24/24 byte-identical** across instances 45 min apart, so the trunk
      path is exactly reproducible and MTP divergence is attributable to MTP, not nondeterminism.
      **OPERATOR RULING 2026-09-04 — ADOPTED: n-max 3 as the fleet default, n-max 4 for coding roles.**
      With `shared-Q8_0` as the head. This is the recommended point below, accepted as given; α-by-class is measured
      so it is a static per-role setting, not a runtime decision. Expected: **1.786x fleet-wide** (α 0.812, mean
      accepted length 3.42, paired min 1.271) and **1.967x on coding roles** (α 0.846). Remaining operator step is
      whether/when this reaches production — the merge at `10acba0ab` is the experimental tree only.
      **RECOMMENDED OPERATING POINT: shared-Q8_0 head** (+0.75 GB/node; the self-contained head is 1.35 GB larger
      and buys nothing), **n-max 3 as fleet default** (better tail — paired min 1.271 vs 1.136 — and better
      general-class 1.556 vs 1.467, for 0.7% aggregate), **n-max 4 for coding-heavy roles** (1.967×). Since α by
      class is now measured, this can be a static per-role setting. Evidence
      `/mnt/raid0/llm/tmp/inf70/agents/e3-run/REPORT-FINAL.md`. (`feedback_measure_alpha_before_specdec_investment`):
      acceptance per draft position and mean accepted length on the production prompt mix, greedy AND the
      production sampler (temp + seed 42), `--spec-draft-n-max` ∈ {1, 2, 3, 4}, both heads, on the C5
      recipe and the C5 build with the C5 trunk. The B200 figures (66% acceptance, 1.67×) are the reference;
      the CPU multiplier will differ because a dispatch-bound trunk verifies n+1 tokens for nearly the
      cost of one — measure, do not extrapolate.
- [ ] **E4 — the comparison arms, one `--spec-type` at a time**: plain, `ngram-mod` (free, no head — but
      the recorded 2.8× n-gram win was a warm-context self-copy artifact, true gain ≤ +1.7%), `draft-mtp`
      with each head. **No DFlash or DFlash2 drafter exists for this model — RE-CHECKED 2026-09-04, still none.** z-lab's `dflash`
      repo lists DFlash2 targets as **Muse-Glimmer-30B and Qwen3.8-27B** — the 27B is a DIFFERENT model, not
      Flash-Next/`qwen4exp` (125B/A6B, Gated DeltaNet + QSA + PLE); DFlash1 covers Qwen variants, Gemma 4, MiniMax
      M2.5/M2.7, Kimi K2.5-2.7, GPT-OSS, Llama-3.1-8B, GLM 5.1, Alpamayo. **Nothing for `qwen4exp`.** The INF-62 arm
      stays excluded. Note the 3.43× DFlash2 headline is on the **27B**, so it is not a like-for-like target for us —
      and our MTP path cannot reach tree drafting anyway (B8(ii)).
      **⚠ BUT the re-check found two knobs the community uses that we have NEVER set — both present in our tree:**
      1. **`--spec-draft-p-min`** (`common/common.h:333`, default **`0.0f`**; live in the driver at
         `common/speculative.cpp:343,644,718`, where it breaks out of drafting when the top candidate is
         low-confidence). **Every arm we have ever run passed only `--spec-draft-n-max`**, so p_min has been 0.0
         throughout: the drafter emits the full n-max tokens even when its own top candidate is weak, and we pay
         verification on drafts that are then rejected. Our per-position acceptance falls 0.91 → 0.590 by position 4,
         so this is measurable waste. **The n-max knee we found between 3 and 4 may be an artifact of drafting
         unconditionally.** Community invocation uses `--spec-draft-p-min 0.75`. Relayed to `be1-ship` to sweep
         p_min ∈ {0, 0.5, 0.75, 0.9} and re-test deeper n-max at the best value.
      2. **`LLAMA_ATTN_ROT_DISABLE=1`** (`src/llama-kv-cache.cpp:316-319`, `llama-kv-cache.h:278`) — force-disables
         **attention rotation in the KV cache**; a community Flash-Next MTP repo calls it a "critical flag required".
         **Never set in any of our arms.** Relayed to `be2-fa` as a candidate mechanism for carrier 2: KV-cache
         rotation is exactly what would treat a wrapped/rotated region differently at a block boundary, and 256 is
         almost certainly a KV block-size constant. **If `LLAMA_ATTN_ROT_DISABLE=1` makes n_kv 257 exact under
         `-fa on`, the fix is one env var instead of a kernel repair or `-fa off`** — the best available outcome for
         the speed goal.
      **Corroboration, not a gap**: the community repo reports acceptance **0.90 code / 0.74 prose**, consistent with
      our 0.846 coding / 0.572 general at n-max 4. Nobody is getting dramatically better acceptance on this model, so
      the opportunity is in wasted work and kernel exactness, not in a better drafter. (An earlier search summary
      claiming "0.93–0.99 acceptance" is NOT corroborated by the repo itself and is treated as marketing; the same
      summary self-contradicted on the head size, 4B vs 2.6B.) Same build,
      same window, same trunk artifact. Concurrency 1 only, per unsloth's own loss at 8.
- [ ] **E-GATE**: acceptance-weighted t/s against the non-speculative C5 number for the same trunk,
      reported per the artifact rule and with the sampler named. Note the PLE regime: under `--no-mmap`
      the 51B table is resident and every draft token pays its own PLE gather and hc stream mixing; that
      cost is part of the measured number, not something to subtract.
      **OPERATOR RULING 2026-09-03 — exactness is NOT a gate for MTP.** Verbatim: *"approximate MTP isn't an issue
      as long as it has a decent acceptance rate and doesn't lead to garbage outputs."* This settles the
      (a)/(b)/(c) fork left open in E2a: **ship (c), approximate MTP**, provided the two criteria below hold. The
      consequence is a re-prioritisation, not just a note — **the exactness hunt no longer blocks MTP serving**:
      - **Criterion 1 — no garbage. ALREADY MET on the evidence to hand**: all 12 production-length chat
        generations on the MTP arm classified COHERENT (`mtp-tip2`), and the divergences are one greedy argmax
        flip per prompt followed by ordinary drift, not corruption. Keep it as a standing gate on every MTP arm
        (classify by REASON, production-length prompts), not a one-off.
      - **Criterion 2 — decent acceptance. NOT YET MEASURED on real prompts; this is now the critical path.**
        `e3-run` is measuring α per draft position on the 24-prompt production mix at n-max 1–4 against build
        10217. Until it lands there is no basis to call MTP deployable, and no basis to quote a multiplier at
        production length — the 1.44x is short-prompt-only.
      **Two things exactness still governs, and they must not be quietly dropped:**
      1. **Measurement discipline.** An MTP run is not token-comparable to a plain run, so **no A/B may have MTP on
         one arm and off the other**, and no greedy-identity gate may be run through the MTP path. That is a
         benchmarking constraint, not a serving one, and it now applies permanently.
      2. **BATCH-ENVELOPE is demoted, not closed** — it is correctness hygiene and a real unknown in the forward
         (it also governs concurrent prefill), but it is no longer a deployment blocker. Pursue it on its own
         merits at the recurrent/GDN path; do not hold MTP for it.

## Concurrency (measured on our CPU, 2026-09-03) — MTP stays a win; a prefill-corruption defect

**UPDATE 2026-09-04 (`batch-envelope`): simultaneous admission is COHERENT again 4/4 on `10acba0ab` — X-CONC's
garbage is gone. But COHERENT ≠ CORRECT: 3 of 4 concurrent streams still DIFFER from the same prompt served alone,
and staggering does not help — ROW COUNT, not admission pattern, is what matters. With the row-exact forward the
streams are SAME 4/4, at ~5–8% per-slot decode cost. So concurrent serving today returns valid-but-different output
per slot; that is a policy question, not a corruption one.**

**Root cause of the prefill-corruption defect found 2026-09-03 (`gdn-rowexact`): it is NOT a multi-sequence bug —
packing 4 sequences in one ubatch is bit-exact (0/5450 nodes differ). Four simultaneous ~12-token prompts make a
48-row ubatch, which crosses iqk's `nrc_y >= 32` IQ4_XS repack threshold (LONG-PROMPT-GARBAGE); staggered starts stay
below it. The same fix (`99425578d`) unblocks simultaneous admission once validated.**

Answering the operator's challenge to our own hardware rather than the unsloth GPU README (`mtp-conc`,
coherence-checked every round):

| concurrency | off agg t/s | MTP on agg t/s | multiplier | coherent |
|---|---|---|---|---|
| C=1 | 9.9 | 14.8 (acc 0.88) | 1.50× | yes |
| C=4 staggered | 17.4 | 19.6 (acc 0.92) | 1.13× | 4/4 |
| C=4 simultaneous | — | — | — | **0/4 — garbage** |

- **MTP is a net win at concurrency, not a loss** (1.50× → 1.13× C=1→C=4); the GPU "net loss at
  concurrency 8" does not apply to a dispatch-bound CPU. Corrects the earlier cited claim.
- **Concurrency scales ~1.76× at C=4** (off, staggered) — the box is not one indivisible resource.
- **NEW DEFECT (below) — concurrent prefill corrupts output.**

**★★ X-CONC RE-SCOPED UPWARD 2026-09-07 — IT IS A BLOCKING PROMOTION GATE, NOT A DEMOTED ITEM.**
The 2026-09-03 row below was wrong in both directions and is replaced. It called this a *multi-sequence*
bug (it is not) and prescribed a staggered-admission scheduler (which treats a symptom), while the
2026-09-04 update above it already carried the resolution and the row was never updated to match. But the
opposite error — filing it at "much lower severity" because blast radius is zero today — is the one that
matters more: **blast-radius-is-zero is a statement about today's exposure, not about whether the defect is
closed, and qwen4exp is a promotion candidate.** Operator, 2026-09-07: *"we may want to promote this
qwen4exp model to production. We can't have it dumping garbage if we do."*

**What is established.** It is **NOT** a multi-sequence bug — `gdn-rowexact` proved packing 4 sequences in
one ubatch is **bit-exact, 0/5450 nodes differ**. It is the **same iqk `nrc_y >= 32` IQ4_XS repack defect as
LONG-PROMPT-GARBAGE**: four simultaneous ~12-token prompts make a **48-row ubatch** and cross the threshold.
Staggering merely kept the ubatch under the threshold, so the original mitigation was treating a symptom.
On `10acba0ab` simultaneous admission is **COHERENT 4/4** — the garbage is gone.

**Ancestry (verified by the coordinator, 2026-09-07): both `99425578d` and the `10acba0ab` merge ARE
ancestors of `inf70/champion3` @ `9c4f73e29`.** So the champion carries the fix and a promotion would not
ship the corruption.

**⚠ THE GAP THAT MUST NOT BE BURIED: the COHERENT 4/4 re-test ran on `10acba0ab`, NOT on the champion.**
Champion-3 stacks levers on top of that merge — `GGML_ROWCOL_SPLIT`, `GGML_TINY_SOLO`, the dequant knobs —
**several of which change row counts and which kernel path a node takes, and the entire defect class is
ROW-COUNT-TRIGGERED.** *"The fix is in the tree"* and *"the champion is coherent under simultaneous
admission"* are **different claims, and only the first is proven.** HYG-1b has just found every build dir in
the shared tree stale, which is exactly why the stronger claim must not be assumed.

- [ ] **G2-CONC — BLOCKING PROMOTION GATE. Must run on the PROMOTION CANDIDATE BINARY, not on an ancestor.**
      **This gate is NOT satisfiable by inheritance: citing `10acba0ab`'s COHERENT 4/4 does not close it**,
      and neither does the ancestry check above — the ancestry proves the fix is present, not that the
      stacked champion still clears the trigger. Arms:
      (a) **`-np 4` simultaneous admission**, coherence classified **by REASON** — `COHERENT` / `SALAD` /
      `EARLY-EOS` / `SHORT` / `EMPTY` / `HTTP-ERROR` — never a pass/fail count, because the degenerate
      rounds ran *faster* per slot while producing garbage and a t/s number without an output check is
      inflated.
      (b) **A direct probe of the `>= 32`-row trigger**: the 48-row ubatch shape that originally broke it
      (4 simultaneous ~12-token prompts) **and** a long-prompt arm — both cross the same threshold by
      different routes, and the champion's row-count-changing levers could move either one independently.
      Record the ubatch row counts actually observed, not the ones predicted from prompt length.
      Prove the binary with `strings` before believing any pass (HYG-1b). Repro and prior evidence:
      `/mnt/raid0/llm/tmp/inf70/agents/mtp-conc/`.
      **Cross-links: PROD-1 (the canonical recipe must carry this gate) and PROD-3 / any champion-artifact
      promotion. Both cross-references are drafted and handed to the coordinator — do not add them here
      while the PROD-1 agent is running.**

- [x] **G2-CONC-POLICY — OPERATOR DECISION, not a defect. Per-slot reproducibility vs throughput.**
      **Even when coherent, 3 of 4 concurrent streams DIFFER from the same prompt served alone**, and
      **ROW COUNT — not admission pattern — decides it**, so a staggered-admission scheduler does not fix
      it. The row-exact forward makes the streams **identical 4/4 at ~5–8% per-slot decode cost.**
      Concurrent serving today therefore returns **valid-but-different output per slot**.
      **Options:** (A) ship as-is — full throughput, per-slot output depends on how many rows shared the
      ubatch; eval determinism and prompt-cache behaviour become concurrency-dependent, and any A/B run
      through a concurrent server inherits an uncontrolled variable. (B) row-exact forward always —
      identical 4/4, costs ~5–8% per-slot decode. (C) row-exact forward as a per-route policy — pay the
      5–8% only on routes that need reproducibility (evals, cached prompts, anything whose output is
      compared across runs) and take full throughput elsewhere; costs a policy surface and a way to prove
      which route a request took.
      **✅ RESOLVED 2026-09-07 — THE OPERATOR CHOSE (C), per-route row-exact.** Reproducibility-sensitive
      routes (evals, cached prompts, anything compared across runs) run row-exact; everything else takes full
      throughput. The open work is the policy surface and a way to prove which route a request took. PROD-1
      is where "which routes are row-exact" becomes importable constants.
      **Original recommendation, retained: (C).** The defect is not correctness — every stream is valid — so paying 5–8%
      fleet-wide buys reproducibility for routes that mostly do not need it, while (A) silently makes
      concurrency a hidden variable in every measurement taken through the server, which this campaign has
      already been bitten by in other forms. **Not decided here.** Operator-queue row drafted and handed to
      the coordinator.
      **✅ CHECKBOX SYNCED 2026-09-07 — the body already recorded `RESOLVED 2026-09-07, the operator chose (C)`
      per-route row-exact, but the box had never been flipped.** Prose-without-checkbox is a wrap-up defect; it
      is corrected here rather than re-narrated.

**Superseded row, retained for the record (filed 2026-09-03, wrong on both the mechanism and the fix):**
*"X-CONC — qwen4exp multi-sequence prefill corruption, serving blocker … the qwen4exp multi-sequence prefill
path corrupting shared state when >1 full sequence shares a prefill batch … Interim mitigation: a staggered-
admission scheduler (one prefill in flight at a time)."* Both the "multi-sequence" diagnosis and the
staggered-admission mitigation are refuted above.

## Disk: the artifact rule costs 92 GB per experiment on this model (measured 2026-09-04)

Surfaced by an operator question — *"I'm surprised we only have 151 GB free, I cleaned up last week and freed
~400 GB"*. The answer is that **this campaign consumed it, predictably and by design.** One model directory holds
**547 GB**:

| variant | size | origin |
|---|---|---|
| `IQ4_XS-uniform` | 92 GB | era anchor (pre-existing, OP-32 baseline) |
| `IQ4_XS-uniform-gateup` | 92 GB | **B3, this campaign** |
| `IQ4_XS-uniform-gateup-r16` | 92 GB | **B3-4, this campaign** (current Axis B/D baseline) |
| `IQ4_XS-uniform-b4` | 91 GB | **B4, this campaign** |
| ~~`IQ4_XS-uniform-b4r`~~ | ~~92 GB~~ | **B4** — deleted 2026-09-04 (regenerable) |
| `UD-IQ4_XS` | 88 GB | served file |

Plus 88 GB of worktrees (one build tree per subagent) and 163 GB of cache. **~367 GB of the ~590 GB consumed since
the 2026-08-31 reclaim (743 GB free then) is this campaign's own artifacts.**

**This is the direct cost of the OP-32 artifact rule**: a delta must be measured with the artifact held identical on
both arms, so every quant experiment on a 125B model mints a new 92 GB file rather than mutating one. That is the
right rule — it is what makes the deltas trustworthy — but on this model it means **~92 GB per experiment, and at
~150–240 GB of working headroom we can hold roughly one experiment in flight at a time.**
**Consequence to plan around, not a defect**: B7 will cost another ~92 GB for its output; any future quant
experiment will too. Budget a deletion per experiment, and prefer artifacts whose recipe + byte count are recorded
(hence regenerable, hence reversibly deletable) when choosing what to drop.

## RECLAIM-1 — the post-convergence artifact reclaim (filed 2026-09-04 on operator prompt)

Operator: *"aren't we now converging on the final kernel/model quant? Once we do, we could delete all the other
unnecessary ones."* Correct, and here is the concrete plan so it happens deliberately rather than under pressure.

**Are we converged?** Nearly, on two of three axes:
- **Kernel — effectively settled**: `c51e4dabf` = D8 + D7a + D1 + B3-k + the iqk IQ4_XS repack fix + `ROWEXACT_N`
  + `FA_SPLIT_KV`. Open only on BE-3 (a non-propagating carrier) and the claim-grade ABA.
- **Serving config — SETTLED, ABA-confirmed 2026-09-04**: MTP head `shared-Q8_0`, `--spec-type draft-mtp
  --spec-draft-n-max 4 --spec-draft-p-min 0.5`, `GGML_ROWEXACT_N` unset, **KV f16 (do NOT quantise)**, `-t 48`,
  `-fa on` + `GGML_FA_SPLIT_KV=0`, canonical env + `taskset -c 0-95 numactl --interleave=all`
  → **23.16 t/s, 1.876× plain** (23.62 superseded; see the ABA block).
- **★ STANDING MEASUREMENT RULE earned by this batch — THE HOST DRIFTS ~3% OVER HOURS.** Same config measured
  23.16 at 12:52 and 22.58–22.73 at 15:05–15:55, while repeating to **1.1% WITHIN a window**. Therefore **any
  INF-70 comparison below ~5% must be SAME-WINDOW and ALTERNATING, or it is not evidence.** Both results
  overturned on 2026-09-04 (the 23.62 headline and the depth-beyond-4 gain) were cross-window artefacts of
  exactly this size, and be1-ship's 18 arms ran sequentially over ~4 hours. A sequential arm matrix measures
  drift as if it were the treatment.
- **Depth beyond n-max 4 — CLOSED, does not pay.** A same-window alternating n4-vs-n5 test returned **ratio
  0.9987** (12/20 and 10/20 prompts — coin flips). The earlier cross-window sweep showing n5/n6/n8 ~3% ahead was
  the drift artefact above. p_min 0.5 vs 0.6 is flat. The plateau is real and **no better operating point exists**.
- **KV cache — SHIP f16, do NOT quantise (B9 CLOSED).** Size analysis was right and irrelevant: 12 of 48 layers
  carry KV, 24.0 KiB/token = 2.42% of budget, 45–90 MiB saved. Sign was **wrong for MTP**: plain gains +0.7% to
  +2.1% as predicted, but **MTP LOSES 2.5–3.5% because α falls 0.8274 → 0.8166.** `attn_rot_k/v` DID flip to 1
  (head dim 256) on both the main and DSA indexer caches, and that never-exercised path is **clean** — 96
  quantised-KV requests, zero incoherence, no assert. `LLAMA_ATTN_ROT_DISABLE=1` was not needed as a rescue but
  was decisive as **attribution**: it recovers 1.9% and lifts α to **0.8329, ABOVE f16's 0.8274** — so the
  **Hadamard rotation, not quantisation error, is what costs acceptance**. q8_0 still loses 1.4% with rotation
  off. A KV-quant win on a plain decoder does not transfer to a speculative one.
- **Bandwidth — MTP takes CPU decode OFF the bandwidth wall.** Plain 51.3 GB/s (33.5% of 153). MTP's
  plain-equivalent 96.3 GB/s (62.9%) is not what it moves: the verify batch carries **3.79 tokens per forward**,
  so actual traffic is **1.096 GB/token = 25.4 GB/s (16.6%)**. The roofline argument for CPU decode changes shape
  under speculation — amortising the weight read across accepted tokens is the lever, not raising GB/s.
**⚠ STALE AS WRITTEN (flagged 2026-09-07): the "B7 in flight" sequencing below is spent.** The PLE-precision
B7 **reported NO on 2026-09-04** and RECLAIM-1 **executed the same day** (123 GB → 421 GB free). Read the
paragraphs that follow as the record of how that decision was reached, not as an outstanding trigger. The
live artifact question is now the OP-37 / PROD-3 reconciliation flagged above (`-gateup-r16` vs B4's
`IQ4_XS-uniform-r16` + F16 router), and **"B7" here means the CLOSED PLE item, never INF-71.**

- **Artifact — NOT yet**: `-gateup-r16` is the best measured (12.73 vs 12.61 plain), but **B7 is in flight** and may
  produce a better one (PLE at Q8_0). **The artifact question closes when B7 reports**, and only then.

**✅ RECLAIM-1 / OP-37 EXECUTED 2026-09-04 (operator: "proceed") — 123 GB → 421 GB free.** Deleted, all
reversibly: `IQ4_XS-uniform-gateup` (92 GB), `IQ4_XS-uniform-b4` (91 GB), `IQ4_XS-uniform-pleQ8` (116 GB —
B7's measured loser). Protected and verified present afterwards: `IQ4_XS-uniform` (era anchor),
`-gateup-r16` (current baseline), `UD-IQ4_XS` (served file), `MTP` (head, in the serving config).
**Precondition satisfied first**: `gguf_swap_ple.py`, the pleQ8 artifact's ONLY regeneration recipe, lived
solely in `/mnt/raid0/llm/tmp/` — a scratch path — so it was committed to `scripts/inf70/` BEFORE the
deletion. `gguf_fuse_gate_up.py` was already in git (`inf70/b3` `dd27ec3bb`). A deletion is only reversible
if its recipe is in git; on the filesystem it is not a recipe, it is a coincidence.

**Original plan, retained:**
**What may be deleted once B7 reports — 183 GB, both reversibly:**
| artifact | size | why deletable | how to regenerate |
|---|---|---|---|
| `IQ4_XS-uniform-gateup` | 92 GB | superseded by `-gateup-r16`, which was built from it | `tools/inf70/gguf_fuse_gate_up.py` from the era anchor (branch `inf70/b3`, `dd27ec3bb`) — one pass, no requant |
| `IQ4_XS-uniform-b4` | 91 GB | B4 complete ✅, an experiment arm | B4's `--tensor-type` overrides, one `llama-quantize` pass |
| B7's loser | ~92 GB | whichever of {IQ4_NL, Q8_0-PLE} B7 rejects | the splice tool, or it is the anchor and stays |

**What must NOT be deleted — CORRECTED 2026-09-04 on operator challenge; my first version was wrong:**
I wrote that deleting `IQ4_XS-uniform` "would invalidate the comparison basis for every future delta on this model."
**That is false, and the operator is right: the comparison basis is TRANSITIVE, exactly as autokernel already
operates it.** A champion that was properly benched against the anchor *inherits its provenance*, and future deltas
are measured against the **champion**, not the anchor — that is the champion-of-record model
(`feedback_one_champion_invariant`: one champion aggregates all work between promotions). The anchor's value lives
in the **recorded delta**, not in the file. Ours is recorded: gate-up 10.33 → r16 10.49 ±0.02 (−1.48 ms) at build
10196 with placement proven, and r16 12.73 vs uniform 12.61 on the production mix at the merged tip — same build,
same window, same recipe, SHA-256 and byte counts on both sides. **So r16 can serve as the champion and the anchor
becomes deletable.**
**Three conditions make that sound, and they should be stated rather than assumed:**
1. The champion was measured against the anchor **under the artifact rule** (same build/window/recipe) — r16 was.
2. The chain is **recorded with enough provenance to reconstruct it** — SHA-256, byte counts, build ids, recipe: yes.
3. The anchor is **re-obtainable** if a future re-validation ever needs it. `IQ4_XS-uniform` is an unsloth-published
   quant, so it is a ~92 GB / ~2.8 h re-download rather than an unrecoverable loss. **Verify that specific file is
   still published before deleting it** — that is the only real precondition, and it is a five-minute check.
**Genuinely keep**: `-gateup-r16` (or whatever B7 promotes) as the champion; `UD-IQ4_XS` (88 GB, the served file);
`MTP/` (6.5 GB, the heads earning the 1.89×).
**Revised ceiling: with the anchor also releasable under a promoted champion, the reclaim is ~275 GB rather than
~183 GB**, leaving champion + served + heads ≈ 187 GB.
**Sequencing unchanged: do NOT reclaim before B7 reports** — it needs ~92 GB now, and deleting its comparison inputs
mid-experiment would be self-defeating. **Trigger: B7's verdict.**

## OPERATOR GOAL 2026-09-04 — "run qwen3.8-Next-Flash AS FAST AS POSSIBLE"

Verbatim. This **reorders the campaign's priorities** and is not just a restatement of intent:
- **Speed ranks above losslessness.** The operator already ruled approximate MTP acceptable (decent acceptance +
  no garbage). So where a lossless and an approximate configuration differ in speed, **the faster one wins** —
  losslessness is a bonus, not a requirement, and no task may treat it as a gate.
- **The comparison that decides this has never been run**: lossless and approximate multipliers have only ever been
  measured at DIFFERENT n-max on DIFFERENT prompt sets (approximate: n-max 2/3/4 on 24 production prompts;
  lossless: n-max 2 on 7 gate prompts with `-fa off`). `be1-ship` Phase 2 runs the cross on one prompt set.
- **`-fa off` is a cost, not a free win.** Every lossless result to date depends on it, and its cost has only been
  characterised as "within noise on the gate table" — not measured at production or long context, where flash
  attention actually earns its keep. `be2-fa` measures it; if it is free the decision is trivial, if it is not then
  `-fa on` with accepted non-exactness is a legitimate answer under this goal.
- **Standing ledger of what speed is still available**, so nothing is lost: BIOS 5600 MT/s + the C8 uncore checklist
  (held for the operator's reboot — the DIMMs run at 4800 of 5600 and the uncore caps at ~37% of nominal); the
  dispatch floor (~65% of the token at the best measured point, Axis A / INF-67 fused decoder); B7 PLE precision
  (quality, not speed); and B8's finding that ~20% of the bandwidth gap to the 122B is architectural.

## Deployable serving speed (claim-grade, 2026-09-03)

Single-stream `llama-server` decode of qwen3.8-next-flash, `-np 1 -c 4096 -t 48 --no-mmap`, canonical env,
forcing eviction, placement 23.0 GiB × 4, warmup + 5 × 128-token greedy `/completion` (`server-tps`),
coherence-gated (all 5 reps' greedy text bit-identical).

**Re-anchored on the merged experimental tip `0d2af8194` (b3k slab merged; build 10203, tree-identical to
`inf70/b3k`; slab default ON, `GGML_MMID_SLAB=0` = control), 2026-09-03, one lock hold, in-window
ggml-linkage + placement proven per arm:**

| artifact | slab | decode | ms/token | GB/s (% of 153) |
|---|---|---|---|---|
| uniform IQ4_XS (era anchor) | on (default) | **12.55 t/s** (ABA 12.589 / 12.516 ±0.05) | 79.7 | 52.3 (34.2%) |
| uniform IQ4_XS | off (control) | 12.079 ±0.033 | 82.79 | 50.3 (32.9%) |
| `IQ4_XS-uniform-gateup-r16` (best artifact) | on (default) | **13.06 ±0.01 t/s** | 76.59 | 52.7 (34.5%) |

- **The slab gain reproduces in the server path**: same binary/window, slab on vs off on uniform =
  **+3.9%** (12.55 vs 12.079, −3.35 ms/token) — confirming, and slightly stronger than, the +3.07%
  `llama-bench` proxy delta. All four arms coherent (greedy text bit-identical across 5 reps).
- **Both headlines beat the pre-measurement projection (12.4 / 12.8).** The prior (pre-b3k) merged tip
  `9e75132e3` measured uniform 12.00 / r16 12.38 in an earlier window — consistent with the slab-off
  control here (12.079). r16 vs uniform (both slab-on): +4.1% decode at ~equal GB/s, tracking the −3.0%
  bytes/token.

**RE-ANCHORED 2026-09-03 on the merged tip `42332502c` with PRODUCTION-LENGTH prompts — the gate the first
anchor lacked.** The earlier 12.00/12.38 and 12.55/13.06 figures were withdrawn because every gate behind them used a
12-token prompt while the tree produced garbage above ~32 (the iqk IQ4_XS ≥32-row repack defect, LONG-PROMPT-GARBAGE,
now fixed and merged). They are **replaced, not restored** — the configuration differs (chat-completions path with
thinking disabled, the production serving path, vs the raw `/completion` path before).

| artifact | decode (n=23 timed) | prompt range | correct behaviour | coherence gate |
|---|---|---|---|---|
| uniform IQ4_XS (era anchor) | **12.61 ±0.10 t/s** (12.43–12.93) | 54–682 tok | **27/27** | 23 COHERENT + 4 correct SHORT, **0 SALAD, 0 EARLY-EOS** |
| `IQ4_XS-uniform-gateup-r16` (best artifact) | **12.73 ±0.10 t/s** (12.50–12.97) | 54–682 tok | **27/27** | 23 COHERENT + 4 correct SHORT, **0 SALAD, 0 EARLY-EOS** |

27 production prompts — 8 coding / 8 reasoning / 8 general from `question_pool.jsonl` plus the three P0 prompts —
greedy, `max_tokens` 200, `enable_thinking` false, `-np 1 -c 8192 -t 48 --no-mmap`, canonical env, forced eviction,
**placement proven 23.0–23.1 GB × 4 and resident `libggml-cpu.so` proven to be the merged-tip build in-window on both
arms**. Coherence classified by REASON in the same window as the timing (`classify.py`); the 4 SHORT rows are
multiple-choice/short-answer items answering correctly (`E`, `B`, `<answer>English</answer>`, `B`) at n=2, where the
classifier correctly declines to compute degeneracy statistics rather than mislabelling them. Evidence
`/mnt/raid0/llm/tmp/inf70/reanchor2/`.

**Finding worth carrying: r16's advantage over uniform SHRINKS at production context lengths — +0.9% here (12.73 vs
12.61) against +3.1% at a 12-token prompt.** r16's edge is a bytes/token effect (−3.0%); as context grows, more of
the token's time goes to attention/KV work that the smaller weight stream does not help, diluting it. An artifact
advantage measured at toy prompt length overstates what production sees.

Note the fused-decode gate is opt-**out** (`GGML_FUSED_DECODE_OFF`), confirmed set in every arm's
`/proc/<pid>/environ`; the graph path is active. Ceiling context: the best served point (r16) reaches
**34.5% of the recipe's 153 GB/s** read bandwidth, i.e. ~65% of the token is still dispatch floor; the
bandwidth third also carries the BIOS headroom (DIMMs at 4800 of 5600, uncore-capped at ~37% of nominal),
held for the reboot. Evidence: `/mnt/raid0/llm/tmp/inf70/reanchor/` (per-arm timelines, `numastat`,
linkage proofs, `summary-*.txt`).

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

### Research-intake follow-up 2026-09-07 — CLOSED on arrival

- [x] **Reconcile INF-70 main vs `lane/inf70-audit-20260902`** ✅ 2026-09-07 — closed by this merge: main now
  carries the audited copy, so the superseded ≈ 100–130 GB/s expert-path figures are gone and 61.8 GB/s at
  proven placement is the only number here. Filed by the 2026-09-07 research-intake wave (`intake-1318#record`).
