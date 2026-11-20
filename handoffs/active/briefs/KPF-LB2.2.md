---
schema: epyc.brief.v1
id: KPF-LB2.2
box_text_sha: 580e729204c51877
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/kpf64_replay
approach: 'Recalibrate E/F knobs (--think-scale 0.1 --think-cap-s 60, --max-children 8) at the first live arm and record changes
  in PREDECLARED.md before reading results. First step: live arm manifest in the KPF-64 timing window.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-LB2\.2\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/kpf64_replay: tree:a0b14606d9e85ad361878f1ffb827280488d884e
---
