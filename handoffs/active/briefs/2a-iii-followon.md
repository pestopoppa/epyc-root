---
schema: epyc.brief.v1
id: 2a-iii-followon
box_text_sha: 850f59e34cf5cc0c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/code_exec_scorer.py
approach: 'Bound process/thread count in code_exec_scorer via cgroup v2 pids.max (counts threads, unlike RLIMIT_NPROC). First
  step: systemd-run/cgroup wrapper behind a flag plus a fork-bomb fixture test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*2a\-iii\-followon\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/code_exec_scorer.py: 443ffbd38ef7be696cba5736dc4d9a4c3fc54bf3
---
