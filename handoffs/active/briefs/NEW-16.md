---
schema: epyc.brief.v1
id: NEW-16
box_text_sha: 05d966f46b2a9557
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:src/llama-kv-cache.cpp
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Prototype faithful ChunkKV on a fresh llama.cpp-experimental tree after the stated gate; first step is a design
  check of chunk selection API vs existing KV code.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*NEW-16\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:src/llama-kv-cache.cpp: c0715cb10a62d81ccd8b53353c071d84e27e3376
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
