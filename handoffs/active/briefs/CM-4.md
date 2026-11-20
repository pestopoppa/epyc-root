---
schema: epyc.brief.v1
id: CM-4
box_text_sha: 2726718a2a8413b6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/repl_environment/codemode_tools.py
- epyc-orchestrator:scripts/benchmark/codemode_ab/CM_FOLLOWUP.md
- epyc-orchestrator:tests/unit/test_codemode_cm45.py
approach: 'Code landed behind ORCHESTRATOR_REPL_CLASSIFY (classify, route_classify, risk_bands, q_scores). Remaining: the
  schema-work rule evaluation of Jev techniques and the REPL-retrieval alternative (write it as a short note), then the live
  N=20/100/500 label-by-script vs in-prompt comparison (accuracy, prompt tokens, wall time) via the prepared cm probe rows
  after S4. First concrete step is the Jev/retrieval evaluation note.

  '
acceptance: test -f docs/design/cm4-classify-jev-evaluation.md
non_goals:
- no enabling before S4 or operator exception
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/repl_environment/codemode_tools.py: cfaae2f92b9ccbc95cefa49fdcb66c24017955aa
    epyc-orchestrator:scripts/benchmark/codemode_ab/CM_FOLLOWUP.md: 9289d4d1ca9be6dc08f149171c9e4a40bc561a65
    epyc-orchestrator:tests/unit/test_codemode_cm45.py: 12412b307efe50f6be4a79ef18c1a02cd9975107
---
