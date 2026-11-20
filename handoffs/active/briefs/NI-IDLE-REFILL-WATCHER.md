---
schema: epyc.brief.v1
id: NI-IDLE-REFILL-WATCHER
box_text_sha: 29c2f38c5efdc0d8
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/rowflow/rowflow.py
- epyc-root:scripts/coordination/session_bus.py
- epyc-root:scripts/coordination/rowflow/notify.py
approach: 'Gap: no zero-token owner nudge exists when a bin stays idle with READY rows past a grace period (the keeper''s
  120 s allocate tick already arms rows and logs IDLE-WHY). Add to the keeper tick: on IDLE-WHY persisting past a grace (reuse
  the IDLE-HELD threshold), send one bus message plus a flag file to the Pipeline owner, deduplicated per bin per grace window.
  No LLM tokens. rowflow.py is FROZEN at 9218dffd1, so the hook goes in via notify.py/hostutil or in rowflow2, not by editing
  the frozen file.

  '
acceptance: python3 -m pytest -q scripts/coordination/tests/test_idle_refill_nudge.py
new_tests:
- scripts/coordination/tests/test_idle_refill_nudge.py
non_goals:
- do not edit frozen rowflow.py
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/rowflow/rowflow.py: 5e76c90af8cfa49c863684663c3ca56084adfa8d
    epyc-root:scripts/coordination/session_bus.py: 3b817976378d091df9a6814d41883de83b0a7457
    epyc-root:scripts/coordination/rowflow/notify.py: e9b81a436e587b0755d6e0d5bc0dbe1882639db2
---
