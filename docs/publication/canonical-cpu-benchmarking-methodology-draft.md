# How We Collapsed Our Own CPU Wins: Canonical Benchmarking On EPYC

Status: draft. Every number below carries its claim label; numbers that cannot
carry a complete label are stated as observations or paraphrased.

## Claim grammar used in this post

A claim is `metric [protocol-id, n/reps, date, host-attestation ref]`. A number
missing any of those fields is an *observation*: it can motivate a hypothesis
but cannot justify a decision. Labels used below:

- `CLAIM (retro-certified)`: produced by a recorded command and environment
  that conform to the named protocol, certified after the fact. Attestation
  reference is stated as `pending` where no attestation artifact exists yet.
- `OBSERVATION (pre-canonical era)`: real data from an instrument that predates
  the canonical protocol. Hypothesis-forming only.
- `PARAPHRASE`: no exact number is quoted because the raw rows are not retained.

Nothing in this post is a statement about current performance. All throughput
figures are from a single host (one EPYC 9655, NPS4, 96 cores, governor
`performance`, NUMA balancing off, THP always) in late April 2026, on a
llama.cpp development branch (build 8931), and are quoted to show how a
comparison changes when the baseline is fixed.

## Working Thesis

CPU inference optimization on a large EPYC host is easy to overclaim because
host state, thread placement, memory placement and the benchmark entry point
can move the result more than the code does. Our story is not that every
optimization worked; it is that a canonical protocol forced several apparent
wins to collapse, and that made the remaining wins more credible.

## Narrative Outline

1. **The attractive results.** Two easy-to-overread wins, both from late April
   2026:
   - A staged NPS4 plus CCD-pool configuration moved single-instance decode
     from about 40 t/s to about 47 t/s, roughly `+17%`
     (`OBSERVATION (pre-canonical era)`; the gain bundled a thread-count change,
     and no raw log is retained, so it is not quoted more precisely).
   - An expert-parallel (EP) front-door change on Qwen3.6-35B-A3B Q8_0 appeared
     to move decode from `14.63` to `17.18 t/s`, `+17%`
     (`OBSERVATION (pre-canonical era)`; summary-level record only, measured
     against a warmed-mmap reference).
2. **The measurement trap.** The reference was a warmed `mmap` run with default
   first-touch page placement. Later rules encoded stricter recipes: a codified
   benchmark entry point (never hand-typed commands), explicit `-fa 1`
   (llama-bench defaults it to 0 and the difference is 8-10%), OpenMP stack
   control, host-health preconditions, no concurrent inference, and live
   affinity verification.
3. **The collapse.** Against a properly distributed baseline (cold cache,
   `--mmap 0`, `numactl --interleave=all`), the same EP change is
   `20.81 -> 21.15 t/s`, `+1.6%`, which we treat as not distinguishable from
   noise.
   - `CLAIM (retro-certified)`: Qwen3.6-35B-A3B Q8_0 decode, canonical baseline
     `20.81 +/- 0.02 t/s` and EP arm `21.15 +/- 0.04 t/s`
     [P-BENCH-1 (retro), n=3, 2026-04-26, attestation: pending]. Per-run
     `+/-` is the benchmark tool's own standard deviation across repetitions.
   - Caveat on the label: n=3 is below the protocol's reps rule for effects of
     2% or less, so `+1.6%` is reported as "no demonstrable effect", never as an
     effect size.
4. **The recipe was the win.** Against the same warmed reference, the canonical
   recipe alone moved this model from `14.63` to `20.81 t/s` (`+44%`) with no
   code change. `OBSERVATION`: this ratio mixes a pre-canonical number
   (`14.63`) with a retro-certified one, so it is analysis across
   instruments, not a claim. It is model- and placement-specific: for two other
   models in the same matrix the canonical recipe was roughly equal or worse
   than the warmed reference, so it must not be generalized.
5. **The useful remnant.** A separate Q8_0 AVX-512BW 8x8 repack kernel
   (`PARAPHRASE`) showed a large single-thread decode gain, tens of percent,
   while at production thread counts decode converged to the same
   memory-bandwidth ceiling, with a gain of a few percent at most. Exact rows
   are not quoted because the raw per-rep logs were not retained. The kernel
   intuition was real but narrower than the deployment story.
6. **The rule we now follow.** A number gates a decision only when it carries
   protocol, reps, date and attestation. Everything else is an observation or
   a prior. When an instrument changes, older benchmark numbers are demoted to
   priors rather than edited, and a decision resting only on demoted numbers
   triggers a re-measurement.
7. **What others can copy.** The recipe, the host-state checks, the failed
   hypotheses, and the reason the old number was demoted.

## Claim Ledger

| Label | Statement | Status |
|---|---|---|
| `METH-C1` | EP front-door `+17%` (`14.63 -> 17.18 t/s`, pre-canonical) vs `20.81 -> 21.15 t/s`, `+1.6%`, canonical. | Collapsed side is `CLAIM (retro-certified)` [P-BENCH-1 (retro), n=3, 2026-04-26, attestation: pending]; the `+17%` side is `OBSERVATION (pre-canonical era)`. |
| `METH-C2` | The canonical recipe, not the EP code path, explains the large Q8_0 delta versus the warmed reference. | `OBSERVATION` (cross-instrument ratio); model- and placement-specific. |
| `METH-S1` | A large single-thread kernel win does not translate to production thread counts on a bandwidth-bound decode. | `PARAPHRASE`; no exact numbers quoted. |
| `METH-P1` | Claim grammar: a decision-gating number includes metric, protocol id, reps, date and attestation. | Policy statement; no benchmark attestation applies. |
| `METH-P2` | Retroactivity: when the benchmark protocol changed, earlier CPU benchmark claims were demoted to priors, not edited or deleted. | Policy statement. |

## The Canonical Recipe (public command shape)

```text
taskset -c <all-host-cores> numactl --interleave=all llama-bench \
  -t <all-host-cores> -fa 1 -mmp 0 -m <model.gguf> -p <prompt_tokens> \
  -n <decode_tokens> -r <repetitions> -o md
```

Environment shape:

```text
OMP_PROC_BIND=spread
OMP_PLACES=cores
OMP_WAIT_POLICY=active
OMP_DYNAMIC=false
LD_LIBRARY_PATH=<clang-libomp-first>
```

Preconditions: no other inference running; governor and NUMA-balancing state
checked per session; page cache dropped and re-warmed with NUMA interleave;
the benchmark binary verified to resolve the intended OpenMP and ggml
libraries (a binary that inherits another build's libraries runs silently
wrong); at least 5 repetitions for effects of 5% or more and at least 10 for
effects of 2% or less, reporting median and spread; cold versus warm declared.

## Before Publication

- Obtain a host-attestation reference for the April 26 runs, or leave the
  label as `attestation: pending` and say so in the post.
- Regenerate the command shape from the current benchmark wrapper's dry-run
  output immediately before posting.
- Keep the April 26 EP collapse and the April 24 kernel lesson as separate
  lessons; do not merge their numbers.
- Tone: measurement discipline, not benchmark drama.
