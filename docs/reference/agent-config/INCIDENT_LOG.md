# Incident Log — origin narratives behind agent-file rules

House style (operator directive 2026-07-30): every negative/incident-derived rule in the agent
files keeps its directive plus a one-line origin pointer (`origin: INC-<id>`); the full
narrative lives here. Rules cite entries; entries never carry rules.

## INC-20260706-iqk-missing-subsystem
The GPU-opts branch forked from v6 on 2026-06-22; the iqk port landed on production 2026-06-25.
Because the fresh-pull step was skipped and the branch never re-synced, it silently lacked the
entire iqk subsystem (0 of 8 `GGML_IQK` references) while on track to "become v7" — a candidate
kernel missing a core CPU-performance subsystem. Discovered and rectified 2026-07-06. Rule fed:
CLAUDE.md § Experimental Kernel Workflow step 1 (always fork from current production tip; full
experimental build before promotion).

## INC-20260727-stale-heartbeat
A live session's heartbeat was 2h stale while it was mid-generation; the stall ladder read it as
a stall and only a second signal prevented a spurious nudge of a healthy agent. Rule fed:
refresh the heartbeat at every task boundary (CLAUDE.md § Agents & Automation;
`agents/coordinator-agent.md`).

## INC-20260728-reload-preemption
Two external API-only reloads (16:26:13Z and 16:40:48Z, the latter spawning uvicorn parent PID
3879640) landed during codex's explicitly protected live E8 q3 collection, crossing in-flight
ordinals 246/249/250 and 279/281/282 and forcing their regeneration. Codex owned that
inference; the reloads should have been requested of it. A structural fix (reload path failing
closed while a protected bench region claim is active) was filed by codex, not yet assigned.
Rule fed: reload ownership (`agents/shared/OPERATING_CONSTRAINTS.md` § Inference and
Benchmarks).

## INC-20260728-ctrlc-destroyed-main
A coordinator sent a ~2000-char dispatch via raw `tmux send-keys`, bypassing the chunking
adapter; it blobbed into two paste fragments. Attempting to clear the buffer it sent `Ctrl-U`,
`Ctrl-C`, `Ctrl-U`, `Ctrl-C` — the second `Ctrl-C` exited Codex and destroyed the
`codex-bus-tests` main, despite `Ctrl-U` alone having already worked earlier the same session.
No work was lost (commits were pushed), but a live main was destroyed to fix a cosmetic
problem, consuming a spawn-capped resource — and a subagent had been commissioned minutes
earlier to characterise exactly this TUI empirically in disposable sessions. The method was
available and self-authored, and was not used. Rules fed: TUI keystroke safety
(`agents/shared/OPERATING_CONSTRAINTS.md` § Dangerous Operations;
`agents/coordinator-agent.md` Guardrails).

## INC-20260728-unread-inbox
The coordinator's cursor sat at offset 63627 while 33 messages accumulated unread — among them
codex reporting a hard block on the critical path requiring an operator signature, a completed
contract audit with two CRITICAL fail-open defects, and three daemon boundary notices that
codex had gone idle. Every piece of delivery machinery worked; the coordinator never read the
inbox, and the operator had to find, unaided, a ratification request and an audit report
already sitting in it. Rule fed: DRAIN BEFORE YOU SPEAK (`agents/coordinator-agent.md`).

## INC-20260728-idle-mains
While the coordinator wrote governance docs on its own main thread, the codex-bus-tests and
claude-gpu-lane mains both went idle with empty queues and the operator had to point it out.
Rule fed: coordinator main thread stays free for coordination; an idle main with an empty queue
is a coordination failure (`agents/coordinator-agent.md`;
`agents/shared/SESSION_LIFECYCLE.md`).

## INC-20260728-cleared-context
A bus-testing main was cleared between two neighbouring bus-defect tasks, discarding directly
relevant context; the same day a combined "wrap-up, then /clear, then read X" nudge lost its own
follow-on instruction to the clear. Rules fed: `/clear` requires wrap-up AND disjoint next task;
never share a nudge with the task that follows a clear (`agents/shared/SESSION_LIFECYCLE.md`).

## INC-20260728-heartbeat-bypass
`claude-gpu-lane` finished a review and sat idle awaiting an answer while its heartbeat still
read `working` (~8094s stale); the adapter correctly refused a nudge twice, and the coordinator
bypassed it with raw `tmux send-keys` instead of escalating. Rule fed: guard-refusal escalation
ladder (`docs/guides/agent-workflows/coordinator-escalation.md`).

## INC-20260729-rate-limit-respawn
During post-reboot bringup, re-spawned mains were unreachable until the nudge rate limit
inherited from their destroyed predecessors expired — the limit keys on roster id, not window
instance. Rule fed: the narrow lower `--min-interval-s` exception
(`docs/guides/agent-workflows/coordinator-escalation.md`).
