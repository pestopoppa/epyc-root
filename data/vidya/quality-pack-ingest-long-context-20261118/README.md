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
listener closure. The full paired capture remains open. [Preparation and publication receipt](receipt.json)

The original-byte envelopes preserve plan and original model receipt bytes.
Prior architecture preparation verified the full 27B model digest. This
packet reused that receipt after checking the registry hash and the file
identity. The staged scratch directory and launcher are in
[row.spec.json](row.spec.json).
