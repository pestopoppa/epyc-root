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
