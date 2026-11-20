---
schema: epyc.brief.v1
id: KT-5
box_text_sha: f7d5bc3459c174d0
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:/mnt/raid0/llm/tmp/ws58-kt5-memory-split-proposal.md
approach: 'First concrete step for: [S] Split the Claude memory `MEMORY.md` index into category index files under the load
  limit, and include memory and progress files in the KT-3 map''s search by reusing the kb-search index (DHM-5 measu. Box
  has no done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_kt_5.py
new_tests:
- tests/test_kt_5.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:/mnt/raid0/llm/tmp/ws58-kt5-memory-split-proposal.md: e345ab0657b4f9c946e4e018c13cd0fb4b3b4a4c
---
