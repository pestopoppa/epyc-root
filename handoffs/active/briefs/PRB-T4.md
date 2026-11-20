---
schema: epyc.brief.v1
id: PRB-T4
box_text_sha: 2e788e147359e19a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:/mnt/raid0/llm/tmp/delegation-context-preassembly/tale-pilot/packet/spec.json
approach: 'Run the PRB-T2 TALE-EP evaluation in an exclusive inference window. First step: launcher manifest; stop on filed
  result.

  '
acceptance: grep -qE '^ *- \[x\] \*\*PRB\-T4\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:/mnt/raid0/llm/tmp/delegation-context-preassembly/tale-pilot/packet/spec.json: 5eb0e93d27a03f44d8f917bf2cc7e32a94901a1f
---
