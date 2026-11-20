---
schema: epyc.brief.v1
id: EV-4b
box_text_sha: a74a978c8eaf5309
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/eval-tower-program.md
approach: 'Rerun calibration axes on the Option-A scorer on HE-R+ (ECE/AUROC/Top-1/Bottom-1/rho/MAE), chained after EV-11c;
  supersede via ledger append. First step: chained manifest entry.

  '
acceptance: grep -qE '^ *- \[x\] \*\*EV\-4b\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/eval-tower-program.md: bb00cad949830eca2617a6993062fa6973a6a1df
---
