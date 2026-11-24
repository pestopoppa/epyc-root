---
schema: epyc.brief.v1
id: INK2-PORT-2d
box_text_sha: t:654056592019e9ae
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:common/speculative.cpp
- epyc-llama:src/llama-model.cpp
approach: 'Port the #32218 Inkling2 DSpark graph (host-sampled noncausal 8-token block with anchor) onto the experimental
  branch; load the published AtomicChat Q8_0 drafter GGUF; extend the DS41 draft-dspark type instead of adding a new one;
  use non-repetitive prompts and compare logits at the first divergence (intake-2863, intake-2866).

  '
acceptance: on the experimental branch the published drafter GGUF loads with --spec-type draft-dspark; on 3 fixed non-repetitive
  greedy prompts the drafter-on output matches drafter-off or its first divergence is a logit near-tie (top-2 gap logged);
  acceptance and decode tok/s vs drafter-off are filed here
non_goals:
- porting the atomic-engine expert executor
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:common/speculative.cpp: 2b365cf37a40c789c52fc38a2ec2420ce5b4a858
    epyc-llama:src/llama-model.cpp: 5e9ba223f5eacdb111249fc9f753b3592c442d5d
---
