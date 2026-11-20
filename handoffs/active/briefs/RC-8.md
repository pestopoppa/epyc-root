---
schema: epyc.brief.v1
id: RC-8
box_text_sha: t:ec53f5fef6a48055
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/autopilot/screening_tier_runner.py
- epyc-inference-research:scripts/benchmark/glm52_reviewer_corpus_direct_runner.py
approach: 'Baseline run: current self-review (architect alias) in shadow on corpus v1 to obtain the first FA/FR numbers. Broken-grader
  guardrail: read transcripts before trusting a surprising number. Prep: runner config for the architect alias in shadow.
  Stop on the full corpus scored; numbers stay observations until RC-6a merges.

  '
acceptance: grep -q 'RC-8 baseline FA' handoffs/active/reviewer-control-plane.md
non_goals:
- no gating on these numbers
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/autopilot/screening_tier_runner.py: b0110ac99b04c08454b4d604e739f1d63f5cd43b
    epyc-inference-research:scripts/benchmark/glm52_reviewer_corpus_direct_runner.py: d9eaad06fb388110b5ed1b0bd5932fa5c27b8a99
---
