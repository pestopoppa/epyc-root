---
schema: epyc.brief.v1
id: REPL-EMB-A7
box_text_sha: 4ddeefe920bcb36c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/deep-dives/ydnlc-20261106
- epyc-orchestrator:src/repl_environment/context_bundle.py
approach: 'Question: does a file plus bounded reads (REPL-EMB-4.1 context.search pointers and bounded context.get windows,
  working set <=32k) match full-input native-context accuracy on the Qwen3.8-27B Q8_0 + DFlash2 (C7r 62cb6a6af)? Arms: A full
  input in native context (items <=128k) vs B file+bounded reads; same items (RULER/NIAH-style plus YARN-AGG-1 Oolong cells).
  Non-inference prep first: task builders and arm configs; then the GPU run. Needs 4.1. Stop at the paired set complete or
  futility on infra failures. Decision: file+bounded reads viable for open-weight.

  '
acceptance: grep -q 'REPL-EMB-A7 verdict' handoffs/active/harness-program.md
non_goals:
- no frontier-model runs
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/deep-dives/ydnlc-20261106: tree:7b83f007d5ceb01f9b06f1b565af302301c8287d
    epyc-orchestrator:src/repl_environment/context_bundle.py: 71d6613f751afc7a0a28754dd19af820d638ce5b
---
