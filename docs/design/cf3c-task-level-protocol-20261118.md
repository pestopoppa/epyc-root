# CF-3c task-level continuation diagnostic

**Prospective · 2026-11-18 · CANDIDATE · bench.** The question is whether the
deterministic CF-3c policy interventions change correct completion, token
cost, wall time and non-termination in a live tool task that depends on old
evidence. The intervention starts from a fixed archived prefix. The task
environment uses direct structured chat with the pinned native implementation
and measures the work after the archive. The archived turns are constructed
fixtures, including the historical reasoning witness. Their generation cost
and production graph behavior are outside the measurement scope.

## Cases and arms

The sealed packet registers three synthetic reconciliation tasks, one paired
seed per task and six arms per seed. Each starts with ten archived desk
reads and a new request to release a named order. The order ID in the user
request identifies a local service record. A successful inspect call reveals
the relevant archive desk and a fresh challenge. A release call changes the
per-task service state only if preceded by a successful inspection and both
supplied values match the service record. The service then reveals the fresh
confirmation. The oracle requires both the released state and the exact
terminal string `RELEASED <confirmation>`. The inspect and release arguments
come from the model. Tool names and arguments are validated against a closed
local environment with no external side effects. Failure to find evidence
can yield an explicit `BLOCKED` abstention.

Each case has one literal receipt in a distinct older carrier. The challenge
and confirmation have no occurrences in the initial history or tool schema.
The task oracle tracks service state independently of message construction or
the rendered prompt. The runner freezes the task IDs, locations, desks, order
IDs, paired seeds and values before qualification. Arm order rotates by case,
and each task starts with a new service instance.

| Archived receipt | A0 | A1-k4 | A1-k8 | A1-k12 | A2 | A3 |
| --- | --- | --- | --- | --- | --- | --- |
| Desk 2 observation tail | Present | Absent | Absent | Absent | Absent | Present |
| Desk 3 observation head | Present | Absent | Absent | Absent | Present | Present |
| Desk 4 assistant reasoning | Present | Present | Present | Present | Present | Absent |

A0 preserves history. A1 uses the source-pinned `ContextCompressor` from
orchestrator `12afe2858f9dbd4691447926d6cf1864de64348c` with thresholds 4,
8 and 12. All thresholds produce six stubs at task entry and stay active on
subsequent growing histories. A2 preserves the newest three observations and
truncates older observations after 180 characters. A3 preserves the newest
three nonempty assistant text/reasoning entries and replaces older fields
with the pilot's `omitted` marker. These policies cost zero model calls.
Every preflight checks activation, original and retained evidence carriers,
ordered tool-pair custody and archived markers in the native rendering. The
runner records later appearances of the receipt, such as in a model-chosen
release argument, separately from archived exposure.

## Execution and reporting

Use the earlier diagnostic's pinned Qwen3.6-35B-A3B-MTP Q8_0 and
production-consolidated-v10 CPU recipe (build 10303, `ffc1bac82`), on four
allocator-assigned cores with 52 GiB of RAM and a private loopback listener on
port 19381. Reuse the model receipt by file identity, and verify serving
binary, libraries, template and source hashes or commit without opening the
GGUF for hashing. Record loaded linkage, CPU affinity and listener
ownership. Keep temperature 0.3, native tool parsing, historical reasoning
preserved, new thinking disabled and prompt caching disabled. Derive each
turn seed from the paired base seed plus turn offset.

Before every generation, record the full original messages, the exact
requested policy projection, native template response, tokenization, and
policy/exposure receipt. Reconcile native completion usage to prompt
tokenization and retain raw completion and executed-action responses. Each
task has a 12,288-token prompt-plus-completion context cap, 112 decode
tokens per turn, four generation turns and a 420-second wall budget. A tool
request on the final turn exhausts the turn budget and produces NA without
executing the action. Decode cap, context cap, task wall budget and an empty
terminal answer also surface as NA and increment non-termination. Model
abstentions and actual final answers are observed task outcomes. Instrument
failure is UNKNOWN and stops the official window. Allocator STOP or the grant
deadline stops the window and retains any partial evidence. Results are
written once per official attempt, with per-task and per-window digests.

Publisher qualification renders and tokenizes the reasoning-only case for
all six arms and executes the whole A0 old-head live continuation. It requires
the registered native exposure pattern, a correct terminal answer after two
or more actual tool calls and confirmation that the private listener exited.
Smoke records stay outside the official schedule and metrics. The official
estimate and cap are 8,280 seconds with a 7,980-second minimum window. At
terminal checkpoints the runner retains each trajectory and updates its
progress record. Stop on answer after all 18 registered tasks have observed
terminal outcomes. Stop on futility on instrument failure, STOP, the grant
deadline, or insufficient time to start the next task within its budget.

Report paired per-task outcomes and per-arm exact accuracy over observed
tasks, counting abstention and NA as unsuccessful. Report UNKNOWN and
unattempted counts separately. Count started generation requests and their
verified usage records. Report mean live tokens per task over observed tasks
with complete cost custody, and report incomplete counts and verified token
lower bounds separately. Report elapsed continuation
wall time including render, tokenization and local tools, with startup
recorded separately. The outcome schema is `epyc.cf3c.task.native.v1`. The
row predicate `completed >= 18` is a coverage check. It has no early success
look and no accuracy acceptance threshold.

Removing a fixture's only archived receipt is expected to reduce successful
release on that case. Successful task accuracy can move in steps of 33.3
percentage points per arm, so these three tasks cannot resolve the
parent's one-percentage-point adoption margin. A parent A/B requires a
representative, source-frozen task suite with multiple task families and
realistic context trajectories, and a prospective paired uncertainty and
sample-size plan for the accuracy margin and cost comparisons. Repeating
these same three cases with more seeds cannot supply task coverage. This
diagnostic supports instrument qualification and scoped descriptive
findings. It changes no production flags or defaults.
