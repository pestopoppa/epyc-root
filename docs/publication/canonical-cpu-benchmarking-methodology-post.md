<!-- INF-85 W2 long-form post. Sources are cited inline as [src: ...]; strip the [src] tags and this comment at posting. Awaits operator tone/venue read. -->

# How we collapsed our own +17% wins to +1.6%: canonical CPU benchmarking on EPYC

For a while we believed we had a set of CPU inference optimizations that worked. On one afternoon in April 2026 we re-measured them against a stricter baseline, and most of them disappeared. This post is about that afternoon: what we measured, why the numbers moved, and the rules we adopted so it does not happen again. It is a story about measurement discipline. It is not a performance claim about any current build.

Scope, stated up front: one host (a single AMD EPYC 9655, 96 cores, NPS4), one llama.cpp development branch (build 8931), one day (2026-04-26), llama-bench decode throughput on MoE models. Nothing here describes current production. The expert-parallel (EP) flags discussed below no longer exist in our current production kernel, so the collapse cannot be reproduced today [src: `handoffs/active/publication-upstream-program.md`, W2 note of 2026-11-10].

## How we label numbers

Every number in this post uses the claim grammar from our measurement constitution: `metric [protocol, n/reps, date, host-attestation]`. A number missing any field is an observation. It can suggest a hypothesis; it cannot justify keeping, reverting or shipping anything [src: `MEASUREMENT.md`; `agents/shared/MEASUREMENT_POLICY.md`, "The claim rule"].

Three labels appear:

- **CLAIM (retro-certified)**: produced by a recorded command and environment that conform to a named protocol, certified after the fact.
- **OBSERVATION (pre-canonical)**: real data from an instrument that predates the protocol. Hypothesis-forming only.
- **PARAPHRASE**: the raw rows were not retained, so no exact figure is quoted.

One label deserves a plain-language note. The headline claim below says `attestation: pending`. That means the run has raw logs and a recorded command, but no host-health receipt (a machine-state snapshot taken alongside the run), because that receipt was introduced later. We say "pending" rather than imply a check that never happened. The sample is also only n=3, below the protocol's minimum of 10 repetitions for effects of 2% or less [src: `agents/shared/MEASUREMENT_POLICY.md`, "Producing new numbers"]. So we word the headline as "no demonstrable effect", not as an effect size.

## The wins we believed

By late April our CPU optimization work had produced two kinds of apparent win.

The first was an expert-parallel front door for the Qwen3.6-35B-A3B Q8_0 model. Against our standing reference it moved decode from 14.63 to 17.18 t/s, which is +17% [src: `handoffs/completed/cpu-benchmark-rigor-and-revalidation.md` line 138; `progress/2026-04/2026-04-26.md` lines 664 and 923]. `OBSERVATION (pre-canonical)`: this is a summary-level record measured against the reference described next.

The second was a pair of smaller wins that had accumulated on the same reference: an automatic memory-binding change for Q8_0 (+6% claimed) and a three-flag thread-pool stack (+1.8% on Qwen3-Coder-30B-A3B Q4_K_M) [src: `progress/2026-04/2026-04-26.md` lines 925-927]. The stack was already suspect by that morning: re-tested on the same day it came out at 12.39 +/- 1.92 t/s on the Q8_0 model against 14.63 for the plain run (-15%), and its repeated runs on the Coder model carried standard deviations of 13 to 18 t/s on means of 41 to 42 [src: `progress/2026-04/2026-04-26.md` lines 196-206].

Those standard deviations (against 0.01 to 0.10 for the plain runs) were the first hint that something was wrong with the instrument rather than the code. A kernel change does not usually make a benchmark that noisy.

## The reference was not a baseline

The reference was our long-standing "canonical" command: `taskset -c 0-95 -t 96 -fa 1`, with llama.cpp's default file mapping. That produced, for example, 14.63 +/- 0.01 t/s on the Q8_0 model [src: `progress/2026-04/2026-04-26.md` line 170 (Phase B baselines)]. The tiny standard deviation made it look trustworthy. It was reproducible, but reproducibility is not correctness.

With the default mapping, which NUMA node each weight page lands on is decided by whichever thread first touches it. On a many-CCD part, that placement can concentrate or scatter pages in ways that have little to do with the code under test. The reference was a stable measurement of one accidental page layout.

On the evening of 2026-04-26 a user-requested "verify lever compounding" check re-ran the optimizations on five production models against a second configuration: `numactl --interleave=all --physcpubind=0-95 -t 96 -fa 1 -p 0 -n 32 --mmap 0`, with the page cache dropped between runs [src: `progress/2026-04/2026-04-26.md`, "Compounding Verification Matrix"; raw logs in epyc-inference-research commit `42f1789ce`, `data/cpu_optimization/2026-04-26-compounding/`].

## The collapse

Against the interleaved baseline, the same EP change gives:

> Qwen3.6-35B-A3B Q8_0 decode, baseline 20.81 +/- 0.02 t/s, EP arm 21.15 +/- 0.04 t/s, +1.6% [P-BENCH-1 (retro), n=3, 2026-04-26, attestation: pending]
> [src: `progress/2026-04/2026-04-26.md` lines 912 and 923; `handoffs/completed/cpu-benchmark-rigor-and-revalidation.md` line 138]

The `+/-` values are llama-bench's own standard deviation across repetitions. Taken at face value, 0.34 t/s on a base of 20.81 is a small effect, and at n=3 we cannot distinguish it from noise. We recorded it as "DOWNGRADE - noise" and the post's headline is deliberately phrased the same way.

The same re-measurement took apart the other wins [src: `progress/2026-04/2026-04-26.md` lines 921-928]:

| Optimization | Claim against old reference | Against interleaved baseline |
|---|---|---|
| EP front door, Qwen3.6-35B Q8_0 | +17% (14.63 -> 17.18) | +1.6% (20.81 -> 21.15) |
| EP on REAP-246B Q4_K_M | -47% (6.85 -> 3.65) | 0% (5.94 -> 5.92) |
| Auto-mbind, Q8_0 | +6% claimed | 0% (20.85 +/- 0.01 vs 20.81 +/- 0.02) |
| Three-flag stack, Coder-30B Q4_K_M | +1.8% | +0.6% |
| Three-flag stack on top of EP, Q8_0 | n/a | -1.2% vs EP alone (20.89 vs 21.15) |

All of these are `OBSERVATION (pre-canonical)` on the left and retro-certified-where-logged on the right; the table is a comparison across instruments and is analysis, not a claim. The REAP-246B row is worth a second look: the old reference had made EP look catastrophic (-47%) on a very large model, and an entire follow-on research item (a hierarchical all-to-all port) existed to fix that regression. Measured properly, there was no regression to fix, and that item was deprioritized [src: `progress/2026-04/2026-04-26.md`, "Strategic implications" items 3-4].

## The recipe was the win

The most uncomfortable result was where the throughput had actually come from. Moving the Q8_0 model from the old reference to the interleaved configuration, with no code change at all, took it from 14.63 to 20.81 t/s [src: `progress/2026-04/2026-04-26.md` line 912]. That is +44%, more than two and a half times the headline win we had been about to ship, delivered by a command-line change.

`OBSERVATION`: this ratio compares a pre-canonical number with a retro-certified one, so it is an analysis across instruments, not a claim. It is also model-specific. Across five models, the interleaved configuration versus the old reference was [src: `progress/2026-04/2026-04-26.md`, baseline comparison table]:

| Model | Interleaved | Old reference | Difference |
|---|---|---|---|
| Qwen3-Coder-30B-A3B Q4_K_M | 42.27 +/- 0.39 | 43.57 +/- 0.10 | -3% |
| Qwen3.6-35B-A3B Q8_0 | 20.81 +/- 0.02 | 14.63 +/- 0.01 | +44% |
| Qwen3-Next-80B-A3B Q4_K_M | 20.51 +/- 0.02 | 23.25 +/- 0.08 | -12% |
| REAP-246B-A35B Q4_K_M | 5.94 +/- 0.01 (r=5) | 6.85 +/- 0.01 | -13% |
| gemma-4-26B-A4B-it Q4_K_M | 34.69 +/- 0.07 | 25.01 +/- 0.08 | +39% |

(All in t/s, decode.) Two models gained a lot, one was equivalent, and two looked worse. We chased that asymmetry the same night. Two findings came out of it [src: `progress/2026-04/2026-04-26.md`, "Asymmetry Investigation"]:

1. The file-mapping mode was irrelevant. A 2x2 matrix of mapping mode and placement policy showed `--interleave=all` was the dominant lever, with `--mmap 0` and `--mmap 1` within noise of each other once interleaving was on. On the Q8_0 model, the interleaved cells read 20.95 and 20.81 against 7.86 and 7.82 for the `taskset` cells.
2. The two models that "preferred" the old reference were not preferring it in any reachable sense. Five consecutive warm runs on Next-80B stayed flat at about 13.5 t/s (13.52, 13.59, 13.52, 13.42, 13.53), well short of the historical 23.25. That number had needed hours to days of kernel page migration to reach. The interleaved configuration reached 89-100% of the long-warmed figure immediately, so we adopted it as the single reference for all models.

The lesson we took is that a baseline's variance is not its validity. Our old reference had a standard deviation of 0.01 and was wrong; the new one has similar spread and is defensible because it removes the placement lottery rather than hoping to average over it.

## The smaller trap: defaults and environment

The same day's sweep turned up two environment effects that are easy to miss because they are silent [src: `handoffs/completed/cpu-benchmark-rigor-and-revalidation.md`, canonical-numbers section; `agents/shared/MEASUREMENT_POLICY.md`]:

- `OMP_PROC_BIND=spread OMP_PLACES=cores` gave +3-8% across model classes versus defaults, and `OMP_WAIT_POLICY=active` added a further 0.5%. `OMP_WAIT_POLICY=passive` was catastrophic: 8.04 versus 43.82 t/s on the Coder model (a 5.5x regression), because threads sleep on barriers instead of spinning. A benchmark that inherits that variable from a shell profile is measuring the profile.
- llama-bench defaults flash attention off. Our policy requires `-fa 1` explicitly, and the difference is large enough (8-10% per our recipe notes) that omitting it can swamp a small effect.

Both are `OBSERVATION`-grade as quoted here (sweep summaries, not per-rep logs we cite individually). The point is not the magnitudes but that each is a way to produce a "result" with no change to the code under test.

## A separate lesson: the kernel that looked bigger than it was

We want to keep one other lesson distinct, because it has a different cause. A Q8_0 AVX-512BW repack kernel showed a large decode gain at a single thread, tens of percent. At production thread counts the decode converged to the same memory-bandwidth ceiling and the gain shrank to a few percent at most. `PARAPHRASE`: we do not quote exact rows because the per-repetition logs for that test were not retained and the surviving sources disagree [src: `handoffs/active/publication-upstream-program.md`, W2 note of 2026-11-10]. The kernel was real. The deployment story was narrower than the single-thread number suggested, because token generation on these models is bandwidth-bound once all the cores are working. We mention it as the counterpart to the EP story: there the baseline was the artifact, here the operating point was.

## What changed in how we work

Out of this came rules that are now part of our measurement policy. They are short.

**One entry point.** Throughput numbers come only from the codified benchmark wrapper, never from a hand-typed command. The wrapper holds the CPU region for the run, runs a binary-resolution check (a binary that inherits another build's shared libraries runs silently wrong), and refuses to run unlocked [src: `agents/shared/MEASUREMENT_POLICY.md`, "Producing new numbers"].

**A number gates a decision only with a full label.** Metric, protocol, repetitions, date, attestation. Without them it is an observation [src: `MEASUREMENT.md`, claim grammar].

**Repetitions scale with the effect.** At least 5 for effects of 5% or more; at least 10 for effects of 2% or less; report median and spread [src: `agents/shared/MEASUREMENT_POLICY.md`]. By that rule our own +1.6% headline is under-powered, which is why it is a "no demonstrable effect" statement.

**Cache state is declared.** Cold versus warm is part of the label, and the host is checked for health before a run (uptime, governor, NUMA balancing, no concurrent inference) [src: `agents/shared/MEASUREMENT_POLICY.md`].

**Two-baseline reporting.** Any new claim reports its delta against both the interleaved baseline and the production-style reference. A mismatch between the two is the signature of a baseline-artifact win, which is exactly what we had missed [src: `handoffs/completed/cpu-benchmark-rigor-and-revalidation.md`, "Two-baseline reporting requirement"].

**Never edit history; demote it.** When the instrument changed, we did not rewrite the old numbers. We era-labelled them. Records with a recorded command and environment that conform to the new protocol were retro-certified; those that did not were demoted to priors, which can propose a hypothesis but cannot gate a decision, and a decision resting only on demoted numbers triggers a re-measurement [src: `MEASUREMENT.md` sections on retroactivity; `agents/shared/MEASUREMENT_POLICY.md`, "Historical numbers"]. The constitution's own audit of our bench-result directories reached the same verdict on the old protocol: it "empirically collapsed on re-measurement" [src: `MEASUREMENT.md` line 314].

## The public command shape

For readers who want to reproduce the method rather than our numbers, this is the shape of the recipe, with host-specific values replaced by placeholders [src: `docs/publication/canonical-cpu-benchmarking-methodology-final.md`, regenerated from the wrapper's dry-run output on 2026-11-11]:

```text
taskset -c <all-host-cores> numactl --interleave=all <build>/bin/llama-bench \
  -t <all-host-cores> -fa 1 -mmp 0 -m <model.gguf> -p <prompt_tokens> \
  -n <decode_tokens> -r <repetitions> -o md

OMP_PROC_BIND=spread  OMP_PLACES=cores  OMP_WAIT_POLICY=active  OMP_DYNAMIC=false
```

The wrapper also drops the page cache per NUMA node before the run and rejects a result if any single node holds more than 40% of the model's pages.

## What to take from this

If you benchmark LLM inference on a many-core NUMA machine, the first thing to check is not your kernel. It is whether your baseline's memory placement is something you chose or something that happened. Our old reference was reproducible to 0.01 t/s and still manufactured a +17% win, a -47% regression and a research item that had no problem to solve. The fix was a different command line, and it delivered more than the code it replaced.

The caveats we owe you are the ones in the labels. The headline is an n=3 retro-certified comparison with attestation pending; it supports "no demonstrable effect" and nothing stronger. The +17% side is a pre-canonical observation. The kernel story is a paraphrase. And none of it is a statement about current performance. If any of this is wrong, the raw logs are in the repository named above, and we would rather be corrected than be quoted.
