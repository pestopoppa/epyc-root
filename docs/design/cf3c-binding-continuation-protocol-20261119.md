# CF-3c binding archive continuation

This prospective diagnostic answers whether deterministic observation policies
change native graph requests when eligible old observations are present, and
how the model recovers a requested receipt after those observations are removed.
It follows the [inactive task-suite result](../research/cf3c-task-suite-results-20261118.md).
The original 1,152-cell extension stays idle under its registered futility rule.

## Fixed cohort and provenance

[`binding.py`](../../scripts/experiments/cf3c-task-suite/binding.py) compiles four
scripted archive tasks: a head receipt, a deep receipt, two deep receipts joined
in order, and a superseding release receipt. Each has ten observations and one
paired seed across A0, A1(k=4,8,12), A2 and A3, for 24 cells. The compiler fixes
task identities, values, output geometry, grading data, arm order and seeds
without model calls or previous outcome inputs. No original benchmark tasks
are replaced. These are development fixtures with four task clusters, not
independent samples from production traffic or held-out confirmation data.

Compiler seed: `cf3c-binding-20261119-v1`.
Canonical cohort digest (the object excluding its own digest field):
`14c79e10bade5909a5406b86ea72d91e44b66f830859044639b0c9c622cb5cc3`.
Generated file: `/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-binding/cohort.json`,
SHA-256 `8027aa45726a8930861c42a7e1cf5fa3c2b43af143ca8008b7c34ba1af59bf93`.
The compiler uses exclusive creation; a changed cohort needs a new version.

## Native seam and cost boundary

The experiment uses orchestrator source
`12afe2858f9dbd4691447926d6cf1864de64348c`. The experimental harness supplies
`initial_history` as task input and calls the source `record_turn` writer before
graph execution. Scripted turns use labels -10 through -1, preserving the live
graph turn counter and its full live-turn allowance. They are explicitly
scripted inputs; neither execution of their code nor model generation of their
content is claimed. Construction cost is excluded from continuation costs.

The source writer creates real UTF-8 byte and character offsets in the private
REPL's verbatim log. All arms receive the same full-log `peek()` pointer.
The native renderer registers that artifact with the existing read boundary.
The parent retains the answer oracle outside the child input and REPL scope.
The child receives only prompt, archive, optional context and paired row identity.
Existing original/sent native request capture and per-generation policy receipts
remain authoritative for intervention custody. The new initial-history receipt
binds the archive and written log digests and states the construction-cost boundary.
A3 remains an inactive control because this graph has no separate historical
reasoning carrier. No reasoning text is invented to activate it.

## Execution and decision rule

This change implements and tests the compiler and native archive seam. It does
not publish or run a new row. A separate, sealed binding profile must point at
these four cases rather than the old source-pool schedule and must qualify
native intervention and log recovery through publisher smoke before execution.
Keep the source-backed task-suite profile and its old results separate.

The prospective row uses Qwen3.6-35B-A3B-MTP Q8_0 and the v10 production kernel
receipt, an isolated listener, four allocator-assigned physical CPU cores and
the existing 16,384-token context, 384 completion-token cap, 18 live-turn cap
and 420-second task allowance. Seal its launcher, serving receipts, native
tokenization checks and smoke conditions before publication. Allow 10,800 seconds
for 24 task allowances plus startup/teardown. Smoke must exercise one active
A1-k12 request and a native recovery tool call, verify exact selected-history
custody and private-server teardown; offline activation alone is insufficient.

Stop on answer after the 24 fixed cells; stop on futility at the first custody,
transport, allocator STOP/deadline or wall-cap failure. No retries, replacements
or automatic extension. Preserve early terminals, NA, instrument UNKNOWN and
incomplete-usage lower bounds with their original denominators. Coverage is
`completed == 24`; report activation separately, including each arm's first
native generation. Any absent A1/A2 intervention blocks scale-up. Retain
inactive outcomes rather than treating them as evidence of policy equivalence.

Report exact task accuracy (higher is better), native tokens/task and wall/task
(lower is better), per-arm activation, log recovery calls, explicit nontermination
and incomplete-cost counts. Paired differences are descriptive. Four task clusters
give 25-percentage-point accuracy steps per arm; this cannot resolve a one-point
noninferiority margin. Formal gate interim looks remain futility-only. Do not
choose or adopt a production policy from this diagnostic; confirmation still
needs the parent's population, simultaneous interval and sample-size design.

## Offline validation

The combined corpus, wire and binding controls pass **28 tests**. They cover
deterministic pairing and oracle separation, all A1 thresholds and A2 activation,
A0/A3 preservation, head versus deep exposure, source-writer byte offsets,
archive immutability, malformed input refusal, repeat-install refusal, and a
real trial bootstrap whose masked receipt is recovered through native `peek()`
while a sibling grading-oracle file is refused. This establishes software
behavior only; no model quality, token savings or native qualification result
is claimed.
