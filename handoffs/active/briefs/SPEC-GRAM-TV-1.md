---
schema: epyc.brief.v1
id: SPEC-GRAM-TV-1
box_text_sha: t:8dee3f839ec5a22e
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:common/sampling.cpp
approach: 'Enumerate each enum schema''s accepted token sequences with llguidance into a prefix trie. For every trie node,
  issue one /completion prefix forward with n_probs on a CPU-quarter llama-server, then compute masked and conditional probabilities
  bottom-up (the conditional renormalises by future-valid mass). Report TV per class at T 1.0 and the served temperature.
  Skip classes whose trie exceeds 10k strings.

  '
acceptance: 'per-class TV at the served temperature filed under this box with the trie sizes, and the verdict: close (every
  class TV < 0.1) or open a cost/benefit box on Phi correction (any class >= 0.1)'
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:common/sampling.cpp: 21642fb71cebfa0057cd19ae7fa5c50877f04a92
---
