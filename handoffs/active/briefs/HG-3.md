---
schema: epyc.brief.v1
id: HG-3
box_text_sha: t:4fd054b532a4ef6b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:coordination/session-bus/human_only_paths.yaml
- epyc-root:coordination/session-bus/BUS_PROTOCOL.md
approach: 'The box premise is wrong (see scoping audit): no SafetyGate action list exists; deploy and DB migrations have no
  enumeration. Do option (b): narrow HG-3 to the three actions that already have enforcement (baseline change, MEASUREMENT-adjacent
  edits, protected-branch merges via human_only_paths.yaml) and state deploy/DB-migration are out of scope; extending human_only_paths.yaml
  is a trust-boundary token request, not an agent edit. Write the narrowed list as a doc with each action pointing at its
  enforcing line.

  '
acceptance: test -f docs/reference/reviewer-protected-actions.md
non_goals:
- no edit of human_only_paths.yaml
- no unenforced action list
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:coordination/session-bus/human_only_paths.yaml: 3c57cae46d483708a4309450b1629be7f620d266
    epyc-root:coordination/session-bus/BUS_PROTOCOL.md: 010480b7014c0c17cbb2ab43d4e836bc6cc9ac0c
---
