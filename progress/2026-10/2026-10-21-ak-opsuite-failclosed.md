# 2026-10-21 ak-opsuite-failclosed

AKX-ALL-17.x: AK op-suite keep gate fails closed on incomplete test-backend-ops runs.
- epyc-inference-research: `49adfa699` (fix + tests), `a3e1cefb5` (stale v9 frozen-tree test -> v10), on origin/main via serialized push.
- Suites: evaluator/, test_t0_provider, test_execution_chain, test_campaign: 2207 passed.
- Historical replay: 30 recorded PASS op-unit verdicts; 28 still pass, 0 would fail, 2 captures missing (r20, r21; status invalid). No verdict changed.
- No autokernel.loop.run was live; change takes effect on next loop start.
