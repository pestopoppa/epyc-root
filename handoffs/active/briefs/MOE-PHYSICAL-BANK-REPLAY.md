---
schema: epyc.brief.v1
id: MOE-PHYSICAL-BANK-REPLAY
box_text_sha: t:d64ad4aeaac06d5c
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3011.md
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/stage3-plan.md
approach: 'The current static-pool replay already prices cold routes; logical layer IDs can misrepresent cache pressure and
  miss overlap. Bind each expert tensor to a physical bank, backend and epoch. Reserve model, KV and scratch before pricing
  the pool; hold back later routes. Output every hit/miss, unique bytes, PCIe overlap, CPU affinity, and uncovered bank. Stop
  if experts fit, identities are all distinct for dedup, or cold-route/transfer costs erase the margin; report these cases
  separately.

  '
acceptance: Bind each expert tensor to a physical bank, backend and epoch. Reserve model, KV and scratch before pricing the
  pool; hold back later routes. Output every hit/miss, unique bytes, PCIe overlap, CPU affinity, and uncovered bank. Stop
  if experts fit, identities are all distinct for dedup, or cold-route/transfer costs erase the margin; report these cases
  separately.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3011.md: d6b6839f9af41a4e8055d0092e96c676746294db
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/stage3-plan.md: ce6451d3eb9ba282c4a51041a256de72d13860db
---
