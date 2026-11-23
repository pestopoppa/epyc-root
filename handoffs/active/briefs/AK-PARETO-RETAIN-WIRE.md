---
schema: epyc.brief.v1
id: AK-PARETO-RETAIN-WIRE
box_text_sha: t:71e272bdaaebf5e4
author: owner
written: '2026-11-23'
accepted: owner
where:
- handoffs/active/autokernel-loop.md
approach: 'Code is in epyc-inference-research scripts/kernel_rnd/autokernel/loop: cross_target.check_one loads pareto-retain.jsonl
  beside the cross-target ledger (pareto_retain.load/front) and passes the non-dominated patch ids to eligible(retained=...).
  New helper cross_target.retained_patch_ids; tests in loop/test_cross_target.py.

  '
acceptance: check_one passes the Pareto front to eligible; a series whose patch is dominated is not marked pareto_retained;
  loop tests and check_regrowth_guards pass
non_goals: []
tier: local
grounded:
  at: '2026-11-23'
  blobs:
    epyc-root:handoffs/active/autokernel-loop.md: 31e98a7fd0ff30b2e5610653112598735365f099
---
