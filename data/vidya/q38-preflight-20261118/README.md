# Q38 model identity preflight control

The [Research patch](research-model-preflight.patch) extends the earlier planner digest forwarding change at Research `6decaeda4481a841b3a85b55b0be87a6963b3042`. The candidate runner accepts a trusted pre-grant receipt through `--belief-model-preflight`, checks it against the selected serving launch and current file identity before claiming resources, then repeats the metadata check when building the planner context. An omitted flag preserves path-only behavior. Split GGUFs require a whole-model digest contract.

The local control exercised the normal Research serving runner, its planner context builder, the real `AgentPlanner` and the shared belief reader. The preflight arm displayed 16 target claims and accounted for four at the reader limit. The path-only arm displayed zero. The registered adapter projected 20 synthetic records into 60 frames. The probe simulated resource claims, profiling, calibration and the provider reply. It used the reader's explicit isolated replay override because a detached checkout shares moving remote refs. The packet verifies its pinned checkout and file content before and after the run. [Control results](local-control.json)

This control supplies software evidence only. The source packet records zero native Q38 observations. The patch has not been adopted into the live Research checkout; official structural acceptance, live adoption and native Q38 planning acceptance remain separate.

## Reproduce

Create the two detached worktrees at the commits below. For reproduction elsewhere, use a fresh scratch path. The published row uses the path in [spec.json](spec.json).

```bash
scratch=/path/to/fresh/scratch
packet=/path/to/epyc-root/data/vidya/q38-preflight-20261118
git -C /path/to/epyc-root worktree add --detach "$scratch/reader" f36c26d6df868016be962a8b631a879ef311f2f6
git -C /path/to/epyc-inference-research worktree add --detach "$scratch/research" 6decaeda4481a841b3a85b55b0be87a6963b3042
git -C "$scratch/research" apply --intent-to-add "$packet/research-model-preflight.patch"
python3 -I -B "$packet/probe.py" prepare --reader "$scratch/reader" --research "$scratch/research" --fixture "$scratch/fixture"
python3 -I -B "$packet/stage.py" "$scratch"
```

Run fixture preparation outside the grant. It verifies the bytes of a small synthetic file. The allocator work directory is separate so permission changes there do not invalidate the fixture identity. The launcher uses four actual assigned CPUs and ends at either the 300-second cap or the grant deadline, whichever comes first. The job also checks STOP and refuses source drift.

The focused Research suite passed 57 tests with one skipped. GitNexus had no index for the detached candidate. The candidate retains the existing Research call paths and explicitly binds the receipt in serial continuations.

Publisher smoke passed at 18:00:08 UTC on CPUs 116–119 with engine rc 0. The row is published for its independent official structural run. [PASS receipt](publisher-PASS.json) · [Native smoke result](publisher-native-result.json) · [Ready manifest](ready-manifest.json)
