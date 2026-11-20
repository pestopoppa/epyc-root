---
schema: epyc.brief.v1
id: TOC-CMP-7
box_text_sha: 5cac8b742f564415
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:src/models/qwen35.cpp
approach: 'RC-CVEC-HOOKS: re-resolve control-vector hook coverage at ffc1bac82 (qwen35/qwen35moe call build_cvec, qwen4exp
  does not) and fail loud on a silent no-op. First step: a grep-based coverage test over the model graph files.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TOC\-CMP\-7\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:src/models/qwen35.cpp: af13da0d82f8179c0005dff2c037a6106741edf4
---
