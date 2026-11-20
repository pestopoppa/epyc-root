---
schema: epyc.brief.v1
id: UFH14-B4b
box_text_sha: 5dbd1875b9f0c321
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/design/ufh14-b4-prefix-cache-policy-20261003.md
- epyc-orchestrator:src/prompt_builders/builder.py
- epyc-orchestrator:src/features.py
- epyc-orchestrator:scripts/analysis/prefix_cache_report.py
approach: 'Question: does emitting the stable head as a system message ([system,user] split at a builder marker after ''##
  Rules'') raise hit_tok / lower missed_prefill_share for REPL roles without quality loss on EvalTower? Code first: builder
  marker plus new default-off flag stable_head_system_message (PromptBuilder.build_root_lm_prompt is CRITICAL blast radius,
  31 nodes; stop and warn, keep the edit additive). Then A/B on isolated eval backend. Runbook /mnt/raid0/llm/tmp/ufh14-b4-20261005
  is missing; reconstructed at docs/design/ufh14-b4cd-ab-runbook-reconstructed-20261101.md.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_stable_head_system_message.py
new_tests:
- tests/unit/test_stable_head_system_message.py
non_goals:
- no default-on
- no edit of build_root_lm_prompt body beyond the marker
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/design/ufh14-b4-prefix-cache-policy-20261003.md: ff90378ca69a29bef7be4957afa2290a89141d2e
    epyc-orchestrator:src/prompt_builders/builder.py: 996e4c4177b8dc8af49651c97fefccf5c95476e7
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
    epyc-orchestrator:scripts/analysis/prefix_cache_report.py: dbf69f359009287e90c0db9e6645185adee48d99
---
