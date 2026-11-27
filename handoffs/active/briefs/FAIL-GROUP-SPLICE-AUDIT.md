---
schema: epyc.brief.v1
id: FAIL-GROUP-SPLICE-AUDIT
box_text_sha: t:b2ac00739402888f
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3014.md
- epyc-orchestrator:src/graph/trajectory_artifact.py
approach: 'A terminal MemRL failure score does not encode the first repairable action, options or a validated continuation.
  Freeze same-policy group membership, exact task environment, tools, rollouts and rewards; hold out tasks. Record all failures
  including infra faults, repairability, local success and continuation success separately. Advance a training proposal only
  if at least one held-out repair verifies end to end and usable counts support the planned comparison; never relabel terminal
  failures from local success alone.

  '
acceptance: Freeze same-policy group membership, exact task environment, tools, rollouts and rewards; hold out tasks. Record
  all failures including infra faults, repairability, local success and continuation success separately. Advance a training
  proposal only if at least one held-out repair verifies end to end and usable counts support the planned comparison; never
  relabel terminal failures from local success alone.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3014.md: 33fff3dd6b8ee3175689be391fcab5934c1a3914
    epyc-orchestrator:src/graph/trajectory_artifact.py: de8908e18c827a95958dc9cab7103a7c9b9bf481
---
