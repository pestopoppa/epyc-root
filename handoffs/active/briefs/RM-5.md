---
schema: epyc.brief.v1
id: RM-5
box_text_sha: t:7d1d392ab304f3a2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/proactive_delegation/bias_probes.py
- epyc-orchestrator:src/proactive_delegation/candidate_sanitizer.py
approach: 'Zero-inference half built (6 injections, orchestrator bdf76ab3). Remaining: the per-reviewer robustness-rate run
  on the held-out probe set (RM-4 protocol, inference-gated): flip rates per injection per reviewer, with swap-augmentation
  for any reference comparison. Prep: the run spec using bias_probes manifest hash. Stop when each leading reviewer has its
  robustness rate with CI.

  '
acceptance: grep -q 'RM-5 robustness rate' handoffs/active/reviewer-control-plane.md
non_goals:
- no reference-comparison mode without swap-augmentation
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/proactive_delegation/bias_probes.py: 21e16ba5979cf9abd34844e2bb469df95e889664
    epyc-orchestrator:src/proactive_delegation/candidate_sanitizer.py: 99dce6a3ed22161bbbf2f3bbaa4345ac1a2f9b40
---
