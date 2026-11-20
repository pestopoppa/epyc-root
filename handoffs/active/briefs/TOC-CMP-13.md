---
schema: epyc.brief.v1
id: TOC-CMP-13
box_text_sha: 9981b97ba0d43fcf
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/api/routes/chat_delegation.py
approach: 'Add the ColBERT KB as an optional prior-decisions source in delegation-context pre-assembly behind dcp_pre_assembly;
  measure quality/latency before default-on. First step: source adapter behind the flag with a test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TOC\-CMP\-13\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/api/routes/chat_delegation.py: b3777c27e973cac82e4735e550fd8f029947a50f
---
