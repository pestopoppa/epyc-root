---
schema: epyc.brief.v1
id: SPEC-FILTER-TIES
box_text_sha: t:c97d9804fe6243d3
author: intake
written: '2026-11-26'
accepted: auto
where:
- epyc-root:handoffs/active/speculative-decoding.md
- epyc-root:research/deep-dives/intake-nov26-kernels/9619.md
approach: 'Hash rows, seeds and sampler chain; test top-k, top-p, min-p, both orders, no-op, infinities and exact ties. Compare
  native support to a whole-tie reference with identical inputs, then repeat on held-out row permutations. Emit every support
  and denominator; reject ambiguous probability labels. File a compatibility result. Serving policy requires a separate gate.

  '
acceptance: SPEC-FILTER-TIES.json contains fixture_sha, row, key, filter_order, support, token, full_logprob, retained_logprob.
  All frozen and held-out cases match their declared reference semantics or record the first discrepancy.
non_goals: []
tier: local
grounded:
  at: '2026-11-26'
  blobs:
    epyc-root:handoffs/active/speculative-decoding.md: 2d51d43d13d3a0ebe6ac12aa35a1b60fee69f344
    epyc-root:research/deep-dives/intake-nov26-kernels/9619.md: d3308d264b1b3bbda9e3e366efefd54130f60402
---
