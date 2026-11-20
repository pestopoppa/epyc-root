---
schema: epyc.brief.v1
id: USAGE-PROV-1
box_text_sha: d076ff23fd3c07f2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/llm_primitives/usage_log.py
- epyc-root:scripts/vidya/adapters/usage_provenance.py
- epyc-root:tests/vidya/test_usage_provenance_adapter.py
- epyc-root:progress/2026-10/2026-10-28-usage-provenance-recovery.md
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: project prospective `epyc.request_call_usage.v1` REFINE 2026-11-03 (ws58): KEEP (writer
  and reader published; no loop reads cost yet). DONE WHEN the running API writes on. Land the source adapter/producer hook
  (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture
  test and refusal controls. Box done-when (live, operational, verified after): the running API writes one real `epyc.request_call_usage.v1`
  declaration that `cli.py ingest usage-provenance` projects with refused=0.

  '
acceptance: python3 -m pytest -q tests/vidya/test_usage_prov_wire.py tests/vidya/test_usage_provenance_adapter.py
new_tests:
- tests/vidya/test_usage_prov_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/llm_primitives/usage_log.py: 0d545681b46db206bfbc38bd8e11e257b7643627
    epyc-root:scripts/vidya/adapters/usage_provenance.py: 6f040a38c9d25aa7a2acb8df95badf531a97f63e
    epyc-root:tests/vidya/test_usage_provenance_adapter.py: 04dd3500d4996c78738f6a99b5a4eb2a2847b988
    epyc-root:progress/2026-10/2026-10-28-usage-provenance-recovery.md: daeea3f6063a5c0f3786d082540cbe9534109a27
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
