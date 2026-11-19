# AM-PORT-2 continuation

Continuation r2 completed all 60 items on 2026-11-19: **L4_BELOW_EA**, with full KV 60/60, L4 0/60 and EA 0/60. The registered early-keep gate failed; faithful AM remains untested and AM-PORT-3 is next.

The first row `am-port2-l4-vs-ea-gpu-20261119` ended rc=75 with native `STOPPED`, after 32 of the 60 seeded items (96 item/arm records). Its automatic filing receipt records **partial**; the final result below combines that checkpoint with r2.

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


## Completed 60-item verdict — 2026-11-19

Row `am-port2-l4-vs-ea-gpu-20261119-r2` ended `rc=0 time=2026-11-19T11:37:19Z reason=complete`. The pinned 96 original records plus 84 incremental records contain 180 unique item/arm units. Full KV scored 60/60; L4 and EA each scored 0/60. Each of the three probe types scored 20/20 for full KV and 0/20 for both compressed arms. Higher exact-match accuracy is better. Full KV clears the registered 90% control threshold; the native summary reports no misaligned arms, no zero-eviction compressed items, positive L4 beta counts, and own HIP/KFD/VRAM residency before and after the continuation.

The L4-minus-EA difference is **0 percentage points**, with b=0 L4-only successes, c=0 EA-only successes and one-sided paired sign-test p=1.0. The registered +10-point/p<=0.05 early-keep criterion fails, giving native **L4_BELOW_EA** and filed `fail`. Execution completed successfully; this fail refers to the early-keep criterion. Both compressed arms tie at zero, so this establishes neither EA superiority nor a verdict on faithful Attention Matching. These are the registered exact-match results at 5x compression on this fixed synthetic cohort, not a population-quality or performance claim. No further L4 repeat is required by the rule; proceed to AM-PORT-3's per-layer/head NNLS beta and OLS value refit.

Final evidence, referenced without copying producer artifacts:

- Native aggregate: `/mnt/raid0/llm/tmp/am-port2-l4-vs-ea-gpu-20261119-r2/out/RESULT.json`, SHA-256 `c54f2b9974fb6e808e6d35f68e833d9ccf9bb924b5f02348906be5d92f73c0b6`.
- Incremental 84 records: `/mnt/raid0/llm/tmp/am-port2-l4-vs-ea-gpu-20261119-r2/out/results.jsonl`, SHA-256 `225d2d456751892a199256f30070287b51b2c7884cf7ee2b10316f7dd7f0503b`.
- Original checkpoint and prepared contract retain the digests listed above. Candidate source is `c9f2e34cea7a0e9ddac5ad7b2088bf06b56ee1db` in `llama.cpp-experimental`; build identity is bound by the original BUILD.json and contract, rather than inferred from a directory name.
- Canonical receipt: `/mnt/raid0/llm/tmp/compute-flags/filing-done/am-port2-l4-vs-ea-gpu-20261119-r2.verdict.json`, already filed `fail` at 11:40:22Z. The handoff owner's filing invocation returned NOOP rather than replacing that receipt. Only its exact-match verdict is adopted here; additional diagnostic explanations in the receipt were not independently established in this filing turn.

This committed conclusion uses `[belief: cc]`; it does not create a retrospective measurement warrant. The existing VB-YARN-E1 long-context source family remains the capture route identified above.
