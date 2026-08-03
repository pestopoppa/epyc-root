# DIVE-C — intake-950 (PIE) + intake-954 (COFFE) — MEASUREMENT INSTRUMENTS

## HEADLINE: wall-clock is NOT replaceable for us, except in the eval ladder.
(a) GPU kernel candidates: **NO — structurally blind**
(b) CPU decode benchmarking: **NO — actively misleading, the worst of the three**
(c) Generated-code eval ladder: **YES, with named caveats. This is where the instrument belongs.**

## THE FALSIFICATION — RUN IN-SESSION ON OUR OWN EPYC
/mnt/raid0/llm/tmp/dive-c-probe/cpi_probe.c, gcc -O2, taskset -c 100, 8 reps, 8192^2 f32 matrix sum:
| candidate            | instructions:u | IPC  | wall     |
| naive column-major   | 444,837,196    | 0.24 | 483.5 ms |
| tiled 64x64          | 453,292,177 (**+1.90%**) | 0.84 | **171.1 ms (2.83x FASTER)** |
**RANK INVERSION.** IPC swings 3.5x between two implementations of the same computation on the same
machine. Instruction count ranks the WRONG candidate first — in exactly the memory-bound regime our
kernels live in, and on exactly the transformation (tiling) an autokernel loop generates.
Also: `perf stat -e instructions:u -- sleep 0.05` = 1,748,588 vs `sleep 0.5` = 1,747,004 —
10x wall difference, **-0.09% instruction difference** (structural analogue of GPU offload).
COFFE's Eq.1 is an IDENTITY, not a model. CPI is a property of the program-MACHINE PAIR.
=> **Instruction count is PRECISE WITHOUT BEING ACCURATE.**

STABILITY SIDE REPLICATES AND IS CONSERVATIVE: on our idle pinned host, instruction-count RSD
0.000007%/0.000035% vs wall-clock RSD 1.16%/1.67% — a 4.8e4-1.7e5 stability ratio vs COFFE's 1e3.

## (a) GPU KERNELS — NO, structurally blind
A HIP kernel retires ZERO host x86 instructions. Host-side counting sees launch/dispatch only, and
Cirron's exclude_kernel=1 + inherit=0 additionally drops ROCm's kernel-mode work and every helper
thread. Two candidates differing 10x in device time can be within noise in host instruction count.
The GPU analogue (rocprof SQ_INSTS_*) is the right MECHANISM instrument but suffers the SAME inversion
(tiled/LDS-staged kernels issue more instructions and run faster) — corroboration only, never ranking.
Our handoff already encodes this at autokernel-research-loop.md:1631.
**BLOCKER FOUND: rocprof/rocprofv2/rocprofv3 are NOT INSTALLED.** /opt/rocm/bin has rocminfo, rocm-smi,
hipcc but no rocprof; only librocprofiler-register.so (the registration shim) in /opt/rocm/lib.
=> C4's "runnable first task" is NOT currently runnable.

## (b) CPU DECODE — NO, actively misleading
Bandwidth-bound decode stalls on DRAM, retiring few instructions per cycle. Instruction count is BY
CONSTRUCTION insensitive to exactly what we optimize: NUMA placement, interleave=all, mmap placement,
thread/core topology, prefetch, quant repacking for locality. Every recorded win (NPS4 topology,
4x48t->32x6t, AVX512 8x8 repack) moves CPI, not instruction count; several move it the WRONG way.
Settled by the probe — not "test first, maybe".
**SALVAGEABLE**: instruction count as a **CONTAMINATION DETECTOR**, not a ranking signal. Same
binary + same recipe => same retired instructions. A material delta means the two runs did DIFFERENT
WORK (different token counts, a fallback, a different code path) and the wall-clock comparison is VOID.
Cheap integrity gate we do not currently have.

## (c) EVAL LADDER — YES, with caveats
Short-running, single-threaded, cache-resident algorithmic Python IS a near-constant-CPI regime (hence
Pearson 0.96-1.0); we want to score ALGORITHMIC efficiency = exactly the instruction-count-visible part;
it makes the score IMMUNE to the co-residency problem that currently prevents our ladder carrying a
runtime axis at all; ratio-only scoring keeps scores portable across heterogeneous hosts.
CAVEATS TO ENCODE: will not reward wins from memory locality or vectorization; and because inherit=0,
a numpy/torch solution dispatching to multithreaded OpenBLAS is scored on the MAIN THREAD ONLY and
looks ARTIFICIALLY CHEAP — a real hole for any numpy-touching task. Also normalize COFFE's
function-level vs file-level scope asymmetry if levels are mixed.

## CIRRON WORKS HERE — UNRESOLVED -> RESOLVED YES
perf_event_paranoid=1, /usr/bin/perf present, container CapEff=0x0. Agent compiled cirronlib.cpp and
ran its exact perf_event_open path: 3 trials -> 204,524,295 / 204,520,723 / 204,520,245 instructions
(RSD 0.001%). **No sudo, no --privileged.**
MEASUREMENT SEMANTICS (absent from the paper, load-bearing): exclude_kernel=1, exclude_hv=1 =>
USER-SPACE ONLY; perf_event_open(pid=0) => CALLING THREAD ONLY; attr.inherit never set => CHILD
PROCESSES AND OTHER THREADS NOT COUNTED; TOTAL_TIME_RUNNING read and DISCARDED => NO MULTIPLEXING-SCALING
CHECK, counts silently under-report if the PMU multiplexes. Failure mode is a hard raise, not a silent
zero (good). COFFE forks a fresh process per measurement; function-level puts exec() OUTSIDE the
collector but file-level puts the whole exec INSIDE — ASYMMETRIC SCOPE BETWEEN LEVELS.

## THE RESTATEMENT QUESTION — CONFIRMED, AND IT IS EXPLICIT
COFFE Sec 1 Challenge 2 VERBATIM: "**Shypula et al. [75]** find that two single time measurements of
the code solution on the same environment can differ as much as 1.91x." [75] = PIE.
**ONE SOURCE, NOT TWO.** Stage-1's suspicion was right; promote the PROVENANCE FLAG to verified.
WORSE THAN A PLAIN RESTATEMENT — IT IS LOSSY: PIE reports 1.91x as the 95th PERCENTILE over 500 pairs
(mean 1.12, sd 0.36); COFFE reframes it as what two measurements "can differ as much as" — a tail
statistic presented as a BOUND. Anyone citing COFFE inherits the degraded version.
=> ALWAYS cite PIE v4/v5 Sec 2 directly, WITH the tail framing.
Credibility effect: intake-954 already took +0 for corroboration on this basis — correct, no change.
intake-950 keeps its +1 (corroborated by intake-939, genuinely disjoint). BUT the 1.91x FIGURE ITSELF
now has ZERO independent corroboration in the compendium and PIE publishes no way to reproduce it.
**Demote from "a measured noise floor we can cite" to "an unreproducible single-source anecdote that
motivates our own A/A calibration."**

## PIE PROTOCOL RECOVERED FROM THE REPO (Stage 1 marked this NOT-FOUND)
github.com/LearningOpt/pie: gem5/benchmarking.py:407 warmup_runs_per_test_case=5; every call site
passes min_runs=10, max_runs=500, warmup=5, cpu_number; :453,457 build
`taskset --cpu-list N hyperfine --min-runs 10 --max-runs 500 --warmup 5 -N`; dual_submission
(:241-251) benchmarks BOTH pair members in ONE hyperfine invocation on the SAME PINNED CORE; -O3 -std=c++17.
**This STRENGTHENS the finding**: the 1.91x tail survived warm-up, 10-500 reps and single-core pinning
— it is not a naive-harness artifact. Caveat: gem5/README.md:59 self-describes hyperfine support as
"not fully implemented yet", so attribution to this exact harness is strong inference, not proof.
STILL NOT-FOUND: host hardware (the i9-13900k in App A.6 is the SELF-PLAY host, NOT the bench host —
entry must say so or someone will misattribute it) and any runtime-vs-noise relation.
=> **THE 1.91x CANNOT BE SCALED TO ms-SCALE GPU KERNELS. Our threshold must come from our own A/A run.**
gem5 determinism is CONDITIONAL: footnote 2 — "This assumes gem5 terminates. Our experiments use a
two-minute timeout, which may introduce slight variability... altering this timeout could change results."

## PIE v4 -> v5 DRIFT (entry currently mixes v4 numbers with v5 framing)
%OPT 87.68 -> 87.63; test pairs 982 -> 978; v4's TWO human refs (Best Human 4.06x / Same Human 3.64x)
COLLAPSED into one 3.66x; abstract reframed from "surpassing the best human performance (4.06x)" to
"higher than average optimizations from individual programmers (3.66x)" — a WEAKENING of the headline.
Noise numbers identical across both versions.

## OTHER CORRECTIONS
- intake-954 reported_results "5-second per-measurement wall cap" is MIS-SCOPED: the 5s cap is Sec 3.4
  BENCHMARK CONSTRUCTION. The released EVALUATION path uses max(0.1, 10.0 x 5) = **50 s**.
- COFFE Apache-2.0 BYTE-VERIFIED (Coffe/LICENSE:1-3) — was README-read only.
- RSD comparison is genuinely apples-to-apples (agent tried to break this and failed): code matches the
  paper's 12-run/drop-max-min/RSD-over-10 for BOTH metrics; a 100-run untrimmed variant exists but is
  NOT imported by evaluator.py.
- Anti-circularity control CONFIRMED.
- intake-954 recommended-action #4 ("test the constant-CPI assumption before porting") is **DISCHARGED
  BY THIS DIVE WITH A NO** — rewrite as a closed finding, not a pending test.
- intake-954 verdict adopt_component STANDS but **scope it to the generated-code eval ladder ONLY.**

## DISPOSITIONS
intake-950 -> dive-verified with corrections. intake-954 -> dive-verified, scope narrowed.

## LEDGER
1 A/A noise floor per backend, threshold above the TAIL not 1.0 -> RIDER on existing
  autokernel-research-loop.md:1866-1868 (which already says noise floors "must be calibrated, not guessed")
2 record that PIE's 1.91x is NOT a usable prior -> same handoff, Annex K rationale
3 port instruction counting to llama-bench -> **DECLINE**, falsified in-session; record the probe so it
  is not re-proposed
4 instruction count as an A/A CONTAMINATION DETECTOR -> NEW, batched-decode-measurement.md
5 efficient@k over instruction counts for the ladder, ratio-only, WITH the numpy/inherit=0 caveat and
  the function/file scope normalization -> NEW, architect-model-selection-bench.md / eval-tower-verification.md
6 **rocprof NOT INSTALLED — C4's runnable first task is not runnable** -> NEW PREREQUISITE,
  rocm-verify-profile-backend.md C4
7 STGen -> carry forward unchanged (test-generation, out of instrument scope)
8 COFFE-vs-SWE-Perf fuse-vs-separate -> STILL OPEN, flag for the Stage-3 synthesis item
NOTE: probe artifacts are at /mnt/raid0/llm/tmp/dive-c-probe/ — if actionable 1 or 4 cites them they
must move to a durable tracked path (MEASUREMENT.md:146-156 forbids scratch citations).

## DIVE-SURFACED SOURCES
- openreview.net/forum?id=ix7rLVHXyY — PIE's ICLR-2024 reviews; would settle host hardware and whether
  reviewers pressed on 1.91x. **BLOCKED**: 403 challenge-verification on HTML and both API hosts.
- github.com/LearningOpt/pie — the official artifact; source of the recovered protocol. NOT currently
  recorded in the entry.
- github.com/s7nfo/Cirron — the actual instrument; its perf_event_open flags are the load-bearing
  detail entirely absent from the COFFE paper.
- github.com/darchr/gem5-skylake-config — fidelity of the exact "Verbatim" Skylake config.
- github.com/sharkdp/hyperfine — default statistics; would let us judge whether PIE's 1.12x MEAN BIAS
  is a hyperfine-mean artifact.
- Patterson & Hennessy (COFFE ref [68]) — the source of Eq.1; its own memory-hierarchy chapter is the
  cleanest refutation of COFFE's inference, FROM COFFE'S OWN CITATION.
- ROCm rocprofiler-sdk docs / gfx90a SQ_INSTS_* counter set.
