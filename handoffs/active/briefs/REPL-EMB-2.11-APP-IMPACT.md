---
schema: epyc.brief.v1
id: REPL-EMB-2.11-APP-IMPACT
box_text_sha: b2eb8661ed8737f6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/reports/repl-shadow-gnx-v2-20261104/gs-app-impact-v2/results.jsonl
- epyc-orchestrator:orchestration/repl_memory
approach: 'Source impact analysis, no model run. v2 found TaskEmbedder._generate_embedding CRITICAL (37 upstream) and StrategyStore.retrieve
  HIGH, so no hook is authorized; remaining work is complete the nine-target receipts (strategy-store assessed under the resource
  guard, exact UID matching) and write the stop/warn conclusion. gitnexus is stale so impact reads weak; use grep callers
  as the structural fallback. Stop on answer when all targets have receipts.

  '
acceptance: grep -q 'StrategyStore.retrieve' docs/reports/repl-shadow-gnx-v2-20261104/gs-app-impact-v2/results.jsonl
non_goals:
- no code edits
- no query-capture hook
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/reports/repl-shadow-gnx-v2-20261104/gs-app-impact-v2/results.jsonl: bcbcb1b67350a3c7726bf5f4e901e58a8cec9125
    epyc-orchestrator:orchestration/repl_memory: tree:06af3a5bf1ae70e70856ee447ef571376da2ec23
---
