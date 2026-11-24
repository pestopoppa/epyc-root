---
schema: epyc.brief.v1
id: FOLD-GATE-SPEC-CORRECTNESS-V2
box_text_sha: t:8d0679046121a0c5
author: planning
written: '2026-11-24'
accepted: owner
where:
- scripts/champion/fold_gates/mk_fold_rows.py
- /mnt/raid0/llm/tmp/c21-fold-gpu-20261124-r3/job.py
approach: 'lift fork_table/correctness/probe_session/run_correctness from r3 job.py into the template; keep r3''s rule text
  verbatim as the pre-registered clause

  '
acceptance: template diff + passing selftest
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:scripts/champion/fold_gates/mk_fold_rows.py: 5a007310e5a884695c637859ca00c48696447de3
    epyc-root:/mnt/raid0/llm/tmp/c21-fold-gpu-20261124-r3/job.py: 4b36224499dddd046f36aa9a1b554474b3386d1a
---
