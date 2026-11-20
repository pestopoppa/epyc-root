---
schema: epyc.brief.v1
id: UFH14-B-8
box_text_sha: 9fe3f3c43917ab73
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/analysis/rte_pfx1_first_divergence.py
- epyc-orchestrator:scripts/benchmark/s4_omega_ab.py
- epyc-orchestrator:src/features.py
approach: 'Question: with prefix_stable_order on, does the repaired RTE-Prefix layout give a real cache benefit without task
  regression? Arms: baseline, prefix-stable, state-append vs state-rewrite, junction-ckpt (frontdoor Qwen3.6-35B-A3B is a
  recurrent hybrid). Per turn record cache_n, prompt_n, prefill latency, first-divergence offset, plus S4 turns/task, token
  cost/task, accuracy as the semantic gate. Run through a keeper-granted window using the harness probe.py/supervisor.py pattern
  of RTE-PFX2-QN-V3. Stop when cache benefit and semantic gate are both decided; futility on two consecutive infra failures.
  Default stays off unless both pass.

  '
acceptance: grep -q 'RTE-Prefix live A/B verdict' handoffs/active/harness-program.md
non_goals:
- no default-ON flip in this box
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/analysis/rte_pfx1_first_divergence.py: 7e5da5dc6ce643331e768f3636f0f37e4a52fbd0
    epyc-orchestrator:scripts/benchmark/s4_omega_ab.py: e3983b403f66361db58be2a64e6a76568988a86d
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
---
