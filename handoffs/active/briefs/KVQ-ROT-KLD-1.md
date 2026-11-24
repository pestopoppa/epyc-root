---
schema: epyc.brief.v1
id: KVQ-ROT-KLD-1
box_text_sha: t:b2a794fe8d0965ef
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:src/llama-kv-cache.cpp
approach: 'Run llama-perplexity --kl-divergence-base on f16 KV once per model, then --kl-divergence for -ctk/-ctv q8_0, q4_0
  and q4_0 with LLAMA_ATTN_ROT_DISABLE=1, on the same 64-chunk corpus. Margin c comes from first-token logits of the same
  runs. The flip arm reuses the G3 (G) GSM8K harness at three launches per arm, scored by math_verify. The A3B CPU arm repeats
  the KLD runs on one quarter.

  '
acceptance: 'per-arm KLD, c and graded-flip excess over the A/A floor filed under this box with verdicts: rot-off >= rot-on
  drops the rotation-off branch; rot-off < 0.9x rot-on is a contradiction that runs the other models; q4_0 rot-on <= 2x q8_0
  KLD makes q4_0 KV a served-gate candidate'
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:src/llama-kv-cache.cpp: c0715cb10a62d81ccd8b53353c071d84e27e3376
---
