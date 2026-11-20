---
schema: epyc.brief.v1
id: UFH14-B4c
box_text_sha: d7f58e472477d45a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/design/ufh14-b4-prefix-cache-policy-20261003.md
- epyc-orchestrator:src/features.py::prefix_stable_order
- epyc-root:docs/reports/ufh14-b4c-isolation-20261104
approach: 'Question: prefix_stable_order ON vs OFF in production-like REPL runs, missed_prefill_share and quality. Blocked
  on (a) the B4b stable-head flag and (b) a fully isolated real EvalTower backend (guard exists, not wired into the real model-backed
  request path; v7 control ran no model). First step: wire the scratch-only private arm guard into the EvalTower request path
  and prove full API/backend isolation. Composes with B4b, same protocol.

  '
acceptance: grep -q 'B4c A/B verdict' handoffs/active/harness-program.md
non_goals:
- no edit of build_root_lm_prompt body
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/design/ufh14-b4-prefix-cache-policy-20261003.md: ff90378ca69a29bef7be4957afa2290a89141d2e
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
    epyc-root:docs/reports/ufh14-b4c-isolation-20261104: tree:7bb0d7795b33fc8f79a1bb1d5f81d061421a8bcc
---
