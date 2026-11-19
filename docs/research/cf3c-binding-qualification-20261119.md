# CF-3c binding qualification: failed native recovery witness

`cf3c-binding-20261119` is **not qualified**. Publisher smoke observed the
preselected `binding_deep_v1/r0/A1-k12` cell on allocator CPUs 116–119 and
returned FAIL on 2026-11-19 at 00:11:30Z. The official 24-cell schedule has not
run. The original inactive source-pool extension remains idle.

The first native request had an active A1-k12 receipt: six observations
(turns -9 through -4) changed. The source writer retained ten observations and
bound both archive and verbatim-log digests. The model then returned an
incorrect answer on turn one, with **zero retrieval calls**, zero log-follow
attempts and zero log follows. This does not satisfy the predeclared successful
native recovery requirement. The qualification predicate correctly rejected it;
there was no transport/custody error and no instrument UNKNOWN.

Observed native usage was **3,429 prompt + 18 completion = 3,447 tokens**,
with complete exchange counters, no tokenizer fallback and **127.307 seconds**
per attempted task. The child exited and the private listener was removed.
Accuracy is higher-is-better; tokens and wall time are lower-is-better. This is
one qualification cell from four development task clusters, not a policy
comparison, noninferiority test or adoption result. Scripted construction cost
is excluded. No interim efficacy or population inference is justified.

The sealed cohort digest remains
`14c79e10bade5909a5406b86ea72d91e44b66f830859044639b0c9c622cb5cc3`;
packet inputs SHA-256 is
`b28aa4492a8141da9761b67c133c1b898b6048d19d95c890e3b3e62626da5cf8`.
Source: orchestrator `12afe2858f9dbd4691447926d6cf1864de64348c`.
The [verdict record](cf3c-binding-qualification-20261119.json) binds existing
native files by path and SHA-256; it contains no copied raw logs or source.

Stop this candidate at the failed qualification. Preserve its fixed schedule
and failed outcome; do not rerun or replace its task to obtain a PASS. The next
code task is to separate an explicit, prospectively specified native recovery
instrument control from the unchanged quality task schedule, with refusal
controls proving that qualification cannot select for task correctness. Any
changed probe requires a new profile/version and the existing failure remains
visible. CF-3c-B2 remains open because successful recovery qualification and the
official 24-cell result are absent.

Software validation: **28 existing native/corpus/binding tests and four new
profile refusal tests passed**. Existing tests used the retained binding source
worktree because the superseded suite-r2 source worktree has been reclaimed.
Ruff, shell syntax and diff checks passed. These checks establish software
behavior separately from the failed native qualification.
