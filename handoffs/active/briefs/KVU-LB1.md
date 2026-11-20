---
schema: epyc.brief.v1
id: KVU-LB1
box_text_sha: 50bbd205e977a096
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'CPU FP16 V-accumulator: attach our reduced repro, accumulator-peak probe data and hybrid-fix results to the existing
  upstream issue/PR (posting is the operator''s call). First step: assemble the attachment bundle.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-LB1\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
