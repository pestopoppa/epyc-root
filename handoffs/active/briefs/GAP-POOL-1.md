---
schema: epyc.brief.v1
id: GAP-POOL-1
box_text_sha: 18aad9a659d15a00
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:.claude/skills/inference-backlog-scheduling/scripts/gap_pool
- epyc-root:docs/guides/agent-workflows/compute-fillers.md
approach: 'R6 combined engine is merged default-off (bc8d98cb2) and proven; open: publish/fold the 28 R6 source changes, integrate
  the filler_run10 affinity pin into the full candidate and rerun the whole candidate''s controls, then cut over the live
  writer; done-when is a standing pool of 6-10 armed short rows (CPU and GPU; GPU rows need operator approval of the GPU class,
  which blocks only the GPU part). First step: rerun the R6 candidate controls with the affinity pin integrated.

  '
acceptance: python3 .claude/skills/inference-backlog-scheduling/scripts/queue_status.py | grep -c ARMED
non_goals:
- no live cutover before the controls pass
- GPU pool rows wait for operator class approval
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:.claude/skills/inference-backlog-scheduling/scripts/gap_pool: tree:e721b35bf4812cd6b25172aa0b6956d3a67f0d47
    epyc-root:docs/guides/agent-workflows/compute-fillers.md: 925fbe42f5feffad1c1920f7563b631e4cf4b881
---
