# CAFE-3 CPU P9 precondition repair — 2026-11-19

Row `df2-cafe3-p9-cpu-20261119` republished with smoke **PASS**, cores 116–119, rc0 at 21:58:10Z. Real compiled server CLI qualified without model loading. Scheduled native inference and the P9 verdict remain pending; parent CAFE-3 stays open.

Original input check refused `prepared input drift`. Both model identities matched exactly. Corpus device, inode, size and mtime matched; only ctime differed. Content SHA-256 still matched `28fe6166386a25b548d5529db02df31a4b7f3e24e5180e92982f7bc69ebdcd31`. The metadata-changing process is unidentified.

Repair finalized corpus read-only permissions before recording its identity, retained original prepared/protocol/inventory records, and sealed replacement references. Launcher/predicate now pin the revised inventory. Model seals, CPU R3 build receipt, runtime and all drift checks remain unchanged. No grant-time weight hashing. Revised precondition exited 0; publisher smoke PASS. Alert `fc7696caa79879b873fd2892` acknowledged.

Evidence retained in place, SHA-256 bindings:

- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/inputs-r1.json`: `fe6598567dfe2c13d641c4cf8f4ff237492c7bd8907c8e467d7a1da9856d5827`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/inputs.json`: `8492f5fb738a02852231470f935cea85ea4ebd7205ed02f75be5831ebd1e2275`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/prepared-r2.json`: `1c83142a288860d5a4cfd088e8bcdc0d6e52a904afbaa5d6859108e90eee3ba2`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/protocol-r2.json`: `b2537d77eb9b874e3509dc187169299eb5a9c8f729a37619f27102d94961c910`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/runtime.py`: `86301fd05cd714fab84fdc942127b42f9021662c86b7fcb46d490059a48e0261`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/launch.sh`: `cb03a94d48645c65f060dc2bc16df819292e3fbc15033ce0c7e4ee459d3ffa05`.
- `/mnt/raid0/llm/tmp/df2/cafe3-p9-cpu-20261119/cafe3-p9/spec.json`: `a4dfa77e4fb8773e3c0fee8184b8613f338ea7dee8ad0682b7351df39523bbed`.
- `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe3-p9-cpu-20261119/superseded/20261119T215804819946Z/FAIL-1.json`: `6dff6ea878426f28ba0218aa20c11142808e7b1a3e7e327c827019772e66abf9`.
- `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe3-p9-cpu-20261119/PASS.json`: `a82de4194973f2a7567fe8e4f30ed0434497cbbd9d06a620236358a1f0619d93`.
