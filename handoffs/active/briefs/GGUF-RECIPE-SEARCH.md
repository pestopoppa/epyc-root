---
schema: epyc.brief.v1
id: GGUF-RECIPE-SEARCH
box_text_sha: fddf160837fd051c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/perplexity/perplexity.cpp
- epyc-inference-research:scripts/benchmark/bench_canonical.sh
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Bytes-budgeted greedy/ASHA search over per-tensor type maps using GGUF-RECIPE-SCORER; RESULT.json with candidates,
  winner, incumbent, bootstrap CI and tok/s.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*GGUF-RECIPE-SEARCH\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/perplexity/perplexity.cpp: 92f88306c74101fb4d0b496d368055d489258eb1
    epyc-inference-research:scripts/benchmark/bench_canonical.sh: d1c5a7becae27de77f61785af7e9420809a6ede4
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
