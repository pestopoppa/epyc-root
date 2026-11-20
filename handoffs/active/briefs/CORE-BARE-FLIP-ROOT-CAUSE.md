---
schema: epyc.brief.v1
id: CORE-BARE-FLIP-ROOT-CAUSE
box_text_sha: 394da159fbb4c01a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/watch_git_config.py
- epyc-root:scripts/coordination/tests/test_watch_git_config.py
approach: 'A flip-capture watcher is armed (watch_git_config.py). Done when a captured flip names its writer; then fix that
  writer. Step: on the next captured flip read the watcher''s record (process, argv, parent) and identify the writer; until
  a flip occurs report armed-and-waiting. Do not wait on the host: check the watcher log now and confirm it is live (kill
  -0 is not proof, use ps).

  '
acceptance: grep -q 'CORE-BARE-FLIP.*writer' handoffs/active/engineering-hygiene-backlog.md
non_goals:
- no git config rewrite in the shared clones
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/watch_git_config.py: adcb4df265c830afe1ce112a5ff7331557d21aef
    epyc-root:scripts/coordination/tests/test_watch_git_config.py: 34d843453499c9f17b6d39350b9351a0b25adc8f
---
