# RTG-48 A-2 — Falsifiable adjudication of RC-1

**Date:** 2026-10-08
**Task:** A-2 in `handoffs/active/coordinator-role-failure-modes-and-refactor.md`
**Scope:** Source review of the F-24 candidate, the later F-38 recurrence, and the rule/mechanism distinction. No new event-rate estimate.

## Verdict

F-24 is a **wrong-mechanism** case. A mechanism was present, but it was not a checkpoint capable of refusing the failure: `pgrep -f "session_bus_coordinator\\.py run"` encoded the supervisor's launch argv. The live daemon's `--bus-root` argument sat between those tokens, so the supervisor could not see the healthy daemon, collapsed “not found” into “unhealthy,” and attempted relaunches. This falsifies **mechanism presence as a proxy for protection**. Under A-1's stricter standard—count a mechanism only when it would refuse the specific failure—F-24 is not a counterexample to a correctly mechanised rule. It belongs in a separate mechanism-quality class.

F-38 is a stronger example of an **active but incorrect mechanism**. The replacement stale-source check treated any recent source mtime as evidence that the running daemon was stale. The contemporaneous incident report attributes 14 restarts of a healthy daemon in 54 minutes to normal edits in the multi-writer tree. The mechanism ran and violated its stated safety rule that a healthy daemon is never disrupted. This is falsifiable evidence that a mechanism can be present and still fail its own safety property. It is a predicate/design defect, not a case of an agent forgetting a rule.

The A-2 aggregate prediction (“near zero” failures on mechanised rules versus common failures on prose rules) is **not estimable** from the selected rows. They do not provide a sampling frame or denominator, and logged mechanism outcomes are observable while prose compliance has no comparable record. The finite source review classifies F-24 and F-38; it does not establish the population rates or the broad causal claim that compliance decays with context. A defensible narrowed conclusion is that mechanism presence alone does not establish protection; these selected cases do not establish predictive rates. Protection requires correct scope, discriminating inputs, and a test showing refusal of the specific failure.

## Source record

1. **Original implementation:** `9565ad6ef` (2026-07-27) introduced the supervisor. Its source says fresh heartbeat means a healthy daemon “does nothing” and implements health as the conjunction of heartbeat age and `pgrep` match. The code therefore had a mechanism and an explicit no-disruption invariant.
2. **F-24 evidence:** `e57a10a67` (2026-08-12 11:02:31Z) records the C49 correction and the event at 10:35–10:36Z: daemon PID 3259108 was alive with a fresh heartbeat; `pids ''` caused unhealthy/restart reports, and singleton-lock exits prevented a new daemon. The commit body gives the exact argv mismatch and changes identity resolution to the heartbeat PID with `alive/dead/unknown` states. The commit's incident report is contemporaneous author evidence, not an independent authentication of the original log. The current host log at `/mnt/raid0/llm/epyc-root/logs/bus_supervisor.out` starts on 2026-08-23; its original F-24 window is not retained. The raw lines therefore cannot be re-opened here.
3. **F-38 evidence:** `bc6dc77f7` (2026-08-12 21:46:53Z) records 14 restarts in 54 minutes under the mtime predicate and explains why a distinct-mtime state file did not bound the repeated false positives. The handoff's F-38 row records the same historical report, including its interval and epoch change; it is not an independent authentication. The current host log files contain later supervisor epochs (the `.out` stream starts 2026-08-23 and `.log` starts 2026-08-16), not the 2026-08-12 F-38 window; counts/times remain scoped historical reports, not freshly authenticated raw-log measurements.
4. **Current implementation:** `scripts/coordination/bus_supervisor.sh` compares daemon heartbeat `source_tree` (captured at process start) to `git rev-parse HEAD:scripts/coordination`; unreadable/missing identity or marker is UNKNOWN, not stale. The current `scripts/coordination/tests/test_supervisor_stale_source.sh` source covers unknown, current, stale, uncommitted-touch, and loop-wiring cases. This is inspection of the current implementation/test source only; neither was executed for this review.
5. **A-1 and denominators:** `docs/reviews/rtg48-mech-column-audit-2026-08-23.md` applies the “would refuse this specific failure” standard. The handoff's selected held/violated rows and its dated RC-1 verdict supply no census denominator. Its later verdict itself acknowledges missing denominators and asymmetric observability. Those facts preclude a rate conclusion.

## Reproducible distinction

For a candidate rule/failure pair, ask in order:

- **Absent:** no executable mechanism reaches the action point; classify as prose/recall.
- **Present but blind or mis-specified:** mechanism executes, but cannot distinguish the target condition from its opposite (F-24); classify as wrong mechanism.
- **Active but incorrect:** mechanism observes an input but its predicate maps a normal/healthy state to the forbidden action (F-38); classify as mechanism failure.
- **Specific refusal demonstrated:** only here count it as protective for that failure, consistent with A-1.

The retained source history supports classifying the reported F-24 and F-38 incidents in the second and third categories. They do not show that every mechanism fails, nor that human compliance decays. A population comparison would need a defined case census and comparable denominators for both mechanism-backed and prose-only rules.

## Evidence limits and scope

The history contains detailed commit-body incident reports, and the live checkout contains current source plus handoff summaries. Raw incident logs cited by those reports are absent, so the exact F-24/F-38 runtime details are attributed to the contemporaneous reports rather than represented as independently reopened raw logs. No new statistics were computed. Per `MEASUREMENT.md` claim grammar, this is a bounded source-based adjudication, not a protocol-backed rate claim. No inference, imports, tests, runtime probe, or process manipulation was performed. The measurement constitution and `agents/shared/MEASUREMENT_POLICY.md` were read; neither permits converting the selected source cases into a population rate.
