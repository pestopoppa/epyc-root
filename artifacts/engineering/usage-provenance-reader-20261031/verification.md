# USAGE-PROV-1 strict reader source partial

Date: 2026-10-31

ROOT reader commits: `657395e78` (initial adapter), `b5d9f418d` (process/value binding), and
`020a992a1` (bounded snapshot index). The companion APP writer is `0d01dc94c`; APP durable proof is
`artifacts/audit/usage-provenance-declaration-20261031/verification.md` in the orchestrator repo.

## Reader behavior

The adapter projects only explicit source-authored declarations on complete begin/settled pairs
that join to a self-hashed physical serving record. It validates existing ClaimTuple fields and
contexts, binds each value to both the declared call counter and the joined physical counter, and
requires matching process PID, run ID, host, start time, and commit. Missing declarations, unknown
context, and unjoined physical rows refuse projection; direction, category, protocol, or model
identity are never filled in on read. Cache replay is linked by the original logical call ID and
does not emit a second physical tuple.

Whole logs are snapshotted and hashed once per ingest file. A bounded index (32 files and 250,000
record lines) is keyed by absolute path, device, inode, size, mtime, ctime, and expected file digest.
Each source line is bound to its self-hash. `project()` reuses that index and checks the open file's
identity and metadata before use; an append, inode replacement, or symlink is refused. It does not
reread or rescan the complete log per claim. Inputs beyond the bounded index refuse explicitly.

## Verification

Model-free command, using the 36–37 CPU prep lock:

```text
flock /mnt/raid0/llm/tmp/compute-flags/prep-locks/36-37.lock taskset -c 132,133 env -u EPYC_ORCHESTRATOR_ROOT OMP_NUM_THREADS=1 python3 -m pytest -q tests/vidya/test_usage_provenance_adapter.py
```

Result: **10 passed, 1 skipped**. The skip is the documented opt-in cross-repo writer canary; all
self-contained reader tests ran. With
`EPYC_ORCHESTRATOR_ROOT=/mnt/raid0/llm/worktrees/mains/codex-ni-orchestrator`, the same suite passed
**11/11**, including actual APP writer → ROOT reader → generic ingest → planning-context canary.

The 250-row control asserted exactly two full snapshot reads total (one usage log and one serving
log) across all `native_rows()` and `project()` calls. Append, replacement, and symlink controls were
refused. Additional controls cover run-ID mismatch despite matching PID, modified projection value,
bool versus integer zero, deep-copy declaration binding, and replay producing one physical count.
Ruff and `py_compile` passed for both changed files.

## Scope status

This is source infrastructure and synthetic correctness evidence. The live orchestrator currently
has no production call site authoring measurement declarations, and no real inference capture was
made. The existing `USAGE-PROV-1` enrollment remains open for real source-authored capture and its
runtime canary. No wired, READY, or measured-cost claim is established.

SHA-256:

```text
scripts/vidya/adapters/usage_provenance.py  7383e76aea54a3fda220c2c0071686e27b12209bfa117dbad3f62d3910632b8d
tests/vidya/test_usage_provenance_adapter.py  c49dcaf638c52267d36903669d175e5c6e26d01732e73e041f8611414520dcc0
```

`[no-belief: source implementation and synthetic correctness controls; no measurement]`
