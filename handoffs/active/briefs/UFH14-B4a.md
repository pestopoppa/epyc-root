---
schema: epyc.brief.v1
id: UFH14-B4a
box_text_sha: e8280fe1f9469dd2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/design/ufh14-b4-prefix-cache-policy-20261003.md
- epyc-orchestrator:scripts/analysis/prefix_cache_report.py
approach: 'Operator pre-approved signing once the baseline exists. Step 1: after >=1 window of >=200 post-deploy calls, run
  prefix_cache_report.py to get the missed_prefill_share baseline per port. Step 2: prepare one stack-change package (skill
  stack-change) per design 3.8/4.4: master prefix_cache per model, topology prefix_cache_selection, compiler + launcher +
  drift checker; derived launch flags equal today''s. Raise :8083 --cache-ram 65536 to 102400 only if the 4.3 rule fires (>5%
  across two windows with evictions logged). Window not yet met.

  '
acceptance: grep -q 'PFX-SEL-1 baseline' handoffs/active/harness-program.md
non_goals:
- no launch flag change
- no apply without operator signature
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/design/ufh14-b4-prefix-cache-policy-20261003.md: ff90378ca69a29bef7be4957afa2290a89141d2e
    epyc-orchestrator:scripts/analysis/prefix_cache_report.py: dbf69f359009287e90c0db9e6645185adee48d99
---
