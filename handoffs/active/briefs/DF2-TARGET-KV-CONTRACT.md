---
schema: epyc.brief.v1
id: DF2-TARGET-KV-CONTRACT
box_text_sha: t:88b623d0334de3af
author: intake
written: '2026-11-26'
accepted: auto
where:
- epyc-root:handoffs/active/speculative-decoding.md
- epyc-root:research/deep-dives/intake-nov26-kernels/2611.34776.md
approach: 'Record exact weight/config revisions, source layer pairs, strides, dtype, ownership and one-step index timestamp.
  Walk representative released mappings against DS41 and the dense 27B control. Require a defined KV read and epoch across
  accept, reject and slot reuse before any execution probe. Mark unsupported layers and absent weights explicitly.

  '
acceptance: DF2-TARGET-KV-CONTRACT.json contains layer_map, kv_stride, selection_epoch, rollback_owner, missing_artifacts.
  Each requested architecture has an ABI verdict for accept, reject and slot reuse.
non_goals: []
tier: local
grounded:
  at: '2026-11-26'
  blobs:
    epyc-root:handoffs/active/speculative-decoding.md: 2d51d43d13d3a0ebe6ac12aa35a1b60fee69f344
    epyc-root:research/deep-dives/intake-nov26-kernels/2611.34776.md: 3022bf3818f5cc8c5f2c7bfaf00c8be0e3bf7b54
---
