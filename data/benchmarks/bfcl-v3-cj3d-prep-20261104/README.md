# BFCL-V3 native-call checker preparation

The manifest contains a deterministic coverage smoke: the first four simple cases and first two cases from each of eleven further gold-bearing categories, with the exact original input and gold records and per-file source digests. It is not a statistically representative fleet-ranking sample. Original input/gold IDs and file SHA-256 values were checked against the cited research corpus.

`bfcl_v3` is the intended candidate key only if the native transport, parser and pinned official V3 checker reproduce the upstream semantics. The official checker and its positive/negative controls are not yet bound, and the rows are not scorable. Do not report a score, silently normalize arguments, infer native parity, or combine this native-call path with a REPL key. Multi-turn categories may need their own official execution/state machinery; this manifest does not establish their readiness.

Source: BFCL-V3 acquired from the [Berkeley Function Calling Leaderboard dataset](https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard), Apache-2.0 per the source corpus record; each record retains its original ID and source file hash. No model or external API ran in this preparation.

The research checkout HEAD is context only: at least the simple input file is untracked, so that commit does not attest the dataset. The manifest instead binds the copied local acquisition by its per-file SHA-256. The upstream V3 scorer revision remains to be pinned.

The original acquired dataset card is retained as [UPSTREAM-README.md](UPSTREAM-README.md); its license declaration is Apache-2.0.
The standard [Apache-2.0 license text](LICENSE-APACHE-2.0) accompanies the selected records.

This preparation manifest contains both case inputs and gold answers. Never mount it in an agent-readable workspace: a later runner must expose only selected inputs and keep gold and checker files behind its independently verified grader boundary.

A proposed [native response adapter](../../../proposed/cj567/openai_tool_calls.py) preserves tool-call order and reports malformed JSON, duplicate keys, non-function calls, absent calls and non-object arguments as parse errors. Its twelve synthetic controls passed; it is not connected to a live transport or the upstream checker and contains no scoring rule.

An upstream BFCL-V3 code candidate is Gorilla commit `70b6a4a2144597b1f99d1f4d3185d35d7ee532a4`. Its Python-only extraction was checked on two simple cases, but this has not established that the official package, dataset snapshot, dot-name mapping or multi-turn machinery match the intended local instrument.
