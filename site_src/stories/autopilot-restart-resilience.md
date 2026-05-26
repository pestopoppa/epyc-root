# Autopilot resilience: when operators move under your feet

AutoPilot, the nightly optimizer that proposes new configurations, runs experiments, and maintains a Pareto archive of the production stack, has one fundamental assumption baked into its design: that the configuration it's testing right now is the configuration that's actually running. If a benchmark scores zero quality and the orchestrator's `/chat` endpoint is returning errors, AutoPilot's planner has two choices for how to interpret that signal — *the config under test is broken* or *something about the environment changed mid-test*. For most of 2026, it didn't actually distinguish between them. The planner learned the wrong lesson three different ways, and the Pareto archive accumulated false-failures that the planner kept tripping over.

The fix landed 2026-05-24 after a careful audit. It's a small story but it's a good one — small in code size, large in implications for any agent that runs experiments against state someone else controls.

## The three pollution modes

The first mode was orchestrator API reloads. An operator running `orchestrator_stack reload orchestrator` mid-trial would briefly bounce the FastAPI process. Every in-flight chat request errored out. The benchmark scorer recorded `EvalResult(quality=0, reliability=0)`. The planner journaled the trial as a "quality_floor" failure. The configuration the trial had actually been testing — usually a perfectly reasonable model parameter — went into the archive as a confirmed-bad data point. Future trials avoided that region of configuration space on the strength of a measurement that had nothing to do with the configuration.

The second mode was llama-server reloads. Same shape, different layer. An operator reloading the `frontdoor` llama-server instance to apply a config change would interrupt every request that happened to route through it. The benchmark scored zero. The planner blamed the trial's config under test.

The third mode was the subtlest. Even when AutoPilot wasn't itself being polluted, its **Pareto archive** could be contaminated by trials that had already failed for exogenous reasons before the resilience work landed. The planner reads from the archive each trial to choose what to explore next. A polluted archive sends it down dead alleys for weeks.

## What the architecture actually needed

The naive fix — wrap every benchmark in a retry loop and only journal if the retries also failed — would have handled mode one. But it wouldn't have caught the asymmetric case where the retries succeed (because the operator's reload finished) but the *original* failure that triggered the retry was an exogenous interruption. Worse, retry loops would have masked legitimate config failures by giving them time to "settle."

The audit pass identified four correctness blockers that any naive fix would have missed:

1. **Safety-gate ordering.** The decision to journal a trial happens before the eval-failure analysis. If the gate runs first, exogenous-detected trials don't reach the archive at all.
2. **Pareto pollution recovery.** Past contaminated entries needed to be retroactively flagged, not just future ones avoided.
3. **Seed-batch metadata gap.** Seed batches that hand off to AutoPilot needed to carry forward a marker indicating whether the seeding itself had been affected by an exogenous event.
4. **Atomicity assumption.** The journal-write needed to be crash-safe (WAL-style) so a mid-write crash didn't leave the archive half-updated and the planner reading garbage on the next start.

Each of these had to land in a specific order. The handoff documenting the work catalogues them as Phases 0 through 7, with Phase 7 being a one-time retroactive scrub of already-polluted historical entries.

## The mechanism that landed

Fleet markers and a process-startup journal close the loop. Every llama-server and the orchestrator API itself now write a marker to a shared file at startup containing the git SHA they're running, when they came up, and whether they were started by the orchestrator's stack management or by a manual operator command. AutoPilot reads the fleet markers when scoring a benchmark; if any backend's startup time is newer than the trial's start time, the trial is tagged `exogenous_retries` and either retried or routed to a journal entry that the planner specifically *does not* learn from.

The orchestrator's `/dashboard/api/version` endpoint returns the running git SHA so the markers can be cross-checked from outside. The `/dashboard/api/llama_fleet_ids` endpoint returns each server's `source=stack_commands` or `source=manual_reload` field, which is how AutoPilot tells "operator did this" apart from "stack lifecycle did this."

On the crash-recovery side, the experiment journal grew a WAL-style helper (`_maybe_reimport_pareto_from_journal`) that runs at AutoPilot startup. If the last journal entry indicates the previous run crashed mid-write, the Pareto archive gets rebuilt from the trustworthy entries — a clean replay rather than a corrupted continuation.

Phase 7 was the scrub. It walked entries from 2026-05-20 onward (when the resilience work was scoped) looking for quality-zero signatures that matched the exogenous-pollution pattern (specific timing alignment with known operator reloads, captured in the audit log). The scrub determined it was a no-op: AutoPilot had been down during all the implementation-window reloads, so no contaminated entries had been written during the implementation window itself. The retroactive cleanup wasn't needed for that window. It exists as a tool for any future post-incident cleanup.

## Tests, and the discipline they enforced

60 of 60 tests passed at the end of implementation. The notable property of those tests is that **half of them simulate exogenous events**. The test suite doesn't just verify the happy path; it explicitly verifies that the planner's behavior under a simulated operator reload is "tag the trial and don't learn from it." That's the kind of regression that's invisible in code review and only catchable in dedicated test cases.

This is a pattern worth surfacing as a general practice. For any agent that runs experiments against shared state, the *exogenous event* tests are at least as important as the *happy path* tests, because the exogenous case is where bad learning compounds invisibly.

## What it cost and what it bought

The commit chain ran from `89ecba3` (Phase 1) through `8b18f35` (Phase 6b), seven commits in epyc-orchestrator. The implementation took one focused day. The audit and the careful pre-implementation handoff took longer — two days of design back-and-forth across r1, r1.5 (external audit), and r2 revisions. The bug-fix-to-design ratio was ~1:3, which is roughly right for changes that touch a load-bearing learning loop.

What it bought, beyond the immediate pollution prevention: the same fleet-marker mechanism now powers a more general property. AutoPilot's journal entries are now *self-describing* about their reliability. The planner can ask "show me the trustworthy entries from the last 50 trials" and get an answer that excludes both exogenous-polluted trials and entries from before the resilience work landed. That self-describing property unblocks the [routing-classifier retrain](investigating-now.md) that depends on filtered telemetry to be tractable.

The deeper claim this story makes is about agent infrastructure as such. Production environments are shared. The agent that lives in one shares its substrate with operators, with other agents, with maintenance routines, with restart cycles. Any agent that learns from outcomes is also learning from *every operator action that happens to overlap with an evaluation window*. The discipline of distinguishing exogenous from endogenous failure is not optional once the agent is doing more than a few trials per day — it just shows up in slow, hard-to-debug ways without the discipline in place.

For deeper reading, [the autonomous research loop](autonomous-research-loop.md) describes AutoPilot's place in the broader pipeline; [SkillBank & Experience Distillation](../subsystems/orchestrator/15-skillbank-experience-distillation.md) is the chapter that documents the experience-distillation infrastructure that AutoPilot's findings feed into.
