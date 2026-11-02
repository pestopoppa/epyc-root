# INF-07 corrected E5 placement grid — design only

Status: **not runnable; not manifests; no inference performed**. This is a
design for the W1 (`qwen36_q8_0`) and W4 (`qwen3_next_80b`) groups named by
`handoffs/active/batched-decode-measurement.md`. It applies the ratified A0–A4
definitions in Research `docs/protocols/numa-placement-measurement-protocol.md`.
The A7 files are inputs for model/prompt identity and recipe comparison only; they
do not define this successor grid.

## Scope and current production qualification

| Group | Model / artifact | Production recipe to carry into every arm | Current serving status |
|---|---|---|---|
| W1 | Qwen3.6-35B-A3B-MTP Q8_0, `/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf` | MTP self-draft `draft-mtp`, `draft_max=4`; production sampling and prompt fields copied from the selected W1 production recipe after fresh registry capture. A7 evidence has `device_draft=none`, ctx 8192, per-stream ctx 2048, ubatch 512, temp 0.3/top-p 0.95/top-k 40/min-p .05, 256 output cap and 43 pinned prompts. | The current topology declares this artifact on frontdoor with 1 full + 2 half instances, policies `interleave=all`, `interleave=0,1`, `interleave=2,3`, `--no-mmap`. Runtime serving was not independently observed for this scratch task. It is not the old defective half cpuset. Current wiring is in `epyc-orchestrator/orchestration/stack_topology.yaml` and must be freshly captured at execution. |
| W4 | Qwen3-Next-80B-A3B-Instruct Q4_K_M, `/mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Next-80B-A3B-Instruct-GGUF/Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf` | Speculation **off**: registry says SSM-hybrid has no working speculation path. Retain `kv_unified=false` (A7 manifest scar), production sampling and W4 prompt/cap values from the chosen manifest, subject to current artifact/recipe capture. Never synthesize an enabled draft recipe. | Configuration records this model as retired from the CPU `ingest_long_context` role on 2026-09-22; that role aliases the GPU architect service. Runtime serving was not independently observed for this scratch task. W4 is therefore a historical model placement experiment, not a live production recipe comparison. |

The handoff's legacy as-wired pair (`0-47,96-143`, no memory policy) is an explicit
historical defect replication. It can be retained as A0 only with
`operating_point=vintage_e5_as_wired_2026-07`; it must not be described as today's
production wiring. If the campaign requires A0 to mean *current* live production,
the owner must register a different A0 per model before execution. This changes the
meaning of the A0→A1→A2 decomposition and cannot be silently decided by this scratch
package.

## NPS4 node map and arm shapes

| NUMA node | Logical CPUs | Physical cores |
|---|---|---|
| N0 | `0-23,96-119` | `0-23` |
| N1 | `24-47,120-143` | `24-47` |
| N2 | `48-71,144-167` | `48-71` |
| N3 | `72-95,168-191` | `72-95` |

| Arm | Instances / cpuset | Memory policy | mmap | Interpretation |
|---|---|---|---|---|
| A0 | 1 × historical production cpuset `0-47,96-143` (N0+N1), 48 physical threads | `none` | mmap (historical default) | Historical defective placement control only. It violates current F1 and cannot stand in for current W1 production. |
| A1 | Same single instance and cpuset as A0 | `interleave=0,1` exactly | mmap | Policy bridge at fixed cpuset. Requires runner support for subset interleave; broad `interleave=all` is invalid. |
| A2 | 1 × `0-95` (N0–N3), 96 physical threads | `interleave=all` | mmap | Full-machine corrected single-instance shape. |
| A3 | 4 × node-aligned instances, in start-order permutations: N0 `0-23,96-119`; N1 `24-47,120-143`; N2 `48-71,144-167`; N3 `72-95,168-191`; 24 physical threads each | Per instance `membind=0`, `membind=1`, `membind=2`, `membind=3` respectively | mmap | Shared-mmap fleet; instance start order and exact GGUF VMA `numa_maps` are outcomes/evidence. |
| A4 | Byte-for-byte same four instance cpusets, thread counts, ports, `np`, and policies as A3 | Same per-instance membind | `--no-mmap` | Private-placement fleet; A4−A3 isolates mmap mode only. Record RAM cost. |

Four node-aligned instances are selected because `membind=<own node>` is only
well-defined for a single-node cpuset. A two-half fleet (`0-47,96-143` and
`48-95,144-191`) would need `interleave=0,1` / `interleave=2,3`, which is not the
protocol's A3/A4 per-instance membind design. Do not substitute it without an
explicit protocol/design amendment. The four-instance fleet is an experimental
protocol arm, not a statement that four quarters are the current serving shape.

## Cell and cache pairing scheme

For each model × arm × registered `np` rung, create a matched `cold` / `warm` pair
with the same `placement_pair_id`, model digest, prompt-set digest, serving recipe,
instance shape, and `np`. Only cache state and its prescribed preparation differ.
Each member gets its own synchronous `sync` + privileged `drop_caches` event, a
receipt, before/after cache-state sample, and post-load per-instance locality read.
For `warm`, re-warm only through the arm's own memory policy; no bare file read.
Interleave arm order within replicate blocks. Run each arm's `np=1` anchor first
after its own cache drop; any failed anchor voids that campaign. Reps, median/MAD,
locality threshold, interleave tolerance, achieved-concurrency floor, and prompt
driver sufficient to sustain target occupancy remain unfilled protocol inputs and
must be registered before generating runnable files.

Known A7 ladder coverage is **not** copied as if complete: W1 has the A7 full/half
12-cell source grid, W4 has 8 cells; neither is an A0–A4 sweep. The old 43-prompt
batch is demonstrably insufficient for T=32. Keep only `np` rungs explicitly
selected by the owner’s corrected analysis and use a driver that meets the
protocol's achieved-concurrency floor.

## Fail-closed readiness gaps

1. **A0 semantic decision:** historical defect replication vs fresh current-role
   operating point. The present production topology changed and W4 is retired.
2. **Runner gap:** unchanged `server_numa_np_sweep.py` accepts only `none` and
   `interleave=all`; it cannot launch A1 subset policies or four A3/A4 instances
   with per-instance `membind`, nor prove cache action per cell, runtime policy,
   exact model-VMA locality, or deterministic fleet launch order. A runner change
   is required before runnable manifests can exist.
3. **Recipe freeze:** W1 exact current production artifact digest, full serving
   args/environment, and sampling fields need a contemporaneous registry/source
   receipt. W4 exact source artifact and historical production recipe need a
   separate provenance pin; W4's known correct spec state is OFF.
4. **Anchor:** no admissible independent W4 anchor/band is present. W1's protocol
   example anchor applies to the MTP-on frontdoor model only if model digest, era,
   prompt regime, and recipe still match. Do not carry forward an old anchor without
   verifying those fields.
5. **Protocol parameters:** locality threshold, interleave tolerance, achieved
   concurrency floor, sufficient prompt/arrival driver, W4 prompt-regime anchor,
   replicate count and model-specific `np` ladder are unresolved in the protocol.
6. **Production/warm policy mismatch:** A0's current W1 production default is
   `--no-mmap`, while protocol A0/A3 call for production mmap defaults. The
   registered arm recipe must state whether this is a vintage decomposition or a
   current production capture; do not conflate them.

No launch command or ready-to-run manifest is emitted. The scratch launcher at
`/mnt/raid0/llm/tmp/gpu-serving-tie-in/e5-corrected/e5_corrected_launcher.py`
remains a fail-closed blocker, not an execution tool.
