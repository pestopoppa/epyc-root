# REPL-EMB-2.8a source wiring draft (main applies root docs)

## Original acceptance boundary

`handoffs/active/repl-embedding-retrieval.md` REPL-EMB-2.8a is done only when one session's **real REPL use** produces trace records that the 2.2 harness can load as a `real_trace` stratum. It is not the 75-trace gate; that is REPL-EMB-2.8 and still needs at least 75 real rows plus the complete frozen evaluation. The source-only tests below do not satisfy either real-use condition.

The native records contain only query digests and span ids. The query text must be supplied through a digest-checked resolver from separately retained, authorized session source; the digest cannot reconstruct it. The content bundle must likewise be separately supplied and hash-bound. No synthetic query, guessed text, or implied corpus identity is acceptable.

## Proposed source-table row

`| REPL context-search and spill-follow trace capture (REPL-EMB-2.8a; orchestrator `src/repl_environment/trace_capture.py`, `epyc.orchestrator.repl_context_trace.v1`) | OBSERVATION | Opt-in through existing `EPYC_REPL_TRACE_CAPTURE=1`; native JSONL keeps query SHA-256, session id, sanitized section/span ids, opened status derivable from a later overlapping `get`/`peek`, timestamp, and `provenance=trace`. PII closed-shape scan refuses unsafe records; raw query and section text are not persisted. Query text and bundle identity are supplied only by separately custody-verified resolvers for offline harness preparation. This source is diagnostic trace evidence, not an offline recall measurement or verdict. | Existing `ClaimTuple.grade()` only if a committed conclusion is later recorded; do not route these records into the `offline_recall` writer or create a new grading ladder. | `VB-UFH12-REPL-TRACE-CUSTODY` (proposed) |`

## Proposed VB task

`VB-UFH12-REPL-TRACE-CUSTODY — Wire the native REPL context-search/spill-follow trace producer from REPL-EMB-2.8a as a distinct observation source. Preserve native schema/version, producer commit, source JSONL digest, session/query digest/span linkage, timestamp and trace provenance. Validate the closed-shape PII gate and require separately supplied, custody-verified query-text and bundle resolvers before exporting rows to `repl_emb_eval.py freeze --trace-queries`; unresolved digests/bundles refuse. Keep this source separate from `VB-UFH12-RETR`'s `offline_recall` instrument and never infer query text from a hash. Reuse the shared carrier / `ClaimTuple.grade()` for any later committed observation; no new grading ladder. Done when a real session's records are discovered, validated and source-pinned, the resolver/bundle join is explicit and hash-checked, and a source-only canary demonstrates the resulting `real_trace` query file passes the harness loader. The REPL-EMB-2.8 75-real-row threshold remains separately open until actual retained artifacts meet it.`

## Source-only acceptance evidence

`pytest.log`: 41 passed across `test_repl_trace_capture.py`, `test_exploration_core.py`, and `test_repl_file_exploration.py`. The new fixture exercises opt-in grep + peek against a locally created spill, confirms the raw query is absent from trace JSONL, resolves text/bundle externally, and verifies the emitted row stays `real_trace` in the 2.2 harness labeler. This is fixture evidence only; it is not a real REPL trace artifact.

`ruff-check.log`: clean. `ruff format --check` reports five touched Python files would reformat, but the diff is pre-existing whole-file style drift (first reported hunks precede this patch); files were not whole-file reformatted. `git diff --check`: clean.
