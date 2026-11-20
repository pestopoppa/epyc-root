---
schema: epyc.brief.v1
id: UFH14-A3A-F2
box_text_sha: fb4b23fca2d4b025
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/reports/ufh14-a3-f2-finite-20261104/analyze_f2.py
- epyc-root:docs/reports/ufh14-a3-f2-finite-20261104/prospective-finite.patch
approach: 'Question: decode stall warm vs cold with ABA alternation (r11 was n=1 per leg). Model Qwen3.8-27B-Q8_0 + DFlash2
  draft (--spec-draft-n-max 7), production v10 GPU kernel, np4 -c 393216 -ub 2048 q8_0 KV --kv-unified --cache-ram 65536;
  harness entry.py + proxy3.py. Run only after F1 picks a warmup that warms both arms, with q3 and GPU quiet verified during
  legs. Prep: apply the finite-validation patch to analyze_f2.py (rejects NaN timing), establish ownership retirement of the
  keeper-owned unpublished packet, then publish the successor. Stop at all legs complete or futility on infra failure.

  '
acceptance: grep -q 'UFH14-A3A-F2.*COMPLETE' handoffs/active/harness-program.md
non_goals:
- do not modify the keeper-owned packet
- no duplicate publish
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/reports/ufh14-a3-f2-finite-20261104/analyze_f2.py: a70bfe59fa4735f8d5358f922549a444b578b982
    epyc-root:docs/reports/ufh14-a3-f2-finite-20261104/prospective-finite.patch: 7886e8d4aa164a137d3095cab01f332f776737c1
---
