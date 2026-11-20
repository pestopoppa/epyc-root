---
schema: epyc.brief.v1
id: STACK-UP-RELOAD-QUEUE
box_text_sha: 5da7372b30ccb948
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/harness-program.md
- epyc-orchestrator:src/features.py
approach: 'Operational queue, three ordered steps once the stack is up (frontdoor/27B :8070/:8083 and embedders :8090-8095
  healthy): (1) republish embedder bring-up row spec-embedder-gpu-bringup.json and require G1-G4 green; (2) rebase feat/codemode-rel-flip,
  rerun its tests, push via serialized_push; (3) one API-only reload (orchestrator_stack.py reload orchestrator) then serving
  proof. First concrete step: prep (2) now, it needs no stack. Box has no done-when; acceptance is the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && git merge-base --is-ancestor feat/codemode-rel-flip origin/main
non_goals:
- do not stop autopilot or the model servers
- no full-stack reload
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/harness-program.md: 3cb5ef0d88bd7c907a51544f584b042ea93e3a23
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
---
