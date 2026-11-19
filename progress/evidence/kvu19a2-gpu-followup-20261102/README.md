# KVU-19a-2 GPU reproducibility follow-up (preparation only)

Status: **capture source and case set recovered; GPU protocol not runnable yet**.
The published CPU build row `handoff-kvu-kvu19a2-build-20261102` now has a native
`status: built` result. This packet performs no build, GPU work, row publication,
or upstream reporting. No binary is copied here.

## Dependency and admission gate

Use only
`/mnt/raid0/llm/tmp/kvu19a2-build-row-20261102/output/RESULT.json` as the build
receipt; it reports `status: built`, `mode: full`, and unchanged source metadata.
Do not infer runtime behavior from the binary digests. Before any GPU row, the
owner must still independently recompute binary hashes and review input/source
custody. The remaining admission gate is all of:

1. `status == "built"`, `mode == "full"`, exact expected source commit/tree and
   pinned base/candidate tile hashes, and unchanged before/after source metadata.
2. Both arms have the expected `test-backend-ops` and HIP DSO SHA-256 entries;
   independently recompute each digest from the paths in the result.
3. The receipt's `source_custody` limitation is accepted as a limitation, not
   silently promoted to immutable custody. The current build producer states
   that same-UID mutation remains possible.
4. The dedicated GPU runner's source and output capture have been reviewed and
   pinned, and an independent GPU row is published with an exclusive gfx90a
   grant. The CPU build grant does not authorize or reserve GPU execution.

If any gate fails, stop before GPU execution and preserve the build failure as
the result. Never build, modify, or run a production kernel; use only the
experimental baseline and candidate artifacts from this row.

## Reproducibility protocol

The intended contrast is within each built arm, not simply base versus candidate:
five fresh process launches per exact case and arm, with byte-identical input
fixtures and environment. Store every raw output tensor in a new, exclusive
run directory and record its SHA-256. Summarize cross-launch hashes separately
for base and candidate. A difference between arms alone does not establish
nondeterminism; five matching outputs only mean no difference was observed in
that sample.

Each invocation must attest, in the same run window:

- exact executable, loaded HIP DSO and transitive source/build identity;
- actual HIP backend and gfx90a device, through `verify_ggml_linkage.sh`,
  non-zero VRAM sampled during the run, and KFD process residency;
- exact test case parameters, suite seed, input-fixture hashes, launch ordinal,
  exit status, stdout/stderr hashes, output tensor size and output digest;
- row/grant identity, CPU affinity, start/end timestamps, stop/deadline handling,
  process-tree cleanup, and result publication by no-replace atomic write.

The historical scratch harness is preserved at
[`historical/fa_harness.cpp`](historical/fa_harness.cpp). It uses `std::mt19937`
seed 1234, accepts `FA_CASE`, writes raw `out_NN.bin` under `FA_DUMP_DIR`, and
prints a per-case hash. Run one case per fresh process into a new, previously
nonexistent directory; never use the old `run_exact.sh`, which removes its
target directory. Before reuse, the harness source must be built in the separate
GPU row and bound to that row's source/toolchain/binary receipt. The scratch
precompiled executable is not admitted by this packet. The `test-backend-ops
--repeat-suite` option alone is insufficient because it does not export raw
output bytes.

## Recovered historical source and cases

The historical harness rows are now pinned in
[`historical/cases.json`](historical/cases.json), including head dimensions,
GQA ratio, KV length, batch, sequence/run/free-cell mask layout, F16 storage,
zero bias/softcap, and deterministic generator seed. Cases 78 and 79 are
`hsk/hsv=576/512`, `nh=1`, `nr2=16`, `kv=8192`, `nb=4/256`; case 80 is
`512/512`, `nh=1`, `nr2=8`, `kv=8192`, `nb=4`. All use `nseq=4`, `run=1024`,
`free=1024`.

The source pair is preserved as
[`fattn-tile.loop-index.cuh`](historical/fattn-tile.loop-index.cuh) and
[`fattn-tile.branch.cuh`](historical/fattn-tile.branch.cuh), pinned by
`source-pair.json`. The recovered
[`branch-vs-loop-index.patch`](historical/branch-vs-loop-index.patch) removes
the `next_live` loop-index helper and adds conditional branches/`continue`
inside the KV loop. Both source files match the source-pair's tile hashes; the
branch file also matches the earlier retained candidate. This is the source
transition matching the historical description, but it does not bind the old
observation to a particular binary or prove that it was the exact source used
for the old measurement.

The preserved `exact_base2.txt`, `exact_off2.txt`, and `exact_on2.txt` logs show
the same hashes for cases 78-80 in base and on, while off differs for each.
Those are cross-capture hashes and do not establish same-binary run-to-run
nondeterminism. The source inventory records this limit. No historical raw
input bytes, executable, loaded DSO, or run environment are bound to those logs.

Run the offline integrity check with:

```bash
python3 progress/evidence/kvu19a2-gpu-followup-20261102/verify_evidence.py
```

## Commands after the build gate

First inspect the final native result (read-only):

```bash
python3 -m json.tool /mnt/raid0/llm/tmp/kvu19a2-build-row-20261102/output/RESULT.json
```

Then verify every recorded binary digest against its recorded path and inspect
the full build logs. Do not launch a GPU process until the output-capture source,
linkage/residency capture, cleanup supervisor, and separate GPU row/grant are
available and reviewed. A future per-invocation capture command is structurally:

```bash
env FA_CASE=78 FA_DUMP_DIR="$NEW_RUN_DIR" GGML_CUDA_FA_MASK_SKIP=0 \
  LD_LIBRARY_PATH="$ARM_LIBRARY_DIR" "$PINNED_HARNESS" ROCm0 exact
```

Repeat with cases `79` and `80`, and five fresh, unique output directories per
case and arm. The command is a protocol sketch, not authorization or a runnable
row launcher. The dedicated runner must call the project linkage
verifier at `/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh`
for the built executable and selected HIP library; `ldd` alone is not a valid
HIP linkage check because HIP is dlopened.

The case set, capture source, and source-pair receipt are now present. The build
result must pass the gate above. GPU execution still requires a separately published GPU row and exclusive grant, plus reviewed
runtime proof and process supervision.

## Scope

This document is preparation only. It creates no measurement claim, belief
tuple, native record, upstream issue, row, or handoff/index edit. When the exact
trigger and producer are available, the resulting native record must bind
source, executable, loaded library, case/input, repeated outputs, residency,
grant, and cleanup before any conclusion is recorded.
