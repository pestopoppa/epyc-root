# Exact GPU-pool candidate requests

This change adds an explicit model-free request to the shared planning reader.
It names the full captured source commit, the SHA-256 of the sealed
source/artifact/shim identity, the native operator and the run ID. It does not
identify a model, a device-wide property or a consumer-wide harness fact.

The candidate identity digest includes the artifact paths and digests, source
dirty-state declaration and shim provenance. Changing any of those fields names
a different candidate. The run selector keeps separate finite selected-case
censuses separate. An incomplete request is an error, not a wildcard.

The adapter locates each observation at its original raw log and captured log
digest, which strict ingestion rechecks. The existing shared grading function
determines the grade. A located observation has no protocol, performance,
promotion or clean-source warrant; source dirty state and shim mismatch remain
explicit in the original capture and claim limits.

Synthetic controls exercise strict write-to-ingest-to-reader visibility and
negative scope matches on an isolated ledger. They do not establish official
native acceptance or production AutoKernel consumer adoption. The existing
AutoKernel wrapper's model requests continue to exclude these claims. Official
GPU-pool captures and their production planning-context canary remain with SC18.

The adjacent KVQ and KVU19 readiness receipts preserve their actual preparation
outcomes. Neither receipt is a measurement verdict.

Validation passed 430 tests on claimed CPUs 72–75, with no failures, errors or
skips. Shared-carrier checks covered 1,007 tuples across 17 source kinds with
zero invariant violations. `validation.json` binds the tested source hashes and
records the positive synthetic candidate reads, model-planner exclusions and
disabled checkout freshness check; `validation.log` preserves the original run.

KVU19's new prospective build uses detached worktrees at the original commit;
all 3,291 source archive file/link entries matched the Git archive. The new
artifacts must be independently pinned after the build completes, rather than
claimed equivalent to the missing original libraries. The private packet still
needs adaptation, preflight and publisher smoke. Its prior 13 MiB residency
result remains below the publisher's 64 MiB requirement. The preserved build
scripts are under `kvu19-build/`; the readiness receipt names the external
completion event and retained code/source worktrees.
