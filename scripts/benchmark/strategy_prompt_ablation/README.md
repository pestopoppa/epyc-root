# Strategy prompt length pilot preparation

This is preparation, not a row or a result. Three distinct arms use an unchanged
base role prompt: `baseline` has no added strategy, `strategy_short` adds
`short.txt`, and `strategy_long` adds `long.txt`. The two additions express the
same plan at different levels of detail; they are not claimed to be exactly 200
and 1500 tokens. Count their tokens with the pinned serving model tokenizer and
record the model and tokenizer identity before any experiment. Differences in
content as well as length can affect outcomes, so this is not a pure length
causal estimate.

`prepare.py` verifies the base prompt by SHA-256 and compares its bytes to the
blob at the specified commit and path in the local `--source-repo` Git object
database (with Git replacement objects disabled). It writes the exact prompt
bytes for the three arms and records the source commit, source path and hashes.
It does not make a network request, invoke a model, or publish a row. The commit
itself must still be selected and trusted by the experiment owner.
For the S4 isolated snapshot, the source manifest identifies orchestrator
commit `9e138e3a3e22ecf8c57cd5bf50beed571d107b54`, base path
`orchestration/prompts/root_lm_system.md`, and digest
`07ee95a143edde00cca053d86cdad80d2980729613c552adb7f15e8d54767628`.

Before publication, implement a distinct strategy-specific runner, native
capture schema and Vidya enrollment. Pin the role, suite, model, kernel,
tokenizer, prompt bytes and parameters; rotate all three arm orders over matched
questions, isolate slots, and retain request/response custody. Record turns,
prompt and output tokens with missingness, elapsed time and scored accuracy per
question. Preregister the stopping rule, acceptable accuracy loss and a
decision rule; report incomplete runs as incomplete and treat a convenience
panel as exploratory, not evidence of non-inferiority. The existing Omega
adapter cannot identify these arms and must not be reused under Omega names.
