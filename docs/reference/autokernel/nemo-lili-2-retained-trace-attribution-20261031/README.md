# NEMO-LILI-2 retained trace attribution

Accepted diagnostic closure for the original `NEMO-LILI-2` row in
[`autokernel-champion-aggregate.md`](../../../../handoffs/active/autokernel-champion-aggregate.md).
This is a source-bounded analysis of an existing MI210 rocprof trace. It is not a new run,
low-bit adoption decision, keep result, or deployment warrant.

## Corrected result

On the original Bolt 24GB IQ2_XXS + LiLiCorr image `gpu-20261021-58a98f088-c-nemotron-dflash`,
36 identical interior target/drafter round pairs averaged **80.4177 ms target batched verify**
plus **11.1099 ms aggregate drafter work** = **91.5276 ms summed GPU kernel duration**.
The 157 identical same-server plain target steps averaged **20.8195 ms**, giving **4.3963x**
for a paired speculative round. Target work is 87.86% of the round; 121 of 225 drafts were
accepted. Within target work, `mul_mat_q` (29.97 ms) and `mul_mat_vec_q` (29.95 ms) total
74.5% of target busy time. These are descriptive kernel-duration attributions; they do not
establish a hardware-counter causal mechanism or elapsed-time rate.

The retained trace does not separate drafter encode, cache injection, and draft-decode times.
The P arm's host/profiler idle makes its wall rate unsuitable for the GPU busy comparison.
The original GPU-target/CPU-drafter control had already aborted because shared `output.weight`
was resident in ROCm memory; see the pinned prior log below. No separate stage timing or CPU
control rerun is claimed.

## Reproduction and attribution boundary

The raw packet remains retained at `/mnt/raid0/llm/tmp/codex-ni-next-gpu-backlog-20261030/`
(its `KEEP` marker and `RETENTION.json` retain the inputs). Re-run from that packet root:

```bash
cd /mnt/raid0/llm/tmp/codex-ni-next-gpu-backlog-20261030
python3 retained_trace_attribution.py
```

The extractor reads `smoke-normal/native/trace/prof_kernel_trace.csv` and
`smoke-normal/native/run.json`, checks the full ordered kernel-name hash for each stage, then
writes `smoke-normal/retained-trace-attribution.json`. The versioned copy beside this README is
the exact extractor used (SHA256 `a53e4ed849ff168ca2dcd1f58a81cac51fef47f0a140d50ef5133dc143d3a799`);
the accepted output is saved here as [`retained-trace-attribution.json`](retained-trace-attribution.json).

Attribution uses 40 target-only SSM scan dispatches per target graph plus exact repeated ordered
sequences: 2,475 target dispatches, 579 drafter dispatches, and 1,873 plain dispatches. Counts
alone do not pass the extractor. Four negative controls refuse attribution: a same-length
single-kernel-name mutation, truncated trace, missing SSM sequence, and malformed kernel name.
The target-side sequence ends at `rms_norm_f32<1024>`; the following first
`convert_unary<float, __hip_bfloat16>` is absent from all 157 plain graphs and recurs as the
first dispatch of all 36 drafter intervals. The source call order corroborates this boundary;
this remains a boundary attribution, not a split of the drafter's three sub-stages.

The S trace has 39 target graph groups (prefill, 37 full verification graphs, final partial).
The 37th full target graph matches the target hash, but its following drafter interval is 576
dispatches rather than the repeated 579 and is excluded. The P trace has 160 groups (prefill,
first edge, 157 interior, final edge); only its 157 repeated interior steps enter the mean.
The 36 paired round mean uses the same repeated S interior groups.

Pinned source `58a98f088`: `tools/server/server-context.cpp:4203` invokes target
`llama_decode`, then `:4264` invokes `common_speculative_process`; `common/speculative.cpp`
`:1603-1616` gathers target features, `:1649-1664` calls DFlash `llama_encode`, `:1692-1702`
injects draft cache, and `:1756-1757` invokes draft decode. The target Nemotron-H graph uses
Mamba SSM (`src/models/nemotron-h.cpp:154-181`, `src/models/mamba-base.cpp:123,261`); DFlash
encoder input/fusion begins at `src/models/dflash.cpp:630-675`.

## Provenance and supersession

- **Kernel/source:** candidate image `gpu-20261021-58a98f088-c-nemotron-dflash`, source commit
  `58a98f088`; produced with `GGML_IQK=1` and HIP graph execution. This does not alter the
  frozen production kernel set or kernel store.
- **Models:** Bolt IQ2_XXS GGUF, size 22,018,326,528 bytes, edge SHA256
  `87b14243a5733ffbfa51b2e106b08a28b642a64ce0f7555f6042cd32ca5ed05f`; LiLiCorr GGUF, size
  998,242,560 bytes, edge SHA256
  `af82462c5627841489c5286b867d2c96c28eb967ba0e730f8e93396a54365c37`.
- **Image/run:** original run `gpu-20261021-58a98f088-c-nemotron-dflash`; the retained normal
  smoke completed with 23.61 GiB peak own-PID VRAM and verified teardown. It is diagnostic
  provenance, not a protocol-grade throughput measurement.
- **Raw trace:** `smoke-normal/native/trace/prof_kernel_trace.csv`, SHA256
  `63fb84108d0701071aa83eb7c13999d571b9cc2aa2a46136f4286f4917cb2fe2`.
- **Native run record:** `smoke-normal/native/run.json`, SHA256
  `5112f67f8c7b1d29ec968a6aa197741986dbe2cd07aa32cbf01565224fceb5d2`.
- **Accepted extractor:** this directory's `retained_trace_attribution.py`, SHA256
  `a53e4ed849ff168ca2dcd1f58a81cac51fef47f0a140d50ef5133dc143d3a799`.
- **Accepted output:** `retained-trace-attribution.json`, SHA256
  `b3f631efea54d90c9a589111f7b0157cb2f4f655ef0ef0c3e04fc01fbe400e32`.
- **CPU-drafter prior:** `/mnt/raid0/llm/tmp/nemotron-c2-prep-20261021/gpu_spec_dcpu.json.server.log`,
  SHA256 `958e6540a5906157bde973ebf9c3b8d83020700b2b377ded08e4f4e6abd6471d`; recorded refusal:
  `pre-allocated tensor (output.weight) in a buffer (ROCm0) that cannot run the operation (NONE)`.
- **Superseded analysis:** the prior 50us segmenter output was invalid: it reported 2,454 plain
  segments for 160 plain tokens and one target segment for 38 rounds. Preserve its raw file and
  hash in the retained packet; do not use its `COMPLETE` / `300345x` headline.

This retained pre-hook trace supplies no native `ClaimTuple`; the accepted handoff tick is a
committed conclusion (`[belief: cc]`) only. The existing native GPU serving profile source row and
`VB-AK-SERVING-PROFILE-WIRE` task were extended in the same publication to include NEMO profiler
fields. No new duplicate source or task was created.
