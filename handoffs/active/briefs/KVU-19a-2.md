---
schema: epyc.brief.v1
id: KVU-19a-2
box_text_sha: 67e0133c198c2753
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/kvu19a2_capture_runner.py
approach: 'Report or investigate latent D=512/576 tile-kernel nondeterminism upstream (draft only, never post). First step:
  assemble repro evidence from kvu19a2 scripts into a draft.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-19a\-2\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/kvu19a2_capture_runner.py: a05f147f3bcd106762b03021ce1671ec9cf1fe4a
---
