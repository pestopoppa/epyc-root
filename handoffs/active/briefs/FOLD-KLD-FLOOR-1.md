---
schema: epyc.brief.v1
id: FOLD-KLD-FLOOR-1
box_text_sha: t:1e139e911d34e2c7
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:tools/perplexity/perplexity.cpp
approach: 'First check whether the C21 fold-gate run kept per-token logits. If so, compute the KLD between two candidate runs
  offline. Otherwise, run llama-perplexity --kl-divergence on the fold-gate corpus twice with only GGML_ROWEXACT_N (CPU) or
  the MMVQ nwarps env (GPU) toggled, then add floor and ratio fields to the fold-gate result template.

  '
acceptance: 'floor per device filed under this box with the run path, the header change committed, and the verdict: floor
  <= 10% of the 0.003 gate keeps the gate with the ratio reported; floor >= 30% makes the gate relative to the floor'
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:tools/perplexity/perplexity.cpp: 92f88306c74101fb4d0b496d368055d489258eb1
---
