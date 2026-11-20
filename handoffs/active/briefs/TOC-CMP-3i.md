---
schema: epyc.brief.v1
id: TOC-CMP-3i
box_text_sha: e61dec8522ce6061
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:/mnt/raid0/llm/tmp/compute-flags/dryrun/toc-cmp-3-evalqual-20261118-r3/cmp3-evalqual-r3-native/PARTIAL.json
approach: 'Qualify a sealed evaluator-rubric candidate on paraphrase, operative contradiction, missing requirement and unsupported
  external-state controls. First step: control fixtures and run manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TOC\-CMP\-3i\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:/mnt/raid0/llm/tmp/compute-flags/dryrun/toc-cmp-3-evalqual-20261118-r3/cmp3-evalqual-r3-native/PARTIAL.json: f0be4102ca0d77d7b0b13fbf1bef7bcc21fd198d
---
