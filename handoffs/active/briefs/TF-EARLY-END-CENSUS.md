---
schema: epyc.brief.v1
id: TF-EARLY-END-CENSUS
box_text_sha: t:289f97f64458b28d
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-root:scripts/coordination/taskflow/dispatch.py
- epyc-root:docs/design/taskflow-stage1-canary-findings.md
approach: 'Read the r8a-r8g run directories'' ledger lines (verdict, reason, failure_class, wall_s) and lane diffs; no reruns.
  Early end = the worker exited with wall_s below its cap and no verified verdict. Decision rule: build the resumable end
  state only if early ends are at least 2 of the units and at least one was later re-run by hand; otherwise decline in one
  line.

  '
acceptance: a census table (unit, end reason, diff lines, re-dispatched yes or no) for every r8a-r8g unit and a one-line build-or-decline
  decision are appended to docs/design/taskflow-stage1-canary-findings.md on origin/main
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:scripts/coordination/taskflow/dispatch.py: 1244813726590dc1baa1611fb79bf4750803484d
    epyc-root:docs/design/taskflow-stage1-canary-findings.md: ad7c5d4fcdc061328015dd5be0a42f5b3b95d28a
---
