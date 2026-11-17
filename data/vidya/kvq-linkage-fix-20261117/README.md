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

Prepared successor uses the original row's detached research base `99301fa149af86a6f9743d2b0405c9234ba39586`, whose producer file is byte-identical to the file above, plus this patch. The 1,689-file script/config closure is pinned before import. Model-free preflight passed source/kernel/model identities and two real repeated binary/linkage witnesses. The ignored lane-local research worktree is locked for the row and must remain until filing; the external shared research checkout was not modified. The run design stays 3 arms x 5 repetitions x 2 depths, with fresh native outputs; no old measurement is reused.
