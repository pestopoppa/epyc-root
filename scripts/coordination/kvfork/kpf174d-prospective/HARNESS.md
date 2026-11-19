# Source-bound research harness

`pinned_harness.py` imports the bisect runner directly, replacing the indirect
import through temporary `cal-1026/.../run.py` and the missing
`research-kpf174c-pin` checkout. It verifies all three Python dependencies and
the argv bytes before executing research code. Cell resume binding rechecks
those pins and records them, so prior bindings cannot be silently reused.

Source: `epyc-inference-research` commit
`1157adc2f007d1b0c45ddc6daf91eafc45358df7`; paths and SHA-256 values are in
`pinned_harness.PINS`. This is a content pin for the imported files, not a claim
that every file in the checkout is pristine or that the server build is qualified.

Recreate the sparse detached dependency checkout outside the lane:

```bash
git -C /mnt/raid0/llm/epyc-inference-research worktree add --detach --no-checkout /mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf174d/research 1157adc2f007d1b0c45ddc6daf91eafc45358df7
git -C /mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf174d/research sparse-checkout set scripts/benchmark/kpf174 scripts/benchmark/kpf13
git -C /mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf174d/research checkout
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts/coordination/kvfork/kpf174d-prospective -p 'test_*.py'
```

This change restores model-free test imports only. Before publishing any successor,
package the loader and custody module dependencies, regenerate source pins, bind
the immutable receipt/manifest/helper, and exclude exposed g0-S2-B and g1-S2-B.
The old launch/spec files still describe the exposed g0 witness and must not be
republished as a successor. No live qualification or historical verdict follows.

Retained build relocation is explicit: `BUILD-PROOF.json.relocated_from_bin`
must equal the immutable receipt's `run_dir/build/bin`. The original receipt
and custody manifest remain byte-for-byte unchanged. `bound_custody.py` checks
the executable and all seven serving libraries against both the receipt's
original absolute file entries and its content digests. The four ggml entries
must reproduce the original manifest; runtime mapping checks still require
the retained paths' current device/inode identities. Relocation is included
in the cell resume binding. Omit the field for the original, strict path check.

2026-11-19 packaging result: the original R5
`/mnt/raid0/llm/tmp/kvu/kpf174-custody-r5-20261104/runs/build-3mWwg0mm/build/bin`
is absent. The retained candidate at
`/mnt/raid0/llm/tmp/kvu/kpf18-item4-retained-20261105/bin` matches **1/8**
receipt-bound serving artifacts: only `llama-server`, SHA-256
`f4d8b3a5cd9bcd537301e15966b4f8aace98f477cdd7c9bfc4b9b89ec2002650`.
All seven libraries differ. The first refusal is `libggml-base.so.0.16.0`:
actual `c50be2d59bf1a62b8f1a878714aba5195773e77da6570ddc3fda3509b939bccb`,
receipt `f04422b31125b5b5f8015ae3ddcbe5c5cfe02fb3f3bbcb8f8db65165f0e751db`.
This candidate cannot inherit R5 custody. Receipt SHA-256 remains
`6427d8c1fa491950c6f9c5f7566e3e2bc49c32ad6a750cac4fe7afbb76141b75`;
custody manifest remains
`e2ba74779ddfbb32560de5c08a2c687e56be562015a1ebce050017d82f1e63a8`.
These are artifact identity checks, with no model load or inference claim.

The successor needs a fresh build row producing a new receipt and manifest
before GPU publication. Never substitute the retained candidate or reuse R5
receipt pins for newly built libraries. Keep g0-S2-B and g1-S2-B excluded.
Validation: the reproduction command above passes 54 model-free tests,
including relocation, every missing attestation, altered serving artifacts,
wrong origins, incomplete receipts and replaced mapped inodes.
