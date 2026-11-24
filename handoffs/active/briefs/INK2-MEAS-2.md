---
schema: epyc.brief.v1
id: INK2-MEAS-2
box_text_sha: t:cafff99944dfa66e
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-root:handoffs/active/model-evaluation-queue.md
approach: 'Same harness, quarter and prompt panel as INK2-MEAS-1 so its IQ4_NL rows are the control; KLD computed against
  our own Q8_0 logits, with the AtomicChat table used only to pick arms; booking is measured rate plus 25 percent.

  '
acceptance: labelled tok/s and KLD table for the three quants filed here with a keep or drop line per quant
non_goals:
- AD-IQ2_M or 1-bit files
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:handoffs/active/model-evaluation-queue.md: d1f70604c5ffdac5ca92cb459683763c639fb578
---
