# UFH-12 G-S two-facet final review packet

Conditional pending MAIN review; no real grant, inference, migration, or production change. Two 8 GiB correctness rows, `ROW-DRAFT.md` (scores) and `ROW-TOKENS-DRAFT.md` (tokens), use explicit physical CPU grant `regions=24-47`; the shared lock makes these rows sequential because they share ports and results. A 900 s tranche fits a requested 1200 s window and can record partial coverage; no unmeasured duration promise is made.

The paired corpus is the accepted reqb copy. Tool, memory-record and strategy text helper match orchestrator origin/main 80ea5528 exactly. BGE historical document identity is an explicit legacy assumption. Fixed seed `ufh12-gs-20261027-v1` selects 489 episodic + 11 strategy IDs as stored-text query proxies; self is excluded, score ties use ID order, similarity is within model space, and no relevance labels are invented. BGE query prefix is empty; EG2 query/document prefixes are `task: search result | query: ` / `title: none | text: `. Full stored-text tokens cover 65,942 rows, with 32-record resumable shards and per-item durable checkpoints. Distributions and overlap are descriptive; thresholds remain unchanged.

`SOURCE.sha256` binds code and `LIBS.sha256`. The job verifies EG2 GGUF 68bae29d62fb8c7d23e98d21fd4662753ddd636e6b62b8a70dfe059a9844f216, BGE GGUF 3379a0e9cea28fc6d7136df8ea7a88ef99ccce5963b9a6f7af9609997be762e3, server a2e62037e37ff0391017bd68fec421f271f94c2dfb1df3e767ff45abeeb4c01b, and mapped ggml/llama libraries; records owned PIDs, start ticks, affinity, maps, model response and proof hashes. It refuses wrong FILLER_ID, noncanonical grant, affinity mismatch, HOLD or occupied ports. The completion marker is written only after both owned servers are signalled, reaped and verified dead. Model-server launch is gated on a MAIN-reviewed digest of the final source manifest.

The q2 bounded fixture test passed under whole-q2 claim and fresh HOLD/grant checks, shared mutex and 4 GiB RSS monitor: fake HTTP, copied fixture stores, deterministic sample, both facets, partial resume, source mutation and checkpoint tamper refusal, malformed token/embedding and HTTP failure refusal, native projection and attestation tamper refusal, owned fake server startup/cleanup, startup failure and injected drain failure. Peak sampled RSS 237732 KiB, captured descendants drained. Synthetic fixture output is not ingested.

Final same-entry T1 tests reached the server-start boundary without loading models and reaped all test processes:

- scores: `dryrun/f4d6f1c299b5680a7eb30e4325df42824f3563baa7bf44b1/pass.json`;
- tokens: `dryrun/9fa9dd84da0ef9801c593ab38c145d16a11557c1d9e381ef/pass.json`.

Both synthetic normal-admission checks passed for 1200 seconds, 8 GiB RAM and a 2 GiB output estimate; free space 156.44 GiB against the 150 GiB floor. The grant was a scratch fixture, not a live grant.

The native coverage writer uses the existing shared carrier with empty protocol and higher-better only for verified record coverage. `native_capture.validate` rederives coverage and validates attestations; no grade is invented for cosine, token length or overlap. Owner-applied source-table and task text are in `VIDYA-DRAFT.md`; registry/adapter filing and a real planning-context canary remain separate from these preparation tests.
