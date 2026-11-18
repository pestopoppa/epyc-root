# Ingest long-context quality-pack input preparation

The paired packet fixes four synthetic ingest requests per arm on isolated
24-CPU v10 and C13 servers with Qwen3.8-27B Q8_0. It uses one slot, a
16,384-token context, split q8_0 K/V, flash attention, and explicit no-spec.
The registered template is pinned and thinking is disabled for these
requests. Three documents must reach at least 4,096 native prompt tokens.
One asks for the latest signed disposition amid intervening records and
carries the recurrent-state fixture label. The short summary provides a
separate input shape. The runner retains exact request and raw response
bytes, verifies zero draft, cold prefill, token counts, finish and cleanup,
and pins the production bank before candidate launch.

The ingest role shares the architect_critic process on MI210 at :8083. The
host uses a 393,216-token unified q8_0 K/V pool and four slots, with a
262,144-token per-request limit and DFlash2 draft cap 7. The compiled alias
view reports speculation disabled even though its launch requirements and the
registry reference the inherited sidecar. The provenance in the plan
preserves both views. The isolated run covers a bounded CPU recipe and
supplies inputs for the broader quality pack. The prior frontdoor JSON
mismatch remains part of that record.

The publisher smoke passed on CPUs 116–119 with one v10 Qwen3-0.6B Q8_0
no-spec completion, eight returned tokens, and verified process exit and
listener closure. [Preparation and publication receipt](receipt.json)

The original-byte envelopes preserve plan and original model receipt bytes.
Prior architecture preparation verified the full 27B model digest. This
packet reused that receipt after checking the registry hash and the file
identity. The staged scratch directory and launcher are in
[row.spec.json](row.spec.json).

## Full paired capture

The capture passed with exit code 0 and eight responses. Two of four pairs
matched exactly in content and token counts. The short summary differed in
content and returned 38 versus 39 completion tokens on v10 and C13. Document
reconciliation also differed in content and returned 34 versus 36 tokens.
Both arms completed uncached prefill intact for all three long inputs at
4,767, 4,892, and 5,439 prompt tokens. Both server processes exited and both
listeners closed.

The pass covers isolated native input capture only. Quality parity, deployed
equivalence, and promotion remain outside its scope. [Full capture receipt](full-capture/receipt.json)

The full capture result and both bank records use `.original-bytes.json`
envelopes in this archive. Decode each envelope's `bytes_b64` into its
original filename and verify the decoded SHA-256 against `sha256` and the
receipt's `original_files_sha256`. The receipt's `files` map covers the
archived files as stored. The scratch result and both bank records retain
their original paths and bytes.
