---
schema: epyc.brief.v1
id: AUTONOMY-DIGEST-REVIEW
box_text_sha: e19c3989d4cfd785
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/delegation_accounting.py
- epyc-root:scripts/hooks/guard_production_kernel.py
- epyc-root:scripts/coordination/codex_budget_meter.py
approach: 'New script scripts/coordination/codex_activity_digest.py: per Codex-session turn, list commits, published rows,
  and touched promotion/production/human-only paths (reuse the path classes in guard_production_kernel.py and the commit hygiene
  hook), emit one markdown digest to the operator flag dir. Read-only over git log and flags; wire to the turn-end hook after
  it works standalone. Covers REPORT.md R7. Box has no done-when; acceptance is the closest check.

  '
acceptance: test -f scripts/coordination/codex_activity_digest.py && python3 scripts/coordination/codex_activity_digest.py
  --since 24h --dry-run
non_goals:
- no new LLM calls
- do not block turns; digest only
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/delegation_accounting.py: 9d3a1ff50bf8e18a1c2ed4bc31a6dcd021d66175
    epyc-root:scripts/hooks/guard_production_kernel.py: 0b2eab75f1d161cfbbc6d0b21da2d1e657b37980
    epyc-root:scripts/coordination/codex_budget_meter.py: 77c2228694486ca4da9e410591154a888a293b14
---
