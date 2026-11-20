---
schema: epyc.brief.v1
id: LOOP-38
box_text_sha: bd65921157794d94
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/codex_pane_liveness.py
- epyc-root:scripts/coordination/session_bus.py
approach: 'codex_pane_liveness.py is on main with mocked tests. Remaining: run against live tmux read-only to prove state
  detection (working / compacting / idle; pane text can never clear a main per SESSION_LIFECYCLE), add the tmux send-keys
  nudge as a tool with an explicit allowlist of panes, replace the channel files, dedup nudges. First step: a read-only live-tmux
  detection run recorded as a fixture.

  '
acceptance: python3 -m pytest -q scripts/coordination/tests/test_codex_pane_liveness.py
non_goals:
- no send-keys to sessions without the allowlist
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/codex_pane_liveness.py: 13e7d05efa86e8e491d677874f9cd8ab33582a30
    epyc-root:scripts/coordination/session_bus.py: 3b817976378d091df9a6814d41883de83b0a7457
---
