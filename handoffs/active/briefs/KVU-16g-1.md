---
schema: epyc.brief.v1
id: KVU-16g-1
box_text_sha: 7fdeb72663a675ce
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:/mnt/raid0/llm/tmp/cal-1026/kvu16g1-fa4-audit/OWNER-READOUT.md
approach: 'Run the row-5c prefill-budget A/B (gpu_slot.sh) and score against the box done-when. First step: launch manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-16g\-1\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:/mnt/raid0/llm/tmp/cal-1026/kvu16g1-fa4-audit/OWNER-READOUT.md: 55dc2bdae311b8d0c53ad7fd1de44fd05247de69
---
