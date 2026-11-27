# AP-W66-PAIR target output acceptance

Frozen 2026-11-27 UTC before the C22 replay outputs. The [input manifest](../ap-w66-replay-inputs/requests.json) pins the four turns. Use the exact last message and the full recorded history in the decoded body as the source of task state. Apply the same criteria to original and prefix-preserved arms. Any body changes beyond the documented replay transport, slot, or template treatment require separate grading or an unknown comparison.

## Decision rules

- An **accepted summary** is a complete and accurate answer to the immediate OFF 56 request.
- An **accepted continuation** is a grounded, in-scope, actionable next step for the exact intermediate state. It can be a useful read, focused test request, or proposed fixture edit. Record the action and the evidence it uses. Syntax and tool-name validity alone are insufficient. Record whether an edit is a plausible diagnostic, a partial repair, or a statically plausible full repair.
- A **partial** output preserves some meaningful state or offers some valid progress but misses material requirements. A **rejected** output is unusable, off scope, materially false, or makes a change that undermines a required check. A **truncated** output has a length or context stop or lacks a complete substantive action. An **unobservable** outcome lacks a complete attributable record. Keep the terminal and grading status separate. For a complete failure, distinguish model rejection from transport failure.
- Grade the assembled visible content and structured calls. Reasoning is diagnostic only. Decode tool arguments as JSON and compare to the provided tool schemas. Inspect actions as text. Direct edit and write proposals may be projected into an in-memory copy of the pinned module and parsed as Python syntax. No replay tool or generated code is executed. Read-only requests can be eligible as actions even when the resulting tool response is unavailable.
- Apply an edit against the source as of the turn. Use the pinned baseline and successful visible historical exact replacements or a sufficiently complete historical read. A mismatched edit is rejected as an action. If history cannot establish the target text, record applicability as unknown. A shell proposal is reviewed as text and receives no execution or patch-verification credit.
- Record fixture-task completion separately as **unverified** for single-turn tool replay. Passing either listed test, observed private-lock behavior, and the mutation-control rejection require independently observed results. A useful next step or complete answer to the summary request carries no fixture-task completion credit or accepted coding tasks/hour credit.

## OFF 52 · repair continuation after digest diagnostics

Sequence 52, slot 2. Previously added diagnostics show the first `selection_reference` receives the anchor. The compare receipt shows the retained candidate has a different `snapshot_digest`. The current failure is `PhaseJournalError: runtime selection receipt differs from the integration`. The visible fixture memoizes the first selection artifact, so reuse of the anchor receipt for the candidate is the immediate hypothesis.

Accept a locally actionable response that traces initial versus retained selection, directly tests the cache/identity hypothesis, or repairs fixture selection to write and return the correct receipt when selection changes. A staged preparatory edit is eligible if its role is clear and it preserves the assertions. A scoped read of the relevant call path or immediately relevant fixture source qualifies if it resolves a still-open question. Unchanged test reruns, generic exploration, changing production verification, and assertions that merely retest reference shape do not meet this threshold.

## OFF 56 · structured handoff summary

Sequence 56, slot 2. The latest user message asks for a summary only, following its template, with concise bullets, ordered next actions, and at most 15 relevant paths. Require the Objective, Requirements, Decisions, Work State with Completed and Active, Next Move, Relevant Files, and Important Context where applicable. Blocked is optional when work can proceed. Minor formatting variation, including literal template wrappers, is recorded separately from content correctness when the structure remains clear.

For acceptance, the summary must carry all of the following facts:

1. The work is the DS41-W-66 runtime/source-continuity fixture repair. Only `scripts/kernel_rnd/autokernel/loop/test_runtime_keep_source_continuity.py` may be edited. Preserve the private lock and existing assertions. Carry both acceptance test identities or the exact command below.
2. The fake fixture receipt originally lacked a verifiable file. The current draft writes real per-selection receipts and removed stale memoization after distinguishing anchor from candidate. The visible edits are in-progress, with no recorded commit or final passing run.
3. The latest focused test reached the `checked` callback and failed at `continuation["runtime_recipe_reference"]`. The continuation carries a real locator and digest, while the assertion still expects the fake literal. The last focused run does not establish that both acceptance tests passed.
4. The next move is to bind the continuation equality to the real receipt captured or independently derived for the selected recipe, keeping the locator, digest, and verified status check, then run both acceptance tests.
5. The response contains only the summary and no tool calls. It avoids tool or system setup presented as user requirements and carries the allowlisted file plus the source files needed to resume.

The exact acceptance command is:

```shell
python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_runtime_keep_source_continuity.py scripts/kernel_rnd/autokernel/loop/test_serial_run.py::test_actual_cpu_post_keep_resume_rebinds_original_launch_without_recalibration
```

## ON 28 · continuation after the first fixture edit

Sequence 28, slot 1. A successful edit added a fixture-private receipt file write and returned a real digest. The callback still expects the literal digest. The edit has not been tested in the visible state. The fixture currently uses a fixed locator and writes on both initial and retained selections, which can overwrite an earlier receipt.

Accept a targeted edit that ties the callback to the exact actual receipt while preserving existing protections, a focused acceptance test that establishes the new failure, or a scoped source read that resolves the receipt-store contract or applicability of the proposed assertion. Review any proposed direct edit for match, syntax, scope and assertion semantics. If it pairs a derived digest with the real fixture locator and preserves all other assertions, it can be a useful staged edit. A fixed locator or file overwrite still requires review before crediting a complete repair. Repeating the recorded first edit, bypassing the receipt check, and claiming tests passed have no acceptance credit.

## ON 29 · continuation after the callback edit

Sequence 29, slot 1. Successful edit receipts are visible for the preceding fixture store change and for the callback's exact equality check with a recomputed digest. There is no test result after these edits. The open technical question is whether the fixed-locator write is valid for both selection events and accepted by production receipt verification.

Accept a focused verification proposal, including rereading the newly edited test, checking the store or journal contract, running the exact tests, or a justified further in-scope correction. An actionable complete edit must retain the exact receipt-identity check and existing protections. Repeating an already applied edit, replacing exact identity with shape-only checks, or claiming final success before verification is rejected.

## Fixture controls and comparison

The existing CPU-quality grading setup pins the case at source commit `dd090a874c22be58e09b18fc1fc86da7b46b1d85`. Its negative control produced the expected source-continuity failure, and its historical positive control passed both tests and rejected same-content receipt substitution. The accepted fixture preserves the non-receipt assertions, verifies the actual journal receipt, and checks the exact receipt produced by the fixture. The substitution varies both locator and digest while retaining payload. Syntax, a digest of whichever file is presented, or a nonempty reference can all miss this control. The CPU controls inform the static review and are not observations of the replay outputs.

Compare corresponding target and arm dispositions. Record comparative loss, tied disposition, or uncertainty and describe material differences within tied dispositions. A tied continuation disposition supports turn-level comparability for that pair. It leaves underlying task quality unverified. Peers and warmups are excluded from grading. The historical response may illustrate a feasible transition but the rubric does not require copying its exact action or prose.
