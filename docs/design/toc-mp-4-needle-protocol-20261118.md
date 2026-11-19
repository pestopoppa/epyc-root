# TOC-MP-4 exact-value recall screen

Prospective diagnostic protocol, 2026-11-18. Owner: context-and-token-economy,
TOC-MP-4. This screen does not amend CMP4 eligibility, enable production flags,
or substitute for the full compaction A/B.

Question: does pointer-only preserve exact-value recall at least as well as
summary-plus-pointer on the same synthetic REPL tasks and sampling seeds?
Higher exact-value recall is better. The candidate decision is deliberately
narrow: pointer-only recall >= summary-plus-pointer keeps arm 3 as a candidate
for the full A/B; lower recall records the miss pattern and fires M-MP2.
The screen does not establish population superiority, equivalence, or safety.

Freeze twenty cases with distinct random 24-character answer values before
publication. Freeze two sampling seeds per case and pair them across
`summary_only`, `summary_pointer`, and `pointer_only`: 120 scheduled graph
trajectories, no replacements. Record the actual arm order in the sealed packet.
Use the registered frontdoor Qwen3.6-35B-A3B-MTP-Q8_0, frozen v10 CPU kernel,
registered template and source-pinned isolated orchestrator. All arms use
C = 16,384 tokens, a 20% recent tail, and the same fixed boundary turn(s).
The packet records the exact boundary schedule and fixture bytes.

Expose each value once through an early tool output exceeding 4,000 characters.
The value must not appear in the task instruction or persistent REPL context,
variables or readable fixture files after that exposure. Preserve it in the
verbatim log; pointer retrieval from that log is the intended mechanism.
At the first post-boundary request verify that the early raw turn is excluded
from the recent tail. Summary retention is allowed in summary arms and is not
itself a leak. Missing boundaries, a retained raw needle, incomplete generation,
ambiguous request/turn binding, source leaks, and missing tokenizer or wire
custody yield UNKNOWN eligibility with an explicit reason. They must not become
successful recall or silently disappear from denominators.

Score the exact submitted final answer only, with no judge, substring credit,
normalization or answer extraction from reasoning. Record a valid incorrect or
missing final answer as failure. Report scheduled, completed, eligible, correct,
incorrect and UNKNOWN counts separately for every arm, including paired counts.
Apply the candidate decision only when all 120 scheduled outcomes have valid
fixture/transport custody and an exact score. Otherwise report the decision
UNKNOWN and retain the observed grades descriptively. No selection by answer
correctness, optional stopping, or replacement of difficult cases is permitted.

This is a finite diagnostic census. Forty trials per arm have 2.5 percentage
point score resolution; paired task/seed outcomes are dependent, and the screen
is not powered for a population MDE or equivalence margin. A tied diagnostic
score preserves a candidate; it does not establish equivalence. Record task-level
paired discordances and the literal numerator/denominator beside any rate.
The expected mechanism is successful log retrieval without a summary; its
population effect size is unknown. Even an independent 40-trial Bernoulli arm
would have a worst-case standard error of about 7.9 percentage points. Task
repetition violates that independence assumption, so this scale illustration
supplies neither a confidence interval nor evidence that a small difference is
real. There is no interim arm decision: stop on the fixed matrix or an instrument
failure, and leave any incomplete eligibility decision UNKNOWN.

Publisher smoke is instrument qualification only: one real generated-summary
trajectory through a boundary and continuation, native wire capture and clean
server exit. It cannot count toward the official matrix. Checkpoint completed
native trials after every unit; resume only the same sealed packet and preserve
all prior attempts. Stop on the fixed matrix, allocator STOP/deadline or row cap;
preserve partial results. An infrastructure or custody failure stops the cell
without a relaxed completion predicate or a new seed. No in-turn long inference:
only the publisher smoke may execute here; official trials require a row grant.

Native custody must include the source/model/template/kernel and packet digests,
actual allocated affinity, tokenizer identity without heuristic fallback, case,
arm, repeat, seed and boundary schedule, original requests/responses, native
trajectory, one-shot-source and tail-exclusion witnesses, exact final answer and
grade, timing and incomplete/failure dispositions. The existing TOC source
projection owns eventual belief integration; no new grading ladder is introduced.
