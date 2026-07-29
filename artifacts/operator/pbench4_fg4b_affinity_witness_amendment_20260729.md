## P-BENCH-4 affinity-witness superseding amendment (FG-4b)

This append-only amendment supersedes the affinity witness in the prior P-BENCH-4
receipt `artifacts/operator/ratify_pbench4_fg4b_server_native_20260729T055435Z.json`
(SHA-256 `8da155e451f94720878d1fc7ffc53c190d8eabb96b106b15ffb32794528c154e`).
That receipt remains durable historical provenance only: it cannot ratify the
affinity-hardened runner or support a new P-BENCH-4 claim.

**All-thread request-boundary affinity.** The live witness must enumerate every
numeric TID in `/proc/<server-pid>/task` immediately before and immediately after
each warmup and each measured request. Each enumeration is valid only when its TID
set is stable across collection, retains the leader TID, contains at least one worker
TID, has no affinity outside the expected CPU list, and has both the all-thread and
worker-thread affinity unions exactly equal to that list. The persisted per-request
witness must retain the complete `before` and `after` observations and reject any
difference between them. TID appearance, removal, leader disappearance, an
incomplete worker set, or any out-of-mask affinity invalidates the arm.

These are stable `/proc` snapshots, not continuous scheduler tracing. A transient
thread or affinity change that begins and ends between the two request-boundary
snapshots is not observable; it remains a disclosed residual risk and may not be
described as continuously monitored affinity.

**Superseding attestation.** A new human receipt must bind the exact runner
repository, commit, tree, source SHA-256, and contract containing this witness. It
must name the prior receipt path and SHA-256 as superseded provenance. The shared
measurement trust-boundary lock, transaction journal, fsync-backed no-replace
receipt publication, and fail-closed recovery requirements of P-BENCH-4 remain in
force. This amendment neither starts inference nor changes a registry, serving
configuration, deployment, or decision gate.
