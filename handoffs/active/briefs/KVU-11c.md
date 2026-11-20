---
schema: epyc.brief.v1
id: KVU-11c
box_text_sha: 3c54927ccc08f4f2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Replace the TTS nprocs LD_PRELOAD shim with a real thread flag in the speech kernel tree. First step: flag patch
  on experimental tree with build and a thread-count check.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-11c\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
