---
schema: epyc.brief.v1
id: GC-1a
box_text_sha: t:d492081c6994e7b4
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/glm52_reviewer_corpus_direct_runner.py
- epyc-inference-research:scripts/benchmark/glm52_reviewer_capability_direct_runner.py
- epyc-inference-research:data/glm52_reviewer_corpus_direct
approach: 'Question: does DeepSeek-V4.1-Flash emit valid typed (strict-IF / ReviewDecision grammar) review output at claim
  grade? Rerun the typed-emission smoke (GC-1/GC-1r equivalent) on the V4.1 chat template, then the approved claim-grade reviewer
  corpus under the K-of-M protocol, grammar/schema kept in the serving path. Retargeted GLM-5.3 -> V4.1-Flash; blocked on
  the port/load/sparse-attention gates of deepseek-v41-flash-evaluation.md. Prep now: adapt the runner''s model/slot config
  to V4.1 and dry-run against the corpus. Stop on K-of-M complete or futility on load failure. Numbers stay observations until
  RC-6a merges.

  '
acceptance: grep -q 'GC-1a verdict' handoffs/active/reviewer-control-plane.md
non_goals:
- no claim-grade gating before RC-6a
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/glm52_reviewer_corpus_direct_runner.py: d9eaad06fb388110b5ed1b0bd5932fa5c27b8a99
    epyc-inference-research:scripts/benchmark/glm52_reviewer_capability_direct_runner.py: 1d964619f44eaf738879b090f83c9fb9fdce767f
    epyc-inference-research:data/glm52_reviewer_corpus_direct: tree:9b95de202139b067eabf45d6f0d195e12a08ed36
---
