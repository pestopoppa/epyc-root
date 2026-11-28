---
schema: epyc.brief.v1
id: AP-LOCAL-DRIVING-PILOT
box_text_sha: t:f348fea54458eec0
author: planning
written: '2026-11-28'
accepted: auto
where:
- epyc-root:docs/reports/autopilot-w66-recovery-replay.md
- epyc-root:docs/reports/autopilot-w66-cpu-quality-q012.md
- epyc-root:docs/reports/autopilot-w66-replay-plan.md
approach: 'Choose two fresh tasks using the routing evidence, with trusted checks and an independent source review. Keep every
  correction tied to its actual patch and remaining wall/token budget. Begin from current full-tools C22 driving and shadow
  the recovery rule before making it disruptive. Score false interventions against late successful edits and detect shell-created
  artifacts. Track configured, triggered, delivered and acted-on guidance independently. Compare a case-neutral patch-first
  instruction or one actionable failing check with the current driver, keeping fresh, resumed and draft-carrying attempts
  distinct. Include one accepted-artifact preservation control because both real W66 CPU continuations failed and cannot certify
  quality neutrality. Use thinking OFF as the initial tested setting and record any matched ON supplement separately. Reuse
  historical main-only results. Run in an authorized compute window, preserving q0-q2 and excluding GPU/q3 until that resource
  scope changes. Check after each completed task and stop after two tasks or earlier on a clear failure of the policy or acceptance
  controls. Report inconclusive results explicitly. Live autonomous-loop launch continues to follow its existing operator
  hold. Operator priority 2026-11-28 is paid-token reduction and privacy with reasonable task deadlines. Account for all paid
  attempts and fallback. Prefer deterministic local repair feedback before paid help. Keep private source local and export
  a minimal diagnostic packet only when useful within existing privacy boundaries. Treat end-to-end elapsed time as a deadline/operational
  constraint. A successful pilot can take longer than historical main-only work. Include actual packet contents/byte counts
  and source sensitivity, and preserve unknown costs instead of assuming zero.

  '
acceptance: two constrained tasks retain quality-qualified outcomes, actual guidance, paid input/cache/output and exported-context
  scope through fallback; accepted work meets declared deadlines and the report assesses paid-token savings and privacy with
  elapsed time as reference.
non_goals: []
tier: local
grounded:
  at: '2026-11-28'
  blobs:
    epyc-root:docs/reports/autopilot-w66-recovery-replay.md: ed5b4c1e223effb59b360389b0764644238ece00
    epyc-root:docs/reports/autopilot-w66-cpu-quality-q012.md: 82d191111d024a9fb5c274cdfb70719691055437
    epyc-root:docs/reports/autopilot-w66-replay-plan.md: 6428401b7da708f33dc563020163a2267fac0648
---
