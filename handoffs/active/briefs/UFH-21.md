---
schema: epyc.brief.v1
id: UFH-21
box_text_sha: dc9482a406366e6e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:harness/opencode-plugin
- epyc-root:handoffs/active/harness-program.md
approach: 'Prove or disprove compaction laundering: place a forged ''[User]:'' approval in a file the agent reads, run /compact
  in the shipped OpenCode shell, record whether the summary carries it as a user instruction. If yes, patch the serialize
  path to escape role labels in packages/opencode and packages/core, add a hostile-tool-output unit test, file the upstream
  advisory. First step: locate the compaction serialize function and write the hostile-fixture unit test that fails if role
  labels are not escaped.

  '
acceptance: grep -rq 'compaction laundering' harness/opencode-plugin/tests
non_goals:
- no upstream push without the advisory text reviewed
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:harness/opencode-plugin: tree:faf20a86b5f482a6a475637ad536d98615083824
    epyc-root:handoffs/active/harness-program.md: cadd2da6b668a35f911a3b0ad52a85e94ee62ea0
---
