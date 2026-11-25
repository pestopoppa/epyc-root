---
schema: epyc.brief.v1
id: AK-MMQ-SK2-CENSUS
box_text_sha: t:d41930c7a810e728
author: intake
written: '2026-11-25'
accepted: auto
where:
- epyc-root:handoffs/active/autokernel-loop.md
- epyc-root:research/deep-dives/intake-kspec-1125/dive-K1-streamk-order.md
approach: 'Read-only. Reuse the dive''s dense-27B arithmetic as is. For the other two families read the C21 tree (/mnt/raid0/llm/llama-worktrees/c21-20261124
  @ 98ff8a4): mmq.cu routing (MMVQ cap, rocBLAS cutover), mmq.cuh stream-k launcher (104 blocks, tile counts) and the CDNA
  mmq config tables, and count tiles from the tensor shapes named in AK-MMQ-SK2 step 2. File one table under the box; tick
  nothing (the owner ticks AK-MMQ-SK2).

  '
acceptance: a census table covering the dense 27B, A3B MUL_MAT_ID and Q4_K/Q6_K shape families, with the C21 code lines it
  rests on, is filed under AK-MMQ-SK2 in handoffs/active/autokernel-loop.md
non_goals:
- No GPU run and no new port; the row verdict is already CLOSE.
tier: local
grounded:
  at: '2026-11-25'
  blobs:
    epyc-root:handoffs/active/autokernel-loop.md: 02486d41f49f48b1aa32b24d0da10be3f50388a7
    epyc-root:research/deep-dives/intake-kspec-1125/dive-K1-streamk-order.md: a4e1dbc51c48d2032079b25f2a256f8fb94f857a
---
