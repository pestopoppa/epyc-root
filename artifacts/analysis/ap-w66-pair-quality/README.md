# AP-W66-PAIR output review

Judgments apply the [pre-replay rubric](rubric.md) to each target's visible text and complete tool proposal. The [input reconstruction](input-state.json) pins the original task state. The run directory is `/mnt/raid0/llm/tmp/ap-w66-pair-20261127-r2/out/run`. Recompute the stream custody and input match on the EPYC host:

```shell
python3 -B artifacts/analysis/ap-w66-pair-quality/review_streams.py /mnt/raid0/llm/tmp/ap-w66-pair-20261127-r2/out/run
```

The checker verifies the original input hashes, the actual request body hash and the terminal stream hashes. It excludes fixed-length timing controls. The quality review uses no generated tool effects. Read-only actions and edits receive credit for the proposed next step only. The underlying DS41-W-66 fixture repair remains unverified across all replay outputs.

## Per-target judgments

| Target | Trial | Arm | Immediate turn | Evidence |
|---|---:|---|---|---|
| ON 28 | 1 | Alone | Rejected | The proposed `edit` applies to the in-turn fixture and preserves non-receipt assertions. It looks up `result["store"]`, which is absent from the pinned `loop-run.json` writer. The callback receives that document through `test_existing_cpu_run.py` and the lookup would raise `KeyError` before the intended check. |
| ON 28 | 1 | Peer | Accepted continuation | Two scoped `grep` proposals investigate how `run.py` constructs the continuation. Searching for the continuation key locates the call to `serial_run.continuation` and its argument source, which is actionable for finding the actual fixture store. |
| ON 28 | 2 | Peer | Rejected | The proposed exact edit parses, but it treats a locator basename as a path relative to the process directory. The receipt is under the private store, so the proposed lookup cannot reach it. |
| ON 28 | 2 | Alone | Partial | The exact edit preserves the assertions and derives the expected proof path from the actual `--store` argument. The historical fixture write appends `runtime-preparation` to an artifact store already rooted there. The proposal leaves that write one directory too deep and cannot fetch the actual receipt in this state. |
| OFF 56 | 1 | Alone | Substantively accepted summary | Carries the required scope, tests, per-selection receipt changes, current callback identity failure, and the exact-receipt assertion and test rerun as next steps. It conflates the earlier missing-file error with the later journal mismatch. The current failure and recovery state remain clear. |
| OFF 56 | 1 | Preserved | Partial | Accurately locates the pending receipt assertion and offers capturing the real reference. It also instructs the next agent that a shape-only locator or digest check is acceptable. That option can accept a substituted reference and violates the original assertion-preservation requirement. |
| OFF 56 | 1 | Peer | Partial | Summarizes the present failure and includes the exact-reference comparison as one next move. It offers using the old fixed locator as an alternative. A fixed locator still cannot satisfy the literal fake digest, and overwriting it across selection events can defeat receipt identity. |
| OFF 56 | 2 | Peer | Substantively accepted summary | Preserves the pending exact-identity assertion and directs the next agent to capture the actual reference and rerun both tests. It mentions manufacturing the old digest, marks that impractical, and reiterates the correct continuation. |
| OFF 56 | 2 | Preserved | Substantively accepted summary | Preserves the receipt-writing and cache diagnosis, the currently failing equality check, and the need to match the actual locator and digest from the store before running both tests. It supplies no shape-only alternative. |
| OFF 56 | 2 | Alone | Partial | Finds the correct callback failure but proposes shape-only checks as a substitute for exact identity and omits rerunning both tests from its next actions. |
| OFF 52 | 1 | Alone | Accepted continuation | Traces initial anchor and retained candidate calls independently, then proposes an exact edit that writes the freshly selected receipt on the no-origin path used by both calls in the fixture. The preexisting callback equality still needs follow-up. |
| OFF 52 | 1 | Peer | Accepted continuation | Proposes an exact, assertion-preserving fixture diagnostic to confirm that `retain` runs with the anchor and returns the candidate. It is a useful narrower step and leaves the cached receipt issue unresolved. |
| OFF 52 | 2 | Peer | Rejected | Diagnoses stale memoization in prose. Its exact edit still writes the anchor when the cache is empty and returns that same cached receipt for the retained candidate. The tested mismatch would remain. |
| OFF 52 | 2 | Alone | Accepted continuation | Replaces the cached fixture path with per-selection content-addressed writes. The exact edit parses and preserves every non-receipt assertion. The callback still needs its real-reference assertion. |
| ON 29 | 1 | Alone | Accepted continuation | Requests a read of the allowlisted fixture immediately after the callback edit. This scoped verification can confirm the applied receipt path and assertions. It is the same next action as the recorded successor. |
| ON 29 | 1 | Peer | Accepted continuation | Requests the same scoped read as the isolated arm and the recorded successor. |
| ON 29 | 2 | Peer | Accepted continuation | Requests the same scoped read as trial 1. |
| ON 29 | 2 | Alone | Accepted continuation | Requests the same scoped read as trial 1. |
| ON 29 | 3 | Alone | Accepted continuation | Requests the same scoped read as trial 1. |
| ON 29 | 3 | Peer | Accepted continuation | Requests the same scoped read as trial 1. |

## Comparison

The review covers 20 natural target outputs. Ten were accepted continuations, three were substantively accepted summaries under the frozen rubric, four were partial, and three were rejected. The six fixed-length timing targets were excluded. The 20 natural streams all finished with a tool proposal or a stop.

- **OFF 56 preservation.** The original-input arm was substantively accepted and the preserved arm was partial in trial 1. The verdicts reversed in trial 2. Each arm produced one substantively accepted summary in two trials. The shape-only branch was a material omission whenever it appeared. The observations establish neither a repeatable quality loss nor equivalent quality.
- **OFF 56 strict format.** All six summaries included literal `<template>` wrappers, which the request explicitly prohibited. Zero of six fully complied with the requested format. [Output custody](output-custody.json) records `strictformat_compliant` as `false` for each. The frozen rubric assesses substantive acceptance separately.
- **OFF 56 overlap.** The peer arm and the original-input isolated arm also switched dispositions across the two trials.
- **ON 28.** The peer arm improved from a broken edit to a useful source lookup in trial 1 relative to the isolated arm. The isolated arm supplied partial progress and the peer arm supplied a broken edit in trial 2.
- **OFF 52.** Both arms supplied useful but different next actions in trial 1. Trial 2's peer proposal retained the same defective caching behavior, while the isolated proposal corrected it.
- **ON 29.** All six replay outputs proposed the same scoped read of the just-edited fixture. This matches the historical next action and establishes comparable immediate-turn quality for these pairs.

The source checks use `epyc-inference-research@dd090a874c22be58e09b18fc1fc86da7b46b1d85`. In `scripts/kernel_rnd/autokernel/loop/run.py`, the runtime store is constructed beneath `args.store / "runtime-preparation"` and passed to `RuntimeAdmission`. The loop result writer places the launch arguments in the continuation and provides no top-level `store` field. `test_existing_cpu_run.py` loads that result into the fixture callback. These contracts establish the static ON 28 rejections and partial credit.

Next: AP-W66-PAIR owner incorporates these judgments into the paired timing attribution.
