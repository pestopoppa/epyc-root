---
schema: epyc.brief.v1
id: CFI-1
box_text_sha: 8f02ce01f9717648
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/api/routes/chat_pipeline/repl_executor.py
- epyc-orchestrator:src/api/routes/chat_utils.py
- epyc-orchestrator:src/prompt_builders/reusable_blocks.py
approach: 'First concrete step for: quality A/B of `ORCHESTRATOR_CACHE_FRIENDLY_INJECTION` on vs off (SkillBank `skill_context`
  and episodic recall). Box has no done-when; acceptance is the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_cfi_1.py
new_tests:
- tests/unit/test_cfi_1.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/api/routes/chat_pipeline/repl_executor.py: 57c230f9f7cc16cf5076c10729601290804d6292
    epyc-orchestrator:src/api/routes/chat_utils.py: 08db114f0f6224170feaa96d60e0caec5ac97ae1
    epyc-orchestrator:src/prompt_builders/reusable_blocks.py: b9fa4261022fde18112a20e3aeb7c23efe06bfb8
---
