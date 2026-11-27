---
schema: epyc.brief.v1
id: ROUTE-BUDGET-LOOKAHEAD
box_text_sha: t:f141aaab34bee1b0
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3016.md
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3023.md
- epyc-orchestrator:src/typed_decisions/routing_replay.py
approach: 'Per-request limits and offline routing snapshots cannot by themselves compare future contention at equal aggregate
  service cost. Replay ordered arrival sets without future leakage. Compare incumbent, percentile pacing with same demand
  scores, and full lookahead under identical occupancy and budget; use a later trace with bursts. Report per-request route,
  satisfaction definition, time, starvation and budget breaches. Advance only on budget compliance and positive held-out utility
  over pacing after solver cost.

  '
acceptance: Replay ordered arrival sets without future leakage. Compare incumbent, percentile pacing with same demand scores,
  and full lookahead under identical occupancy and budget; use a later trace with bursts. Report per-request route, satisfaction
  definition, time, starvation and budget breaches. Advance only on budget compliance and positive held-out utility over pacing
  after solver cost.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3016.md: d26702b24a4f39b101741ab8c0917af5a1f5b0cc
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3023.md: e85c85bfd34d87047bcad2adf2c2f6a253bd404b
    epyc-orchestrator:src/typed_decisions/routing_replay.py: 3749d4cf11e3ef9aeca463db0e91f464a63da947
---
