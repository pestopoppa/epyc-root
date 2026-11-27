---
schema: epyc.brief.v1
id: DRAFTER-CCD-RESIDENCY
box_text_sha: t:3855fd87b9db7558
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3012.md
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/stage3-plan.md
approach: 'The completed NTA-only seed failed its speed gate; it did not partition a reusable working set by CCD capacity.
  Size working sets per CCD after KV and scratch. Baselines include current champion, NTA-only and unmodified OS page policy.
  Record realized page size and NUMA placement plus per-thread work; separate prefill, single-stream and drafts at a later
  prompt/width. Stop if LLC misses or matched-throughput intervals fail to improve, or if a negative control regresses.

  '
acceptance: Size working sets per CCD after KV and scratch. Baselines include current champion, NTA-only and unmodified OS
  page policy. Record realized page size and NUMA placement plus per-thread work; separate prefill, single-stream and drafts
  at a later prompt/width. Stop if LLC misses or matched-throughput intervals fail to improve, or if a negative control regresses.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3012.md: f262d352148dbedd8e3f6fe771cf42444c59216c
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/stage3-plan.md: ce6451d3eb9ba282c4a51041a256de72d13860db
---
