---
schema: epyc.brief.v1
id: TB-SEM-1
box_text_sha: edc1c11a8bfe4064
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:/mnt/raid0/llm/tmp/delegation-context-preassembly/thinking-probe-headroom/native/RESULT.json
approach: 'Finite native thinking-budget semantics probe on Qwen3.6-35B-A3B-MTP Q8_0 under v10, interpret before deciding
  the historical Step 3 fix. First step: probe launcher manifest; stop on filed interpretation.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TB\-SEM\-1\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:/mnt/raid0/llm/tmp/delegation-context-preassembly/thinking-probe-headroom/native/RESULT.json: bc30f437ca34300128141e4b426ba68fe85e686b
---
