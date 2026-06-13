# How We Collapsed Our Own CPU Wins: Canonical Benchmarking On EPYC

Status: internal draft scaffold, not publication-ready.

This draft is the source-backed skeleton for F6-W2. It intentionally separates
historical observations from publishable claims. Before posting externally,
convert each publishable number into the MEASUREMENT.md grammar:

`metric [protocol-id, n/reps, date, host-attestation ref]`

## Working Thesis

CPU inference optimization on a large EPYC host is easy to overclaim because
the host state, thread placement, memory placement, and benchmark entry point
can move more than the code. Our strongest methodology story is not that every
optimization worked; it is that the canonical protocol forced several apparent
wins to collapse, and that made the remaining wins more credible.

## Narrative Outline

1. **The attractive result.** Late-April CPU optimization notes contained two
   easy-to-overread wins: a staged NPS4/CCD stack that appeared to move a
   single-instance configuration into the 46.6-47.2 t/s range (`+17%`), and an
   EP-frontdoor result on Qwen3.6 Q8 that appeared to move `14.63 -> 17.18 t/s`
   (`+17%`) against the warmed mmap reference.
2. **The measurement trap.** The same project later encoded stricter rules:
   codified benchmark recipes, explicit `-fa 1`, OMP stack control, host-health
   preconditions, no concurrent inference, and live affinity verification.
3. **The collapse.** Under the later canonical framing, the clean EP-frontdoor
   comparison is `20.81 -> 21.15 t/s`, or `+1.6%`, not the earlier `+17%`.
   The artifact summary explicitly labels it a downgrade/noise result.
4. **The useful remnant.** The kernel-level intuition was not fake, but it was
   narrower than the deployment story. The separate Q8 repack/AVX-512BW table
   shows a clear 1-thread edge (`0.85 -> 1.12 t/s`, `+31.8%`) while production
   thread counts converge near the same ceiling (`4.32 -> 4.39 t/s`, `+1.6%`).
5. **The rule we now follow.** A number can only gate a decision when it carries
   protocol, reps, date, and attestation. Everything else is an observation or
   a prior.
6. **What others can copy.** Publish the recipe, the host-state checks, the
   failed hypotheses, and the reason the old number was demoted.

## Claim Ledger

| Draft claim | Source | Publication status |
|---|---|---|
| `+17%` historical stage result after NPS4 + Phase 1.0-1.3 v1 | `progress/2026-04/2026-04-24.md`, "Final session single-instance throughput" | Historical observation only; use as the collapsed claim, not as a current performance claim. |
| EP frontdoor `+17%` (`14.63 -> 17.18 t/s`) collapses to `+1.6%` (`20.81 -> 21.15 t/s`) against the proper canonical baseline | `progress/2026-04/2026-04-26.md`, "Optimization deltas re-measured against proper canonical"; `epyc-inference-research/data/cpu_optimization/2026-04-26-compounding/SUMMARY.md` | Best main publishable example after scrub. Evidence bundle records date, command shape, branch, host state, `drop_caches`, and `r=3`/`r=5` policy; still needs public-safe artifact label and host-attestation id. |
| Proper canonical itself moved Qwen3.6 Q8 from warmed mmap reference `14.63 +/- 0.01` to cold canonical `20.81 +/- 0.02` | `epyc-inference-research/data/cpu_optimization/2026-04-26-compounding/SUMMARY.md`, "Baseline comparison" | Candidate methodology claim: the recipe, not the code, captured the largest gain. Publish only with the recipe caveat and without implying universal model behavior. |
| 96-thread Q8 repack row `4.32 -> 4.39 t/s`, `+1.6%` | `progress/2026-04/2026-04-24.md`, "Final thread scaling"; `epyc-inference-research/data/cpu_optimization/2026-04-24-q8-8x8-kernel/thread-scaling-summary.md` | Supplemental microkernel lesson, not the main `+17%` collapse. Artifact has date/host/build/flags; needs exact log/reps and attestation before publishing as a number. |
| 1-thread Q8 repack row `0.85 -> 1.12 t/s`, `+31.8%` | `progress/2026-04/2026-04-24.md`, "Final thread scaling"; `epyc-inference-research/data/cpu_optimization/2026-04-24-q8-8x8-kernel/thread-scaling-summary.md` | Candidate supporting claim after protocol/rep/attestation backfill; explain why it does not imply multi-thread deployment gain. |
| PPL preserved: Wikitext-2 3 chunks, ctx=512, `6.6985 +/- 0.708` | `progress/2026-04/2026-04-24.md`, same section; `2026-04-24-q8-8x8-kernel/thread-scaling-summary.md` correctness section | Candidate correctness guard; needs exact command/log bundle and public-safe wording before publication. |
| Claim grammar rule: claim = metric + protocol-id + n/reps + date + host-attestation ref | `MEASUREMENT.md` section 2 | Publishable project policy. |
| Retroactivity rule: pre-canonical CPU bench claims demote-to-prior at E0->E1 | `MEASUREMENT.md` section 5 | Publishable methodology policy, but keep internal artifact counts private unless scrubbed. |

## Backfilled Evidence State

| Evidence item | Current state | Remaining work |
|---|---|---|
| April 26 compounding matrix | Strongest source for the main collapse story. Summary captures command shape, branch, host state, `drop_caches`, and rep policy. | Assign a public artifact label, attach/derive host-attestation id, and decide whether the post cites `r=3` plus `r=5` reruns or only the stable rerun rows. |
| April 24 Q8 8x8 thread scaling | Useful as a second lesson: local kernel win survives at 1 thread, disappears at production thread counts. | Locate exact raw logs behind the table before publishing precise rows; otherwise paraphrase as "large single-thread gain, noise-level production-thread gain." |
| `bench_canonical.sh` / `canonical_recipe.py` | Current recipe source of truth: taskset + NUMA interleave, `-t 96`, `-fa 1`, `-mmp 0`, canonical OMP env, libomp linkage checks, host validation. | Quote the recipe behavior, not local paths. If commands are included, generate them from the wrapper in `--dry-run` during the publication-prep pass. |
| MEASUREMENT.md policy | Already expresses the claim grammar and the E0->E1 demotion precedent. | Keep policy excerpts short; link to public-safe policy text if this repo is published, otherwise summarize. |

## Source Checklist Before Publication

- Replace internal paths with scrubbed artifact labels or public repo links.
- Backfill protocol IDs for every retained number; otherwise remove the number.
- Add the exact benchmark recipe from `bench_canonical.sh` / `canonical_recipe.py`
  rather than hand-written commands. Use the wrapper's `--dry-run` output during
  the final prep pass.
- Do not mix the April 26 EP-frontdoor collapse with the April 24 CPU2
  microkernel table; they are separate lessons.
- Strip personal-task, dashboard, and host-identifier details.
- Keep the tone focused on measurement discipline, not benchmark drama.
