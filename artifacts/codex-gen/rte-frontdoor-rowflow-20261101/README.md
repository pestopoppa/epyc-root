# RTE frontdoor rowflow v15 candidate

This packet migrates the existing RTE frontdoor row to the canonical rowflow `filler_run15.sh` engine. It was published for keeper qualification; this session did not run inference, tokenizer work, or an API request.

The rowflow dry-run executes the same job path as production under rowflow's short grant and region-lock claim. It starts the pinned production kernel-store server and calls the original owner checker, which sends one real `/chat` request. A result unit is emitted only after matched dispatch/serving records, native token counts, exact loaded source provenance, and the committed live checker all pass. The dry-run unit is tagged qualification-only and cannot complete the row; a separate scheduled production attempt must emit a production-mode unit. Tokenizer preflight is recorded but never counts by itself. Each request and its owner-checker output live under a unique attempt directory; the strict completion predicate validates production mode, grant hash, owner receipt hash, and request identity.

The engine's `FILLER_STOPFILE` is used for both dry-run stop and production stop. The v15 engine owns grant admission; both modes require its row ID in `FILLER_ID` and the matching active grant file. Each attempt writes into a unique dry-run or production directory. Rowflow observes `attempts/*/ROWFLOW-UNIT.json`; the production completion predicate accepts only a production-mode unit with a successful owner receipt and verified final cleanup.

`SOURCE-REVIEW.sha256` seals runtime Python/shell/recipe files and the external owner checker, live checker, and exact v15 engine. The launcher pins the manifest digest; the rowflow spec separately pins the launcher and engine by the normal rowflow publication contract. The manifest does not hash the launcher itself, avoiding a self-reference.

Validation is model-free: source-seal verification, Python compilation, rowflow launcher/spec parsing, result-unit counting, production-only completion-predicate tests, and shell syntax. Publication does not establish qualification or production acceptance.
