---
schema: epyc.brief.v1
id: INTAKE-VALIDATE-86
box_text_sha: t:7d492f20c44aa2e4
author: owner
written: '2026-11-20'
accepted: auto
where:
- epyc-root:.claude/skills/research-intake/scripts/validate_intake.py::_HandoffReferences
- epyc-root:research/intake_index.yaml
- epyc-root:handoffs/active/.folded.json
- epyc-root:.claude/skills/research-intake/scripts/tests/test_folded_resolve.py
approach: 'The 218 errors (was 86) are fold targets that later moved, not bad intake entries. In _HandoffReferences.resolve,
  when a redirected destination file is missing, relocate its basename with self._locate_handoff (frontier-lab-automation.md
  now lives in handoffs/completed/).

  model-architecture-readiness.md was renamed to handoffs/completed/model-architecture-readiness-completed-20261107.md: add
  a basename alias map with that one entry, used by resolve and _locate_handoff.

  When the redirected ''## Track:'' is missing in the destination (dynamic-stack-concurrency, within-role-placement-state-machine
  were split out of numa-placement-and-contention.md on 2026-11-10), fall back to the original source basename via _locate_handoff
  (handoffs/completed/dynamic-stack-concurrency.md exists).

  Add a case for each fallback to test_folded_resolve.py. Do not edit intake_index.yaml entries unless one still fails after
  this; decline those with a note.

  '
acceptance: bash scripts/validate/validate_intake.sh
non_goals:
- do not rewrite the 218 cross-refs in research/intake_index.yaml by hand
- do not change fold-list-1a/1b.json or .folded.json targets
- do not loosen other validator checks
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:.claude/skills/research-intake/scripts/validate_intake.py: 1b41f062e96cd74d14c7f6dc0c1674ec54e5001b
    epyc-root:research/intake_index.yaml: 8a5da1c715192005eeb85b67289eb0b5a40093d1
    epyc-root:handoffs/active/.folded.json: 9c48bc4283b08cb125c887b145c5cd55ff65977a
    epyc-root:.claude/skills/research-intake/scripts/tests/test_folded_resolve.py: 24ed181f793db6b48c0d9b9da5d29f71e60f396f
---
