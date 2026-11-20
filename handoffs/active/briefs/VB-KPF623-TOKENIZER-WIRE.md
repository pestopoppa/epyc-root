---
schema: epyc.brief.v1
id: VB-KPF623-TOKENIZER-WIRE
box_text_sha: 45efddcd299a6ce7
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/reports/kv-cache/kpf623-tokenizer-roundtrip-20261105/worker.py
- epyc-root:scripts/vidya/ingest_sources.py
- epyc-root:scripts/vidya/adapters/README.md
approach: 'Add adapter for worker.py observations: sealed source/header/library/helper/executable and case identities, ordered
  byte and ID outcomes, return codes, bounds, child cleanup; differing IDs conditional on matching bytes, missing custody
  UNKNOWN; grade via claim_tuple.grade(). Box has no done-when; acceptance is the closest check: new adapter test with synthetic
  worker output. 256-case history is committed-conclusion only.

  '
acceptance: python3 -m pytest -q tests/vidya/test_kpf623_tokenizer_adapter.py
new_tests:
- tests/vidya/test_kpf623_tokenizer_adapter.py
non_goals:
- no retrospective measurement warrant
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/reports/kv-cache/kpf623-tokenizer-roundtrip-20261105/worker.py: 04792391e5753c3bc81a4afd7d1c3796103b58cb
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
    epyc-root:scripts/vidya/adapters/README.md: e3c2ef4730581badb912189e13072542bc78a2cf
---
