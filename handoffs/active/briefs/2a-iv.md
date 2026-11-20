---
schema: epyc.brief.v1
id: 2a-iv
box_text_sha: 83871edc143de2d3
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/code_exec_scorer.py
approach: 'Wrap code_exec_scorer.py in bubblewrap (--unshare-net, read-only root, tmpfs workdir). First step: bwrap argv builder
  behind a flag with a test asserting net is unreachable inside.

  '
acceptance: grep -qE '^ *- \[x\] \*\*2a\-iv\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/code_exec_scorer.py: 443ffbd38ef7be696cba5736dc4d9a4c3fc54bf3
---
