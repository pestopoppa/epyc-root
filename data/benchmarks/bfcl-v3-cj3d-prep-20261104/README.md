# BFCL-V3 native-call checker preparation

The manifest contains a deterministic coverage smoke: the first four simple cases and first two cases from each of eleven further gold-bearing categories, with the exact original input and gold records and per-file source digests. It is not a statistically representative fleet-ranking sample. Original input/gold IDs and file SHA-256 values were checked against the cited research corpus.

`bfcl_v3` is the intended candidate key only if the native transport, parser and pinned official V3 checker reproduce the upstream semantics. The single-turn Python subset now has the pinned official checker and software controls described below; the full 26-case manifest remains unready for scoring. Do not report a score, silently normalize arguments, infer native parity, or combine this native-call path with a REPL key. Multi-turn categories may need their own official execution/state machinery; this manifest does not establish their readiness.

Source: BFCL-V3 acquired from the [Berkeley Function Calling Leaderboard dataset](https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard), Apache-2.0 per the source corpus record; each record retains its original ID and source file hash. No model or external API ran in this preparation.

The research checkout HEAD is context only: at least the simple input file is untracked, so that commit does not attest the dataset. The manifest instead binds the copied local acquisition by its per-file SHA-256. The upstream V3 scorer revision remains to be pinned.

The original acquired dataset card is retained as [UPSTREAM-README.md](UPSTREAM-README.md); its license declaration is Apache-2.0.
The standard [Apache-2.0 license text](LICENSE-APACHE-2.0) accompanies the selected records.

This preparation manifest contains both case inputs and gold answers. Never mount it in an agent-readable workspace: a later runner must expose only selected inputs and keep gold and checker files behind its independently verified grader boundary.

A proposed [native response adapter](../../../proposed/cj567/openai_tool_calls.py) preserves tool-call order and reports malformed JSON, duplicate keys, non-function calls, absent calls and non-object arguments as parse errors. Its twelve synthetic controls passed; the single-turn bridge below connects it to HTTP transport and the upstream checker. It contains no scoring rule.

An upstream BFCL-V3 code candidate is Gorilla commit `70b6a4a2144597b1f99d1f4d3185d35d7ee532a4`. The bridge imports the original package directly and tests exact dot-name mapping on the selected Python single-turn cases. The earlier Python-only extraction is not used; multi-turn and other language machinery still require integration.

The [single-turn native bridge](../../../proposed/cj567/bfcl_native.py) now binds that original upstream revision, refuses modified package trees, converts tools with the upstream OpenAI converter, rejects name collisions and reverses declared wire names exactly before official checking. Nine integration tests cover the ten selected Python AST cases (`simple`, `multiple`, `parallel`, `parallel_multiple`), negative argument/count controls, malformed-response UNKNOWN, ID/source refusal and a local scripted HTTP endpoint. No argument coercion or local scoring rule is added. Run with `BFCL_CHECKOUT=<Gorilla checkout at the pinned commit> <prepared-python> -B -m unittest discover -s proposed/cj567 -p test_bfcl_native.py -v`; prepared Python needs the three tree-sitter pins in the qualification record. These tests do not establish a representative sample or fleet result. The other sixteen cases still require their official language/stateful execution integration; they fail explicitly in this bridge. Before model runs, add native write-time custody under `VB-BFCL-NATIVE-WIRE` and keep gold/checker files outside the model workspace.
