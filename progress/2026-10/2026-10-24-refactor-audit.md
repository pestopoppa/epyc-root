# 2026-10-24 — refactor audit (cloud session)

Session: claude.ai/code session_01C4SLLAQhop8AA9rJJusAYj (cloud container, fresh clones; never on the host).
Plan: [`handoffs/active/refactoring-multirepo-2026-10.md`](../../handoffs/active/refactoring-multirepo-2026-10.md). Evidence:
[`research/refactor-audit-2026-10/`](../../research/refactor-audit-2026-10/README.md).

- Audit of epyc-orchestrator (incl. autopilot) and AutoKernel: 382 verified or raw findings across 17 units
  (A 148, B 113, C 121; C4-C6 unverified after a 2026-10-07 usage limit).
- Operator decisions: evaluator changes as ONE era event; delete all three unreachable AutoKernel planes, staying
  current with main; add orchestrator CI + repair the AutoKernel workflow; full program, paced.
- Wave 1 partly implemented and stopped by the operator. Pushed, none reviewed by a second agent:
  epyc-root `refactor/containment-scanner` (operator review required) and `refactor/refactoring-plan`;
  epyc-orchestrator `refactor/{hermetic-tests,request-path,config-registry,scripts-cleanup,test-hazards,autopilot-loop,autopilot-gate}`;
  epyc-inference-research `refactor/autokernel-loop-bugs` (do not merge: AutoKernel launch hold).
- Found on the way: epyc-root main since 84b0de13 lets `sudo mount` through the containment hook's
  degraded mode (fix on `refactor/containment-scanner`); the ni63 source pin for `orchestrator_stack.py`
  is stale on main (4 tests red there).
- Usage: 6 concurrent agents exhausted a 5-hour window in ~55 min (extra usage `out_of_credits`); 2 is sustainable.
