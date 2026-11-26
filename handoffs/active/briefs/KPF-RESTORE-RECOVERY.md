---
schema: epyc.brief.v1
id: KPF-RESTORE-RECOVERY
box_text_sha: t:31b4758cb769edda
author: intake
written: '2026-11-26'
accepted: auto
where:
- epyc-root:handoffs/active/kv-cache-program.md
- epyc-root:research/deep-dives/intake-nov26-kernels/30318.md
approach: 'A source-pinned regression on two populated slots must return zero on failure, clear any partially modified destination
  as required, preserve the neighbor, and round-trip valid state. Repeat on a new sequence ID and in reverse slot order. Log
  each case and return value. Require a CPU build proof before model-backed evaluation and HIP residency proof before claiming
  device coverage.

  '
acceptance: KPF-RESTORE-RECOVERY.json contains valid_count, failed_destination_removed, survivor_hash_equal, deferred_writes_after_failure.
  All valid restores succeed, no write survives discard and every neighbor hash matches.
non_goals: []
tier: local
grounded:
  at: '2026-11-26'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 2711f1bf442a85a9d70e2fe437b06fcd51124bab
    epyc-root:research/deep-dives/intake-nov26-kernels/30318.md: 7eb2f2ddfd51abe24c7bb4eb6560e1a98131f908
---
