# W3 canonical half-A r2 checkpoint — 2026-10-29

This checkpoint records the bounded repair and smoke for the W3 half-A launcher. It does not close the canonical W3 census or the broader P0d task.

## Repair

The original half-A grant attempt (`/mnt/raid0/llm/tmp/codex-w3-canonical-halfa-20261028/run-20261029T001749Z-3769280`) exited `rc=1` before its first request with `FileNotFoundError`; it completed zero requests and verified cleanup. Its `capture_inputs.build_receipt_binding` pointed to the removed half-A r1 `BUILD-RECEIPT-PATH`.

The r2 successor uses the existing genuine half-B pointer at `/mnt/raid0/llm/tmp/codex-ni-20261027-inf75-census-prep/w3-halfb-r1/BUILD-RECEIPT-PATH`. The pointer contents name the pinned C5 CPU build directory. The entry preflight separately verifies the `BUILD_COMPLETE` source and `kind=cpu` fields, the no-model-runs field, and the required build artifacts before model I/O or NUMA eviction. It does not manufacture a replacement receipt. Source tests recorded 17 passing tests in `source-tests-r2.log`, 12 passing tests in `source-tests-final.log`, and one build-pointer fixture test in `probe-fixture-tests.log` under `/mnt/raid0/llm/tmp/codex-w3-canonical-halfa-r2-20261029/`.

## Smoke evidence and limits

The same r2 `launch.sh --smoke` path ran under the exclusive q3 lock with CPUs 72–73. The captured run (`smoke-20261029T004513Z-4135399`) completed eight real requests, with a 62.214-second request span and 117.193 seconds total wall time. The first request and result writer succeeded; the server was reaped with `rc=0`, and cleanup was verified. Logs and result: `/mnt/raid0/llm/tmp/codex-w3-canonical-halfa-r2-20261029/actual-smoke-r2-retry.log` and `/mnt/raid0/llm/tmp/codex-w3-canonical-halfa-r2-20261029/smoke-20261029T004513Z-4135399/result.json`.

This was a non-admitted, CPU-only, small-context smoke. It did not observe canonical W3 geometry or close the full census. The separate coactivity record reports a possible 1.769-second overlap during the final request based on the half-B holder's reported start time at 00:47:06.812Z. Its launcher log says it waited 8.8 seconds for locks, so that start time does not establish when q3 was acquired. No performance or causal impact is inferred. See `/mnt/raid0/llm/tmp/codex-w3-canonical-halfa-r2-20261029/COACTIVITY-DISCLOSURE.json`.

A separate 5.019-second q2 source test also has possible overlap with the LB4.9 grant covering CPUs 48–71. Its exact UTC interval was not captured; the conservative possible interval is 00:37Z–00:43:32Z. The peer was notified. This is retained as possible coactivity only, with no impact inferred.

## Submission state

The candidate JSON and row are staged as `BACKLOG`, `ready=y`, with an unarmed launcher. Digest validation reports zero mismatches across 892 source-manifest entries; the row validator returned zero. The last observed keeper state was `READY-WAIT`; no queue, grant, FILLERS row, arm state, or diagnostic seal/receipt was written by this checkpoint. The exact staged artifacts remain in `/mnt/raid0/llm/tmp/compute-flags/ready/inf75-w3-canonical-halfa-r2-20261029.json` and `.row.md`.

The only conclusion recorded here is that the r2 preflight repair and bounded smoke completed as described. **[no-belief: smoke-only; no canonical W3 result or P0d closure]**
