# Dive A-inbox-outbox (intake run always-on-1124, 2026-11-24)

Stage-2 deep dive. Sources were read from the retained anchor snapshots through the machine_anchor extractor; every anchored quote is an exact substring of that text and carries a script-written anchor_mark in the index. In-house reads at epyc-root 3b11e6c82 (no drift to a290df6 on the cited files) and epyc-inference-research 82d5822.

## intake-2942: Building always-on agents (William Hu, Anthropic, 2026-11-13)

- URL: https://claude.com/resources/articles/building-always-on-agents
- Read depth: FULL
- Verdict: adopt_patterns; relevance high; credibility 3

| # | Claim | Status | Locator |
|---|---|---|---|
| 0 | Event sources never call the agent directly; they append to a durable inbox that a worker drains, because direct calls cause competing runs and lost events on crash. | CONFIRMED | Event inbox |
| 1 | The inbox is the source of truth, so a replacement worker can retry an event after the first worker dies mid-run. | CONFIRMED | Event inbox (best practices) |
| 2 | An inbox has exactly one active worker at a time; inboxes are split (one per user by default) only for parallelism. | PARTIAL | Event inbox (best practices) |
| 3 | Events can be deduplicated by unique source identifiers and the inbox tracks per-event status. | PARTIAL | Event inbox |
| 4 | A mid-run event is pushed to the next run, folded into the current run, or interrupts and restarts it; pending events are batched. | CONFIRMED | Event inbox (best practices) |
| 5 | Timers live in their own durable store; a scheduler finds due timers, marks follow-ups done or advances schedules, then adds an event to the inbox. | CONFIRMED | Timers |
| 6 | A deferred tool call ends the run and saves the session mid-call; the answer comes back as an inbox event that starts a run resuming that session. | CONFIRMED | Permissions (Deferred tool calls) |
| 7 | Memory belongs on durable storage that outlives the worker. | CONFIRMED | Memory |
| 8 | Each ongoing task keeps a progress file; any new run reads it and continues from where the previous run stopped. | CONFIRMED | Memory (Task progress) |
| 9 | Compaction and new sessions both lose detail, so anything that must persist is written to memory during the run. | CONFIRMED | Inside the context window |
| 10 | A formal outbox and dispatcher are needed only to pace messages or recover from errors; a send tool is enough otherwise. | CONFIRMED | Outbox |
| 11 | Agents should start quiet and earn attention, tuned with evals. | PARTIAL | Outbox |
| 12 | Opus 5.5 cost 78% less per solved task than Opus 5 on one long-horizon coding benchmark. | PARTIAL | Introduction |

Claim notes:

- [0] Rationale is two named failure modes only; no measurement.
- [1] No retry cap, attempt count or dead-letter state is given.
- [2] Narrowed: no lease, expiry or fencing of a stuck or dead worker is described; independent sources (intake-2951, intake-2952) supply lease claims and at-least-once plus idempotent effects.
- [3] Says can, names no status vocabulary and no idempotency for downstream side effects.
- [4] Options listed without a recommendation or measurement.
- [5] Durable execution engines are named as an alternative to a hand-built scheduler.
- [6] No timeout or reminder for an unanswered deferral is given (intake-2950 adds a timer per parked question).
- [7] Design guidance only.
- [8] Assumes the run writes progress along the way, not only at a final wrap-up.
- [9] No numbers.
- [10] A run ends in one of three ways: send, nothing to send, deferred call.
- [11] Assertion without data; the eval is not specified.
- [12] Vendor self-report on an unnamed benchmark (link only); no n, cost definition or configuration. Not usable as evidence.

Dive record: 2026-11-24 Stage-2 wave 1 (dives A and D, sonnet, FULL read from the retained snapshot): 13 claims; 9 CONFIRMED, 4 PARTIAL (single worker has no lease; dedup optional and stops at the inbox; start-quiet unsupported; the 78% Opus cost figure is a vendor self-report on an unnamed benchmark). Independent corroboration of the inbox shape and fast ack: intake-2952 (2020, pre-agent) and intake-2951. Live-lesson tests: L1 agrees (deferred call and progress file both make every run end resumable); L2 and L3 agree as a pattern (one inbox, one worker, everything through it is the single-reservation shape; rowflow.py L8405-L8428 @ 3b11e6c records five patch rules a shadow reservation planner subsumes); L4 silent; L5 silent.

Contradicting or limiting evidence:

- No worker lease or expiry: intake-2951 (lease-style claims, dead-letter state) and intake-2952 (at-least-once delivery needs idempotent effects) show one active worker plus dedup is under-specified.
- intake-2950 (RAZ critique) reports, without a linked source, that vendor webhooks are dropped after three tries and deferrals have no timeout, so the inbox and a follow-up timer must be owned by the builder.

## intake-2950: An always-on agent is mostly asleep. So what's awake? (RAZ Team, 2026-11-16)

- URL: https://www.realaization.com/blog/an-always-on-agent-is-mostly-asleep-so-what-s-awake
- Read depth: FULL
- Verdict: worth_investigating; relevance medium; credibility 1

| # | Claim | Status | Locator |
|---|---|---|---|
| 0 | Anthropic's hosted-agent webhook docs say a delivery is attempted three times and then dropped without a signal. | PARTIAL | The inbox |
| 1 | A filter in front of the inbox sets much of the cost; in one report 41 of 645 alerts reached the agent. | PARTIAL | The inbox |
| 2 | Models are poor clocks: on AgentTime one model stopped at about the right moment in 4% of runs and the best in 63%. | PARTIAL | The clock |
| 3 | A fifteen-minute check used 103.7 million tokens in ten days because the cache lapsed between wakes. | PARTIAL | The clock |
| 4 | Every parked question needs a follow-up timer so that silence also becomes an event. | CONFIRMED | The parked question |

Claim notes:

- [0] No URL or version for the docs; unverified secondary report.
- [1] No named source; anecdote.
- [2] Benchmark named but not linked; checked against the paper in intake-2953.
- [3] One uncited developer anecdote.
- [4] The critique's own contribution; intake-2942 offers timers but does not tie them to deferrals.

Dive record: 2026-11-24 Stage-2 wave 1 (dive A, sonnet, FULL): 5 claims, 1 CONFIRMED, 4 PARTIAL. None of its numbers has a linked primary source; its design points stand on their own logic. Live-lesson test: L1 adds a follow-up timer per parked question; our session bus already redelivers an unacknowledged requires_ack message as a nudge (BUS_PROTOCOL.md L28-L31 @ 3b11e6c), but nothing produces a resume event for a worker that ended early. The AgentTime figure was taken to wave 2 (intake-2953). Wave 2 (intake-2953) checked the AgentTime figures: exact, but they measure duration-following. Dive-surfaced sources: AgentTime and TicToc ingested in wave 2 (intake-2953, intake-2954); Anthropic hosted-agent webhook documentation declined (no locator in the post, and its conclusion that the builder must own the inbox is independently supported by intake-2951 and intake-2952).

Contradicting or limiting evidence:

- No primary source is linked for any number.

## intake-2951: Webhook Inboxes for AI Agents That Do Not Duplicate Side Effects (Anirudh Negi, 2026-05-29)

- URL: https://negiadventures.github.io/blog/webhook-inboxes-ai-agents.html
- Read depth: FULL
- Verdict: adopt_patterns; relevance medium; credibility 2

| # | Claim | Status | Locator |
|---|---|---|---|
| 0 | Acknowledge after durable intake, not after the work completes. | CONFIRMED | Pitfalls and best-practices |
| 1 | Use explicit states and lease-style claims with an expiry; a row whose lease expired can be claimed again. | CONFIRMED | Implementation details 2 |
| 2 | Inbox dedup is necessary but not sufficient; downstream effects need idempotency keys. | CONFIRMED | Implementation details 3 |
| 3 | Expiring-key dedupe alone is fragile. | CONFIRMED | Tradeoff table |

Claim notes:

- [0] Agrees with intake-2942's fast acknowledgement.
- [1] SQL sketch with claimed_by, claimed_until and attempt_count; no tests or production data.
- [2] Adds what intake-2942 omits.
- [3] Assertion without measurement.

Dive record: 2026-11-24 Stage-2 wave 1 (dive A, sonnet, FULL): 4 claims, all CONFIRMED (design sketch, no data). Live-lesson test: L2 is already covered for expiry. The dive first read our light claim's expiry as advisory; main review overturned that: reap_build_grants ends every build or light grant past its end= on the keeper tick (rowflow.py L6771-L6787 @ 3b11e6c), and the advisory rules are only the nice/taskset usage contract (L6455-L6457). The real gap was that claims never consulted the planner (rowflow.py L8419, root cause E), which the reservation addresses.

## intake-2952: Outbox, Inbox patterns and delivery guarantees explained (Oskar Dudycz, 2020-12-30)

- URL: https://event-driven.io/en/Outbox_Inbox_patterns_and_delivery_guarantees_explained/
- Read depth: FULL
- Verdict: already_integrated; relevance medium; credibility 2

| # | Claim | Status | Locator |
|---|---|---|---|
| 0 | The inbox first saves the event and then acknowledges the queue; an outbox-like process runs the handlers later. | CONFIRMED | Inbox Pattern |
| 1 | At-least-once delivery means consumers must defend themselves with idempotency. | CONFIRMED | Delivery guarantees |
| 2 | A per-consumer offset row enables locking and competing consumers, with ordering held only within a partition. | CONFIRMED | Outbox Pattern (parallelisation) |

Claim notes:

- [0] Independent, pre-agent source; corroborates intake-2942's inbox shape and fast acknowledgement.
- [1] intake-2942 never states a delivery guarantee.
- [2] The general form of intake-2942's inbox per user.

Dive record: 2026-11-24 Stage-2 wave 1 (dive A, sonnet, FULL): 3 claims, all CONFIRMED. Independent corroboration of intake-2942, adding the at-least-once contract it omits. Live-lesson test: L2 agrees; the session bus is already this design, so it needs no change.

