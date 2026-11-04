# Offline code checkpoint

Prepared from the private LSA lanes on 2026-11-03. `MANIFEST.json` records lane identity, observed working-tree state, explicit source-only proposed local commit groups, observed file sizes, retained test evidence and limits, and deliberate exclusions. It preserves the historical runner source and separately lists the P1 reference lane, P4 evidence wiring, native C5 candidate, and research code. The 257 frozen synthetic gzip token-ID inputs (498,123 bytes total) are individually listed with the cohort/manifests so the runner inputs survive checkout.

The native source list remains provisional while the integration owner completes the approved standalone runtime/lifecycle bridge; refresh it from that report before main review. P4 has a transcribed validation record, not an execution-time stdout artifact, and its post-test source snapshots do not prove exact test-time bytes. A later 3-test preflight does have captured stdout and matching before/after source hashes. The pilot-canary files are a synthetic test fixture only.

This is an inventory artifact only. No staging, commits, pushes, tests, builds, inference, GPU work, downloads, handoff/index edits, or production-tree writes were performed here. Model and build assets remain external scratch prerequisites; no broad artifact glob is proposed.
