---
schema: epyc.brief.v1
id: VB-EVALPERF-ENDPOINT-WIRE
box_text_sha: t:aabe7e3ac45bbbf9
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/experiments/evalperf_endpoint.py
- epyc-root:tests/experiments/test_evalperf_endpoint.py
- epyc-root:scripts/vidya/ingest_sources.py
- epyc-root:scripts/vidya/adapters/README.md
approach: 'Add adapter projecting evalperf_endpoint native records (EvalPlus pin, model/build identities, launch and sample/token
  limits, raw+sanitized code, correctness/instruction profiles, arm checkpoints, partial/failure) through the shared carrier
  and claim_tuple.grade(); one-sample uncertainty preserved. Box has no done-when; acceptance is the closest check: new adapter
  test with synthetic records plus refusal controls.

  '
acceptance: python3 -m pytest -q tests/vidya/test_evalperf_endpoint_adapter.py tests/experiments/test_evalperf_endpoint.py
new_tests:
- tests/vidya/test_evalperf_endpoint_adapter.py
non_goals:
- do not infer kernel efficiency or production-role equivalence
- no retrospective warrant
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/experiments/evalperf_endpoint.py: 76b781a22df60eaaf4f465eca640b9daf19e85eb
    epyc-root:tests/experiments/test_evalperf_endpoint.py: dfd1b675998f2b78a81403f4840ff8f04f49b61b
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
    epyc-root:scripts/vidya/adapters/README.md: e3c2ef4730581badb912189e13072542bc78a2cf
---
