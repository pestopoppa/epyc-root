---
schema: epyc.brief.v1
id: Strategy-prompt-length
box_text_sha: 509af67509ce9a51
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/benchmark/s4_omega_ab.py
- epyc-orchestrator:orchestration/prompts/root_lm_system.s4_omega.md
- epyc-orchestrator:orchestration/prompts
approach: 'Question: does an explicit task-strategy prompt (1500-token original) cut rollout time/turns vs the current role
  prompt, and does a 200-token compression converge lower/less stably? Reuse the S4 Omega A/B runner with a strategy-prompt
  arm (and the compressed arm) as extra arms; paired per-task diff on turns, wall-clock, tokens, with run-to-run spread. Stop
  when the paired effect is clear; futility on backend fault or deadline. Decides whether role prompts get a strategy section.
  Prep step: add the strategy-prompt arm file and arm selector to s4_omega_ab.py.

  '
acceptance: grep -q 'Strategy-prompt-length verdict' handoffs/active/harness-program.md
non_goals:
- no training
- no change to production role prompts
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/benchmark/s4_omega_ab.py: e3983b403f66361db58be2a64e6a76568988a86d
    epyc-orchestrator:orchestration/prompts/root_lm_system.s4_omega.md: f9f0808dcd30532834f5b6fd2f73cc0d6fe2c6e8
    epyc-orchestrator:orchestration/prompts: tree:cdb0f9aa323ba319f5e7edc73d531074dfe6ce3e
---
