# CPU decode roofline — 2026-11-01

## CLS-RECT-1a live-token validation row

Published `inf70-cls-rect-live-20261101` for keeper qualification (initial status `needs-dryrun`), CPU region `0-95`, 100 GiB, port 18499. The row tests the already-landed harness1 rectification using the pinned v10 CPU server and served UD-IQ4_XS shards; it does not measure a kernel lever. Durable launcher, spec, and validation instructions: `artifacts/compute/inf70-cls-rect-live-20261101/`. The keeper owns qualification and execution; no inference ran in this session. After `.ended`/`.complete`, inspect `/mnt/raid0/llm/tmp/inf70-cls-rect-live-20261101/results/CLS-RECT-1a.jsonl`, apply the decision rule, file evidence in the handoff, and write the filing receipt. Keep CLS-RECT-1a open until the live evidence qualifies.

The generated top suggestions were checked against the handoff: D3 requires a >=96-thread operating point, whereas completed INF-66 R23-64 favored t48; SYNC-18 was untestable as built per RETEST-1; the pure kernel research stop remains in force. No historical finding was changed. Shell syntax, Python compilation and spec JSON parsing passed. GitNexus status was stale; the prescribed reindex was denied by CPU admission (exit 64). No indexed source symbol was edited. [no-belief: preparation and publication only]
