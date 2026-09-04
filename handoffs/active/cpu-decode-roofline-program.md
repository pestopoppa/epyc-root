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
      makes the identical shape bit-exact at prefix 254 and 300 while `--fa 1` diverges. **It predicted the two
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
      **FINAL RECOMMENDED CONFIGURATION: n-max 4, `--spec-draft-p-min 0.5`, row-exact off, `--fa 1` +
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
      keep `--fa 1` with the split path ON and accept the non-exactness — that is also the fastest configuration at
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
      **Proof (`llama-rowexact`, build 10221, prefix 254, `--fa 1`, carrier 1 already removed):** default split ON →
      `node_584 FLASH_ATTN_EXT [256,24,3]` row 2 only, 68,334,110 state bytes differ (reproduces batch-envelope's
      `e7fa1p254` exactly); **`GGML_FA_SPLIT_KV=0` → ALL 3 ROWS IDENTICAL, 0/248320 logits, 0 state bytes.** One
      boolean removes the entire carrier with FA still on.
      **SPEED — and this is what decides it** (llama-bench, build 10221, depth sweep, t48):
      | depth | `--fa 1` split ON (default) | `--fa 1` `SPLIT_KV=0` (exact) | `--fa 0` |
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
      **RECOMMENDATION (ranked, and it inverts the earlier note): (a) `--fa 1` + `GGML_FA_SPLIT_KV=0`** — the fastest
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
- [ ] **B8 — the head-to-head the campaign never did: qwen4exp (125B/A6B) vs the LIVE 122B/A10B, and where its
      2.12x MTP multiplier comes from.** Filed 2026-09-03 on an operator challenge ("I'm surprised we're still
      getting such low tok/s on a model with only 6B active weights ... the older 122B-10B Q4 ran 20+ t/s").
      **First correction: that 20+ is a SPECULATIVE number.** The live `architect_critic` role
      (Qwen3.5-122B-A10B UD-Q4_K_M, `orchestration/derived/stack_priors.yaml`) records `baseline_tps: 11.3`,
      `optimized_tps: 24.0`, `speedup: 2.12x` under `spec_type: draft-mtp`, **`draft_max: 4`, `k: 4`**,
      `optimized_tps_long_context: 15.76`, measured 2026-07-31, category OPTIMUM. **Plain vs plain, qwen4exp is
      already ~12% AHEAD: 12.61 vs 11.3 t/s.** The honest counterpart to 24.0 is our MTP number (~18.1), not our
      plain one.
      **Two real gaps remain.** (a) **The MTP multiplier: 2.12x vs our 1.44x** — the largest unexplained lever in
      the program. Production runs `draft_max: 4`; every qwen4exp MTP measurement so far used n-max 2. Relayed to
      `e3-run` 2026-09-03 to sweep n-max 4 (and 5-6 if acceptance holds) — we may simply have been sampling below
      the operating point a comparable model already uses in production. (b) **Bandwidth efficiency: ~64 vs
      52.4 GB/s.** From the registry's 69 GB / 122B params (~4.5 bpw) the 122B streams ~5.65 GB/token and converts
      it at ~64 GB/s; qwen4exp streams a MEASURED 4.16 GB/token at 52.4 GB/s. **At the 122B's efficiency qwen4exp
      would run ~15.3 t/s, so ~20% is on the floor.** (The 122B's bytes/token is DERIVED, not measured like ours —
      treat (b) as indicative until a like-for-like measurement is taken; that measurement is task (i) below.)
      **The likely cause is the architecture itself, and this is the finding worth having.** Fewer active
      parameters spread over MORE and SMALLER ops is worse on a bandwidth-bound CPU. Already measured here: 33.4 ms
      of a 97.3 ms token in **3,468 nodes that move no weights**, out of ~7,000 nodes/token; small gemvs at 40% of
      read bandwidth against 94% for the one big `lm_head`. Every layer pays GDN recurrence + QSA indexing + a PLE
      gather + 4-stream hyper-connection mixing + a 10-of-512 expert gather. The 122B has 64 conventional attention
      layers and a plainer MoE: 10B active in fewer, bigger GEMMs. It streams 36% more bytes and converts them far
      better. **qwen4exp trades arithmetic efficiency for parameter efficiency, and on this machine that trade is
      currently winning by only 12% on plain decode while costing most of a speculative multiplier** — a model-choice
      finding, not merely an optimization gap.
      Tasks: **(i)** measure the 122B's ACTUAL bytes/token and plain decode under our canonical recipe + coherence
      gate, so the efficiency comparison is like-for-like instead of derived; **(ii)** ✅ RESOLVED 2026-09-03 — **the gap is ARCHITECTURAL, not a tuning gap.** Confirmed from source
      (`e3-run` Addendum A): `draft-mtp` and `draft-tree` are separate impl classes selected from an ordered
      priority list and **do not compose**; the tree drafter's contract requires a STANDALONE draft model (vocab
      check, own sampler on `ctx_dft`, drafts via `llama_decode(ctx_dft, batch)`), while the MTP head is a single
      block with no independent forward and **no `k` parameter exists on the MTP path**. So the production 122B's
      2.12× (`k: 4` tree) is **not a target our MTP path can be tuned toward**. Against the LINEAR ceiling, our
      1.967× on coding is near the practical maximum. Original wording retained: **the comparison was NOT
      like-for-like: `architect_critic`'s 2.12x uses `k: 4`
      TREE drafting, while every qwen4exp MTP arm run so far is LINEAR (`e3-run`, 2026-09-03). Establish FIRST
      whether our runtime supports tree drafting for `draft-mtp` at all; if it does not, the 1.44x-vs-2.12x gap is
      STRUCTURAL rather than a tuning gap — a materially different conclusion.** Then n-max, then acceptance per
      position vs the 122B's, then whether native-MTP vs our ported path differs; **(iii)** decide whether the dispatch floor is reducible enough to make the
      architecture pay, or whether the honest conclusion is that this model class needs bigger fused ops (Axis A /
      INF-67) before it beats a plainer MoE on CPU. Feeds the operator's model-choice decision; do not treat
      qwen4exp's suitability as settled.

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
      **Recommended scope: ONE arm** — `-ctk q8_0 -ctv q8_0` vs f16 at ctx 4096 and 8192, plain AND with MTP,
      token-weighted decode + prefill + coherence by REASON, plus an explicit check of whether `attn_rot_k/v` flip to
      1 in the server log and whether output stays coherent when they do. **Predicted gain ~1–2% decode at
      production context; adopt only if measured and if the MTP path stays clean.** Do not pursue q4_0.
- [ ] **B7 — is the PLE table under-quantized FOR THIS MACHINE? (precision UP, the inversion of B4)**
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
         `--fa 1`, the fix is one env var instead of a kernel repair or `-fa off`** — the best available outcome for
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

- [ ] **X-CONC — qwen4exp multi-sequence prefill corruption (filed 2026-09-03, serving blocker).**
      With `-np 4` and 4 requests that prefill in one batch (simultaneous starts), greedy output is
      deterministic garbage (0/4 coherent; an 18-token early stop on prompt 3); staggering the starts by
      ~0.7 s gives 4/4 coherent. **Reproduced on the plain merged binary (build 10202, no MTP/spec)**, so it
      is the qwen4exp multi-sequence prefill path corrupting shared state when >1 full sequence shares a
      prefill batch — the same non-row-exact batched forward E2c localized, here escalated from a logit
      drift to garbage. Repro and evidence: `/mnt/raid0/llm/tmp/inf70/agents/mtp-conc/`. Interim
      mitigation: a staggered-admission scheduler (one prefill in flight at a time). Real fix: the SAME kernel fix as E2a/E2c — make `build_delta_net_chunking` (delta-net-base.cpp:435) row-exact vs `_autoregressive` for small n; mtp-exact confirmed 2026-09-03 this one site is the common cause. **Blocks concurrent serving with
      simultaneous admission.** The coherence-check lesson: a concurrency t/s number without an output
      check is inflated (the degenerate rounds ran faster per slot while producing garbage).

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
- **Serving config — settled pending the ABA**: n-max 4, `--spec-draft-p-min 0.5`, `--fa 1` + `GGML_FA_SPLIT_KV=0`,
  row-exact off → 23.62 t/s.
- **Artifact — NOT yet**: `-gateup-r16` is the best measured (12.73 vs 12.61 plain), but **B7 is in flight** and may
  produce a better one (PLE at Q8_0). **The artifact question closes when B7 reports**, and only then.

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
