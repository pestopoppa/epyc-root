# Frontier F6 — Upstream & Publication Leverage

**Status**: SPEC'D, not started (created from the Fable 5 strategic-frontiers review)
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
- [ ] **W2 — methodology post** (2–3 days, research-writer role): "How we collapsed our own +17% wins to +1.6%: canonical CPU benchmarking on EPYC" — content exists in CPU20 + 2026-04-26 compounding data + MEASUREMENT.md. Venue: blog + llama.cpp discussions cross-post. Acceptance: every number carries the claims grammar.
- [ ] **W3 — public results page** (optional, 1 day): generated from `RESULTS.md` (models × quant × t/s on EPYC, protocol-tagged). Regenerated per release, never hand-edited. Acceptance: generation script, no manual numbers.
- [ ] **W4 — cadence**: one artifact/month max. Candidates queue: NUMA topology laws; gemma4 MTP recipe; closure-inflation/remediation story; instrument-era reconciliation (epistemics piece). Acceptance: queue maintained in this file.

## Gates & pitfalls

- NEVER publish F1 personal-task data — real-task corpus and operator workload stay local.
- Strip personal/infra identifiers from everything published.
- Only publish numbers that carry a protocol tag (MEASUREMENT.md grade) — dogfooding the claims grammar is the credibility.
- One artifact per month cap — publishing is yield-capture, not a second job.
- D1 smoke requires the standing bench-approval; no concurrent inference without per-run approval.

## Reporting

Tick waypoints here, update master index row, log each published artifact in progress. W1 progress reports also go to llama-cpp-dsa-contribution.md.
