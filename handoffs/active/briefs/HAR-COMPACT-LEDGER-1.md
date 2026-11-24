---
schema: epyc.brief.v1
id: HAR-COMPACT-LEDGER-1
box_text_sha: t:5a3e635b7de7793a
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-orchestrator:src/graph/compaction.py
approach: 'In compaction.py, behind a settings flag, collect failed tool calls (non-zero exit or error result) into a verbatim
  ledger block kept across compactions. Extract pinned tokens (paths, IDs, numbers) from the pre-compaction context with regexes
  and assert they appear byte-exact after compaction. Add a pytest replay over 3-5 retained trajectories.

  '
acceptance: flagged change committed with its SHA and a replay test over retained trajectories showing every failed action
  and pinned pointer survives compaction byte-exact, recorded under this box
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-orchestrator:src/graph/compaction.py: 92a7e5f4cee1cf66739a1419a13ff5f839198d39
---
