# CF-3c active-evidence diagnostic

**Prospective · 2026-11-18 · CANDIDATE · bench.** The
[initial pilot](../research/cf3c-pilot-results-20261118.md) left two mechanism
questions open. Can each active production B2 threshold remove a target in
an older tool observation, and can A3 remove a target found only in older
assistant reasoning? The follow-up holds history length and target desk fixed
and changes where the answer appears.

## Cases and arms

Each case has ten archived assistant-tool interactions, with the target at
desk 2 in the old, stubbable region. With the pinned production pair
alignment, the middle section has 13 assistant/tool messages. The three
target locations are the tail of the target tool observation, the head of
that observation and the historical assistant reasoning field. The
reasoning-only case leaves the target tool observation without a receipt
field or decoy value. Other desks place their decoys in tool-observation
tails. The final user turn asks for the exact archived desk receipt from the
transcript and specifies `UNKNOWN` when absent.

The six arms retain the [initial pilot's policy definitions](cf3c-pilot-protocol-20261118.md).
A0 replays full history. A1-k4, A1-k8 and A1-k12 use the actual
`ContextCompressor` from orchestrator `12afe2858f9dbd4691447926d6cf1864de64348c`.
A2 truncates older observations to their first 180 characters and preserves
the three newest observations. A3 preserves the three newest historical
assistant entries and substitutes `omitted` in older nonempty reasoning or
text fields. All six policies make zero model calls.

| Target location | A0 | A1-k4 | A1-k8 | A1-k12 | A2 | A3 |
| --- | --- | --- | --- | --- | --- | --- |
| Old tool tail | Present | Absent | Absent | Absent | Absent | Present |
| Old tool head | Present | Absent | Absent | Absent | Present | Present |
| Old assistant reasoning | Present | Present | Present | Present | Present | Absent |

The table registers target visibility, separate from the eventual model
answer. Each A1 application must report six native compressor stubs. The
sealed runner checks the original target appears exactly once in the intended
field, then checks selected-history exposure and all message fields,
including system and final user text. It also checks native-render
head, tail and reasoning markers and the exact rendered target occurrence
count. A mismatch stops the window with instrument UNKNOWN. The three cases
each use one independently prepared seed shared across arms. Arm order
rotates by case index.

## Execution and reporting

Run the initial pilot's Qwen3.6-35B-A3B-MTP Q8_0 and frozen CMP-4 v10 CPU
recipe on four allocator-assigned physical cores with 52 GiB of RAM and an
isolated loopback listener on port 19380. The prior verified model receipt
binds the weight identity by stat and the serving binary, libraries and
template by digest. It supplies the original weight digest without rereading
model weights. The runner records linkage and listener ownership. Once per
cell, render and tokenize natively, then request one continuation at
temperature 0.3 with prompt caching and new reasoning disabled, historical
reasoning preserved, a 12,288-token allowance and a 96-token decode cap.
Reconcile completion usage with native preflight.

Publisher smoke runs the six real native renders and tokenizer calls on the
reasoning-only fixture and requests one A0 completion. Qualification
requires the target in A0, all A1 renders and A2, and its absence in A3.
Smoke records are outside the official matrix. The official row has a
3,600-second estimate and cap, a 3,300-second minimum window and a
180-second per-cell limit. It stops after 18 attempts or on the first
instrument failure, allocator STOP or deadline. A partial window retains
custody for each attempted cell.

Report each scheduled cell with activation, exposure, exact recovery,
abstention, NA or instrument UNKNOWN, non-termination, usage and wall time.
Report arm denominators over scheduled, attempted, graded and usage-bearing
cells. Literal `UNKNOWN` in a stopped completion is an abstention.
Budget exhaustion or an unexecuted tool request is NA. Evidence or
transport failure is instrument UNKNOWN. Separate server startup from
attempted-cell wall, which includes native template and tokenizer overhead.
The `epyc.cf3c.native.v1` record binds the cases, seeds, raw exchanges,
policy receipt, trajectory, build evidence and window digests.

The effect expected on these fixtures is a deterministic visibility change
and lower native prompt token counts where the policy removes text. Three
synthetic histories with one seed each support a mechanism and custody
diagnostic. The coverage predicate `completed >= 18` applies solely to that
diagnostic. Estimating retained quality within the parent's one-percentage-point
adoption margin requires separately powered workloads.
