---
schema: epyc.brief.v1
id: KV-NONDET-FIRST-DIFF
box_text_sha: t:67e062ab043effc5
author: intake
written: '2026-11-26'
accepted: auto
where:
- epyc-root:handoffs/active/kv-cache-program.md
- epyc-root:research/deep-dives/intake-nov26-kernels/32081.md
approach: 'Freeze model, store digest, prompt bytes, state, seeds and launch choices. Replay OFF/OFF and width-1/verify on
  identical logits inputs where captured. Preserve first mismatched op, tensor bits, route, reduction geometry and missing
  captures. Hold out later long prompts. Stop on a located first mismatch or insufficient captures; measure HIP cost for that
  isolated path only after a matched input reproduces. Reuse the fixed-width SKINNY0 atomic-flush diagnosis recorded under
  GPU-27B-LONGCTX-SECOND-NONDET on November 26.

  '
acceptance: KV-NONDET-FIRST-DIFF.json contains prompt_sha, repeat_pair, width_pair, first_different_op, reduction_route. Each
  replay distinguishes within-width variation from width-dependent differences or records missing inputs.
non_goals: []
tier: local
grounded:
  at: '2026-11-26'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 2711f1bf442a85a9d70e2fe437b06fcd51124bab
    epyc-root:research/deep-dives/intake-nov26-kernels/32081.md: 1c89830a93dbaea3a26b7f30b195c0845374b2f5
---
