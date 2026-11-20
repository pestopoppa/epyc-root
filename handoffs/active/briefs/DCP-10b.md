---
schema: epyc.brief.v1
id: DCP-10b
box_text_sha: dd6074472045bcfd
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/context_discovery.py
approach: 'Secondary Python ranking cross-check on Loc-Bench V1 after DCP-10: Acc@5/@10 file and Function Acc@10 over discover_candidates
  ordering with evaluate_results(dataset=czlll/Loc-Bench_V1), strip .__init__. First step: scorer script with fixture test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*DCP\-10b\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/context_discovery.py: 923e748929bb163f2c45446b75a24e2528b9c7af
---
