---
schema: epyc.brief.v1
id: UFH14-A7
box_text_sha: 2c69692897464cce
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/harness-program.md
approach: 'Mechanism finding is complete (checkpoints only during prefill; 179/230 F12 follow-ons had zero re-prefill; the
  intake guess is refuted for the common case) but the report dir /mnt/raid0/llm/tmp/p6p7-20261003/ no longer exists, so the
  citation cannot be made as is. Decide: close as code-read finding citing the box''s own Mechanism section with [belief:
  cc], or name the remaining build task, which is the box''s step 1 root-cause run (LLAMA_SERVER_SLOTS_DEBUG=1 on next :8083
  relaunch, classify mismatches as template re-render vs other). Recommended: close with the finding and file the debug-relaunch
  as its own row.

  '
acceptance: 'grep -q ''UFH14-A7.*belief: cc'' handoffs/active/harness-program.md'
non_goals:
- no kernel change
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/harness-program.md: aa7dc419bf8eb745819bc97721912f46fb95d42d
---
