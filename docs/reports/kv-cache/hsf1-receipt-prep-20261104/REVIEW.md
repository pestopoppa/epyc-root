# HSF-1 receipt draft review

This is an unintegrated source draft, not a producer, a launch receipt, or measurement evidence. Do not deploy it as written. The draft computes `argv_sha256` from the redacted arguments, so it does not bind the effective argv. Its option-name redaction also misses secrets embedded in free-form values; `argv_redacted: true` is not a complete privacy guarantee. The writer fsyncs file content but not the destination directory, so it does not prove crash durability of the published entry.

The source is a proposal for offline review only. A validated privacy/custody contract, phase parsing and lifecycle tests, source-bound impact analysis, and owner integration remain before any production receipt claim. The existing planned belief wiring is VB-SWAP-C; this draft does not emit a claim tuple.

A later scratch revision, retained as `tested-receipt.py`, stores no argv text and hashes the original argv; five isolated lifecycle/privacy/custody tests passed. This corrects the redacted-argv digest mismatch but does not meet the handoff's effective-argv capture requirement. An unkeyed digest of secret-bearing argv can also permit guessing low-entropy values, so it is not a complete secret-protection contract. The tests were against a scratch absolute path, and the revision is still unintegrated; no measurement or deployment follows.
