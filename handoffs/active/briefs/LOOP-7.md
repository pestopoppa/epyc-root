---
schema: epyc.brief.v1
id: LOOP-7
box_text_sha: fe7295d11c4fb932
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:artifacts/ni08
- epyc-root:docs/guides/agent-workflows/compute-fillers.md
approach: 'Disk table /mnt/raid0/llm/tmp/rtg22-loop7-20261109.md: of the remaining UNCLEAR KEEP dirs 23 are owner-known (4.97
  GiB) and 23 unclaimed (0.02 GiB). Step: message the named owners (bus) for the 23 owner-known dirs and reclaim the unclaimed
  ones through the guarded reclaim path after the 7-day rule; record confirmations. No raw rm. First step: generate the owner-ask
  list from the table.

  '
acceptance: grep -q 'LOOP-7.*reclaimed' handoffs/active/engineering-hygiene-backlog.md
non_goals:
- no deletion without owner confirmation or the 7-day rule
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:artifacts/ni08: tree:3a1e30d967fbb357361ab49a5f02c34220eabd9d
    epyc-root:docs/guides/agent-workflows/compute-fillers.md: 925fbe42f5feffad1c1920f7563b631e4cf4b881
---
