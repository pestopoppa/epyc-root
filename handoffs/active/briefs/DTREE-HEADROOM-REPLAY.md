---
schema: epyc.brief.v1
id: DTREE-HEADROOM-REPLAY
box_text_sha: t:a0effb0390d40e40
author: intake
written: '2026-11-25'
accepted: auto
where:
- epyc-root:handoffs/active/speculative-decoding.md
- epyc-inference-research:scripts/kernel_rnd/dice_replay/dice_replay_27b.py
approach: 'Reuse dice_replay_27b.py (and draft_sharpen_replay.py for the fit/holdout harness) and its V0/V1 verifiers unchanged;
  add two arms: a ceiling arm computing the branching-random-walk bound from each round''s captured target top-k distribution,
  and a Pando tree builder over the captured draft lattice. Seal the predeclaration (thresholds above) before replay, as SPEC-DRAFT-SHARPEN
  did. CPU only, no GPU and no server.

  '
acceptance: 'a RESULT.json filed under this box gives the ceiling and the Pando-tree and current-builder holdout ratios to
  V0 per T and N with CIs, and the verdict: CLOSE_TREE_SHAPE (ceiling over V0 < 1.10 at N=16 at both T, or Pando-tree ratio
  CI-upper < 1.02 at both T), FILE_GPU_ROW (Pando-tree ratio >= 1.03 with CI-lower > 1.0 at some T), or INCONCLUSIVE'
non_goals:
- No noise coupling (lossless only with a target-sample walk, not our rejection verifier); no GPU row in this box.
tier: local
grounded:
  at: '2026-11-25'
  blobs:
    epyc-root:handoffs/active/speculative-decoding.md: 417dbb8d05a3c5588e8ba55b2bcae9136041f40d
    epyc-inference-research:scripts/kernel_rnd/dice_replay/dice_replay_27b.py: 5fc59fc8da980a021c0dc9b6c507beb495cc975d
---
