# Comparator run-end filing, 2026-11-19

D-RI-PREVIEW-1.4 / D-RI-PREVIEW-1.2: **INCONCLUSIVE / INCOMPLETE**. Both
row-ended mailbox records report rc=75, hard-end, 2026-11-19T21:50:06Z.
The dispatcher supplied contract-v2 start 20:34:59Z, regions 24-47.
Neither native result.json exists. The progress JSONL contains server-ready only;
server startup is not an accuracy result. No frozen statistical look was reached.

All-seven-fields correct is higher-is-better. The frozen decision requires n=30
paired with absolute gap >=0.30 and exact McNemar p<0.05/3. Futility-only looks
are n=10 (all >=9 or all zero) and n=20 (max-min <=2). No rule can be applied
at these checkpoint counts. No separation, equivalence, futility or comparator
unseparability claim is supported. D-RI-PREVIEW-1.2 remains open.

| Variant | current retained / correct | bounded_k3 retained / correct | half_first25 retained / correct | Fully paired n |
|---|---|---|---|---|
| progressive-final-contract-v2 | 3 / 0 | 3 / 3 | 3 / 3 | 3 |
| upfront-dependent-research-v1 | 2 / 0 | 2 / 0 | 1 / 0 | 1 |

Counts are checkpoint descriptions only, not interim statistical conclusions.
Contract-v2 current has two no_final and one partial; other cells have three
correct finals each. Upfront bounded_k3 has one wrong final and one no_final;
the other saved episodes are no_final. No saved record is bad_final. This does
not establish validity of a full run. All retained records carry the respective
variant binding. Interrupted in-flight episodes have no persisted row.

Continuation must preserve these exact cell paths and bindings and resume only
missing episodes; do not restart or import across variants. Preserve n=30 and the
original looks/stop rules. Prepare a continuation row with actual checkpoint-aware
resumability and a booking based on observed per-episode cost; the published
manifests currently say resumable=false despite the driver retaining cell records.
The 75-minute window ended both jobs long before their declared estimates. This
is an interrupted run, not one of three failed model qualifications.

Source producer: epyc-orchestrator commit
`fe2c0b9e3b5c127aef300229a66a9e5197a8a93a`. Evidence remains at native paths:

- `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview14-contract-v2-20261119/PREDECLARED.md` — SHA-256 `c2647240a8d0f63a9e953b9705c14722444638bcad3c91c2bc95947bfcab0f38`.
- `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview14-contract-v2-20261119/out/results.jsonl` — SHA-256 `329cc579eaa642b397f538766e20a1143eedd46bb81fa0b4d2d38578dcfae857`.
- `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview14-contract-v2-out-20261119/cells/worker_general__bounded_k3.jsonl` — SHA-256 `99777936b933a42e4cc7b6ae48ef177f808d8c81323b3b39da0d5016d0ae4c90`.
- `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview14-contract-v2-out-20261119/cells/worker_general__current.jsonl` — SHA-256 `f0c10c90b3f931a3f02112b84804c1ee56f3dfd25c950dddf8c0ba4fe792bc04`.
- `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview14-contract-v2-out-20261119/cells/worker_general__half_first25.jsonl` — SHA-256 `1764de315c9adf5a57f560763d24aeb3138463f12fabd367bb4af20c0eec1862`.
- `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview15-upfront-20261119/PREDECLARED.md` — SHA-256 `82cebc39940c102fd8fdd82a72573448756cb261e277af3fab45169e6c918148`.
- `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview15-upfront-20261119/out/results.jsonl` — SHA-256 `0fb55234d8f02a788ac97a94f319337d8cd6723238e451beca20ed10e94a249e`.
- `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview15-upfront-out-20261119/cells/worker_general__bounded_k3.jsonl` — SHA-256 `d06f7a3717e36e8aad623e665cad6d88b49dd5fdc12c2815ef85c23a3f3c2835`.
- `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview15-upfront-out-20261119/cells/worker_general__current.jsonl` — SHA-256 `d5bfec3d6d6880a07b6884e9aeeb64c676da0e3c56ac9ee89d4c46c81b36dff6`.
- `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview15-upfront-out-20261119/cells/worker_general__half_first25.jsonl` — SHA-256 `4676cd646a0d1069f47dd9c8b6f765bfd8ff8a08d00e274355b7ab81be6c9a4d`.

The end files were absent when read in this turn; no grant file was recreated.
Run-end evidence is the dispatcher event plus existing inference mailbox keys
`926f31fec3b95b45d7b84d80` and `d5294730cee65e47ab2df68b` in
`/mnt/raid0/llm/tmp/compute-flags/notify/inbox/inference.jsonl`.
Manual filing receipts acknowledge these events; they do not mark the experiment complete.

M-12k mailbox triage: smoke rc=3, 2026-11-19T15:26:34Z. Native smoke
`/mnt/raid0/llm/tmp/m12k-gpu-20261119T1500Z/out/smoke/m12k-gpu-frontdoor-memory-ab-20261119.json`
reports four http_error requests (two ON/OFF pairs) and episodic custody
unchanged=false: rows 64514 -> 64515. No usable answer-quality result exists.
Residency watcher records GPU residency, which does not establish API success.
The warning is acknowledged as a failed qualification; M-12k remains open.
Next repair: diagnose API errors and isolate episodic writes before republishing
that existing row. Do not weaken smoke or custody checks.

GitNexus status and upstream impact had no index; prescribed index wrapper
was denied CPU admission (64). Scope here is report/handoff documentation only.
Existing prospective VB-REPL-COMPOSITE-WRITE covers the comparator native source;
no new source class or measurement warrant is created.

M-12k smoke evidence SHA-256: `5accda020487bac59928419d7354069468f0aba0225ffc056fc9223b9562ca96`.

## Upfront second window, ended 23:06Z

This is a new run-end event, not a duplicate of the 21:50Z interruption.
`dripreview15-upfront-20261119` resumed at 21:52:17Z on regions 0-23 and
ended at 23:06:06Z with rc=75, reason=hard-end (4,429 seconds). Alert key
`22f208a7a70e2954d52bebb1` is acknowledged. The earlier empty FILED marker
predates this window end; the owner correction files the new checkpoint as
**INCOMPLETE / INCONCLUSIVE** and preserves the earlier marker.

Cumulative retained episodes are indices 0 through 4 in every cell: **n=5
fully paired**, all-seven-fields exact-correct **current 0/5, bounded_k3 0/5,
half_first25 0/5**. Current and half_first25 each have five no_answer records;
bounded_k3 has one wrong, three no_answer and one partial. No bad_final record
is retained. Every retained record matches the native contract-binding.json,
variant upfront-dependent-research-v1 and producer commit
`fe2c0b9e3b5c127aef300229a66a9e5197a8a93a`; indices are unique per cell.

The first frozen look is n=10. Zero correct at n=5 does not authorize a floor
stop, separation, equivalence or comparator-unseparability claim. The native
result.json is still absent; launcher progress contains two server-ready
records, neither an accuracy result. D-RI-PREVIEW-1.2 stays open. Resume only
missing episodes under the existing binding and frozen n=10/20/30 stops;
retain the original n=30 cap. The continuation must declare checkpoint-aware
resumability and account for repeated short windows; this is a hard-end
interruption, not a failed model qualification.

Native evidence at filing (SHA-256; no source, logs or cells copied):

- `/mnt/raid0/llm/tmp/compute-flags/grants/dripreview15-upfront-20261119.ended`:
  `0bb5543f522fefd2e0f1d54dfe0fed3036aa298d84914962368f0f54c6787b0d`.
- `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview15-upfront-20261119/out/results.jsonl`:
  `cc9c1f6f95c412157daf5eb5515a88a8ffc103331ef12f7309f2270964aeeca4`.
- `/mnt/raid0/llm/tmp/episodic-memory-integrity/dripreview15-upfront-out-20261119/cells/contract-binding.json`:
  `a886e09ef93a3230220e0f84cb17ee3837350ee9f706ac376018da5256c17290`.
- Same cells directory, `worker_general__current.jsonl`:
  `24db64008dcffa9b1512e71ca8d5042169e8832368890167a41799d2918fb8ff`.
- Same cells directory, `worker_general__bounded_k3.jsonl`:
  `0fc69fbc04452a18252d640ead11cedc9b4d5ade1e2b117a3c15030bb5a3f3b9`.
- Same cells directory, `worker_general__half_first25.jsonl`:
  `c820415dea601ba6f7c5e3b4974612b5606b71b84ffe496d6d39903d8f67b046`.

This supersedes only the earlier upfront checkpoint counts, not the contract-v2
filing or any frozen decision rule. Existing VB-REPL-COMPOSITE-WRITE covers
the producer; these are retained observations, not reconstructed measurement
warrants. GitNexus status/impact found no index and the prescribed wrapper was
denied CPU admission; changed surface is report/handoff prose only.
