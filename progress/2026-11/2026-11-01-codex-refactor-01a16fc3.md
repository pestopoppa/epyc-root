# 2026-11-01 — codex-refactor-01a16fc3

Completed and independently reproduced the read-only, zero-inference KV-1 serving-log scan. The
130-row source contains 125 dispatched records with fingerprints (98 at `c2048`, 27 shorter) and
five undispatched rows without fingerprints. Rolling 60-minute `c2048` distinct-prefix upper
bounds grouped by recorded port reached 4 on 8083 (two configured slots), 1 on 8199, 1 on 18283,
and 2 on 18973; one launch identity shared across roles at port 8083 had an upper bound of 4.
Most endpoints lack launch IDs, and exact router-key counts remain unresolved because the serving
log fingerprints raw caller-wire `c2048` while PrefixRouter hashes the canonicalized first 256
characters. Evidence and complete counts: [KV-1 audit](../../docs/reports/kv1-prefix-working-set-audit-20261101.md).
KV-1 remains open; new child KV-1a records the required privacy-preserving producer change.

No source code, models, server, or production process were changed or run. No code-queue tick is
claimed for this partial audit.
