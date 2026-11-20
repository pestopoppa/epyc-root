---
schema: epyc.brief.v1
id: HS-OD-4
box_text_sha: c8de24fecd2273df
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/api/routes/openai_compat.py
- epyc-root:docs/design/hs-od-4-max-tokens-decision-prep-20261006.md
approach: 'Implement the decision-prep recommendation A: one per-request generation budget (request.max_tokens, counting code/tool-call
  args and hidden reasoning) consumed across every REPL model call in BOTH the streaming (~:1870-1887) and non-streaming (~:2238-2255)
  loops, replacing the hardcoded n_tokens=1024; keep the 5-turn ceiling as a separate control; usage unknown stays unknown.
  Keep the 422 on image requests. If per-request accounting cannot be enforced use B (fail closed) as the interim. Default-path
  compatibility change: new test pins it.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_openai_compat_max_tokens_budget.py
new_tests:
- tests/unit/test_openai_compat_max_tokens_budget.py
non_goals:
- no rendered-text cap
- no vision-handler token field
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/api/routes/openai_compat.py: f83a4473bda2e3e0b064f2fbe373e1755069c4b3
    epyc-root:docs/design/hs-od-4-max-tokens-decision-prep-20261006.md: 1947a82620121560dbf5142041f33aa6134b71ed
---
