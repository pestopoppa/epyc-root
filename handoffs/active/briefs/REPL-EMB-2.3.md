---
schema: epyc.brief.v1
id: REPL-EMB-2.3
box_text_sha: 58ae80cb64b96a2f
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/repl_environment/context_bundle.py::ContextBundle
- epyc-orchestrator:src/repl_environment/trace_capture.py
- epyc-orchestrator:scripts/benchmark/repl_retrieval_capture.py
approach: 'Online shadow: run all retrieval arms on each REPL spill-follow/context-bundle call, show one to the model, and
  log which returned spans the model opens next (UFH-07 field spill_pointer_follows). Ingest side is done (2.3-INGEST). ContextBundle.get
  is HIGH blast radius (17 upstream nodes): stop and warn before editing it, hook through the existing default-off trace_capture
  tap in context_bundle.py instead. First step: add a shadow-arm recorder behind a default-off flag that reuses trace_capture''s
  closed-shape records.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_repl_trace_capture.py
non_goals:
- no edit of ContextBundle.get body
- no production enable
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/repl_environment/context_bundle.py: 71d6613f751afc7a0a28754dd19af820d638ce5b
    epyc-orchestrator:src/repl_environment/trace_capture.py: a8a27b9dfa1295819c112895c5d66b28efad4d77
    epyc-orchestrator:scripts/benchmark/repl_retrieval_capture.py: 6ebdd8947ed731ec298bcac126bab32b892d115d
---
