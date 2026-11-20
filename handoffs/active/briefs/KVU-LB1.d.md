---
schema: epyc.brief.v1
id: KVU-LB1.d
box_text_sha: a3c6844f6b196fb7
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:/mnt/raid0/llm/tmp/codex-rtg57-t96-repair-20261028/run-20261028T201026Z-1835607/result.json
approach: 'Adopt always-F32 VKQ on the CPU FA path (GGML_FA_VKQ_F32=1 or compiled default in next champion): decide carrier
  then roll through. First step: recipe env per CPU role with measurement.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-LB1\.d\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:/mnt/raid0/llm/tmp/codex-rtg57-t96-repair-20261028/run-20261028T201026Z-1835607/result.json: af99aada9c356ec89fcbfc9e94c99ef50342ff9a
---
