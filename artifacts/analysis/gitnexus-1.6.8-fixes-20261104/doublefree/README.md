# GitNexus 1.6.8: intermittent "double free or corruption" at the end of analyze

## Symptom

`gitnexus analyze` sometimes aborts after the last `[gitnexus-heap] scope-lang-end` line, before
`Repository indexed successfully`. glibc reports `double free or corruption (out)`,
`free(): invalid size` or `munmap_chunk(): invalid pointer`, and occasionally the process gets SIGSEGV.
On 2026-11-04/05, 2 of 26 job `analyze.stderr` files under `/mnt/raid0/llm/tmp` had this signature:
`hsf3-adjacency-impact-3a09` and `kvfork/kpf30-impact-8952-r8`.

## Root cause

`gdb` backtrace (3 of 3 aborts captured under gdb):
`NodeConnection::Close -> Connection::~Connection -> ClientContext::~ClientContext -> free -> abort`,
called from `safeClose` (`dist/core/lbug/lbug-adapter.js:1604`, via `closeLbug` and `run-analyze.js:1155`).
Disassembly shows the faulting free is in the `ClientContext+0x1b8` member, which
`ClientContext::ClientContext` builds as `WarningContext` (`operator new(0x78)` then
`WarningContext::WarningContext`). The fault is in that context's vector of populated-warning strings.

Those warnings come from GitNexus data:

- `dist/core/ingestion/community-processor.js:127-132` emits a membership for every node, including
  nodes in singleton communities.
- `createCommunityNodes` (`community-processor.js:224-226`) skips singleton communities, so they have no
  Community node.
- `dist/core/ingestion/pipeline-phases/communities.js:54` still emits a `MEMBER_OF` edge for every
  membership. Each edge into a singleton community therefore points at a primary key that does not exist.
- The relationship COPY fails with `Unable to find primary key value comm_N`. `copyCsvWithRetry`
  (`lbug-adapter.js:751`) then retries it with `IGNORE_ERRORS=true`. On this snapshot, LadybugDB keeps
  322-383 warnings in the connection's WarningContext (`CALL show_warnings()` just before close).

The memory corruption itself is inside the prebuilt LadybugDB binary (`@ladybugdb/core` 0.17.1,
`lbugjs.node`). JavaScript does not free anything twice. Evidence that the warning store is what gets
corrupted: running `CALL clear_warnings()` before close does not prevent the crash, it moves the abort into
`clear_warnings` (3 of 20 runs).

## Fix: JavaScript-side avoidance

`fix.patch` emits `MEMBER_OF` only for communities that have a node. With no dangling rows, the COPY does not
fail, the `IGNORE_ERRORS` retry and warnings never happen, and the native warning-teardown path is never
reached. The loaded graph is identical, because `IGNORE_ERRORS` dropped exactly those rows: the summary
shows the same `113,135 nodes | 177,464 edges | 3153 clusters | 300 flows`. In-memory community
memberships, which processes and skills use, are unchanged.

## Ruled out

- **Manual WAL CHECKPOINT driver.** The 5 s driver does overlap COPYs on the same connection.
  Setting `GITNEXUS_WAL_MANUAL_CHECKPOINT=0` still failed 5 of 32 runs. A connection gate that serialises
  CHECKPOINT against other queries failed 10 of 32. Neither is the cause.
- **ASan preload.** With `libasan` preloaded (it replaces malloc), 0 of 16 runs failed and nothing was
  reported. The interposed allocator hides the bug, so ASan gives no diagnosis here.

## Validation

Reproducer: the 3a09 source snapshot, run with `repro/run.sh` (the same env as `job.py`, `--workers 1 --force`),
4-16 runs in parallel. Results are in `validation-results.json`.

## Apply / rollback

The scripts follow the same contract as the sibling fixes.

- Apply: `sudo -n ./apply-or-rollback.sh apply /usr/local/share/npm-global/lib/node_modules/gitnexus`.
  It verifies the package name and version and the pinned preimage SHA, runs a dry-run patch, applies it,
  then verifies the postimage SHA.
- Roll back: run the same script with `rollback`.
- `apply-test.txt` records a disposable apply, rollback and wrong-preimage refusal.
- Only apply or roll back when no `gitnexus analyze` is running.

| Package code | Runs | Crash rate |
|---|---|---|
| Original (baseline, trace, nockpt, clear arms) | 80 | 13/80 (16%) |
| Rejected CHECKPOINT-gate candidate | 32 | 10/32 |
| **This fix** | 56 | **0/56 (56 consecutive successes)** |

With this fix, `show_warnings` reports 0 warnings at close in all 32 traced runs.
