---
schema: epyc.brief.v1
id: INK2-INKBLOT-PAIR
box_text_sha: t:7a23e3e0cb6b054a
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-orchestrator:scripts/autopilot/paired_stats.py@59a1d4695
- epyc-root:handoffs/active/model-evaluation-queue.md@23e9ec151
approach: 'Follow the approved CPU evaluation protocol in research/deep-dives/intake-inkblot-20261127/stage3-plan.md. Seal
  24 math, 20 coding and 20 worker/tool IDs during the disjoint 12-case smoke test. Retain every attempt and stop cause, count
  invalids in the denominator and verify identical ID sets before paired statistics. Interleave arms on one quarter, compare
  both decode depths and apply the fixed 64-item decision rule.

  '
acceptance: A result exists for every expected ID and arm, including failures, with source and build digests, per-item outputs,
  matched profile, paired counts and the predeclared decision.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-orchestrator:scripts/autopilot/paired_stats.py@59a1d4695: c02b057204641dd6e2fc2defe21a1f7587aaead1
    epyc-root:handoffs/active/model-evaluation-queue.md@23e9ec151: 3230bfdbda2f2007ba1863de231905c8d47039fd
---
