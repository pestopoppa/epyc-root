---
schema: epyc.brief.v1
id: CODEMODE-REL-EMBED-PLACE
box_text_sha: cbc6ef561880900f
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/harness-program.md
- epyc-orchestrator:src/features.py
approach: 'Option A is signed and code applied (d2be521c). Remaining: republish the bring-up row /mnt/raid0/llm/tmp/embedder-gpu-bringup-20261119
  (job-embedder-gpu.sh, gates.py: G1 residency, G2 GPU-vs-CPU cosine >=0.999, G3 p95 <=250 ms with the 27B decoding, G4 pool
  fallback and idle CPU <=5%) once the stack is up. Stop on all four gates green (service left resident) or on the first failed
  gate (service stopped via orchestrator_stack, row filed fail). Decision: keep embedder_gpu :8099 as production picker embedder.
  Prep: verify the spec still matches source SHA.

  '
acceptance: grep -q 'G1-G4 green' handoffs/active/harness-program.md
non_goals:
- no change to option A
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/harness-program.md: 3cb5ef0d88bd7c907a51544f584b042ea93e3a23
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
---
