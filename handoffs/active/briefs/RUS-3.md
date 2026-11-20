---
schema: epyc.brief.v1
id: RUS-3
box_text_sha: b7b3c0a75b151ab0
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/analysis/rus2_trace_length_probe.py
- epyc-root:progress/2026-10/2026-10-28-rus3-r3-capture-audit.md
approach: 'Question: within-question trace-length agreement (pooled AUROC with N mixed questions) for reasoning-model roles.
  Previous capture rus3-repeated-samples-r3 was 31/40 truncated; the precondition RUS-3-TRUNC is to raise n_predict so >=4
  untruncated samples per question exist; r4 smoke failed rc1 (result writer, cleanup not certified), so fix the writer/cleanup
  first. Then K>=4 samples at recorded temperature, rerun rus2_trace_length_probe.py within-question arm. Stop when >=8 of
  10 questions have computable agreement or on futility. Decision: keep or drop the RUS-1 length row.

  '
acceptance: grep -q 'within-question pooled AUROC' handoffs/active/harness-program.md
non_goals:
- no promotion claim
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/analysis/rus2_trace_length_probe.py: 467836ccc85fb120176baabb3b6df2ea782ea12e
    epyc-root:progress/2026-10/2026-10-28-rus3-r3-capture-audit.md: 3aa0c4ef9046436057c68d41d0e958eca986ee24
---
