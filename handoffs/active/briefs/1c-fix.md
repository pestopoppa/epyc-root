---
schema: epyc.brief.v1
id: 1c-fix
box_text_sha: 015a4a787e7841a6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:tests/fixtures/answer_scoring_golden_corpus.json
approach: 'Vendor the canonical answer_scoring into the production path per the audit (answer_scoring_vendored.py exists;
  golden corpus tests/fixtures/answer_scoring_golden_corpus.json), gated by the audit''s conditions. First step: diff vendored
  vs canonical and extend the golden-corpus parity test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*1c\-fix\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:tests/fixtures/answer_scoring_golden_corpus.json: d5e4e992e8b0d71fe0ec50dbc84440b5815ace24
---
