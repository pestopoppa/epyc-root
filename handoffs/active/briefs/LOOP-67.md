---
schema: epyc.brief.v1
id: LOOP-67
box_text_sha: 8a021f326c3ad9c9
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave1.json
- epyc-orchestrator:scripts/autopilot/autopilot.py
- epyc-orchestrator:src/autopilot_core/infra_fingerprint.py
approach: 'Adversarial review then merge of refactor/autopilot-gate (P2). B2-03 changes what is admitted to learning, so review
  as a DECISION-SEMANTICS change (replay old gate decisions through old and new code, require identical admit sets or an explicit
  era note). Reviewed variant refactor/autopilot-gate-reviewed-01a16fc3 (25 ahead). Step: write the old-vs-new decision replay,
  then merge via serialized_push.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && git merge-base --is-ancestor refactor/autopilot-gate-reviewed-01a16fc3
  origin/main
non_goals:
- do not touch evaluator files (that is P5/LOOP-78)
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave1.json: bb376c30536182d94ec0a5257025cef934db2098
    epyc-orchestrator:scripts/autopilot/autopilot.py: da41d9e6aba6c969b6eafb2730b1ae7f76e960c3
    epyc-orchestrator:src/autopilot_core/infra_fingerprint.py: 5673025fff54213490cc6eee12a91ab1645074e3
---
