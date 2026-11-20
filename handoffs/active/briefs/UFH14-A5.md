---
schema: epyc.brief.v1
id: UFH14-A5
box_text_sha: 179c376572cc8268
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/adapters/README.md
- epyc-root:handoffs/active/harness-program.md
approach: 'Phase A verdict write-up: for each demonstrated fix (D1-D5) state its measured effect on P(keep), wall time and
  prefill seconds on the 27B from the C95 results, and extend the existing VB-DS41-C95 row in scripts/vidya/adapters/README.md
  rather than adding a ladder. First step: tabulate fixes vs the three metrics from /mnt/raid0/llm/tmp/ds41-c95/results; report
  unmeasured cells as unknown.

  '
acceptance: grep -q 'UFH14-A5 verdict' handoffs/active/harness-program.md
non_goals:
- no new belief ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/adapters/README.md: e3c2ef4730581badb912189e13072542bc78a2cf
    epyc-root:handoffs/active/harness-program.md: aa7dc419bf8eb745819bc97721912f46fb95d42d
---
