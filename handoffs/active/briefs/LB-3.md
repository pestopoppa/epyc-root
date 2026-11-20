---
schema: epyc.brief.v1
id: LB-3
box_text_sha: fd49c36b0fa93497
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/proactive_delegation/delegator.py::ProactiveDelegator._should_review_subtask
- epyc-orchestrator:orchestration/review_plane_knobs.yaml
approach: 'Add a seeded k% sampling knob (review_sample_pct, default 100 = inert) to the review-knobs dataclass and gate it
  in _should_review_subtask after the complexity check; declare it in review_plane_knobs.yaml. Seed from the step id so replays
  are deterministic. quick_mode tier wiring and fan-out effort-scaling stay separate follow-ups.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest tests/unit/test_review_sampling.py -q
new_tests:
- tests/unit/test_review_sampling.py
non_goals:
- No enforce-mode flip; no budget threshold (LB-6/OP-5b)
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/proactive_delegation/delegator.py: 4ae56089935b24a5e1697c67618ef349b9eb8e32
    epyc-orchestrator:orchestration/review_plane_knobs.yaml: e9971ea0733c0d83b78cf1d625700d02d053ac18
---
