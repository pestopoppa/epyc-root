# Frontier F6 — Upstream & Publication Leverage

**Status**: IN PROGRESS — W2 methodology-post draft scaffold + claim backfill landed 2026-06-13; W1/W3/W4 still open
**Created**: 2026-06-12
**Priority**: MED — D2 PR is the spearhead and already an ACTIVE queue item
**Spec**: [fable5-findings-07-strategic-frontiers.md](fable5-findings-07-strategic-frontiers.md) §F6 — read before claiming
**Related**: [llama-cpp-dsa-contribution.md](llama-cpp-dsa-contribution.md) (D2 = spearhead); MEASUREMENT.md (claims grammar governs every published number); `agents/research-writer.md`

## Why

Nobody else publishes EPYC CPU-inference engineering at this depth (NUMA laws,
canonical-measurement discipline, compounding-matrix self-correction, MoE-Spec
data, roofline). The open-source-only constraint governs deploys, not publishing.
Returns: upstream maintainers prioritizing PRs we are already waiting on (DSA
#21149, STQ1_0 #22836, MTP upstreaming), free external replication, collaborators.

## Waypoints

- [ ] **W1 — D2 PR spearhead** (1–2 weeks; specced in llama-cpp-dsa-contribution.md): the prompt-processing sparse path the PR author asked for help with — upstream citizenship AND our own unlock (V3.2 + GLM-5.1 on 1.1TB). Do D1 smoke first (1 day, needs standing bench-approval). Acceptance: PR submitted upstream.
- [ ] **W2 — methodology post** (2–3 days, research-writer role): "How we collapsed our own +17% wins to +1.6%: canonical CPU benchmarking on EPYC" — content exists in CPU20 + 2026-04-26 compounding data + MEASUREMENT.md. Venue: blog + llama.cpp discussions cross-post. Acceptance: every number carries the claims grammar. **Draft scaffold + claim backfill landed 2026-06-13**: `docs/publication/canonical-cpu-benchmarking-methodology-draft.md` now separates the April 26 EP-frontdoor `+17% -> +1.6%` collapse from the April 24 CPU2 Q8 microkernel thread-scaling lesson and records evidence readiness per claim. Not publication-ready: public-safe artifact labels, host-attestation IDs, raw-log/reps backfill for CPU2 rows, and final scrub remain.
- [ ] **W3 — public results page** (optional, 1 day): generated from `RESULTS.md` (models × quant × t/s on EPYC, protocol-tagged). Regenerated per release, never hand-edited. Acceptance: generation script, no manual numbers.
- [ ] **W4 — cadence**: one artifact/month max. Candidates queue: NUMA topology laws; gemma4 MTP recipe; closure-inflation/remediation story; instrument-era reconciliation (epistemics piece). Acceptance: queue maintained in this file. **Queue initialized 2026-06-13**; keep unchecked until the first monthly review uses it.

## Gates & pitfalls

- NEVER publish F1 personal-task data — real-task corpus and operator workload stay local.
- Strip personal/infra identifiers from everything published.
- Only publish numbers that carry a protocol tag (MEASUREMENT.md grade) — dogfooding the claims grammar is the credibility.
- One artifact per month cap — publishing is yield-capture, not a second job.
- D1 smoke requires the standing bench-approval; no concurrent inference without per-run approval.

## Reporting

Tick waypoints here, update master index row, log each published artifact in progress. W1 progress reports also go to llama-cpp-dsa-contribution.md.

## Publication Cadence Queue

One artifact per month maximum. Do not publish two items in one month to "catch up"; stale drafts stay in queue.

| Candidate | Format | Gate before drafting | Notes |
|---|---|---|---|
| Canonical CPU benchmarking collapse story | Blog post + llama.cpp discussion | F6-W2 claim backfill/scrub complete | Draft scaffold exists in `docs/publication/canonical-cpu-benchmarking-methodology-draft.md`. |
| NUMA topology laws on EPYC | Technical note | P-BENCH-2 references and public-safe diagrams | Focus on quarter/full instance law, not private deployment details. |
| Gemma4 / MTP recipe | Repro recipe | Local canonical result with protocol tag | Do not publish vendor or upstream claims without local reproduction. |
| Closure-inflation and remediation | Postmortem | Instrument-era references scrubbed | Teach how stale derived views created false confidence; avoid personal task data. |
| Instrument-era reconciliation | Epistemics note | MEASUREMENT.md section 5 stable | Use demote/retro-certify/retire-view vocabulary; no operational secrets. |

## Checkpoints

- 2026-06-13 W2 draft scaffold: added `docs/publication/canonical-cpu-benchmarking-methodology-draft.md`. The draft keeps `+17%` as a historical collapsed observation, distinguishes candidate publishable numbers (`4.32 -> 4.39 t/s`, `+1.6%`; `0.85 -> 1.12 t/s`, `+31.8%`; PPL `6.6985 +/- 0.708`) from claim-ready facts, and points every number at `progress/2026-04/2026-04-24.md` or `MEASUREMENT.md`. Remaining W2: backfill protocol IDs/reps/attestation refs, replace internal paths with public-safe links, and scrub host/personal details before external posting.
- 2026-06-13 W4 queue scaffold: initialized the publication cadence queue in this handoff with one-artifact/month rule, candidate formats, and gates. This is not a published artifact and does not complete W4 until the first monthly review uses the queue.
- 2026-06-13 W2 claim backfill: updated the CPU methodology draft to use the April 26 compounding matrix as the main collapse evidence (`EP frontdoor +17%` from `14.63 -> 17.18 t/s` became `+1.6%` from `20.81 -> 21.15 t/s` against proper canonical) and to treat the April 24 Q8 repack rows (`0.85 -> 1.12`, `4.32 -> 4.39`) as a separate microkernel lesson. Evidence pointers now include `epyc-inference-research/data/cpu_optimization/2026-04-26-compounding/SUMMARY.md`, `2026-04-24-q8-8x8-kernel/thread-scaling-summary.md`, `bench_canonical.sh`, `canonical_recipe.py`, and `MEASUREMENT.md`. Remaining W2: public-safe artifact labels, host-attestation IDs, raw-log/reps confirmation for CPU2 rows, final generated recipe snippet, and external scrub.
