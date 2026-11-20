---
schema: epyc.brief.v1
id: UFH14-B1e
box_text_sha: a5d1d4c054a74579
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/api/routes/chat_pipeline/repl_executor.py
- epyc-orchestrator:src/features.py
approach: 'Port a non-terminal PROVISIONAL(answer) REPL primitive behind its own default-off flag: it stores state.provisional_answers;
  at max turns (repl_executor.py ~:771) the final answer is the last provisional that validates against output_schema. The
  original design note (/mnt/raid0/llm/tmp/ufh14-b1-20261003/orch/DESIGN-NOTE.md) is gone; the box text is the spec. Byte-identical
  when off, test asserts that.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_repl_provisional_answer.py
new_tests:
- tests/unit/test_repl_provisional_answer.py
non_goals:
- no default-on
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/api/routes/chat_pipeline/repl_executor.py: 57c230f9f7cc16cf5076c10729601290804d6292
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
---
