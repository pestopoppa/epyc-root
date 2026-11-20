---
schema: epyc.brief.v1
id: LR-8
box_text_sha: eb3e3499f20b368f
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/system/opencode_event_reaper.sh
- epyc-root:scripts/system/codex_retention_reaper.py
- epyc-root:scripts/system/host_hygiene_tick.py
approach: 'Source is complete and accepted (LR-8-SRC, 78c88908). Remaining: the owning session swaps the live opencode_event_reaper.sh
  daemon for its once duty inside the merged tick at a reviewed boundary (preserving the 1800 s cadence, fail-closed VACUUM
  guard, unified alarms), per REFRESH-20261109.md. Do not duplicate codex_retention_reaper (already a daily heavy-phase duty)
  and never enable apply. Scope: opencode event table in idle sessions only. First step: confirm the tick registry entry and
  handover checklist are consistent.

  '
acceptance: python3 -m py_compile scripts/system/host_hygiene_tick.py && grep -q 'opencode_event' scripts/system/host_hygiene_tick.py
non_goals:
- keep current daemon running until handover
- no sessions/messages/parts deletion
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/system/opencode_event_reaper.sh: 75ff72a6400449e47b81bd7ae02f41a2ad60ec6e
    epyc-root:scripts/system/codex_retention_reaper.py: 36836ba97d07dbc9e24280fcc48271df5fa910b9
    epyc-root:scripts/system/host_hygiene_tick.py: f1287ee79e99adc89eaab32910e2edf5a0dea182
---
