# AM-PORT-2 continuation

The first row `am-port2-l4-vs-ea-gpu-20261119` ended rc=75 with native `STOPPED`, after 32 of the 60 seeded items (96 item/arm records). The automatic filing receipt records **partial**. No final AM quality verdict is available, and AM-PORT-2 stays open.

Continuation `am-port2-l4-vs-ea-gpu-20261119-r2` retains the original decision rule, all 60 seeded items and per-item arm rotation. It reads the original checkpoint by reference and writes only missing units to its own results file. Final native `out/RESULT.json` aggregates the pinned original checkpoint and continuation records; the continuation JSONL alone is not the full experiment.

The continuation refuses a changed checkpoint or duplicate unit identity. It pins the original job, server, shared libraries, build proof and prepared items by content. The native completion checker accepts `L4_KEEP`, `L4_BELOW_EA(...)` and `FUTILITY_*`, and rejects `STOPPED` and smoke results; the original checker incorrectly accepted only old KEEP/DROP names. Three unit tests pass for checkpoint preservation/output separation, duplicate/corrupt checkpoint refusal, and terminal verdict handling.

Before publication, a vocabulary-only CPU load prepared all 60 items and the smaller smoke item (no model-weight inference). All first 32 regenerated items exactly matched their original cached tokens and metadata. Grant-time prompt preparation is removed. Source remains `c9f2e34cea7a0e9ddac5ad7b2088bf06b56ee1db`, tree `dba95c08862f897fa1c2e228f9ba9e5260752ec6`; retained binaries match original `BUILD.json` digests. Planning estimate is 16,000 seconds for the 28 remaining items based on observed arm durations; this is a scheduling estimate, not a performance conclusion.

Evidence is referenced in place:

- Original checkpoint: `/mnt/raid0/llm/tmp/am-port2-l4-vs-ea-gpu-20261119/out/results.jsonl`, SHA-256 `3a1d29b80eba0cf1eebda65e03e5847947d0f115720206cdb1eb535aa0c5f032`.
- Original build proof: `/mnt/raid0/llm/tmp/am-port2-l4-vs-ea-gpu-20261119/out/BUILD.json`, SHA-256 `b9e2c647eeebef42e977117622d1021468cb0ec89ac353e73b021cac655b2467`.
- Prepared contract: `/mnt/raid0/llm/tmp/am-port2-l4-vs-ea-gpu-20261119-r2/inputs/contract.json`, SHA-256 `5a3bbf91b4634f733b177c5ab4030f36045ae9b0e5c2033b686fe4e059269640`.
- Driver: `scripts/benchmark/am_port2/continuation.py`; tests: `scripts/benchmark/am_port2/test_continuation.py`.

Only bounded engineering conclusions are recorded here (`[belief: cc]`); no prospective measurement warrant is invented for the original records. Future AM row capture belongs to the existing VB-YARN-E1 long-context source family and must prove the shared planning-context canary before being called wired.

Publication completed with smoke PASS for `am-port2-l4-vs-ea-gpu-20261119-r2`; proof `/mnt/raid0/llm/tmp/compute-flags/dryrun/am-port2-l4-vs-ea-gpu-20261119-r2/PASS.json`, SHA-256 `dbd54063fdbbaa855d73574e86bae58eb7208983d006d684b6358534fd1200f4`. This qualifies the continuation protocol; it does not settle the 60-item quality rule.
