# HSF-3 bounded source census — 2026-11-04

A read-only, aggregate-only pricing pass found no session keys in either of two local logs. This does not establish an inter-call distribution, a client class, an idle TTL, or HSF-3 completion. The three other source classes named by HSF-3 (structured tap, progress events and chat checkpoints) were not censused. The existing source-boundary review remains applicable to their missing exact-pair fields.

The prospective serving-call extractor `scripts/harness/session_gap_measure.py` (SHA-256 `d8b1e6140c3de918e1335686cfd39a295a5f795fa5ecae5e7efb2a7de02d6eff`) read a snapshot of the serving-call log (SHA-256 `363be1ee4d06c7482697ee0f549bea31cfc5187e0a1d489c28166b744d1e1405`) with two nonoverlapping UTC windows: A, 2026-10-20 00:00 through 2026-10-27 00:00; B, 2026-10-27 00:00 through 2026-11-04 00:00. Across the entire source snapshot it saw 195 records, all 195 missing session keys; it found zero keyed sessions and no exact or proxy pairs in either window. Its manifest SHA-256 is `2022941ef8a1c09307d0d5193e7b35546ef9237c417e2e0ac0152f2fbe199161`; the aggregate report SHA-256 is `7332ddaf4069835e363eb33a7e42eb905b826d8aafc7b708d5f7510ad017a4c0`, and its empty pair file SHA-256 is `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. The counts of missing keys are whole-snapshot counts; neither is an in-window traffic count.

A separate read-only dispatch.v1 whole-file census counted 290 valid records, zero keyed records, zero keyed/classed records, and zero eligible nonoverlapping frontend-arrival pairs. There were no invalid JSON records, other schemas, or invalid times encountered. The source SHA-256 was `2eeb5a5753d098a11a8871fb891f7fa6087b19b7ff46ca8f649ac49970e84b67`. This is coverage pricing only: frontend arrival is not backend enqueue, and the census deliberately does not substitute it for the HSF-3 gap. It reports no raw session key, prompt, message or private payload.

Reproduce against unchanged source files in the local orchestrator log directory:

```bash
python3 -B scripts/harness/session_gap_measure.py \
  --source /mnt/raid0/llm/epyc-orchestrator/logs/serving_calls/serving_calls.jsonl \
  --window 'A,2026-10-20T00:00:00Z,2026-10-27T00:00:00Z' \
  --window 'B,2026-10-27T00:00:00Z,2026-11-04T00:00:00Z' \
  --out /mnt/raid0/llm/tmp/kvfork/hsf3-census-20261104
python3 -B docs/reports/kv-cache/hsf3-census-20261104/dispatch_census.py \
  /mnt/raid0/llm/epyc-orchestrator/logs/dispatch/dispatch.jsonl
```

The first tool retains a private source snapshot and any prospective pair receipts under its output path; that scratch is not published here. The dispatch script refuses a changed source digest and prints only aggregate counters. No inference ran. The serving-call census used the enrolled gap producer; no pair was available to warrant an ingested claim. Both logs have last-modified timestamps on November 2; the absence of eligible records in these snapshots does not establish absence of traffic elsewhere or after their frontiers.
