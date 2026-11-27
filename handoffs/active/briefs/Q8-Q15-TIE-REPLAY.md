---
schema: epyc.brief.v1
id: Q8-Q15-TIE-REPLAY
box_text_sha: t:ea49b6064375b462
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3012.md
- epyc-llama:ggml/src/ggml-cpu/arch/x86/repack.cpp
approach: 'The sampler fixture starts after logit formation; a Q8 activation rounding error can change which logit is largest
  before sampling. Freeze pre-activation rows plus weight bytes and golden logits with deliberate near and wide gaps; compare
  Q8, Q15 and reference on unseen prompts and thread counts. Persist token, gap, logits, packing time, and signed-pair overflow
  cases. Reject a candidate on a new held-out greedy mismatch or if conversion cost erases its measured benefit.

  '
acceptance: Freeze pre-activation rows plus weight bytes and golden logits with deliberate near and wide gaps; compare Q8,
  Q15 and reference on unseen prompts and thread counts. Persist token, gap, logits, packing time, and signed-pair overflow
  cases. Reject a candidate on a new held-out greedy mismatch or if conversion cost erases its measured benefit.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3012.md: f262d352148dbedd8e3f6fe771cf42444c59216c
    epyc-llama:ggml/src/ggml-cpu/arch/x86/repack.cpp: af1cebad131d17118c26634faccb9a6e0c08a6f9
---
