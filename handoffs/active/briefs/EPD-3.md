---
schema: epyc.brief.v1
id: EPD-3
box_text_sha: 5bf6f5d62cc1d2ec
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/maintenance/repair_episodic_embeddings.py
- epyc-orchestrator:scripts/migration/reembed_stores_eg2.py
- epyc-root:progress/2026-08/2026-08-09.md
approach: 'First concrete step for: the embedding index mixes >=3 text conventions, so the vector leaks the writer path. Box
  has no done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_epd_3.py
new_tests:
- tests/test_epd_3.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/maintenance/repair_episodic_embeddings.py: 521b1fea8e5a5183d49bcc5303e173d26797a692
    epyc-orchestrator:scripts/migration/reembed_stores_eg2.py: 9defbbd43f16ade62ea1dbe99255a81f269cbb03
    epyc-root:progress/2026-08/2026-08-09.md: 9a7c3fd30bfb5f715d875048194a7b6e5c8978e2
---
