# CF-3c native task-suite coverage shard

The source-backed shard's no-intervention result stops its frozen extension.
The separate [binding-continuation protocol](../../../docs/design/cf3c-binding-continuation-protocol-20261119.md)
defines a four-task scripted archive diagnostic. `binding.py` compiles that
cohort without model calls; `graph_trial.py` accepts its `initial_history` and
persists it through the source writer with real log-recovery offsets. The
existing `prepare.py` still prepares the original source-pool profile; publishing
the binding cohort requires a separate sealed profile and native publisher smoke.
Do not rerun the original extension to exercise this new seam.

This packet runs the pinned orchestrator's REPL graph from the original
benchmark prompt and context to its terminal or budget outcome. It compares
A0, A1 at k=4, 8 and 12, A2 observation truncation, and A3 removal of older
assistant reasoning. Each arm receives the same task and seed in a frozen
order. The graph starts with an empty task history and the model selects its
actions. The request intervention and evidence are specified in the
[task-suite protocol](../../../docs/design/cf3c-task-suite-protocol-20261118.md).

## Frozen scope

The source is the `core_v2.jsonl` text and vision pool already bound into
the CMP4 receipt. Its 50 distinct task IDs equal the union of the CMP4 draw
and reserve task IDs. The suite keeps the original prompt, context, format
requirements, grading data and metadata for each scheduled task. Existing
use in CMP4 is part of the provenance. Held-out status is unknown.

- `inventory.json` accounts for all 50 cases. Two cases require images
  and are outside the text execution scope.
- `cases.json` contains 48 unmodified text records. The frozen accuracy
  cohort contains 29 cases with exact, choice, F1, structural or
  programmatic local graders. The other 19 stay in the workload with named
  grade-unavailable reasons. Twelve are substring proxies, four need a
  bounded code grader, and three need an external judge. The isolated graph
  receives task inputs only. The pinned local scorer evaluates its terminal
  answer against the separate source grading data.
- `schedule.json` records the first 24 cells and the complete prospective
  text matrix of 1,152 cells. Each of four rounds includes all 48 tasks.
  Blocks pair all six arms under one task/seed. Seeds and arm order are
  generated from schedule seed `20261118` and the block identity. The
  first shard is the exact prefix of the full matrix.

The first shard covers IFEval formatting, LongCoT structured reasoning,
RULER retrieval and the oversized LongBench prompt. All 24 assigned
cells remain in the shard accounting, including early termination,
budget exhaustion and instrument failures. The packet uses no forced
CMP4 boundary, post-boundary BAPS eligibility, replacement point, or
accuracy-based retry. If the first shard shows no native A1/A2 history
changes or all tasks finish before a policy can intervene, stop scaling
this cohort. Retain its outcomes and freeze a binding-context cohort
prospectively before a wider run.

## Prepare and verify

Run this command from the umbrella checkout.

```bash
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -I -B scripts/experiments/cf3c-task-suite/prepare.py
```

Preparation checks the clean detached orchestrator worktree under the
scratch root, CMP4 source pool and draw, preserved GGUF custody receipt,
build and template. It hashes packet files and the small serving
artifacts. Model custody uses the retained SHA-256 receipt and file
identity, so preparation does not rehash the GGUF. The resulting scratch
packet is read-only. The launcher uses its `spec.json`, four allocated
physical cores, 52 GiB RAM and private port 19382. Publisher smoke runs the
LongCoT and oversized tasks in A0 outside the official cells. It requires a
completed LongCoT generation exchange on graph turn 2 or later with nonempty
selected history verified on the wire and server-reported prompt and
completion tokens. If a later exchange reaches the wall cap, LongCoT
retains its `NA` outcome and the interrupted exchange retains its incomplete
usage. The oversized task must exhaust the native context budget before
generation. The smoke confirms server exit and establishes instrument readiness.

The r2 instrument repair preserves the complete original shard schedule and
uses a separate scratch root. The original candidate stopped at task 06
when its custody guard rejected the trailing whitespace removed by native
chat serialization. Its outcomes and two failed qualification attempts
remain in the same lineage. The new shard repeats tasks and seeds exposed
in the failed official run and in qualification. Each run reports its own
outcomes, and the original task-06 UNKNOWN remains in the original record.

The experiment caps each task at 18 graph turns, 384 completion
tokens per call, 16,384 context tokens and 420 wall seconds. Native graph
continuations within one turn remain separately attributed generation
attempts and contribute to task cost. Any earlier
binding task cap produces the recorded budget outcome. The prior CMP4
four-core server logged 2,794 prompt tokens in 58.55 seconds and 83
decode tokens in 9.94 seconds on one call. At that prefill rate, 5,000
prompt tokens take roughly 100 seconds before decoding.
[CMP4 server trace](/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp4-r3/native/window-1c7_y332/server.log:17)

The 420-second limit can bind before the generation-count limit. The
10,800-second estimate and cap cover all 24 task wall budgets (10,080
seconds) plus 720 seconds for startup, recording and teardown. The
minimum grant is 10,500 seconds, allowing the row engine's 300-second
admission margin to reach the capped booking.

## Interpretation and prospective sizing

The first shard reports complete and incomplete task outcomes, local
correctness, token and wall cost, budget and nontermination counts, and
per-arm activation. An observed terminal answer with unavailable grading
remains an observed task outcome. Native custody/transport failure is
instrument UNKNOWN. The predicate `completed >= 24` measures coverage.
Four task clusters yield 25-percentage-point accuracy steps per arm.
The exploratory full matrix has only 29 distinct source cases with
deterministic grades and four nested sampling seeds per case. Independence
of source variants is unproven; case IDs alone do not establish independent
experimental units.

For the future one-percentage-point decision, fix the intended task
population, family weights, candidate cost comparison and simultaneous
one-sided accuracy bounds before running a confirmation set. Estimate
paired discordance and between-task variance from exploratory data
using task clusters and prespecified family weights. For each candidate
versus comparator, a binary paired loss has variance `q - d²`, with
discordance `q` and mean loss `d`. A planning approximation for the
effective number of independent pairs is
`(z[1-alpha*] + z[power])² (q - d²) / (0.01 - d)²` for a plausible
`d < 0.01`. Use conservative variance and loss scenarios. Select
`alpha*` to account for comparisons and the selection of the cheapest
arm against the best of six. Repeated seeds share task-level difficulty.
For `m` seeds and paired-loss intratask correlation `rho`, their
design effect is approximately `1 + (m - 1) rho`. Resolve shared underlying problem IDs and source variants before defining
independent clusters. Plan distinct task counts using the paired task-mean variance and confirm the clustered
interval design, with rare-discordance checks when asymptotics are weak.
Zero observed discordance in this shard gives little information about
a one-point margin. Missing grades and instrument outcomes require
prespecified handling and sensitivity bounds. This packet establishes
exploratory coverage, with adoption reserved for a powered decision
design.
