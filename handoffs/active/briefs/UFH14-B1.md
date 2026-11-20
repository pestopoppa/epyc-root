---
schema: epyc.brief.v1
id: UFH14-B1
box_text_sha: efa64686bac074c8
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actors.py
- epyc-root:harness/opencode-plugin
- epyc-orchestrator:src/graph/compaction.py
approach: 'Epic; first concrete step: inventory D1-D5 client fixes in /mnt/raid0/llm/tmp/ds41-c95/run2.py and proxy2.py and
  write them as one model-independent settings module (names and defaults) that the AutoKernel actor launch in actors.py reads;
  opencode/codex provider configs (B1c) and orchestrator compaction (HS-4) follow as separate steps. Acceptance is the closest
  check: actors.py imports the shared settings.

  '
acceptance: grep -q 'harness_client_settings' /workspace/repos/epyc-inference-research/scripts/kernel_rnd/autokernel/loop/actors.py
non_goals:
- no change to C95 experiment results
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actors.py: 21068b0fdc4d1522aca8e7f93dec12d74def2f33
    epyc-root:harness/opencode-plugin: tree:faf20a86b5f482a6a475637ad536d98615083824
    epyc-orchestrator:src/graph/compaction.py: 92a7e5f4cee1cf66739a1419a13ff5f839198d39
---
