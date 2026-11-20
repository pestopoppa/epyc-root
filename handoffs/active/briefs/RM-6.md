---
schema: epyc.brief.v1
id: RM-6
box_text_sha: t:17ffd2fb5fb0622a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/glm52_reviewer_corpus_direct_runner.py
- epyc-orchestrator:src/proactive_delegation/review_grammar.py
approach: 'Question: evidence-first vs verdict-first field order in the review GBNF on the leading arm (intake-836 vs intake-837
  predict opposite effects). Two grammar variants in review_grammar.py, identical corpus slice, paired FA/FR/AUC and parse
  rate; stop when N>=100 paired or futility. Prep: add the verdict-first grammar variant with a validity test.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_review_grammar_field_order.py
new_tests:
- tests/unit/test_review_grammar_field_order.py
non_goals:
- no promotion
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/glm52_reviewer_corpus_direct_runner.py: d9eaad06fb388110b5ed1b0bd5932fa5c27b8a99
    epyc-orchestrator:src/proactive_delegation/review_grammar.py: a15037b12940d2f40929b7bd9ba99592445b84a0
---
