---
schema: epyc.brief.v1
id: F32-ROUTER-SPLITK-CENSUS
box_text_sha: t:8c6fc24a3990c1ca
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3008.md
- epyc-llama:ggml/src/ggml-cuda/ggml-cuda.cu
approach: 'The existing Q8 atomic-flush determinism task addresses a different type and reduction path. Reuse retained A3B
  router traces at decode and prefill. Baseline is the resolved Tensile solution; keep a later request window. Record M/N/K,
  workgroups, slices and all partial-buffer writes. The upstream half-CU test bounds unsplit tile count, not slices. Stop
  if even eliminating targeted time would miss the owner’s served gate. Test CPU splitting only for underoccupied cores after
  NPS4-local partitioning.

  '
acceptance: Reuse retained A3B router traces at decode and prefill. Baseline is the resolved Tensile solution; keep a later
  request window. Record M/N/K, workgroups, slices and all partial-buffer writes. The upstream half-CU test bounds unsplit
  tile count, not slices. Stop if even eliminating targeted time would miss the owner’s served gate. Test CPU splitting only
  for underoccupied cores after NPS4-local partitioning.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3008.md: 5f576a15d2b59d7ee3f835703c94e2fd06587d06
    epyc-llama:ggml/src/ggml-cuda/ggml-cuda.cu: fe4652125893551b139328a54d4b243ccaba3bf2
---
