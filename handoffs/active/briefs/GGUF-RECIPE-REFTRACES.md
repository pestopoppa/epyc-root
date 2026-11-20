---
schema: epyc.brief.v1
id: GGUF-RECIPE-REFTRACES
box_text_sha: efc7f1c9ee96c186
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/perplexity/perplexity.cpp
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Generate and freeze held-out reference traces from the served model (search and final splits; agent, wiki, code)
  and save full-vocab KLD base files.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*GGUF-RECIPE-REFTRACES\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/perplexity/perplexity.cpp: 92f88306c74101fb4d0b496d368055d489258eb1
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
