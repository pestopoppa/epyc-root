---
schema: epyc.brief.v1
id: M15-DPE-HOLD
box_text_sha: 72701c49d4176f5f
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/harness-program.md
- epyc-root:research/intake_index.yaml
approach: 'Record-only: DP-E is decided HOLD (OP-AMENDCAND 2026-11-11, nothing drafted, human-only). Write one line under
  M15 stating HOLD with the monitor trigger preserved (draft a package only if CME-6 reports a headroom or replication problem
  or a no-regression claim needs a margin). Do not edit any measurement-trust-boundary file.

  '
acceptance: grep -q 'DP-E.*HOLD' handoffs/active/harness-program.md
non_goals:
- no measurement amendment drafting
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/harness-program.md: cadd2da6b668a35f911a3b0ad52a85e94ee62ea0
    epyc-root:research/intake_index.yaml: 8a5da1c715192005eeb85b67289eb0b5a40093d1
---
