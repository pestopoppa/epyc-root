# TOC-MP-4 exact-value diagnostic

[Prospective protocol](../../../docs/design/toc-mp-4-needle-protocol-20261118.md)
and [arm design](../../../docs/design/toc-mp-ab-design-20261031.md).

`python3 -B scripts/experiments/toc-mp-4-live/prepare.py` seals the packet under
`/mnt/raid0/llm/tmp/delegation-context-preassembly/mp4/packet`. It checks the
retained CMP-4 r2 model receipt and the current GGUF file identity and rechecks
the CPU kernel and template digests. Model weights are never reread. The
orchestrator source is a clean detached worktree at the frozen CMP-4 base.

Twenty 96-bit synthetic receipts and two sampling seeds per case are generated
once and sealed. Each seed is paired across the three arms. The first REPL
action invokes a one-shot Python helper that prints a 24-character receipt
near the start of a 5,250+ character record, then discards its input. The
second action prints a checkpoint padded with a different repeated token
sequence. The graph forces the only boundary at turn 3 with C = 16,384 and a
20% recent tail. The judge checks the actual served continuation and native
tail state as well as the exact REPL submission. A generated summary may
retain the receipt. The pointer arms may recover it from the native verbatim
log. The fixture observes pre-boundary state for persistent variables or
artifacts, and uses stdin for the helper input. The value is absent from the
task and REPL context.
The tail audit samples native state and request scope at the forced-boundary
generation call, including when the model emits no REPL code on that turn.
Assessment requires the witness and independently checks the served continuation.
The trial uses a read-only request scope rooted at a fresh directory with no
additional read roots. The native verbatim log is readable through its
per-task file capability. The parent fixture, packet case file, raw input
receipt and stdin descriptor are outside the REPL request scope.

The private loopback listener uses port 19369 and four allocated CPU cores,
the CMP-4 Qwen3.6-35B-A3B-MTP-Q8_0 serving recipe and OpenClaw boundary
summary. The booking estimate assumes 650 seconds per cell, including summary
generation when assigned, with a 7,200-second window cap and 1,150-second
per-cell cap. These are planning bounds. Publisher smoke uses the first
summary-plus-pointer row, requires the real summary and a native log read that
returned the needle in a turn before an exact FINAL, and checks the listener
exited. Its artifacts are kept outside the official matrix.

Every official cell receives one immutable native directory and receipt.
Resume verifies the packet and previously recorded file digests and skips all
reserved cells. A cell interrupted without a final receipt becomes UNKNOWN
with its partial files preserved. A keeper deadline that burns the row ID
can be resumed via a new row `-rN` with its own allocator STOP path. Keep
pointing at the original sealed runner and matrix. After an ended partial
grant, run `python3 -B scripts/experiments/toc-mp-4-live/prepare.py --next-round 2`
to prepare a successor spec and launcher under `mp4/rounds/`. Subsequent
rounds use the next integer. The helper does not publish. There are no automatic
replacements, retries or new seeds. Stop on the fixed matrix or keeper
STOP/deadline. The allocator also bounds each window.
An instrument failure stops its window after saving the affected receipt.
A model finishing before the forced boundary or hitting a generation token
limit receives an UNKNOWN grade.

The [first cohort's disposition](../../../docs/research/toc-mp-4-results-20261118.md)
records the instrument stop at cell 000. Its frozen UNKNOWN receipt makes the
120-eligible decision threshold unreachable, so that cohort ended inconclusive.

The native result reports scheduled, recorded, completed, eligible, correct,
incorrect, UNKNOWN and unattempted and includes task/seed discordances.
All 120 grades must be eligible before the pointer-only recall comparison.
A tie retains pointer-only as a full-A/B candidate. Lower pointer-only recall
fires M-MP2. An incomplete eligibility matrix leaves the decision UNKNOWN.
