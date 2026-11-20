---
schema: epyc.brief.v1
id: TOC-CMP-6
box_text_sha: e5054842e3a20ddc
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/graph/context_arm_ab.py
approach: 'First-party A/B: verbatim-append trajectory log with grep/Python read vs current summarize-and-compact on frontdoor
  Qwen3.6-35B-A3B and architect Qwen3.8-Flash-Next. First step: arm implementation in context_arm_ab.py and run manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TOC\-CMP\-6\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/graph/context_arm_ab.py: 5f04f543e3d659b4f40e3683181386af6c9cae88
---
