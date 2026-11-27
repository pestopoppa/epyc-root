---
schema: epyc.brief.v1
id: MEM-HARNESS-CANDIDATE-REPLAY
box_text_sha: t:4ed27070abcd8b6e
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3015.md
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3022.md
- epyc-inference-research:scripts/benchmark/beam_memory_retrievers.py
approach: 'M-12 receipt admission binds existing runs; candidate selection also needs versioned memory and isolation between
  search and final cases. Pin M-12 judge, prompts, receipts, dataset and explicit independent BEAM partition. Hold out conversations
  from search, filter post-hoc intersections visibly and score all scheduled cases. Compare incumbent, smoke-gated and fully
  evaluated candidate on quality, total construction cost, query tokens, and unchanged-memory reuse. Reject leaked cases or
  unverified archive hashes. Preserve ratified abstention handling.

  '
acceptance: Pin M-12 judge, prompts, receipts, dataset and explicit independent BEAM partition. Hold out conversations from
  search, filter post-hoc intersections visibly and score all scheduled cases. Compare incumbent, smoke-gated and fully evaluated
  candidate on quality, total construction cost, query tokens, and unchanged-memory reuse. Reject leaked cases or unverified
  archive hashes. Preserve ratified abstention handling.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3015.md: 15b28bb611f0cd5b7f6dff7ad77900e7b3ad1d4e
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3022.md: 2eedf88600a49b953caebd4b8a8b6846f7793e2f
    epyc-inference-research:scripts/benchmark/beam_memory_retrievers.py: 991788d57426f79dcb03fb4b302dee2eba28cf63
---
