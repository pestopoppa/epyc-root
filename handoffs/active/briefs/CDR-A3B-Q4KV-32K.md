---
schema: epyc.brief.v1
id: CDR-A3B-Q4KV-32K
box_text_sha: t:ffec4423e43914af
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:ggml/src/ggml-cpu/ops.cpp
approach: 'Use llama-bench (or the served recipe through the bench harness) with -ctk/-ctv q8_0 then q4_0 at 32k depth on
  one quarter, three launches each, and capture GGML per-op timings to get the attention share. Compare against the A/A spread
  from the three launches.

  '
acceptance: tok/s per arm with A/A floor and the attention share filed under this box with verdict KEEP (>= 5% tok/s and the
  KVQ-ROT-KLD-1 CPU-arm KLD gate passing) or FUTILITY (attention < 10% of the step)
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:ggml/src/ggml-cpu/ops.cpp: 17ede663b8c2d81516073412c7dc13fa0d0d70ce
---
