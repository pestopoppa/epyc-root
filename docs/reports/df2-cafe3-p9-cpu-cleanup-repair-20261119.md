# CAFE-3 CPU P9 cleanup-induced corpus drift repair — 2026-11-19

The previously repaired CPU row parked again at 23:06:11Z with `prepared input drift`.
Model identities still matched; corpus device/inode/size/mtime and content SHA-256
matched, but ctime changed after smoke. The engine cleanup in
`scripts/coordination/rowflow/filler_run15.sh:292` runs `chmod -R u+rwX "$WORKDIR"`
after recording the terminal event. Engine source blob: `a2cc40b568bb9a96cbf95a88cabea1fcd209e804`.
This explains why sealing permissions before publication did not survive smoke.

A bounded filesystem regression executed that exact cleanup command against the
row work directory. The old corpus ctime changed; the new corpus outside the work
directory retained its complete identity. Its bytes match the original
`28fe6166386a25b548d5529db02df31a4b7f3e24e5180e92982f7bc69ebdcd31` hash.

The new corpus resides under the same row scratch root in `prepared-inputs/`,
outside `cafe3-p9/` (the engine work directory). Prepared/protocol r3 records bind
its finalized identity; inventory/launcher/predicate references were resealed.
Previous records remain in place, including inventory r2. Model/build/runtime
seals and all identity/content checks remain unchanged. Inputs validate without
model hashing. Keeper retention includes the external input and regression record.
The engine and grants were not edited. Parent CAFE-3 remains open for native P9.

Evidence retained in place, SHA-256:

- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/corpus-cleanup-regression.json`: `47838e262720d30956dd2965cdf841f99755d4f53ae1323d9b26cbfff2987d6e`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/prepared-inputs/corpus-r3.jsonl`: `28fe6166386a25b548d5529db02df31a4b7f3e24e5180e92982f7bc69ebdcd31`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/inputs-r2.json`: `8492f5fb738a02852231470f935cea85ea4ebd7205ed02f75be5831ebd1e2275`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/inputs.json`: `ba5976902eee06fcbb8c88763b1695db49e5e6fad4db0f565ac110d2aaf8f713`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/prepared-r3.json`: `969cdb3be3fd4dbf2d6e9b3f6298b153e24dbbda1a1e20d35b98b9fc41223ccd`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/protocol-r3.json`: `2066e177b9449a610a2c1dfa3a21a2141cdfa3708ff4890e3c696365d160a1e7`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/launch.sh`: `2919fcf532d60ba3891b6013866d6e8e9e33170e3af0223bb138de9e60863e97`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/spec.json`: `e58260ced446c2105724b7b8d69800d5f61d5a5d93cb126348f300f8c3717dae`.

[no-belief: input repair and filesystem regression; no native P9 verdict]

Publication and post-cleanup regression
---------------------------------------

Republished with **smoke PASS** on cores **116–119**, rc0 at **23:18:20Z**.
The sealed input precondition also exits 0 **after smoke cleanup**, directly
covering the original failure boundary. Smoke executed the real compiled server
CLI without model loading. Native inference/P9 assessment remains pending.

PASS receipt `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe3-p9-cpu-20261119/PASS.json`, SHA-256
`58c4efe555c3a8406f6ed772ece78270ee15c3454d8f61224460499d26535496`.
