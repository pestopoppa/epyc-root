# KVQ linkage receipt ASLR comparison fix

Lane-local preparation only. This patch targets the current external producer file but does not modify that checkout.

- Source repository commit: `a794f5b54bea1a1f0752e0e3514ce07fa14c5ff2`
- Source path: `scripts/benchmark/kv_quant_27b_v10_sweep.py`
- Source SHA-256: `b268e3067fb576f05915310b0df1b29ca0507442c87d6e3fb0a2be209c390cb5`
- Patch SHA-256: `97553e077b9f21d7da05d8fe22c6af9b24047210c928a923bf5c416e2848b91b`
- Patched producer copy SHA-256: `cca1c05f955d3249bb75d9a2a8930b8ce2c3c895f353442ad8eba738d74cd556`
- Regression SHA-256: `8675603175b1cf92e6643e5ef15fbb2fb2c59f632b04b04126c9e1da720f2c21`

The comparison deep-copies the binary witness and replaces only a trailing `ldd.stdout` `(0xHEX)` load-address field on each line with a stable token. It retains paths (including path components that look like hex addresses), SONAMEs, return codes, stderr, verifier identity/output, binary identity, and inspected library SONAME/path/digest. Original receipts remain unchanged in native records. No historical result is rewritten or salvaged.

Static call-site impact: `identity_witness_matches` has one production call site in `run_sweep`, after the matrix, and controls whether all observations remain valid. GitNexus was unavailable for this lane (`gitnexus status`: repository not indexed); this is a direct static call-site count, not a GitNexus graph report.

The successor uses the original detached research worktree at base `99301fa149af86a6f9743d2b0405c9234ba39586` plus the reviewed patch. The same worktree moved to `/mnt/raid0/llm/tmp/vidya-belief-substrate/kvq-ready/research` and is locked for the row. The wrapper checks the pinned 1,689-file script and config closure before import. The matrix runs 3 arms x 5 repetitions x 2 depths and emits fresh native outputs.

The prior preflight passed source, kernel, and model identity checks and compared two real binary linkage witnesses. Its saved model SHA-256 is bound to `row/prepared-model.json`. The model's device, inode, byte length, and mtime matched the preflight, and the current ctime predates the original source closure and preflight. The wrapper checks the pinned pathname, resolved path, regular-file type, device, inode, size, mtime, and ctime at the producer's model identity checkpoints. The producer still checks the mapped model while requests run. The smoke marker requires a valid closing identity witness.

The live scratch packet is `/mnt/raid0/llm/tmp/vidya-belief-substrate-program/vidya-kvq-v10-sweep-20261117-r2/spec.json`. Its metadata-only `job.py --check` passed after deployment to scratch. Focused controls covered metadata-only reuse, a same-size edit with restored mtime, a missing model, symlink substitution, and smoke failure on an invalid closing witness. The unchanged host guard exited 5 with `process blocker: llama-server`.
