# AutoKernel pytest current-run pointer isolation — 2026-10-27

[belief: cc] The authenticated-control test's fixture router lies within the default trusted `/mnt/raid0/llm/tmp` root. Its real serial startup can therefore publish to the live current-run pointer. Research branch `codex/ak-pointer-test-isolation-20261027`, commit `62f33a49560d785c0e97c4ee704a8245729a3800`, redirects the pointer and trusted root for AutoKernel tests and child processes, and fixes the simulated actor-seat setup of the publisher wrapper. Production publisher and actor gate are unchanged.

The guarded focused run passed 5 tests. Landlock refused writes outside the owned work directory, except `/dev/null`; a protected fake pointer stayed unchanged, and its write-refusal positive control passed. A dynamically linked `execve` tripwire refused a synthetic `llama-server` positive control; this is not coverage of raw syscalls or every execution path. Receipt: `/mnt/raid0/llm/tmp/codex-ni-20261027-ak-pointer-test-isolation/proof4/admitted-command.log`. GitNexus impact is UNKNOWN: the fresh checkout was unindexed and reindexing was stopped for shared-compute fairness; manual review covers the AutoKernel autouse fixture and its callers.

The observed native pointer has `generated_at` `2026-10-27T19:11:11.985450Z`, phase `complete`, run ID `eecb21a8bf98447cb099816e02de063c`, and `state_dir` `/mnt/raid0/llm/tmp/codex-ni-20261027-ak-flake-blocker/run-absolute/tmp/pytest-of-node/pytest-0/test_shared_author_sandbox_rea1/router`. This identifies the record as a pytest fixture, not an actual campaign roster or proof of a prior record. The pointer was not altered by this work; recovery requires actual campaign source and liveness evidence and an owner decision.

Owner-applied wiring drafts, not yet applied to the shared tables:

- Source table: committed AutoKernel pointer-isolation conclusion, through the committed-conclusion register as a Judged/Located observation at the committed handoff path and line.
- Substrate task: register that committed conclusion and expose it to planning context through the existing committed-conclusion adapter. Do not invent a measurement warrant or grading ladder.
