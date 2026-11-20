---
schema: epyc.brief.v1
id: HIL-17
box_text_sha: 878a07a266071c22
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/trace/attribution/ladder.py
- epyc-orchestrator:src/trace/attribution/aggregate.py
- epyc-orchestrator:scripts/trace/attribution_ladder.py
- epyc-orchestrator:tests/unit/test_attribution_ladder.py
approach: 'Code is built and unit-tested (40560f2f). Remaining measured step, gated on the HIL-13 unclassified-share report:
  run Detect and Attribute on 20 failed AutoPilot traces with a local judge, compare rule-pack hits to the L2 scan, and report
  accuracy and tokens per rung against the HIL-12 human consensus ranking; k=5 at temperature 0.7 across two local families
  with random baseline and single temperature-0 comparator. Stop when 20 traces are attributed or on futility. First step:
  check the HIL-13 report exists and carries the unclassified share.

  '
acceptance: grep -q 'HIL-17 attribution-ladder result' handoffs/active/harness-program.md
non_goals:
- no Node helper
- no new judge model install
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/trace/attribution/ladder.py: d923bbd7916cf8278e43b4775f614f32e82cd115
    epyc-orchestrator:src/trace/attribution/aggregate.py: e39a9c11935ac5f66fac93620f1ae2c4d6750b42
    epyc-orchestrator:scripts/trace/attribution_ladder.py: e2fafebbff17e261f3b344e35d05114ef3c4273b
    epyc-orchestrator:tests/unit/test_attribution_ladder.py: b992a7b88fec7746f185ace046aecd00be45b315
---
