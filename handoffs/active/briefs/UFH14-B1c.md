---
schema: epyc.brief.v1
id: UFH14-B1c
box_text_sha: 369acedacc5e5d71
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/harness-program.md
- epyc-root:docs/design/ufh14-b1-timeout-stackchange-item-20261003.md
approach: 'opencode half is already applied (headerTimeout/chunkTimeout 14,400,000 ms for qwen-local and qwen-gpu, operator
  OK 2026-10-04). Remaining: the codex provider config for local models gets the same derived parameters (server-derived values:
  timeouts, context, max output), then verify one local-model request through the codex config. Step 1: locate the codex provider
  config and diff against the opencode values.

  '
acceptance: grep -q 'codex.*14400000\|14400000.*codex' /home/node/.codex/config.toml
non_goals:
- no change to the already-applied opencode config
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/harness-program.md: aa7dc419bf8eb745819bc97721912f46fb95d42d
    epyc-root:docs/design/ufh14-b1-timeout-stackchange-item-20261003.md: 5774c829761af9058dc27ac69fef002b55edf6ec
---
