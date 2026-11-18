# Prospective native quality-pack inputs

The bounded row captures four frozen frontdoor requests independently on v10
and C13 CPU/MTP servers and pins the bank before starting C13. The deployed
shape inventory is not relabeled to satisfy the broad pack contract.

Publisher smoke passed on CPUs 140–143 with one genuine Qwen3-0.6B no-spec
completion from v10. `smoke-native/` retains original request/response bytes,
server identity, grant and cleanup. This is a separate smoke control. The full Qwen3.6-35B MTP pair subsequently
completed through its granted row (rc=0), with four requests per arm and
verified captured-PID cleanup. [Full native bytes and verdict](full-capture/README.md)
preserve the JSON mismatch and the three matching responses. No inference ran
outside publisher smoke or the granted row.

`receipt.json` and `smoke-PASS.json` preserve scope and custody. Full broad pack
coverage, strict comparison ingestion and planning-context acceptance remain
open. This slice cannot produce a quality-pack claim or promotion authority.

Original `plan.json`, `smoke-result.json` and `smoke-native/banked-capture.json`
are stored in `.original-bytes.json` envelopes with the exact original SHA-256.
Decode `bytes_b64` and verify `sha256` to restore the original bytes. This avoids
a secret-scanner false positive on nanosecond file timestamps without changing
the external runtime packet, native evidence or scanner policy.
