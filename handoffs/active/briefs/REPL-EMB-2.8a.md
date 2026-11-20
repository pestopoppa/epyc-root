---
schema: epyc.brief.v1
id: REPL-EMB-2.8a
box_text_sha: 9b5cbaf3572fe0ac
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/repl_environment/trace_capture.py
- epyc-orchestrator:scripts/benchmark/repl_retrieval_capture.py
- epyc-orchestrator:scripts/benchmark/repl_emb_eval.py
- epyc-orchestrator:tests/unit/test_repl_trace_capture.py
approach: 'Finish the two NOT-done items from the 2026-10-24 note: (1) route the recorder''s records through the VB-UFH12-RETR
  write side (repl_retrieval_capture.py) with trace provenance; (2) add real_trace to TRACE_STRATA in repl_emb_eval.py. Then
  done-when: one session''s real REPL use yields records the 2.2 harness loads as a real_trace stratum. Capture stays default-off
  (EPYC_REPL_TRACE_CAPTURE=1); enabling at reload is an operator package.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_repl_trace_capture.py
non_goals:
- no stack change
- no raw text in records
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/repl_environment/trace_capture.py: a8a27b9dfa1295819c112895c5d66b28efad4d77
    epyc-orchestrator:scripts/benchmark/repl_retrieval_capture.py: 6ebdd8947ed731ec298bcac126bab32b892d115d
    epyc-orchestrator:scripts/benchmark/repl_emb_eval.py: 1668d4b48c04da06ee4229a3bf65ccc925d48256
    epyc-orchestrator:tests/unit/test_repl_trace_capture.py: 9b5066ad47a051eff44ab1be79c9dea90319e07d
---
