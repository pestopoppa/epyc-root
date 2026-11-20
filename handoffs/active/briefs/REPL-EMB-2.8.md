---
schema: epyc.brief.v1
id: REPL-EMB-2.8
box_text_sha: c4cb56f7e041b013
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/benchmark/repl_emb_eval.py
- epyc-orchestrator:src/repl_environment/trace_capture.py
approach: 'Question: does EmbeddingGemma 2 BF16 @256 hybrid still beat grep on a REAL-trace stratum? Trigger: >=75 real REPL
  spill-follow traces (needs 2.8a capture first). Rerun the recall legs with the frozen rule (k=5, M=0.10, X=0.05, n>=120
  with >=75 trace rows, CI condition) on real_trace plus probe45 via repl_emb_eval.py. Stop when n>=120 with >=75 trace rows
  or report trigger-not-met. Decision: confirm or reverse the 2.2 verdict.

  '
acceptance: grep -q 'REPL-EMB-2.8 real-trace verdict' handoffs/active/harness-program.md
non_goals:
- no stack or config change
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/benchmark/repl_emb_eval.py: 1668d4b48c04da06ee4229a3bf65ccc925d48256
    epyc-orchestrator:src/repl_environment/trace_capture.py: a8a27b9dfa1295819c112895c5d66b28efad4d77
---
