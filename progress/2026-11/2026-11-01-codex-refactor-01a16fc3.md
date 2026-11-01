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

No source code, models, server, or production process were changed or run for the KV-1 partial audit;
that audit receives no code-queue tick.

Closed UFH14-A6's bounded isolation prerequisite using committed source and canary evidence: research
`276d75fab38b5c541624daba29affb7bc8dbbd4b` puts normal `run3.py` calls through `sandbox3.py`, and
canary update `618201db9e9acebd4fba2622149ddd506f5f70f3` records the real Gemma 1B CPU call denying
planted live/future campaign reads while retaining its own workspace,
result directory, and wire proxy. This is not a 27B study or efficacy result. Evidence: [A6 canary
source qualification](../../artifacts/compute/refactor-a6-native-cutoff-canary-source-20261030.json).
