---
schema: epyc.brief.v1
id: EV-SKILL-NULL-REPLAY
box_text_sha: t:5c84232031aeeae7
author: intake
written: '2026-11-26'
accepted: auto
where:
- epyc-root:handoffs/active/eval-tower-program.md
- epyc-root:research/deep-dives/intake-nov26-kernels/2611.33943.md
approach: 'Freeze archive hashes, paired seeds, grader revision, effective inventories and folds. Compare the current suite
  gate, no gate and selected gate on the same cells. Refit the policy on each permuted training fold. Score untouched later
  trials and unseen task families separately with paired intervals. Publish cell-level outcomes including missing and timed-out
  arms. Stop if effective-arm identity or split independence cannot be established; a gain inside the null band cannot authorize
  gating.

  '
acceptance: EV-SKILL-NULL-REPLAY.json contains paired_cells, effective_manifest_by_arm, heldout_delta, shuffled_delta, missing_arm_count.
  Each cell has a traceable manifest or explicit exclusion and zero training/holdout overlap.
non_goals: []
tier: local
grounded:
  at: '2026-11-26'
  blobs:
    epyc-root:handoffs/active/eval-tower-program.md: ead5f195ca99b7da4b6d59751f785df4555b262f
    epyc-root:research/deep-dives/intake-nov26-kernels/2611.33943.md: 694931a771abb9e09380c62f330963658d17e054
---
