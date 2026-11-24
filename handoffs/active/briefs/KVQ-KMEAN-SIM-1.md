---
schema: epyc.brief.v1
id: KVQ-KMEAN-SIM-1
box_text_sha: t:e68268c0cc08f97c
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:src/llama-kv-cache.cpp
approach: 'Use a cb_eval hook (or GGML_SCHED dump) to save post-RoPE K and Q per full-attention layer to .npy for 64 prompts.
  Then, offline in numpy, port calib_kv.py''s static mean, quantize to q4_0 (-8..7, 32-value blocks), recompute attention
  and measure KL against the f16 attention output per layer and arm. Plot mean-energy share per layer.

  '
acceptance: 'per-layer mean-energy share and simulated KL per arm filed under this box with verdict: implement static mean
  subtraction if mean energy > 30% or simulated KL drops >= 20%; selective rotation kept only if it cuts KL >= 30%'
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:src/llama-kv-cache.cpp: c0715cb10a62d81ccd8b53353c071d84e27e3376
---
