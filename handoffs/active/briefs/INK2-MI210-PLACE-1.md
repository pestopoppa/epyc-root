---
schema: epyc.brief.v1
id: INK2-MI210-PLACE-1
box_text_sha: t:8697986a12d03bf9
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:src/llama-model.cpp
- epyc-root:handoffs/active/model-evaluation-queue.md
approach: 'Read tensor sizes from GGUF headers only (no download beyond INK2-MEAS-1''s IQ4_NL); roofline from measured HBM
  and DDR bandwidth; KV from 4 full-attention physical layers plus 1024-window SWA (intake-2866).

  '
acceptance: a table (layer group, bytes, placement, projected tok/s bound, KV GiB) and a one-line recommendation are filed
  under this box
non_goals:
- porting the atomic-engine expert executor
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:src/llama-model.cpp: 5e9ba223f5eacdb111249fc9f753b3592c442d5d
    epyc-root:handoffs/active/model-evaluation-queue.md: d1f70604c5ffdac5ca92cb459683763c639fb578
---
