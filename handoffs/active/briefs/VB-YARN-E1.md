---
schema: epyc.brief.v1
id: VB-YARN-E1
box_text_sha: 1eab0dd1264dfb5a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/benchmark/yarn_e1/cpu_continuation.py
- epyc-root:/mnt/raid0/llm/tmp/yarn-e1-mem-chain-20261104/run_chain.py
- epyc-root:docs/reports/am-port2-continuation-20261119.md
- epyc-root:docs/reports/kshift-model-r1-20261119.md
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: write side for the INF-59 long-context needle runs (E0 runner, E1 window). Land the source
  adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with
  a synthetic-fixture test and refusal controls. Box done-when (live, operational, verified after): the next long-context
  needle / depth-recipe run after the hook ingests with refused=0 and the AK canary for its model target lists the window
  claim. Native row `yarn-cpu-512k-20261119` must file COMPLETE for the live proof.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_yarn_e1_wire.py
new_tests:
- tests/vidya/test_vb_yarn_e1_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/benchmark/yarn_e1/cpu_continuation.py: a7ef732518010e4dc1187dbc3db695c2cdf9bb29
    epyc-root:/mnt/raid0/llm/tmp/yarn-e1-mem-chain-20261104/run_chain.py: 7fe19cc98ff92b7ffa69608912ba43b77fd32861
    epyc-root:docs/reports/am-port2-continuation-20261119.md: 8c92d8e89023dda24f113297b4eb3204f5bbf0d4
    epyc-root:docs/reports/kshift-model-r1-20261119.md: ffb1d30b529334df5305896a02a613cb3e63ad51
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
