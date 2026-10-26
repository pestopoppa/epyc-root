# Refactor audit, 2026-10 — evidence, data and tooling

Plan and branch status: [`handoffs/active/refactoring-multirepo-2026-10.md`](../../handoffs/active/refactoring-multirepo-2026-10.md).

The original findings and implementer reports preserve the cloud checkpoint. Current resumed-session
review, test and integration state is in the handoff and each finding's `resolution` field in
`data/finding-status.json`; an original commit or historical "unreviewed" label is not its current state.

| File | What it is |
|---|---|
| [`BUG-REPORT-autopilot-autokernel.md`](BUG-REPORT-autopilot-autokernel.md) | Every autopilot and AutoKernel bug the audit found, with severity, evidence, fix and current status (fixed on which `refactor/*` branch and commit, WIP, or planned in which package); orchestrator-core bug statuses in an appendix |
| [`findings-orchestrator-core.md`](findings-orchestrator-core.md) | Units A1-A6 (API, inference hot path, config/registry/runtime, REPL/tools, scripts, tests): 148 findings |
| [`findings-autopilot.md`](findings-autopilot.md) | Units B1-B5 (loop, eval + safety gate, actions/planner/journal, satellites, autopilot_core + tests): 113 findings |
| [`findings-autokernel.md`](findings-autokernel.md) | Units C1-C6 (loop core, loop periphery, controller, evaluator/execution, release + top level, tests): 121 findings; C4-C6 UNVERIFIED |
| [`OPERATOR-DECISIONS.md`](OPERATOR-DECISIONS.md) | The four operator decisions of 2026-10-24 and the standing inputs |
| [`K2-CURRENT-SOURCE-REVIEW.md`](K2-CURRENT-SOURCE-REVIEW.md) | 2026-10-25 current-source review and successful GitNexus guard status; source-guard edits remain unapplied |
| `metrics/` | AST metrics (largest files, longest and most complex functions, swallowed excepts, import-time calls, sys.path mutations, duplicate bodies) and git churn per area, as of 2026-10-07 |
| `packages/wave1.json`, `packages/wave2.json`, `packages/deferred.json` | Work-package definitions: finding ids per package, order and notes |
| `packages/mkpkg.py` | Regenerates the per-package briefs from `data/` |
| `packages/impl_workflow_w2.js` | The implementer + adversarial-reviewer prompt contract used for the packages |
| `implementer-reports/` | Final reports of the implementer agents that finished (O1 stage 1, O3, O6 stage 1, P1 stage 1, P2) |
| `data/findings-*.json` | Machine-readable findings (per unit: summary, bloat estimate, findings with verdicts and safety reviews) |
| `data/finding-status.json` | Per finding: package, commits on `refactor/*` branches, deferral |
| `data/orch_baseline_failing_ids.txt` | The 148 failing/erroring orchestrator test ids at origin/main + hermetic-tests (2026-10-24) |
| `data/ak_baseline_failing_ids_2026-10-07.txt` | The 539 failing/erroring AutoKernel test ids at 2026-10-07 |

Each finding records the files and lines as of 2026-10-07. Line numbers have drifted since; the finding
text identifies the problem.

**How the findings were produced.** Static metrics first, then for each of 17 units: a deep finder, then an
adversarial verifier that defaulted to *refuted* unless it could confirm the finding first-hand. Severity ≥ 4
autopilot findings then went through a production-safety review. A finding marked `partially` carries the
verifier's corrected proposal, which takes precedence; `verifier-added` findings (`-M` ids) were found by the
verifier.
