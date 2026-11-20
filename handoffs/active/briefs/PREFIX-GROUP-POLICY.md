---
schema: epyc.brief.v1
id: PREFIX-GROUP-POLICY
box_text_sha: 2bb050f1fd6cd1e4
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/api/routes/chat_pipeline/scout_stage.py
- epyc-orchestrator:src/features.py
- epyc-orchestrator:src/typed_decisions/fanout_policy.py
approach: 'Add default-off FeatureSpec dispatch_prefix_grouping in src/features.py (plus Features dataclass field and autopilot
  surface wiring) and group siblings by prefix hash onto one server''s slots in the fan-out dispatcher when they would otherwise
  spread; reuse scout_stage.resolve_cap admission. Box gate says only build if REMEASURE shows a material shared fraction;
  first step is the flag plus a pure grouping function with a unit test, inert when off.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_dispatch_prefix_grouping.py
non_goals:
- no default-on
- no kernel work
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/api/routes/chat_pipeline/scout_stage.py: 5ed48af7db1ae4a7fcad3120d604835b55a0a428
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
    epyc-orchestrator:src/typed_decisions/fanout_policy.py: b00e3eb3ca0317bd5059bd124769858809e5e3bc
---
