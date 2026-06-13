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

1. **The attractive result.** A late-April CPU optimization session recorded a
   headline path where a staged NPS4/CCD optimization stack appeared to move a
   single-instance configuration from roughly the old baseline into the
   46.6-47.2 t/s range, described there as a `+17%` stage result.
2. **The measurement trap.** The same project later encoded stricter rules:
   codified benchmark recipes, explicit `-fa 1`, OMP stack control, host-health
   preconditions, no concurrent inference, and live affinity verification.
3. **The collapse.** Under the later canonical framing, the Q8 repack/AVX-512BW
   end-to-end advantage at bandwidth saturation is represented by the
   96-thread table row `4.32 -> 4.39 t/s`, or `+1.6%`, not by the earlier
   story-level `+17%`.
4. **The useful remnant.** The kernel-level intuition was not fake. The same
   table shows a clear 1-thread edge (`0.85 -> 1.12 t/s`, `+31.8%`), while
   multi-thread decode converges near the memory-bandwidth ceiling.
5. **The rule we now follow.** A number can only gate a decision when it carries
   protocol, reps, date, and attestation. Everything else is an observation or
   a prior.
6. **What others can copy.** Publish the recipe, the host-state checks, the
   failed hypotheses, and the reason the old number was demoted.

## Claim Ledger

| Draft claim | Source | Publication status |
|---|---|---|
| `+17%` historical stage result after NPS4 + Phase 1.0-1.3 v1 | `progress/2026-04/2026-04-24.md`, "Final session single-instance throughput" | Historical observation only; use as the collapsed claim, not as a current performance claim. |
| 96-thread Q8 repack row `4.32 -> 4.39 t/s`, `+1.6%` | `progress/2026-04/2026-04-24.md`, "Final thread scaling" | Candidate publishable number after protocol/rep/attestation backfill. |
| 1-thread Q8 repack row `0.85 -> 1.12 t/s`, `+31.8%` | `progress/2026-04/2026-04-24.md`, "Final thread scaling" | Candidate publishable number after protocol/rep/attestation backfill; explain why it does not imply multi-thread gain. |
| PPL preserved: Wikitext-2 3 chunks, ctx=512, `6.6985 +/- 0.708` | `progress/2026-04/2026-04-24.md`, same section | Candidate correctness guard; needs protocol/attestation backfill before publication. |
| Claim grammar rule: claim = metric + protocol-id + n/reps + date + host-attestation ref | `MEASUREMENT.md` section 2 | Publishable project policy. |
| Retroactivity rule: pre-canonical CPU bench claims demote-to-prior at E0->E1 | `MEASUREMENT.md` section 5 | Publishable methodology policy, but keep internal artifact counts private unless scrubbed. |

## Source Checklist Before Publication

- Replace internal paths with scrubbed artifact labels or public repo links.
- Backfill protocol IDs for every retained number; otherwise remove the number.
- Add the exact benchmark recipe from `bench_canonical.sh` / `canonical_recipe.py`
  rather than hand-written commands.
- Strip personal-task, dashboard, and host-identifier details.
- Keep the tone focused on measurement discipline, not benchmark drama.
